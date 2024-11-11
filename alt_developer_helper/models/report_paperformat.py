from odoo import models

class ReportPaperformat(models.Model):
    _name = "report.paperformat"
    _inherit = ["report.paperformat", "alt.external.id.computer"]