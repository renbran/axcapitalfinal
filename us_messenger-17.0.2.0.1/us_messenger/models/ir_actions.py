from odoo import fields, models


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    messenger_task_id = fields.Many2one("us.messenger.task")
    project_id = fields.Many2one(
        "us.messenger.project", related="messenger_task_id.project_id", readonly=True
    )
