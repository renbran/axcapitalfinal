from odoo import models

class Groups(models.Model):
    _name = "res.groups"
    _inherit = ["res.groups", "alt.external.id.computer"]