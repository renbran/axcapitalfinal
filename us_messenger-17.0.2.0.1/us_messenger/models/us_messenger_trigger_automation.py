import logging
from odoo import SUPERUSER_ID
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

ODOO_CHANNEL_TYPES = ["chat", "livechat", "group"]


class UsMessengerTriggerAutomation(models.Model):
    _name = "us.messenger.trigger.automation"
    _inherit = ["us.messenger.trigger.mixin", "us.messenger.trigger.mixin.actions"]
    _description = "DB Trigger"
    _messenger_handler = "handle_db"

    automation_id = fields.Many2one(
        "base.automation", delegate=True, required=True, ondelete="cascade"
    )
    messenger_task_id = fields.Many2one("us.messenger.task", name="Task", ondelete="cascade")

    project_id = fields.Many2one(
        "us.messenger.project", related="messenger_task_id.project_id", readonly=True
    )

    def unlink(self):
        actions = self.automation_id.mapped("action_server_ids")
        automations = self.mapped("automation_id")
        super().unlink()
        automations.unlink()
        actions.unlink()
        return True

    def start(self, records):
        if self.active:
            if not self.messenger_task_id:
                # workaround for old deployments
                _logger.warning(
                    "Task was deleted, but there is still base.automation record for it: %s"
                    % self.automation_id
                )
                return
            if self.is_record_mail_message(records):
                if records and records[0]._name == 'mail.message':
                    for message in records:
                        channel = self.env["discuss.channel"].browse(message.res_id)
                        values = []
                        for channel_member in channel.channel_member_ids:
                            values.append((4, channel_member.partner_id.id))
                        author_message = (4, message.author_id.id)
                        if author_message in values:
                            values.remove(author_message)
                        message.write({'partner_ids': values})
                self.messenger_task_id.start(self, args=(records,), with_delay=True)

    def is_message_from_operators(self, records):
        # Перевірка повідомлення від оператора чи від користувача мессенджера
        # Якщо повідомлення від користувача тоді повертає False
        if records._name == "mail.message":
            return records.author_id.type_messenger == 'none' and records.author_id.id != 2  # OdooBot
        else:
            return True

    def is_record_mail_message(self, records):
        odoobot_id = self.env.user.browse(SUPERUSER_ID).partner_id.id
        # Перевірка чи тип каналу не в ODOO_CHANNEL_TYPES, і чи бот прив'язаний до каналу, якщо не прив'язаний повертаємо False
        if records._name == "mail.message":
            channel = self.env['discuss.channel'].search([('id', '=', records.res_id)])
            link = self.env['us.messenger.link'].search(
                [('ref2', '=', records.res_id), ('model', '=', 'discuss.channel'), ('bot_id', '=', self.project_id.id)])
            return channel and channel.channel_type not in ODOO_CHANNEL_TYPES and link and records.author_id.id != odoobot_id
        return True

    def get_code(self):
        return (
                """
    env["us.messenger.trigger.automation"].browse(%s).sudo().start(records)
    """
                % self.id
        )

    @api.onchange("model_id")
    def onchange_model_id(self):
        self.model_name = self.model_id.model

    # @api.onchange("trigger")
    # def onchange_trigger(self):
    #     if self.trigger in ["on_create", "on_create_or_write", "on_unlink"]:
    #         self.filter_pre_domain = (
    #             self.trg_date_id
    #         ) = self.trg_date_range = self.trg_date_range_type = False
    #     elif self.trigger in ["on_write", "on_create_or_write"]:
    #         self.trg_date_id = self.trg_date_range = self.trg_date_range_type = False
    #     elif self.trigger == "on_time":
    #         self.filter_pre_domain = False
