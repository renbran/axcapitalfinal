from odoo import models, fields

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    description = fields.Char(string="Description")
