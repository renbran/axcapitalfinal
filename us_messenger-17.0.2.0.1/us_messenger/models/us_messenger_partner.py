from odoo import api, fields, models, tools
from odoo.exceptions import ValidationError

import logging

from .ir_logging import LOG_DEBUG

_logger = logging.getLogger(__name__)


class UsMessengerPartner(models.Model):
    _name = 'us.messenger.partner'
    _description = 'Union res_partner and us_messenger_link'
    _order = 'id'

    partner_id = fields.Many2one('res.partner', ondelete='cascade', required=True)
    bot_id = fields.Many2one('us.messenger.project', ondelete='cascade', required=True)
    external_id = fields.Char('ID User', required=True)
    state_user = fields.Char('State', default='None')
    name = fields.Char('Name', related="partner_id.name")

    def set_user(self, partner_id, bot_id, external_id):
        ''' Create new record'''
        existing = self._search_partner(bot_id, external_id)
        if existing:
            return existing
        vals = {'partner_id': partner_id, 'bot_id': bot_id, 'external_id': external_id}
        return self.create(vals)

    def _search_partner(self, bot_id, external_id):
        domain = [('bot_id', '=', bot_id), ('external_id', '=', external_id)]
        return self.search(domain)

    def get_partner(self, bot_id, external_id):
        users = self._search_partner(bot_id, external_id)
        if len(users) > 1:
            raise ValidationError(
                (
                    "Us_messenger_partner get_partner found multiple links"
                )
            )
        return users.odoo if users else None

    def get_partner_with_create(self, bot_id, external_id, callback_func=None, callback_kwargs=None):
        ''' If not exist create one'''
        links = self.get_partner(bot_id, external_id)
        if not links and callback_func and callback_kwargs:
            vals = callback_func(**callback_kwargs)
            vals['type_messenger'] = self.env['us.messenger.project'].browse(bot_id).eval_context_ids.name
            partner = self.env["res.partner"].sudo().create(vals)
            list_name = partner.name.split('[')
            list_name.pop()
            name = ''.join(list_name)
            parent = self.env['res.partner'].sudo().create({'name': name})
            partner.parent_id = parent.id
            self.set_user(partner.id, bot_id, external_id)
            return partner
        return links

    @property
    def odoo(self):
        self.ensure_one()
        return self.env['res.partner'].browse(self.partner_id).id

    def set_state(self, partner_id, bot_id, state):
        user = self.search([('bot_id', '=', bot_id), ('partner_id', '=', partner_id)])
        # if not user:
        #     return
        current_state = user.state_user
        if (current_state == 'phone' or current_state == 'mail') and state == 'None':
            child_partner = self.env['res.partner'].browse(partner_id)
            is_deleting_partner = False
            ch_phone = child_partner.phone
            ch_email = child_partner.email
            if current_state == 'phone':
                parent = self.env['res.partner'].search(
                    [('phone', '=', ch_phone), ('type_messenger', '=', 'none')])
            else:
                parent = self.env['res.partner'].search(
                    [('email', '=', ch_email),
                     ('type_messenger', '=', 'none')])
            if parent and len(parent) > 1:
                count_child_max = -1
                parent_result = None
                parents_equal_child = []
                for p in parent:
                    num = 0
                    for c in p.child_ids:
                        if c.type_messenger != 'none':
                            num += 1
                    if count_child_max < num:
                        count_child_max = num
                        parent_result = p
                        parents_equal_child = []
                    elif count_child_max == num:
                        parents_equal_child.append(p)

                if len(parents_equal_child) == 0:
                    parent = parent_result
                else:
                    ids = [parent_result.id] + [p.id for p in parents_equal_child]
                    parent = self.env['res.partner'].search(
                        [('id', 'in', ids)],
                        order='create_date desc'
                    )[0]

            if not parent and not child_partner.parent_id:
                list_name = child_partner.name.split('[')
                list_name.pop()
                name = ' '.join(list_name)
                parent = self.env['res.partner'].create({'name': name, 'phone': ch_phone, 'email': ch_email})
            elif not parent and child_partner.parent_id:
                parent = child_partner.parent_id
                if not parent.email:
                    parent.email = ch_email
                if not parent.phone:
                    parent.phone = ch_phone
            else:
                if child_partner.parent_id and parent.id != child_partner.parent_id.id and parent.active:
                    is_deleting_partner = True
                    new_parent = parent
                    old_parent = child_partner.parent_id
                    all = self.env['res.partner'].search([('parent_id', '=', old_parent.id)])
                    model_name = self.env['us.messenger.project.param'].search([
                        ('project_id', '=', bot_id), ('key', '=', 'CHAT_MODEL')]).value
                    records = self.env[model_name].search([('partner_id', '=', old_parent.id)])
                    for record in records:
                        record.write({'partner_id': new_parent.id})

                    for partner in all:
                        partner.parent_id = new_parent.id

                    old_parent.action_archive()

            if not parent.email and current_state == 'mail':
                parent.email = ch_email
            if not is_deleting_partner:
                child_partner.parent_id = parent.id
        user.state_user = state
        return True

    def get_state(self, partner_id, bot_id):
        user = self.search([('bot_id', '=', bot_id), ('partner_id', '=', partner_id)])
        return user.state_user

    def _get_eval_context(self):
        return {
            'get_partner': self.get_partner_with_create,
            'get_state': self.get_state,
            'set_state': self.set_state,
        }

