import logging
import time
import traceback
from io import StringIO

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval, test_python_expr

from .ir_logging import LOG_CRITICAL, LOG_DEBUG

_logger = logging.getLogger(__name__)


class UsMessengerTask(models.Model):

    _name = "us.messenger.task"
    _description = "Messenger Task"

    project_id = fields.Many2one("us.messenger.project", ondelete="cascade")
    name = fields.Char("Name", help="e.g. Messenger Products", required=True)
    code = fields.Text("Code")
    code_check = fields.Text("Syntax check", store=False, readonly=True)
    active = fields.Boolean(default=True)
    cron_ids = fields.One2many("us.messenger.trigger.cron", "messenger_task_id", copy=True)
    automation_ids = fields.One2many(
        "us.messenger.trigger.automation", "messenger_task_id", copy=True
    )
    webhook_ids = fields.One2many("us.messenger.trigger.webhook", "messenger_task_id", copy=True)
    button_ids = fields.One2many(
        "us.messenger.trigger.button", "messenger_task_id", string="Manual Triggers", copy=True
    )
    active_cron_ids = fields.Many2many(
        "us.messenger.trigger.cron",
        string="Enabled Crons",
        compute="_compute_active_triggers",
        context={"active_test": False},
        ondelete='cascade'
    )
    active_automation_ids = fields.Many2many(
        "us.messenger.trigger.automation",
        string="Enabled DB Triggers",
        compute="_compute_active_triggers",
        context={"active_test": False},
        ondelete='cascade'
    )
    active_webhook_ids = fields.Many2many(
        "us.messenger.trigger.webhook",
        string="Enabled Webhooks",
        compute="_compute_active_triggers",
        context={"active_test": False},
        ondelete='cascade'
    )
    active_button_ids = fields.Many2many(
        "us.messenger.trigger.button",
        string="Enabled Buttons",
        compute="_compute_active_triggers",
        context={"active_test": False},
        ondelete='cascade'
    )
    job_ids = fields.One2many("us.messenger.job", "task_id")
    job_count = fields.Integer(compute="_compute_job_count")
    log_ids = fields.One2many("ir.logging", "messenger_task_id")
    log_count = fields.Integer(compute="_compute_log_count")

    @api.depends("job_ids")
    def _compute_job_count(self):
        for r in self:
            r.job_count = len(r.job_ids)

    @api.depends("log_ids")
    def _compute_log_count(self):
        for r in self:
            r.log_count = len(r.log_ids)

    @api.constrains("code")
    def _check_python_code(self):
        for r in self.sudo().filtered("code"):
            msg = test_python_expr(expr=r.code, mode="exec")
            if msg:
                raise ValidationError(msg)

    @api.onchange("code")
    def onchange_code(self):
        for r in self:
            if not r.code:
                continue
            msg = test_python_expr(expr=r.code, mode="exec")
            r.code_check = msg

    @api.depends(
        "cron_ids.active",
        "automation_ids.active",
        "webhook_ids.active",
        "button_ids.active",
    )
    def _compute_active_triggers(self):
        for r in self.with_context(active_test=False):
            r.active_cron_ids = r.with_context(active_test=True).cron_ids
            r.active_automation_ids = r.with_context(active_test=True).automation_ids
            r.active_webhook_ids = r.with_context(active_test=True).webhook_ids
            r.active_button_ids = r.with_context(active_test=True).button_ids

    def start(
        self, trigger, args=None, with_delay=False, force=False, raise_on_error=True
    ):
        self.ensure_one()
        if not force and not (self.active and self.project_id.active):
            _logger.info(
                "Triggering archived project or task: %s", trigger.trigger_name
            )
            return None

        job = self.env["us.messenger.job"].create_trigger_job(trigger)
        run = self.with_delay().run if with_delay else self.run
        if not with_delay and self.env.context.get("new_cursor_logs") is not False:
            # log records are created via new cursor and they use job.id value for sync_job_id field
            self.env.cr.commit()  # pylint: disable=invalid-commit

        queue_job_or_result = run(
            job, trigger._messenger_handler, args, raise_on_error=raise_on_error
        )
        if with_delay and not self.env.context.get("test_queue_job_no_delay"):
            # збереження queue_job в us_messenger_job
            job.queue_job_id = queue_job_or_result.db_record()
            return job
        else:
            return job, queue_job_or_result

    def run(self, job, function, args=None, kwargs=None, raise_on_error=True):
        log = self.project_id._get_log_function(job, function)
        try:
            eval_context = self.project_id._get_eval_context(job, log)
            code = self.code
            start_time = time.time()
            result = self._eval(code, function, args, kwargs, eval_context)
            log(
                "Executing {}: {:05.3f} sec".format(function, time.time() - start_time),
                LOG_DEBUG,
            )
            log("Job finished")
            return result, log
        except Exception:
            buff = StringIO()
            traceback.print_exc(file=buff)
            log(buff.getvalue(), LOG_CRITICAL)
            if raise_on_error:
                raise

    @api.model
    def _eval(self, code, function, args, kwargs, eval_context):
        ARGS = "EXECUTION_ARGS_"
        KWARGS = "EXECUTION_KWARGS_"
        RESULT = "EXECUTION_RESULT_"

        code += """
{RESULT} = {function}(*{ARGS}, **{KWARGS})
        """.format(
            RESULT=RESULT, function=function, ARGS=ARGS, KWARGS=KWARGS
        )
        eval_context[ARGS] = args or ()
        eval_context[KWARGS] = kwargs or {}

        safe_eval(
            code, eval_context, mode="exec", nocopy=True
        )  # nocopy allows to return RESULT
        return eval_context[RESULT]

    def name_get(self):
        if not self.env.context.get("name_with_project"):
            return super(UsMessengerTask, self).name_get()
        result = []
        for r in self:
            name = r.project_id.name + ": " + r.name
            result.append((r.id, name))
        return result

    def unlink(self):
        self.with_context(active_test=False).mapped("automation_ids").unlink()
        self.with_context(active_test=False).mapped("webhook_ids").unlink()
        self.with_context(active_test=False).mapped("cron_ids").unlink()
        return super(UsMessengerTask, self).unlink()
