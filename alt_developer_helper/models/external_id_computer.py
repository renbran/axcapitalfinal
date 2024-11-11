from odoo import fields, models

class ExternalIDComputer(models.Model):
    _name = "alt.external.id.computer"
    _description = "External ID Computer"
    
    xml_id = fields.Char('External ID', compute="_compute_xml_id")

    def _compute_xml_id(self):
        for rec in self:
            rec.xml_id = rec.get_external_id()[rec.id]