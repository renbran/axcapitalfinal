# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions
     

class UniquePartner(models.Model):
    _inherit = 'res.partner'

    _sql_constraints = [('res_partner_name_uniqu', 'unique(name)', 'Name of partner already exists!')]
     
    @api.onchange('name')
    def _compute_maj_par(self):
        """Convert the partner name to uppercase."""
        self.name = self.name.upper() if self.name else False
