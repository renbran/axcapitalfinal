from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

class PropertySale(models.Model):
    _name = 'property.sale'
    _description = 'Property Sale'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ========== Fields Definition ==========
    name = fields.Char(string='Sale Reference', default='New', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('invoiced', 'Invoiced'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    # Customer Information
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', 
                                default=lambda self: self.env.company.currency_id)
    start_date = fields.Date(string='Start Date', required=True)
    sale_date = fields.Date(string='Sale Date', default=fields.Date.today)
    
    # Property Information
    property_id = fields.Many2one('property.property', string='Property', required=True)
    seller_id = fields.Many2one('res.partner', string='Broker/Seller', 
                               domain=[('is_company','=',True)])
    
    # Financial Fields
    property_value = fields.Monetary(string='Property Value', compute='_compute_property_value', 
                                   store=True, currency_field='currency_id')
    total_selling_price = fields.Monetary(string='Total Selling Price', compute='_compute_total_selling_price',
                                        store=True, currency_field='currency_id')
    down_payment_percentage = fields.Float(string='Down Payment (%)', default=20.0)
    down_payment = fields.Monetary(string='Down Payment', compute='_compute_down_payment',
                                 store=True, currency_field='currency_id')
    dld_fee = fields.Monetary(string='DLD Fee', compute='_compute_dld_fee',
                            store=True, currency_field='currency_id')
    admin_fee = fields.Monetary(string='Admin Fee', default=1.0, currency_field='currency_id')
    remaining_balance = fields.Monetary(string='Remaining Balance', compute='_compute_remaining_balance',
                                      store=True, currency_field='currency_id')
    
    # Payment Plan
    no_of_installments = fields.Integer(string='No. of Installments', default=1)
    amount_per_installment = fields.Monetary(string='Amount Per Installment', 
                                           compute='_compute_amount_per_installment',
                                           store=True, currency_field='currency_id')
    payment_progress = fields.Float(string='Payment Progress %', compute='_compute_payment_progress',
                                  store=True, group_operator="avg")
    
    # Broker Commission
    broker_commission_percentage = fields.Float(string='Broker Commission %', default=5.0)
    broker_commission_invoice_ids = fields.One2many('broker.commission.invoice', 'property_sale_id',
                                                  string='Broker Commission Invoices')
    
    # Installment Lines
    property_sale_line_ids = fields.One2many('property.sale.line', 'property_sale_id',
                                           string='Installment Lines')

    # ========== Compute Methods ==========
    @api.depends('property_id')
    def _compute_property_value(self):
        for record in self:
            record.property_value = record.property_id.property_price if record.property_id else 0.0

    @api.depends('property_value', 'dld_fee', 'admin_fee')
    def _compute_total_selling_price(self):
        for record in self:
            record.total_selling_price = record.property_value + record.dld_fee + record.admin_fee

    @api.depends('property_value', 'down_payment_percentage')
    def _compute_down_payment(self):
        for record in self:
            record.down_payment = (record.down_payment_percentage / 100) * record.property_value

    @api.depends('property_value')
    def _compute_dld_fee(self):
        for record in self:
            record.dld_fee = record.property_value * 0.04  # 4% of property value

    @api.depends('total_selling_price', 'down_payment')
    def _compute_remaining_balance(self):
        for record in self:
            record.remaining_balance = record.total_selling_price - record.down_payment

    @api.depends('remaining_balance', 'no_of_installments')
    def _compute_amount_per_installment(self):
        for record in self:
            if record.no_of_installments > 0:
                record.amount_per_installment = record.remaining_balance / record.no_of_installments
            else:
                record.amount_per_installment = 0.0

    @api.depends('property_sale_line_ids.collection_status')
    def _compute_payment_progress(self):
        for record in self:
            total_lines = record.property_sale_line_ids
            if total_lines:
                total_amount = sum(total_lines.mapped('capital_repayment'))
                paid_amount = sum(total_lines.filtered(
                    lambda l: l.collection_status == 'paid'
                ).mapped('capital_repayment'))
                record.payment_progress = (paid_amount / total_amount) * 100 if total_amount else 0
            else:
                record.payment_progress = 0.0

    # ========== Action Methods ==========
    def action_confirm(self):
        """Confirm the property sale and create installment lines"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only draft sales can be confirmed.'))
            
            # Create installment lines
            record._create_emi_lines()
            
            # Update property status
            record.property_id.write({
                'state': 'sold',
                'partner_id': record.partner_id.id
            })

    def action_generate_broker_invoice(self):
        if not self.seller_id:
            raise UserError(_('Please specify a broker first'))
        if not self.broker_commission_percentage:
            raise UserError(_('Please set the broker commission percentage'))
        
        commission_amount = (self.broker_commission_percentage / 100) * self.property_value
        
        commission = self.env['broker.commission.invoice'].create({
            'property_sale_id': self.id,
            'seller_id': self.seller_id.id,
            'commission_percentage': self.broker_commission_percentage,
            'commission_amount': commission_amount,
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Broker Commission',
            'res_model': 'broker.commission.invoice',
            'res_id': commission.id,
            'view_mode': 'form',
            'target': 'current',
        }
    def action_view_invoices(self):
        """View all invoices related to this sale"""
        self.ensure_one()
        invoice_ids = self.property_sale_line_ids.mapped('invoice_id')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Invoices',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', invoice_ids.ids)],
            'context': {'create': False},
        }

    def action_generate_all_invoices(self):
        """Generate invoices for all unpaid installments"""
        self.ensure_one()
        unpaid_lines = self.property_sale_line_ids.filtered(
            lambda l: l.collection_status == 'unpaid' and not l.invoice_id
        )
        
        if not unpaid_lines:
            raise UserError(_('No unpaid installments found for invoicing.'))
        
        # Group lines by due date and create invoices
        invoices = self.env['account.move']
        for due_date, lines in unpaid_lines.groupby('collection_date'):
            invoice_lines = [(0, 0, {
                'name': f"{line.line_type} - Installment {line.serial_number}",
                'quantity': 1,
                'price_unit': line.capital_repayment,
                'account_id': self.property_id.revenue_account_id.id,
            }) for line in lines]
            
            invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': self.partner_id.id,
                'invoice_date': fields.Date.context_today(self),
                'invoice_date_due': due_date,
                'invoice_line_ids': invoice_lines,
                'property_order_id': self.id,
            })
            
            lines.write({'invoice_id': invoice.id})
            invoices += invoice
        
        # Update state if all lines are invoiced
        if all(line.invoice_id for line in self.property_sale_line_ids):
            self.state = 'invoiced'
        
        # Show created invoices
        if len(invoices) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': invoices.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Generated Invoices',
                'res_model': 'account.move',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', invoices.ids)],
            }

    def action_cancel(self):
        """Cancel the property sale"""
        for record in self:
            if record.state == 'cancelled':
                raise UserError(_('This sale is already cancelled.'))
            
            # Check for active invoices
            active_invoices = self.env['account.move'].search([
                ('property_order_id', '=', record.id),
                ('state', 'not in', ['cancel', 'draft'])
            ])
            if active_invoices:
                raise UserError(_(
                    'Cannot cancel sale with active invoices. Please cancel invoices first: %s'
                ) % ', '.join(active_invoices.mapped('name')))
            
            # Reset property status if this was the active sale
            if record.property_id.active_sale_id.id == record.id:
                record.property_id.write({
                    'state': 'available',
                    'partner_id': False
                })
            
            # Reset installment lines
            record.property_sale_line_ids.write({
                'collection_status': 'unpaid',
                'invoice_id': False
            })
            
            record.state = 'cancelled'

    def action_draft(self):
        """Reset sale to draft"""
        self.ensure_one()
        if self.state == 'cancelled':
            self.state = 'draft'
        else:
            raise UserError(_('Only cancelled sales can be reset to draft.'))

    # ========== Private Methods ==========
    def _create_emi_lines(self):
        """Create installment lines for the payment plan"""
        self.ensure_one()
        if not self.start_date:
            raise UserError(_('Start date is required to create payment schedule.'))
        
        # Clear existing lines
        self.property_sale_line_ids.unlink()

        # Create downpayment line
        self.env['property.sale.line'].create({
            'property_sale_id': self.id,
            'serial_number': 0,
            'capital_repayment': self.down_payment,
            'remaining_capital': self.down_payment,
            'collection_date': self.start_date,
            'line_type': 'downpayment'
        })

        # Create DLD fee line
        self.env['property.sale.line'].create({
            'property_sale_id': self.id,
            'serial_number': 0,
            'capital_repayment': self.dld_fee,
            'remaining_capital': self.dld_fee,
            'collection_date': self.start_date,
            'line_type': 'dld_fee'
        })

        # Create admin fee line
        self.env['property.sale.line'].create({
            'property_sale_id': self.id,
            'serial_number': 0,
            'capital_repayment': self.admin_fee,
            'remaining_capital': self.admin_fee,
            'collection_date': self.start_date,
            'line_type': 'admin_fee'
        })

        # Create EMI lines
        for i in range(1, self.no_of_installments + 1):
            due_date = self._calculate_due_date(self.start_date, i)
            self.env['property.sale.line'].create({
                'property_sale_id': self.id,
                'serial_number': i,
                'capital_repayment': self.amount_per_installment,
                'remaining_capital': self.amount_per_installment,
                'collection_date': due_date,
                'line_type': 'emi'
            })

    def _calculate_due_date(self, start_date, installment_number):
        """Calculate due date for installment"""
        try:
            due_date = start_date + relativedelta(months=installment_number)
            if due_date.month != (start_date + relativedelta(months=installment_number)).month:
                due_date = (start_date + relativedelta(months=installment_number)).replace(day=1) - relativedelta(days=1)
            return due_date
        except Exception as e:
            raise UserError(_('Error calculating due date: %s') % str(e))

    # ========== Overrides ==========
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('property.sale') or 'New'
        return super().create(vals)

    def write(self, vals):
        """Handle state changes and property updates"""
        res = super().write(vals)
        
        if 'state' in vals or 'partner_id' in vals:
            for record in self:
                if record.property_id:
                    if vals.get('state') == 'confirm' and record.property_id.state != 'sold':
                        record.property_id.write({
                            'state': 'sold',
                            'partner_id': record.partner_id.id
                        })
                    elif vals.get('state') == 'cancelled' and record.property_id.state == 'sold':
                        # Only reset if this was the active sale
                        if not self.search([
                            ('property_id', '=', record.property_id.id),
                            ('state', '=', 'confirm'),
                            ('id', '!=', record.id)
                        ]):
                            record.property_id.write({
                                'state': 'available',
                                'partner_id': False
                            })
        return res


class PropertySaleLine(models.Model):
    _name = 'property.sale.line'
    _description = 'Property Sale Installment Line'
    _order = 'collection_date, serial_number'

    property_sale_id = fields.Many2one('property.sale', string='Property Sale', required=True, ondelete='cascade')
    serial_number = fields.Integer(string='Installment #')
    line_type = fields.Selection([
        ('downpayment', 'Down Payment'),
        ('dld_fee', 'DLD Fee'),
        ('admin_fee', 'Admin Fee'),
        ('emi', 'EMI')
    ], string='Type', required=True)
    capital_repayment = fields.Monetary(string='Amount', currency_field='currency_id')
    remaining_capital = fields.Monetary(string='Remaining', currency_field='currency_id')
    collection_date = fields.Date(string='Due Date', required=True)
    collection_status = fields.Selection([
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid')
    ], string='Status', default='unpaid')
    invoice_id = fields.Many2one('account.move', string='Invoice')
    currency_id = fields.Many2one(related='property_sale_id.currency_id', store=True)

    def write(self, vals):
        """Update payment progress when status changes"""
        res = super().write(vals)
        if 'collection_status' in vals:
            for line in self:
                line.property_sale_id._compute_payment_progress()
                if line.property_sale_id.property_id:
                    line.property_sale_id.property_id._compute_payment_progress()
        return res