import base64
import logging
import os

import xml.etree.ElementTree as ET  # для загрузки контексту

from pytz import timezone

from odoo.addons.queue_job.job import FAILED

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, frozendict, html2plaintext
from odoo.tools.misc import get_lang
from odoo.tools.safe_eval import (
    datetime,
    dateutil,
    json,
    safe_eval,
    test_python_expr,
    time,
)
from odoo.tools.translate import _
from odoo.http import request

from odoo.addons.queue_job.exception import RetryableJobError

from ..tools import url2base64, url2bin
from .ir_logging import LOG_CRITICAL, LOG_DEBUG, LOG_ERROR, LOG_INFO, LOG_WARNING

from re import match

_logger = logging.getLogger(__name__)
DEFAULT_LOG_NAME = "Log"


def cleanup_eval_context(eval_context):
    delete = [k for k in eval_context if k.startswith("_")]
    for k in delete:
        del eval_context[k]
    return eval_context


def edit_text_message(text='', author_name='', is_signature=True):
    text = text.split('<b><a href="/web#id=')[0]
    return "%s\n\n<br/><i>%s</i>" % (text, author_name) if is_signature else text


class UsMessengerProject(models.Model):
    _name = "us.messenger.project"
    _description = "Messenger Project"

    name = fields.Char(
        "Name", help="Your bot name", required=True, default='Enter_bot_name'
    )
    active = fields.Boolean(default=True)
    # Deprecated, please use eval_context_ids
    # TODO: delete in v17 release
    # eval_context = fields.Selection([], string="Evaluation context")
    eval_context_ids = fields.Many2one(
        "us.messenger.project.context", string="Evaluation contexts", required=True, ondelete='cascade'
    )

    eval_context_description = fields.Text(compute="_compute_eval_context_description")

    common_code = fields.Text(
        "Common Code",
        help="""
        A place for helpers and constants.

        You can add here a function or variable, that don't start with underscore and then reuse it in task's code.
    """,
    )
    text_param_ids = fields.One2many("us.messenger.project.text", "project_id", copy=True)
    param_ids = fields.One2many("us.messenger.project.param", "project_id", copy=True)
    task_ids = fields.One2many("us.messenger.task", "project_id", copy=True)
    task_count = fields.Integer(compute="_compute_task_count")
    trigger_cron_count = fields.Integer(
        compute="_compute_triggers", help="Enabled Crons"
    )
    trigger_automation_count = fields.Integer(
        compute="_compute_triggers", help="Enabled DB Triggers"
    )
    trigger_webhook_count = fields.Integer(
        compute="_compute_triggers", help="Enabled Webhooks"
    )
    trigger_button_count = fields.Integer(
        compute="_compute_triggers", help="Manual Triggers"
    )
    trigger_button_ids = fields.Many2many(
        "us.messenger.trigger.button", compute="_compute_triggers", string="Manual Triggers"
    )
    job_ids = fields.One2many("us.messenger.job", "project_id")
    job_count = fields.Integer(compute="_compute_job_count")
    log_ids = fields.One2many("ir.logging", "project_id")
    log_count = fields.Integer(compute="_compute_log_count")

    user_ids = fields.One2many('us.messenger.partner', 'bot_id')
    users_count = fields.Integer(compute="_compute_users_count")
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company", required=True, default=lambda self: self.env.company.id
    )
    token = fields.Char('Token', required=True, default='Token')

    messenger_image = fields.Binary(string="Messenger Image", compute="compute_image_default")

    # state = fields.Selection(string='State',
    #                          selection=[("new", "New"), ("active_webhook", "Active Webhook")],
    #                          default="new",
    #                          copy=False,
    #                          help="Type is used to separate New, Active Webhook, Not active Webhook")
    state = fields.Selection(string='State',
                             selection=[("new", "New"), ("active_webhook", "Active Webhook"),
                                        ("enabled_webhook", "Enabled Webhook")],
                             default="new",
                             copy=False,
                             help="Type is used to separate New, Active Webhook, Not active Webhook")

    send_to_everyone_ids = fields.One2many("us.messenger.mass.mailing", "project_id")
    operator_ids = fields.Many2many("res.users", required=True, check_company=True)
    assistant_id = fields.Many2one('res.partner', string='Assistant', domain=[('is_assistant', '=', True)],
                                   help="You can integrate ChatGPT Assistant by installing the 'us_assistant' module")
    is_us_assistant_installed = fields.Boolean(compute='_compute_assistant_id')

    link_on_bot = fields.Char(string='Link on Bot')

    @api.depends('assistant_id')
    def _compute_assistant_id(self):
        module = self.env['ir.module.module'].search(
            [('name', '=', 'us_assistant'), ('state', '=', 'installed')],
            limit=1
        )
        self.is_us_assistant_installed = bool(module.exists())

    def compute_image_default(self):
        for record in self:
            if record.eval_context_ids.name is False:
                self.messenger_image = None
            else:
                name_module = "us_" + record.eval_context_ids.name
                file_path = os.path.dirname(__file__)
                replace_path = r"us_messenger\models"
                if r"us_messenger\models" not in file_path:
                    replace_path = r"us_messenger/models"

                image_path = file_path.replace(replace_path,
                                               "".join(
                                                   r"{}/static/description/icon.png".format(name_module)))
                image_binary_data = open(image_path, 'rb').read()
                self.update({'messenger_image': base64.b64encode(image_binary_data)})

    @api.constrains('name')
    def _check_name(self):
        for record in self:
            if len(record.name.split(' ')) != 1:
                raise UserError('Field name must be without spaces')

    def copy(self, default=None):
        default = dict(default or {})
        default["active"] = False
        return super(UsMessengerProject, self).copy(default)

    def unlink(self):
        self.with_context(active_test=False).mapped("task_ids").unlink()
        return super().unlink()

    def action_start_button(self):

        url_from_params = self.env['ir.config_parameter'].sudo().get_param('web.base.url', default='')
        if 'https' not in url_from_params:
            scheme_from_odoo = request.httprequest.scheme
            if 'https' == scheme_from_odoo:
                self.env['ir.config_parameter'].sudo().set_param('web.base.url',
                                                                 url_from_params.replace('http', 'https'))

        button = [b for b in self.trigger_button_ids if b.type_button == 'start'][0]
        tmp = button.start_button()
        self.env.cr.commit()
        if self.env[tmp['res_model']].browse(tmp['res_id']).state != FAILED:
            self.state = 'active_webhook'
        else:
            self.active = True

        return tmp

    def action_remove_button(self):
        button = [b for b in self.trigger_button_ids if b.type_button == 'remove'][0]
        button.start_button()
        #self.state = 'new'
        self.state = 'enabled_webhook'
        #self.active = False

    def action_send_to_everyone(self):
        return {
            'view_mode': 'form',
            'res_model': 'us.messenger.mass.mailing',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_project_id': self.id,
                'save': 'Send',  # Змінено назву кнопки "Save" на "Send"
                'discard': 'Cancel',  # Змінено назву кнопки "Discard" на "Cancel"
                'default_bot_type': self.eval_context_ids.name
            }
        }

    def action_open_instruction(self):
        id_module = self.env['ir.module.module'].search([('name', '=', 'us_' + self.eval_context_ids.name.lower())]).id
        return {
            'view_mode': 'form',
            'res_model': 'ir.module.module',
            'type': 'ir.actions.act_window',
            'res_id': id_module
        }

    def _compute_eval_context_description(self):
        for r in self:
            r.eval_context_description = (
                "\n".join(
                    r.eval_context_ids.mapped(
                        lambda c: "-= " + c.display_name + " =-\n\n" + c.description
                    )
                )
                if r.eval_context_ids
                else ""
            )

    def _compute_network_access_readonly(self):
        for r in self:
            r.network_access_readonly = r.sudo().network_access

    @api.depends("task_ids")
    def _compute_task_count(self):
        for r in self:
            r.task_count = len(r.with_context(active_test=False).task_ids)

    @api.depends("job_ids")
    def _compute_job_count(self):
        for r in self:
            r.job_count = len(r.job_ids)

    @api.depends("log_ids")
    def _compute_log_count(self):
        for r in self:
            r.log_count = len(r.log_ids)

    @api.depends('user_ids')
    def _compute_users_count(self):
        for r in self:
            r.users_count = len(r.user_ids)

    def _compute_triggers(self):
        for r in self:
            r.trigger_cron_count = len(r.mapped("task_ids.cron_ids"))
            r.trigger_automation_count = len(r.mapped("task_ids.automation_ids"))
            r.trigger_webhook_count = len(r.mapped("task_ids.webhook_ids"))
            r.trigger_button_count = len(r.mapped("task_ids.button_ids"))
            r.trigger_button_ids = r.mapped("task_ids.button_ids")

    @api.constrains("common_code")
    def _check_python_code(self):
        for r in self.sudo().filtered("common_code"):
            msg = test_python_expr(expr=(r.common_code or "").strip(), mode="exec")
            if msg:
                raise ValidationError(msg)

    def _get_log_function(self, job, function):
        self.ensure_one()

        def _log(cr, message, level, name, log_type):
            cr.execute(
                """
                INSERT INTO ir_logging(create_date, create_uid, type, dbname, name, level, message, path, line, func, messenger_job_id)
                VALUES (NOW() at time zone 'UTC', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    self.env.uid,
                    log_type,
                    self._cr.dbname,
                    name,
                    level,
                    message,
                    "us.messenger.job",
                    job.id,
                    function,
                    job.id,
                ),
            )

        def log(message, level=LOG_INFO, name=DEFAULT_LOG_NAME, log_type="server"):
            if self.env.context.get("new_cursor_logs") is False:
                return _log(self.env.cr, message, level, name, log_type)

            with self.env.registry.cursor() as cr:
                return _log(cr, message, level, name, log_type)

        return log

    def _get_eval_context(self, job, log):
        """Executed Secret and Common codes and return "exported" variables and functions"""
        self.ensure_one()
        log("Job started", LOG_DEBUG)
        start_time = time.time()

        def add_job(function, **options):
            if callable(function):
                function = function.__name__

            def f(*args, **kwargs):
                sub_job = self.env["us.messenger.job"].create(
                    {"parent_job_id": job.id, "function": function}
                )
                queue_job = job.task_id.with_delay(**options).run(
                    sub_job, function, args, kwargs
                )
                sub_job.queue_job_id = queue_job.db_record()
                log(
                    "add_job: %s(*%s, **%s). See %s"
                    % (function, args, kwargs, sub_job),
                    level=LOG_INFO,
                )

            return f

        params = AttrDict()
        for p in self.param_ids:
            params[p.key] = p.value

        texts = AttrDict()
        for p in self.text_param_ids:
            texts[p.key] = p._fields["text"]._get_stored_translations(p)

        webhooks = AttrDict()
        for w in self.task_ids.mapped("webhook_ids"):
            webhooks[w.trigger_name] = w.website_url

        def log_transmission(recipient_str, data_str):
            log(data_str, name=recipient_str, log_type="data_out")

        def safe_getattr(o, k, d=None):
            if k.startswith("_"):
                raise ValidationError(_("You cannot use %s with getattr") % k)
            return getattr(o, k, d)

        def safe_setattr(o, k, v):
            if k.startswith("_"):
                raise ValidationError(_("You cannot use %s with setattr") % k)
            return setattr(o, k, v)

        def type2str(obj):
            return "%s" % type(obj)

        def record2image(record, fname=None):
            # TODO: implement test, that is useful for backporting to 12.0
            if not fname:
                fname = "image_1920"

            return (
                record.sudo()
                .env["ir.attachment"]
                .search(
                    [
                        ("res_model", "=", record._name),
                        ("res_field", "=", fname),
                        ("res_id", "=", record.id),
                    ],
                    limit=1,
                )
            )

        context = dict(self.env.context, log_function=log)
        env = self.env(context=context)
        messenger_partner_context = env['us.messenger.partner']._get_eval_context()
        link_functions = env["us.messenger.link"]._get_eval_context()
        eval_context = dict(
            **link_functions,
            **self._get_sync_functions(log, link_functions),
            **messenger_partner_context,
            **{
                "bot": self,
                "re_match": match,
                "edit_text_message": edit_text_message,
                "env": env,
                "log": log,
                "log_transmission": log_transmission,
                "LOG_DEBUG": LOG_DEBUG,
                "LOG_INFO": LOG_INFO,
                "LOG_WARNING": LOG_WARNING,
                "LOG_ERROR": LOG_ERROR,
                "LOG_CRITICAL": LOG_CRITICAL,
                "params": params,
                "texts": texts,
                "webhooks": webhooks,
                "user": self.env.user,
                "trigger": job.trigger_name,
                "add_job": add_job,
                "json": json,
                "UserError": UserError,
                "ValidationError": ValidationError,
                "OSError": OSError,
                "RetryableJobError": RetryableJobError,
                "getattr": safe_getattr,
                "setattr": safe_setattr,
                "get_lang": get_lang,
                "url2base64": url2base64,
                "url2bin": url2bin,
                "html2plaintext": html2plaintext,
                "time": time,
                "datetime": datetime,
                "dateutil": dateutil,
                "timezone": timezone,
                "b64encode": base64.b64encode,
                "b64decode": base64.b64decode,
                "type2str": type2str,
                "record2image": record2image,
                "DEFAULT_SERVER_DATETIME_FORMAT": DEFAULT_SERVER_DATETIME_FORMAT,
            }
        )
        reading_time = time.time() - start_time

        executing_custom_context = 0
        if self.eval_context_ids:
            start_time = time.time()

            eval_context_frozen = frozendict(eval_context)

            for ec in self.eval_context_ids:
                method = ec.get_eval_context_method()
                eval_context = dict(
                    **eval_context, **method(self.token, eval_context_frozen)
                )
            cleanup_eval_context(eval_context)

            executing_custom_context = time.time() - start_time

        start_time = time.time()
        safe_eval(
            (self.common_code or "").strip(), eval_context, mode="exec", nocopy=True
        )
        executing_common_code = time.time() - start_time
        log(
            "Evalution context is prepared. Reading project data: %05.3f sec; preparing custom evalution context: %05.3f sec; Executing Common Code: %05.3f sec"
            % (reading_time, executing_custom_context, executing_common_code),
            LOG_DEBUG,
        )
        cleanup_eval_context(eval_context)
        return eval_context

    def _get_sync_functions(self, log, link_functions):
        # функція під питанням
        def _sync(src_list, src2dst, link_src_dst, create=None, update=None):
            # * src_list: iterator of src_data
            # * src2dst: src_data -> dst_ref
            # * link_src_dst: links pair (src_data, dst_ref)
            # * create(src_data) -> dst_ref
            # * update(dst_ref, src_data)
            for src_data in src_list:
                dst_ref = src2dst(src_data)
                if dst_ref and update:
                    update(dst_ref, src_data)
                elif not dst_ref and create:
                    dst_ref = create(src_data)
                    link_src_dst(src_data, dst_ref)
                elif dst_ref:
                    log("Destination record already exists: %s" % dst_ref, LOG_DEBUG)
                elif not dst_ref:
                    log("Destination record not found for %s" % src_data, LOG_DEBUG)

        def sync_odoo2x(src_list, sync_info, create=False, update=False):
            # sync_info["relation"]
            # sync_info["x"]["update"]: (external_ref, odoo_record)
            # sync_info["x"]["create"]: odoo_record -> external_ref
            relation = sync_info["relation"]

            def _odoo2external(odoo_record):
                link = odoo_record.search_links(relation)
                return link.external

            def _add_link(odoo_record, external):
                odoo_record.set_link(relation, external)

            return _sync(
                src_list,
                _odoo2external,
                _add_link,
                create and sync_info["x"]["create"],
                update and sync_info["x"]["update"],
            )

        def sync_x2odoo(src_list, sync_info, create=False, update=False):
            # sync_info["relation"]
            # sync_info["x"]["get_ref"]
            # sync_info["odoo"]["update"]: (odoo_record, x)
            # sync_info["odoo"]["create"]: x -> odoo_record
            relation = sync_info["relation"]
            x2ref = sync_info["x"]["get_ref"]

            def _x2odoo(x):
                ref = x2ref(x)
                link = link_functions["get_link"](relation, ref)
                return link.odoo

            def _add_link(x, odoo_record):
                ref = x2ref(x)
                link = odoo_record.set_link(relation, ref)
                return link

            return _sync(
                src_list,
                _x2odoo,
                _add_link,
                create and sync_info["odoo"]["create"],
                update and sync_info["odoo"]["update"],
            )

        def sync_external(
                src_list, relation, src_info, dst_info, create=False, update=False
        ):
            def src2dst(src_data):
                src_ref = src_info["get_ref"](src_data)
                refs = {src_info["system"]: src_ref, dst_info["system"]: None}
                link = link_functions["get_link"](relation, refs)
                res = link.get(dst_info["system"])
                if len(res) == 1:
                    return res[0]

            def link_src_dst(src_data, dst_ref):
                src_ref = src_info["get_ref"](src_data)
                refs = {src_info["system"]: src_ref, dst_info["system"]: dst_ref}
                return link_functions["set_link"](relation, refs)

            return _sync(
                src_list,
                src2dst,
                link_src_dst,
                create and src_info["odoo"]["create_odoo"],
                update and src_info["odoo"]["update_odoo"],
            )

        return {
            "sync_odoo2x": sync_odoo2x,
            "sync_x2odoo": sync_x2odoo,
            "sync_external": sync_external,
        }

    # @api.onchange('eval_context_ids')
    # def duplicate_bot(self):
    #     if self.eval_context_ids:
    #         name_messenger = self.eval_context_ids.name
    #         base_bot = self.env['us.messenger.project'].search(
    #             [('state', '=', 'base_record'), ('eval_context_ids.name', '=', name_messenger)])
    #         if not base_bot:
    #             raise UserError(_("Base bot isn't exist"))
    #         print(base_bot)
    #         # text_param_ids  task_ids  param_ids trigger_button_ids
    #         for record in base_bot.param_ids:
    #             record.copy({'project_id':self.id})
    #
    #         for record in base_bot.task_ids:
    #             record.copy({'project_id':self.id})
    #
    #         for record in base_bot.text_param_ids:
    #             record.copy({'project_id':self.id})
    #
    #         for record in base_bot.trigger_button_ids:
    #             record.copy({'project_id':self.id})
    def parse_xml(self, eval_name=None):
        if self.eval_context_ids:
            name_context = eval_name
            # self.env['us.messenger.project.param'].sudo().with_context(active_test=False).search(
            #     ['|', ('id', 'in', self.param_ids.ids), ('project_id', '=', False)]).unlink()
            # self.env['us.messenger.project.text'].sudo().with_context(active_test=False).search(
            #     ['|', ('id', 'in', self.param_ids.ids), ('project_id', '=', False)]).unlink()
            # self.env['us.messenger.trigger.button'].sudo().with_context(active_test=False).search(
            #     [('id', 'in', self.task_ids.button_ids.ids)]).unlink()
            # self.env['us.messenger.trigger.automation'].sudo().with_context(active_test=False).search(
            #     [('id', 'in', self.task_ids.automation_ids.ids)]).unlink()
            # self.env['us.messenger.trigger.webhook'].sudo().with_context(active_test=False).search(
            #     [('id', 'in', self.task_ids.webhook_ids.ids)]).unlink()
            # self.env['us.messenger.task'].sudo().with_context(active_test=False).search([
            #     '|', ('id', 'in', self.task_ids.ids), ('project_id', '=', False)]).unlink()
            self.param_ids.unlink()
            self.text_param_ids.unlink()
            self.task_ids.unlink()
            self.trigger_button_ids.unlink()
            self.send_to_everyone_ids.unlink()
            self.compute_image_default()
            name_module = 'us_' + eval_name
            file_path = os.path.dirname(__file__)
            replace_path = r"us_messenger\models"
            if r"us_messenger\models" not in file_path:
                replace_path = r"us_messenger/models"

            path = file_path.replace(replace_path,
                                     "".join(r"{}/data/us_project_data.xml".format(name_module)))
            tree = ET.parse(path)
            root = tree.getroot()

            base_bot = self.env['us.messenger.project'].search(
                [('state', '=', 'progenitor_' + name_context.lower())])

            if not base_bot and 'progenitor_' + name_context.lower() != self.state:
                raise UserError(_("Base bot isn't exist"))

            for record in root.findall(".//record"):
                model_name = record.get('model')
                if model_name not in ["us.messenger.project.context", "us.messenger.project.text",
                                      "us.messenger.project.param"]:
                    self.extract_fields(root, model_name, record)

            for rec in base_bot.text_param_ids:
                rec.copy({'project_id': self.id})

            for rec in base_bot.param_ids:
                rec.copy({'project_id': self.id})

    def extract_fields(self, root, model_name, record):
        model_data = {}
        data = record.findall(".//field")
        for field in data:
            field_name = field.get('name')
            field_value = None
            if field_name == "common_code" and model_name == "us.messenger.project":
                self.update({"common_code": field.text})
                continue
            elif field_name == 'project_id':
                field_value = self.id
            elif field_name == "active":
                field_value = self.check_bool(field.get("eval")) if model_name not in ["us.messenger.trigger.automation", "us.messenger.trigger.webhook"] else True
            elif field_name == "messenger_task_id":
                task = field.get("ref")
                field_value = self.find_task(root, task)
            elif field_name == "filter_pre_domain":
                field_value = field
            elif field_name == "model_id":
                model_id = field.get("ref")
                model_id = model_id.split("model_", 1)[1].replace("_", ".")
                model_obj = self.env['ir.model'].search([('model', '=', model_id)], limit=1)
                field_value = model_obj.id
            elif field_name == "trigger_field_ids":
                eval = field.get("eval").replace("obj()", "env['ir.model.fields']")
                model_obj = safe_eval(eval, {"env": self.env})
                field_value = model_obj
            else:
                field_value = field.text
            model_data[field_name] = field_value
        if model_name != "us.messenger.project" and model_name != "us.messenger.task":
            self.create_model_instance(model_name, model_data)

    def create_model_instance(self, model_name, data):
        model_obj = self.env[model_name]
        model_obj.create(data)

    def find_task(self, root, task_ref, ):
        for task_record in root.findall(".//record[@model='us.messenger.task']"):
            if task_record.get("id") == task_ref:
                name = task_record.find(".//field[@name='name']").text
                active = task_record.find(".//field[@name='active']")
                active = self.check_bool(active.get("eval"))
                code = task_record.find(".//field[@name='code']").text
                param_obj = self.env['us.messenger.task'].create({
                    'name': name,
                    'active': active,
                    'code': code,
                    'project_id': self.id,
                })
                return param_obj.id

    def check_bool(self, value):
        return value.lower() == 'true' or value == '1'

    @api.model_create_multi
    def create(self, vals_list):
        records = super(UsMessengerProject, self).create(vals_list)
        if 'state' in vals_list[0] and 'progenitor_' not in vals_list[0]['state']:
            eval_name = self.env['us.messenger.project.context'].browse(vals_list[0]['eval_context_ids']).name
            for record in records:
                record.parse_xml(eval_name)
        return records

    def write(self, vals):
        if 'eval_context_ids' in vals:
            if self.eval_context_ids.id != vals['eval_context_ids']:
                eval_name = self.env['us.messenger.project.context'].browse(vals['eval_context_ids']).name
                self.parse_xml(eval_name)
        if 'assistant_id' in vals:
            new_assistant_id = vals['assistant_id']
            if new_assistant_id is False:
                current_assistant_id = self.assistant_id.id if self.assistant_id else None
                if current_assistant_id:
                    links = self.env['us.messenger.link'].search(
                        [('model', '=', 'discuss.channel'), ('bot_id', '=', self.id)])
                    bot_channels = [self.env['discuss.channel'].browse(int(x.ref2)) for x in links]
                    for channel in bot_channels:
                        if current_assistant_id in channel.channel_partner_ids.ids:
                            channel.channel_partner_ids = [(3, current_assistant_id)]
            else:
                links = self.env['us.messenger.link'].search(
                    [('model', '=', 'discuss.channel'), ('bot_id', '=', self.id)])
                bot_channels = [self.env['discuss.channel'].browse(int(x.ref2)) for x in links]
                for channel in bot_channels:
                    if new_assistant_id not in channel.channel_partner_ids.ids:
                        channel.channel_partner_ids = [(4, new_assistant_id)]

        if 'operator_ids' in vals:
            operators_to_add = set()
            operators_to_remove = set()

            for pair in vals['operator_ids']:
                if pair[0] == 4:
                    operators_to_add.add(pair[1])

                elif pair[0] == 3:
                    operators_to_remove.add(pair[1])

            links = self.env['us.messenger.link'].search([('model', '=', 'discuss.channel'), ('bot_id', '=', self.id)])
            bot_channels = [self.env['discuss.channel'].browse(int(x.ref2)) for x in links]

            if operators_to_remove:
                partners = set([self.env['res.users'].browse(record).partner_id.id for record in operators_to_remove])
                for channel in bot_channels:
                    chanel_part_ids = set(channel.channel_partner_ids.ids)
                    result = chanel_part_ids - partners
                    channel.write({'channel_partner_ids': list(result)})
            if operators_to_add:
                partners = set([self.env['res.users'].browse(record).partner_id.id for record in operators_to_add])
                for channel in bot_channels:
                    chanel_part_ids = set(channel.channel_partner_ids.ids)
                    chanel_part_ids.update(partners)
                    channel.write({'channel_partner_ids': list(chanel_part_ids)})

        return super(UsMessengerProject, self).write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_partner(self):
        for record in self:
            if 'progenitor_' in record.state:
                raise UserError(_("You can't delete this bot. This bot is base record for other bots"))
            if record.user_ids:
                # raise Warning('If you delete this bot, you will be not able to send message to messenger users, '
                #               'to do this, you can create new bot with the same token, but old channels will not work')
                for user in record.user_ids:
                    user.partner_id.action_archive()


class UsMessengerProjectParam(models.Model):
    _name = "us.messenger.project.param"
    _description = "Project Parameter"
    _rec_name = "key"

    key = fields.Char("Key", required=True)
    value = fields.Char("Value")
    initial_value = fields.Char(
        compute="_compute_initial_value",
        inverse="_inverse_initial_value",
        help="A virtual field that, during writing, stores the value in the value field, but only if it is empty. \
             It's used during module upgrade to prevent overwriting parameter values. ",
    )
    description = fields.Char("Description", translate=True)
    url = fields.Char("Documentation")
    project_id = fields.Many2one("us.messenger.project", ondelete="cascade")

    _sql_constraints = [("key_uniq", "unique (project_id, key)", "Key must be unique.")]

    def _compute_initial_value(self):
        for r in self:
            r.initial_value = r.value

    def _inverse_initial_value(self):
        for r in self:
            if not r.value:
                r.value = r.initial_value


class UsMessengerProjectText(models.Model):
    _name = "us.messenger.project.text"
    _description = "Project Text Parameter"
    _inherit = "us.messenger.project.param"

    text = fields.Text("Text", translate=True)


# see https://stackoverflow.com/a/14620633/222675
class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self
