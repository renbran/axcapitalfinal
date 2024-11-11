from odoo import api, models, fields


class MailMessage(models.Model):
    _inherit = 'mail.message'

    external_messenger_id = fields.Char(help='External id for messenger', default='')
    document_message_id = fields.Many2one('mail.message',help="Relates a message that was duplicated from the document")