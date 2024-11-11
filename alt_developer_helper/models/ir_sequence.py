from odoo import models

class IrSequence(models.Model):
    _name = "ir.sequence"
    _inherit = ["ir.sequence", "alt.external.id.computer"]