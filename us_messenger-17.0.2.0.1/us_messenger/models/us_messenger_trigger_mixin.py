from odoo import api, fields, models


class UsMessengerTriggerMixin(models.AbstractModel):

    _name = "us.messenger.trigger.mixin"
    _description = "Mixing for trigger models"
    _rec_name = "trigger_name"

    trigger_name = fields.Char(
        "Trigger Name", help="Technical name to be used in task code", required=True
    )
    job_ids = fields.One2many("us.messenger.job", "task_id")
    job_count = fields.Integer(compute="_compute_job_count")

    def _compute_job_count(self):
        for r in self:
            r.job_count = len(r.job_ids)

    def _update_name(self, vals):
        if not ("messenger_task_id" in vals or "trigger_name" in vals):
            return
        if not self._fields["name"].required: # перевірка чи є поле 'name' required
            return

        for record in self:
            if record.name != self._description:
                continue
            name = "Messengers: %s -> %s" % (
                record.project_id.name,
                record.trigger_name,
            )

            record.write({"name": name})

    def write(self, vals):
        res = super().write(vals)
        self._update_name(vals)
        return res

    @api.model_create_multi
    def create(self, vals):
        res = super().create(vals)
        res._update_name(vals)
        return res

    def default_get(self, fields):
        vals = super(UsMessengerTriggerMixin, self).default_get(fields)
        # put model description in case if name is required field
        if self._fields["name"].required:
            vals["name"] = self._description
        return vals


class UsMessengerTriggerMixinModelId(models.AbstractModel):

    _name = "us.messenger.trigger.mixin.model_id"
    _description = "Mixing to fill model_id field"

    @api.model_create_multi
    def create(self, vals_list):
        model_id = self.env.ref("base.model_res_partner").id
        for vals in vals_list:
            vals.setdefault("model_id", model_id)
        return super(UsMessengerTriggerMixinModelId, self).create(vals_list)


class UsMessengerTriggerMixinActions(models.AbstractModel):

    _name = "us.messenger.trigger.mixin.actions"
    _description = "Mixing for triggers that inherit actions"

    @api.model
    def default_get(self, fields):
        vals = super().default_get(fields)
        if "state" in vals:
            vals["state"] = "code"
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for r in records:
            if "code" not in r._fields:
                r.automation_id.write({
                    'action_server_ids': [(0, 0, {
                        'name': r.name,
                        'model_id': r.model_id.id,
                        'state': 'code',
                        'code': r.get_code(),
                    })]
                })
            else:
                r.code = r.get_code()
        return records
