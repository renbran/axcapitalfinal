from odoo import fields, models


class UsMessengerTriggerButton(models.Model):

    _name = "us.messenger.trigger.button"
    _inherit = "us.messenger.trigger.mixin"
    _description = "Manual Trigger"
    _messenger_handler = "handle_button"

    name = fields.Char("Description")
    messenger_task_id = fields.Many2one("us.messenger.task", name="Task", ondelete="cascade")
    project_id = fields.Many2one(
        "us.messenger.project", related="messenger_task_id.project_id", readonly=True
    )

    # delete_my_code
    type_button = fields.Selection(string='Button type',
                                   selection=[('start', 'Start Button'), ('remove', 'Remove Webhook')])
    active = fields.Boolean(default=True)

    def start_button(self):
        job, _result = self.start(raise_on_error=False)

        # змінює поле в якому була натиснута кнопка
        return {
            "name": "Job triggered by clicking Button",
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "us.messenger.job",
            "res_id": job.id,
            "target": "self",
        }

    def start(self, raise_on_error=True):
        return self.messenger_task_id.start(self, force=True, raise_on_error=raise_on_error)
