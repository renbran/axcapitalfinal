from odoo import api, fields, models
from odoo.tools.translate import _

from odoo.addons.queue_job.job import DONE, ENQUEUED, FAILED, PENDING, STARTED

from .ir_logging import LOG_CRITICAL, LOG_ERROR, LOG_WARNING

DONE_WARNING = "done_warning"
TRIGGER_MODEL2FIELD = {
    "us.messenger.trigger.cron": "trigger_cron_id",
    "us.messenger.trigger.automation": "trigger_automation_id",
    "us.messenger.trigger.webhook": "trigger_webhook_id",
    "us.messenger.trigger.button": "trigger_button_id",
}
TRIGGER_FIELDS = TRIGGER_MODEL2FIELD.values()


class UsMessengerJob(models.Model):

    _name = "us.messenger.job"
    _description = "Messenger Job"
    _rec_name = "trigger_name"
    _order = "id desc"

    trigger_name = fields.Char(compute="_compute_trigger_name", store=True)
    trigger_cron_id = fields.Many2one("us.messenger.trigger.cron", readonly=True)
    trigger_automation_id = fields.Many2one("us.messenger.trigger.automation", readonly=True)
    trigger_webhook_id = fields.Many2one("us.messenger.trigger.webhook", readonly=True)
    trigger_button_id = fields.Many2one("us.messenger.trigger.button", readonly=True)
    task_id = fields.Many2one(
        "us.messenger.task", compute="_compute_messenger_task_id", store=True, ondelete="cascade"
    )
    project_id = fields.Many2one(
        "us.messenger.project", related="task_id.project_id", readonly=True
    )
    parent_job_id = fields.Many2one("us.messenger.job", readonly=True, ondelete="cascade")
    job_ids = fields.One2many("us.messenger.job", "parent_job_id", "Sub jobs", readonly=True)
    log_ids = fields.One2many("ir.logging", "messenger_job_id", readonly=True)
    log_count = fields.Integer(compute="_compute_log_count")
    queue_job_id = fields.Many2one("queue.job", string="Queue Job", readonly=True)
    queue_job_state = fields.Selection(
        related="queue_job_id.state", readonly=True, string="Queue Job State"
    )
    function = fields.Char(string="Task Function")
    func_string = fields.Char(
        related="queue_job_id.func_string", readonly=True, string="Function"
    )
    retry = fields.Integer(related="queue_job_id.retry", readonly=True)
    max_retries_str = fields.Char(compute="_compute_max_retries_str")
    state = fields.Selection(
        [
            (PENDING, "Pending"),
            (ENQUEUED, "Enqueued"),
            (STARTED, "Started"),
            (DONE, "Done"),
            (DONE_WARNING, "Done With Warnings"),
            (FAILED, "Failed"),
        ],
        compute="_compute_state",
    )
    in_progress = fields.Boolean(
        compute="_compute_state",
    )

    @api.depends("queue_job_id.max_retries")
    def _compute_max_retries_str(self):
        for r in self:
            max_retries = r.queue_job_id.max_retries
            if not max_retries:
                r.max_retries_str = _("infinity")
            else:
                r.max_retries_str = str(max_retries)

    @api.depends("queue_job_id.state", "job_ids.queue_job_id.state", "log_ids.level")
    def _compute_state(self):
        for r in self:
            jobs = r + r.job_ids
            states = [q.state for q in jobs.mapped("queue_job_id")]
            levels = {log.level for log in jobs.mapped("log_ids")}
            computed_state = DONE
            has_errors = any(lev in [LOG_CRITICAL, LOG_ERROR] for lev in levels)
            has_warnings = any(lev == LOG_WARNING for lev in levels)
            for s in [FAILED, STARTED, ENQUEUED, PENDING]:
                if any(s == ss for ss in states):
                    computed_state = s
                    break
            if computed_state == DONE and has_errors:
                computed_state = FAILED
            elif computed_state == DONE and has_warnings:
                computed_state = DONE_WARNING
            r.state = computed_state
            r.in_progress = any(s in [PENDING, ENQUEUED, STARTED] for s in states)

    @api.depends("log_ids")
    def _compute_log_count(self):
        for r in self:
            r.log_count = len(r.log_ids)

    @api.depends("parent_job_id", *TRIGGER_FIELDS)
    def _compute_messenger_task_id(self):
        for r in self:
            if r.parent_job_id:
                r.task_id = r.parent_job_id.task_id
            for f in TRIGGER_FIELDS:
                obj = getattr(r, f)
                if obj:
                    r.task_id = obj.messenger_task_id
                    break


    @api.depends(*TRIGGER_FIELDS)
    def _compute_trigger_name(self):
        for r in self:
            if r.parent_job_id:
                r.trigger_name = (r.parent_job_id.trigger_name or "") + "." + r.function
                continue
            for f in TRIGGER_FIELDS:
                t = getattr(r, f)
                if t:
                    r.trigger_name = t.trigger_name
                    break

    def create_trigger_job(self, trigger):
        return self.create(
            {
                TRIGGER_MODEL2FIELD[trigger._name]: trigger.id,
                "function": trigger._messenger_handler,
            }
        )

    def refresh_button(self):
        # magic empty method to refresh form content
        pass

    def requeue_button(self):
        self.queue_job_id.requeue()
