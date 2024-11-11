from odoo import models

class IrUiMenu(models.Model):
    _name = "ir.ui.menu"
    _inherit = ["ir.ui.menu", "alt.external.id.computer"]