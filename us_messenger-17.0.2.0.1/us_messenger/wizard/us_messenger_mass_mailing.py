from odoo import api, models, fields


class UsMessengerMassMailing(models.Model):
    _name = "us.messenger.mass.mailing"
    _description = "Send message to all bot subscribers"

    msg = fields.Text("Message")
    image = fields.Image("Image")

    project_id = fields.Many2one("us.messenger.project")
    url = fields.Char("Image url")
    bot_name = fields.Char('Bot Name', related='project_id.name')
    bot_type = fields.Char('Bot type')
    rich_media = fields.Boolean("Carousel", default=False)

    def action_open_send_to_everyone(self):
        context = dict(self.env.context)
        context['form_view_initial_mode'] = 'readonly'
        return {
            'type': 'ir.actions.act_window',
            'name': 'Send to everyone Form',
            'res_model': 'us.messenger.mass.mailing',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'current',
            'res_id': self.id,
            'context': context,
        }


