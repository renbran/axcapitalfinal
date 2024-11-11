from odoo import models, fields, api
from odoo.exceptions import ValidationError

class SaleOrderType(models.Model):
    _name = 'sale.order.type'
    _description = 'Sale Order Type'

    name = fields.Char(required=True, string="Sale Type")
    description = fields.Text(string="Description")
    sequence_id = fields.Many2one('ir.sequence', string="Sequence", required=True)
    active = fields.Boolean(string="Active", default=True)
    prefix = fields.Char("Prefix")

    @api.model
    def create(self, vals):
        # Ensure the sequence prefix is updated when creating the sale order type
        if 'sequence_id' in vals and 'prefix' in vals:
            sequence = self.env['ir.sequence'].browse(vals['sequence_id'])
            if sequence:
                sequence.prefix = vals['prefix']
        return super(SaleOrderType, self).create(vals)

    def write(self, vals):
        # Ensure the sequence prefix is updated when editing the sale order type
        for rec in self:
            if 'prefix' in vals:
                rec.sequence_id.prefix = vals.get('prefix', rec.prefix)
        return super(SaleOrderType, self).write(vals)

    @api.constrains('sequence_id')
    def _check_unique_sequence(self):
        for record in self:
            # Check if the sequence is already used by another sale order type
            existing_type = self.search([('sequence_id', '=', record.sequence_id.id), ('id', '!=', record.id)], limit=1)
            if existing_type:
                raise ValidationError(
                    "The sequence is already used by another Sale Order Type: %s." % existing_type.name)

    def unlink(self):
        # Check if the sale order type is used in any sale orders before deletion
        sale_order_obj = self.env['sale.order']
        for record in self:
            # Search for sale orders that reference this sale order type
            sale_orders = sale_order_obj.search([('sale_order_type_id', '=', record.id)])
            if sale_orders:
                raise ValidationError(
                    "You cannot delete the Sale Order Type '%s' because it is used in existing Sale Orders." % record.name
                )
        # Proceed with deletion if no related sale orders found
        return super(SaleOrderType, self).unlink()
