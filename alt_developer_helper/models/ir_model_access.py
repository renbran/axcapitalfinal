from odoo import models

class IrModelAccess(models.Model):
    _name = "ir.model.access"
    _inherit = ["ir.model.access", "alt.external.id.computer"]
