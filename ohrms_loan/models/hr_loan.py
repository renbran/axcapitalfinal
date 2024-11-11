# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class HrLoan(models.Model):
    _name = 'hr.loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Loan Request"

    name = fields.Char(string="Loan Reference", readonly=True, copy=False,
                       default=lambda self: _('New'))
    date = fields.Date(string="Date", default=fields.Date.today(), readonly=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True)
    department_id = fields.Many2one('hr.department', related="employee_id.department_id", readonly=True)
    job_position = fields.Many2one('hr.job', related="employee_id.job_id", readonly=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id')
    loan_type_id = fields.Many2one('loan.type', string='Loan Type', required=True)
    loan_amount = fields.Float(string="Loan Amount", required=True)
    disbursal_amount = fields.Float(string="Disbursal Amount")
    tenure = fields.Integer(string="Tenure (Months)", default=1)
    interest_rate = fields.Float(string="Interest Rate (%)")
    installment = fields.Integer(string="No. of Installments", compute='_compute_installment', store=True)
    payment_date = fields.Date(string="Payment Start Date", required=True, default=fields.Date.today())
    loan_lines = fields.One2many('hr.loan.line', 'loan_id', string="Loan Lines", index=True)
    total_amount = fields.Float(string="Total Amount", compute='_compute_total_amount', store=True)
    balance_amount = fields.Float(string="Balance Amount", compute='_compute_total_amount', store=True)
    total_paid_amount = fields.Float(string="Total Paid Amount", compute='_compute_total_amount', store=True)
    
    documents_ids = fields.Many2many('loan.documents', string="Proofs")
    journal_id = fields.Many2one('account.journal', string="Journal", domain="[('type', '=', 'purchase'), ('company_id', '=', company_id)]")
    debit_account_id = fields.Many2one('account.account', string="Debit account")
    credit_account_id = fields.Many2one('account.account', string="Credit account")
    reject_reason = fields.Text(string="Reject Reason")
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('waiting_approval', 'Waiting Approval'),
        ('approved', 'Approved'),
        ('disbursed', 'Disbursed'),
        ('rejected', 'Rejected'),
        ('closed', 'Closed')
    ], string="State", default='draft', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.loan.seq') or _('New')
        
        # Check for existing active loans
        existing_loan = self.env['hr.loan'].search([
            ('employee_id', '=', vals.get('employee_id')),
            ('state', 'not in', ('draft', 'rejected', 'closed'))
        ], limit=1)
        
        if existing_loan:
            raise UserError(_('The employee has already an ongoing loan.'))
        
        return super(HrLoan, self).create(vals)

    @api.depends('loan_amount', 'tenure')
    def _compute_installment(self):
        for loan in self:
            loan.installment = loan.tenure

    @api.onchange('loan_type_id')
    def _onchange_loan_type_id(self):
        if self.loan_type_id:
            self.loan_amount = self.loan_type_id.loan_amount
            self.disbursal_amount = self.loan_type_id.disbursal_amount
            self.tenure = self.loan_type_id.tenure
            self.interest_rate = self.loan_type_id.interest_rate
            self.documents_ids = self.loan_type_id.documents_ids

    @api.depends('loan_lines.amount', 'loan_lines.paid')
    def _compute_total_amount(self):
        for loan in self:
            total_paid = sum(line.amount for line in loan.loan_lines if line.paid)
            loan.total_amount = sum(line.amount for line in loan.loan_lines)
            loan.balance_amount = loan.total_amount - total_paid
            loan.total_paid_amount = total_paid

    def action_confirm(self):
        self.write({'state': 'confirmed'})
        # Add email sending logic here

    def action_submit_for_approval(self):
        if not self.loan_lines:
            raise UserError(_("Please compute the loan lines before submitting for approval."))
        self.write({'state': 'waiting_approval'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_disburse(self):
        self.ensure_one()
        if not self.journal_id or not self.debit_account_id or not self.credit_account_id:
            raise UserError(_("Please set the journal and accounts for disbursement."))
        
        move_vals = {
            'journal_id': self.journal_id.id,
            'date': fields.Date.today(),
            'ref': f'Loan Disbursement - {self.name}',
            'line_ids': [
                (0, 0, {
                    'name': f'Loan Disbursement to {self.employee_id.name}',
                    'account_id': self.debit_account_id.id,
                    'debit': self.disbursal_amount,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'name': f'Loan Disbursement to {self.employee_id.name}',
                    'account_id': self.credit_account_id.id,
                    'debit': 0.0,
                    'credit': self.disbursal_amount,
                })
            ]
        }
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        self.write({'state': 'disbursed'})

    def action_reject(self):
        return {
            'name': _('Reject Loan'),
            'view_mode': 'form',
            'res_model': 'loan.reject.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'default_loan_id': self.id}
        }

    def action_close_loan(self):
        if any(not line.paid for line in self.loan_lines):
            raise UserError(_("Cannot close the loan. There are unpaid installments."))
        self.write({'state': 'closed'})

    def compute_loan_line(self):
        self.ensure_one()
        self.loan_lines.unlink()
        payment_date = self.payment_date
        amount_per_installment = self.loan_amount / self.tenure
        interest_per_installment = (self.loan_amount * (self.interest_rate / 100)) / self.tenure
        total_per_installment = amount_per_installment + interest_per_installment

        for i in range(1, self.tenure + 1):
            self.env['hr.loan.line'].create({
                'loan_id': self.id,
                'date': payment_date,
                'amount': amount_per_installment,
                'interest': interest_per_installment,
                'total_amount': total_per_installment,
                'sequence': i,
            })
            payment_date = payment_date + relativedelta(months=1)
        
        self._compute_total_amount()
        return True

class HrLoanLine(models.Model):
    _name = 'hr.loan.line'
    _description = 'Loan Installment Line'

    loan_id = fields.Many2one('hr.loan', string='Loan', required=True, ondelete='cascade')
    date = fields.Date(string='Payment Date', required=True)
    amount = fields.Float(string='Principal Amount', required=True)
    interest = fields.Float(string='Interest Amount', required=True)
    total_amount = fields.Float(string='Total Amount', compute='_compute_total_amount', store=True)
    paid = fields.Boolean(string='Paid', default=False)
    sequence = fields.Integer(string='Sequence', help='Installment number')

    @api.depends('amount', 'interest')
    def _compute_total_amount(self):
        for line in self:
            line.total_amount = line.amount + line.interest