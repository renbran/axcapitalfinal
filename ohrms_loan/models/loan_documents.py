from odoo import models, fields

class LoanDocuments(models.Model):
    _name = 'loan.documents'
    _description = 'Loan Documents'

    # Define your fields here
    name = fields.Char(string='Name')
    employee_id = fields.Many2one('hr.employee', string='Employee')