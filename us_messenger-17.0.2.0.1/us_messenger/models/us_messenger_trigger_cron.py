from odoo import api, fields, models
from odoo.tools.translate import _


class UsMessengerTriggerCron(models.Model):

    _name = "us.messenger.trigger.cron"
    _inherit = [
        "us.messenger.trigger.mixin",
        "us.messenger.trigger.mixin.model_id",
        "us.messenger.trigger.mixin.actions",
    ]
    _description = "Cron Trigger"
    _messenger_handler = "handle_cron"

    messenger_task_id = fields.Many2one("us.messenger.task", name="Task", ondelete="cascade")
    project_id = fields.Many2one(
        "us.messenger.project", related="messenger_task_id.project_id", readonly=True
    )
    cron_id = fields.Many2one(
        "ir.cron", delegate=True, required=True, ondelete="cascade"
    )

    def unlink(self):
        crons = self.mapped("cron_id")
        if crons:
            crons.unlink()
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault("name", vals.get("trigger_name", "Messenger"))
        return super(UsMessengerTriggerCron, self).create(vals_list)

    def start_button(self):
        job = self.start(force=True)
        return {
            "name": "Job triggered by clicking Button",
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "us.messenger.job",
            "res_id": job.id,
            "target": "self",
        }

    def start(self, force=False):
        if self.active:
            return self.messenger_task_id.start(self, with_delay=True, force=force)

    def get_code(self):
        return (
            """
env["us.messenger.trigger.cron"].browse(%s).start()
"""
            % self.id
        )

    def name_get(self):
        result = []
        for r in self:
            name = _("%s: every %s %s") % (
                r.trigger_name,
                r.interval_number,
                r.interval_type,
            )
            if r.numbercall > 0:
                name += " (%s times)" % r.numbercall
            result.append((r.id, name))
        return result
