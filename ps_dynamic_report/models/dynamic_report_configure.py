# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

import xlwt
import base64
from io import BytesIO


class DynamicReportConfigure(models.Model):
    _name = 'dynamic.report.configure'
    _rec_name = 'name'

    name = fields.Char('Name')
    model_id = fields.Many2one('ir.model', 'Model', domain="[('transient', '=', False)]")
    dynamic_field_id = fields.One2many('dynamic.report.field', 'dynamic_configure_id', 'Dynamic Field')
    is_action_created = fields.Boolean('Is Created?', default=False)
    server_action_id = fields.Many2one('ir.actions.server', 'Server id')
    report_type = fields.Selection([('pdf', 'PDF'), ('xls', 'XLS')], default='pdf', string="Report Type")

    @api.onchange('model_id')
    def _onchange_model_id(self):
        if self.dynamic_field_id:
            self.dynamic_field_id.unlink()

    def create_dynamic_pdf_report(self, server):
        server_id = self.env['ir.actions.server'].search([('dynamic_report_id', '=', server)])
        dynamic_report_id = server_id.dynamic_report_id.dynamic_field_id.filtered(lambda a: a.field_id)
        Heading_values = [item.field_id.field_description for item in dynamic_report_id]

        record_data = []
        total_data = []
        active_model_id = self.env[self._context.get('active_model')].browse(self._context.get('active_ids'))
        for model in active_model_id:
            temp = []
            for item in dynamic_report_id:
                if item.field_type == 'selection':
                    state = dict(model._fields[item.field_name_id].selection).get(model[item.field_name_id])
                    temp.append(state)
                elif item.field_type == 'datetime':
                    date = getattr(model, item.field_name_id)
                    temp.append(str(date.date()) if date else '')
                elif item.field_type == 'date':
                    temp.append(str(getattr(model, item.field_name_id) or ''))
                elif item.field_type == 'many2one':
                    temp_value = getattr(model, item.field_name_id)
                    value = getattr(temp_value, temp_value._rec_name)
                    temp.append(value)
                else:
                    temp.append(getattr(model, item.field_name_id))

                if len(total_data) < len(Heading_values):
                    if item.is_sum_calc:
                        m_value = sum(active_model_id.mapped(item.field_name_id))
                        total_data.append(m_value)
                    else:
                        total_data.append('')

            record_data.append(temp)
        data = {
            'report_name': server_id.dynamic_report_id.name,
            'model_id': server_id.dynamic_report_id.model_id.model,
            'name': server_id.dynamic_report_id.name,
            'table_heading': Heading_values,
            'record_data': record_data,
            'total_data': total_data
        }
        if server_id.dynamic_report_id.report_type == 'pdf':
            return self.env.ref('ps_dynamic_report.action_dynamic_report_print').report_action(self, data=data)
        else:
            workbook = xlwt.Workbook(encoding='utf-8', style_compression=0)
            fl = BytesIO()
            worksheet = workbook.add_sheet('Report Details', cell_overwrite_ok=True)
            font = xlwt.Font()

            xlwt.add_palette_colour("custom_colour", 0x21)
            workbook.set_colour_RGB(0x21, 245, 184, 103)
            style1 = xlwt.easyxf("pattern: pattern solid, fore_colour custom_colour; alignment: vert centre, horiz center; font: name Arial, bold True;")
            style2 = xlwt.easyxf("pattern: pattern solid, fore_colour silver_ega; alignment: horizontal center; font: name Arial, bold True;")
            style3 = xlwt.easyxf('alignment: horizontal center;')
            style4 = xlwt.easyxf('alignment: horizontal center; font: name Arial, bold True;')

            cell_value = xlwt.XFStyle()
            cell_value.font = font

            worksheet.write_merge(0, 1, 0, len(Heading_values)-1, server_id.dynamic_report_id.name or '', style1)

            row = 3
            col = 0
            for heading in Heading_values:
                worksheet.col(col).width = 500 * 12
                worksheet.write(row, col, heading, style2)
                col += 1

            row = 4
            col = 0
            for data in record_data:
                for rec in data:
                    worksheet.write(row, col, rec, style3)
                    col += 1
                col = 0
                row += 1

            col = 0
            for total in total_data:
                worksheet.write(row, col, total, style4)
                col += 1

            filename = server_id.dynamic_report_id.name or "Report Detail"
            workbook.save(fl)
            fl.seek(0)
            test = base64.encodebytes(fl.read())
            attach_vals = {
                'name': '%s.xlsx' % (filename),
                'datas': test,
            }
            doc_id = self.env['ir.attachment'].create(attach_vals)
            return {
                'type': 'ir.actions.act_url',
                'url': 'web/content/%s?download=true' % (doc_id.id),
                'target': 'self',
            }

    def create_server_action(self):
        if not self.dynamic_field_id:
            raise UserError(_("Please Select few Fields!!"))
        vals = {
            'name': self.name if self.name else 'Custom Action',
            'model_id': self.model_id.id,
            'model_name': self.model_id.name,
            'state': 'code',
            'binding_model_id': self.model_id.id,
            'binding_view_types': 'list',
            'dynamic_report_id': self.id,
            'code': "action = env['dynamic.report.configure'].create_dynamic_pdf_report(server={server_id})".format(server_id=self.id)
        }
        server_action_id = self.env['ir.actions.server'].create(vals)
        self.server_action_id = server_action_id.id
        self.is_action_created = True
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def remove_server_action(self):
        if self.is_action_created and self.server_action_id:
            self.server_action_id.unlink()
            self.is_action_created = False


class DynamicReportField(models.Model):
    _name = 'dynamic.report.field'

    field_id = fields.Many2one('ir.model.fields', 'Field')
    sequence = fields.Integer('..', help="Gives the sequence order when displaying a list O2m.")
    field_name_id = fields.Char(related='field_id.name', string='Target Model Name', readonly=True)
    field_type = fields.Selection(related='field_id.ttype', string='Field Type')
    dynamic_configure_id = fields.Many2one('dynamic.report.configure', 'Reference')
    is_sum_calc = fields.Boolean("Sum")

    @api.model
    def default_get(self, fields):
        res = super(DynamicReportField, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'dynamic_field_id' in context_keys:
                if len(self._context.get('dynamic_field_id')) > 0:
                    next_sequence = len(self._context.get('dynamic_field_id')) + 1
        res.update({'sequence': next_sequence})
        return res
