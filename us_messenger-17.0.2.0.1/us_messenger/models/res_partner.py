from odoo import api, models, fields
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    type_messenger = fields.Selection(string='Type Messenger',
                                      selection=[('none', 'None')],
                                      default='none')

    @api.ondelete(at_uninstall=False)
    def _unlink_partner(self):
        for record in self:
            if record.type_messenger != 'none':
                raise UserError('Partner cannot be deleted, only archived')

    def action_archive(self):
        for record in self:
            parent = record.parent_id
            result_achive = None
            if parent and record.type_messenger != 'none':
                if len(parent.child_ids) == 1:
                    parent.action_archive()
                member = self.env['discuss.channel.member'].sudo().search([('partner_id', '=', record.id)])
                channels_records = self.env['discuss.channel'].sudo().search([('channel_member_ids', 'in', member.id)])

                for channel in channels_records:
                    channel.action_archive()

                # archive us_messenger_partner
                # messenger_partners = self.env['us.messenger.partner'].search([('partner_id','=',record.id)])
                # for messenger_partner in messenger_partners:
                #     print(messenger_partner)
                #     messenger_partner.action_archive()

                result_achive = super(ResPartner, self).action_archive()

            elif record.type_messenger == 'none' and record.active:
                childs = self.env['res.partner'].sudo().search([('parent_id', '=', record.id),('type_messenger','!=','none'),('active','=',True)])
                result_achive = super(ResPartner, self).action_archive()
                for child in childs:
                    child.action_archive()
        return result_achive

    def action_unarchive(self):
        for record in self:
            parent = record.parent_id
            result_unachive = None
            if parent and record.type_messenger != 'none':
                childs = self.env['res.partner'].sudo().search([('parent_id','=',parent.id),('active','=',False)])
                if len(childs) == 1:
                    parent.action_unarchive()
                member = self.env['discuss.channel.member'].sudo().search([('partner_id', '=', record.id)])
                channels_records = self.env['discuss.channel'].sudo().search([('channel_member_ids', 'in', member.id)])

                for channel in channels_records:
                    channel.action_unarchive()
                result_unachive = super(ResPartner, self).action_unarchive()

            elif record.type_messenger == 'none' and not record.active:
                childs = self.env['res.partner'].sudo().search([('parent_id', '=', record.id),('type_messenger','!=','none'),('active','=',False)])
                result_unachive = super(ResPartner, self).action_unarchive()
                for child in childs:
                    child.action_unarchive()

            member = self.env['discuss.channel.member'].sudo().search([('partner_id', '=', record.id)])
            channels_records = self.env['discuss.channel'].sudo().search([('channel_member_ids', 'in', member.ids),('active','=',False)])
            for channel in channels_records:
                channel.action_unarchive()
        return result_unachive
