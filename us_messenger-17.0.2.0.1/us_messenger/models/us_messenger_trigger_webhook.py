import json
import uuid

from odoo import api, fields, models
from odoo.http import Response, request

from .ir_logging import LOG_DEBUG


class UsMessengerTriggerWebhook(models.Model):

    _name = "us.messenger.trigger.webhook"
    _inherit = [
        "us.messenger.trigger.mixin",
        "us.messenger.trigger.mixin.model_id",
        "us.messenger.trigger.mixin.actions",
    ]
    _description = "Webhook Trigger"
    _messenger_handler = "handle_webhook"

    messenger_task_id = fields.Many2one("us.messenger.task", name="Task", ondelete="cascade")
    project_id = fields.Many2one(
        "us.messenger.project", related="messenger_task_id.project_id", readonly=True
    )
    action_server_id = fields.Many2one(
        "ir.actions.server", delegate=True, required=True, ondelete="cascade"
    )
    active = fields.Boolean(default=True)

    @api.model
    def default_get(self, fields):
        vals = super(UsMessengerTriggerWebhook, self).default_get(fields)
        vals["groups_id"] = [(4, self.env.ref("base.group_public").id, 0)]
        vals["website_path"] = uuid.uuid4()
        return vals

    def start(self):
        record = self.sudo()

        is_delivered_or_seen = True
        if 'application/json' in request.httprequest.content_type:
            request_data = json.loads(request.httprequest.data.decode("utf-8"))
            if "event" in request_data:
                if request_data["event"] == "delivered" or request_data["event"] == "seen":
                    is_delivered_or_seen = False

        if record.active and is_delivered_or_seen:
            start_result = record.messenger_task_id.start(
                record, args=(request.httprequest,)
            )

            if not start_result:
                return self.make_response("Task or Project is disabled", 404)

            _job, (result, log) = start_result
            return self._process_handler_result(result, log)
        else:
            return self.make_response("This webhook is disabled", 404)

    def get_code(self):
        return (
            """
action = env["us.messenger.trigger.webhook"].browse(%s).start()
"""
            % self.id
        )

    @api.model
    def _process_handler_result(self, result, log):
        if not result:
            result = "OK"
        data = None
        headers = []
        status = 200
        if isinstance(result, tuple):
            if len(result) == 3:
                data, status, headers = result
            elif len(result) == 2:
                data, status = result
        else:
            data = result
        log("Webhook response: {} {}\n{}".format(status, headers, data), LOG_DEBUG)
        return self.make_response(data, status, headers)

    @api.model
    def make_response(self, data, status=200, headers=None):
        return Response(data, status=status, headers=headers)

    def unlink(self):
        actions = self.mapped("action_server_id")
        super().unlink()
        actions.unlink()
        return True