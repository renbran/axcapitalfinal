# -*- coding: utf-8 -*-
################################################################################
#
#    Kolpolok Ltd. (https://www.kolpolok.com)
#    Author: Kaushik Ahmed Apu, Aqil Mahmud, Zarin Tasnim(<https://www.kolpolok.com>)
#
################################################################################
from odoo import fields, models


from odoo import models, fields

class PropertyFacility(models.Model):
    _name = 'property.facility'
    _description = 'Property Facility'

    name = fields.Char(string='Facility Name')
    status = fields.Selection([
        ('available', 'Available'),
        ('unavailable', 'Unavailable'),
        ('maintenance', 'Under Maintenance'),
    ], string='Status', default='available')

