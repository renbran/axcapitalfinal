
from odoo import models

from .discuss_channel import ODOO_CHANNEL_TYPES


class Partners(models.Model):
    _inherit = "res.partner"

    def _get_channels_as_member(self):
        channels = super()._get_channels_as_member()
        channels |= self.env["discuss.channel"].search(
            [
                ("channel_type", "not in", ODOO_CHANNEL_TYPES),
                # ('channel_last_seen_partner_ids', 'in', self.env['discuss.channel.partner'].sudo()._search([
                #    ('partner_id', '=', self.id),
                #    ('is_pinned', '=', True),
                # ])),
            ]
        )
        return channels
