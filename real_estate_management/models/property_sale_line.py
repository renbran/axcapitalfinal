from odoo import models, fields

class PropertySaleLine(models.Model):
    _name = 'property.sale.line'
    _description = 'Property Sale Installment Line'

    property_sale_id = fields.Many2one('property.sale', string="Property Sale", required=True)
    serial_number = fields.Integer(string="Installment No.", required=True)
    capital_repayment = fields.Monetary(string="Capital Repayment", required=True, currency_field='currency_id')
    remaining_capital = fields.Monetary(string="Remaining Capital", required=True, currency_field='currency_id')
    collection_status = fields.Selection([('pending', 'Pending'), ('paid', 'Paid')], string="Status", default="pending")
    collection_amount = fields.Monetary(string="Collection Amount", required=False, currency_field='currency_id')
    collection_date = fields.Date(string="Collection Date", required=True)
    currency_id = fields.Many2one('res.currency', string="Currency", related='property_sale_id.currency_id', store=True, readonly=True)