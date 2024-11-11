from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sale_order_type_id = fields.Many2one('sale.order.type', string="Sale Type")

    @api.model
    def create(self, vals):
        # Check if sale_order_type_id is provided in vals
        if vals.get('sale_order_type_id'):
            sale_type = self.env['sale.order.type'].browse(vals['sale_order_type_id'])
            # Ensure that sale_type has a valid sequence
            if sale_type.sequence_id:
                # Generate the next sequence number for the sale order name
                vals['name'] = sale_type.sequence_id.next_by_id()
            else:
                # Raise an exception if no sequence is associated with the sale type
                raise ValueError("The selected Sale Order Type does not have a sequence associated with it.")
        return super(SaleOrder, self).create(vals)
