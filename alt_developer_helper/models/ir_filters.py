from odoo import models

class IrFilters(models.Model):
    _name = "ir.filters"
    _inherit = ["ir.filters", "alt.external.id.computer"]