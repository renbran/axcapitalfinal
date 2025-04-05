from odoo import api, fields, models, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

class Property(models.Model):
    _name = 'property.property'
    _description = 'Property Details'
    _order = 'name'
    
    name = fields.Char(string="Property Name", required=True)
    property_image = fields.Image("Property Image")
    floor_plan = fields.Image("Floor Plan")
    
    # New fields for additional images
    interior_image = fields.Image("Interior View")  # Field for interior view image
    amenities_image = fields.Image("Amenities")    # Field for amenities image
    
    partner_id = fields.Many2one('res.partner', string="Partner")
    property_price = fields.Monetary(string="Property Price", required=True)
    revenue_account_id = fields.Many2one('account.account', string="Revenue Account", required=True, 
                                        default=lambda self: self.env['account.account'].search([('name', '=', 'Sales Account')], limit=1))
    address = fields.Text(string="Address")
    sale_rent = fields.Selection([
        ('for_sale', 'For Sale'),
        ('for_rent', 'For Rent'),
    ], string="Sale or Rent", required=True)
    state = fields.Selection([
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('booked', 'Booked'),
        ('sold', 'Sold')
    ], string="State", default='available', required=True)
    currency_id = fields.Many2one('res.currency', string="Currency", required=True, default=lambda self: self.env.company.currency_id)
    description = fields.Text(string="Description")
    
    property_sale_ids = fields.One2many('property.sale', 'property_id', string="Related Sales")
    sale_count = fields.Integer(string="Sale Count", compute="_compute_sale_count")
    
    # New payment tracking fields
    payment_progress = fields.Float(string="Payment Progress (%)", compute="_compute_payment_progress", store=True)
    total_invoiced = fields.Monetary(compute='_compute_payment_details')
    total_paid = fields.Monetary(string="Total Paid", compute="_compute_payment_details", store=True)
    remaining_amount = fields.Monetary(string="Remaining Amount", compute="_compute_payment_details", store=True)
    active_sale_id = fields.Many2one('property.sale', string="Active Sale", compute="_compute_active_sale")
    
    # Existing fields
    field_id = fields.Integer(string="ID")
    property_reference = fields.Char(string="Property Reference")
    status = fields.Char(string="Status", compute="_compute_status", store=True)
    tower = fields.Char(string="Tower")
    level = fields.Char(string="Level")
    project_name = fields.Char(string="Project Name", default="Sky Hills Astra")
    unit_no = fields.Char(string="Unit No")
    unit_view = fields.Char(string="Unit View")
    total_sqft = fields.Float(string="Total Sqft")
    price_per_sqft = fields.Float(string="Price / Sqft")
    total_sale_value = fields.Float(string="Total Sale Value", compute="_compute_total_sale_value", store=True)
    property_type = fields.Char(string="Type")
    
    @api.depends('state')
    def _compute_status(self):
        for record in self:
            if record.state == 'available':
                record.status = 'Available'
            elif record.state == 'reserved':
                record.status = 'Reserved'
            elif record.state == 'booked':
                record.status = 'Booked'
            elif record.state == 'sold':
                record.status = 'Sold'
            else:
                record.status = 'Unknown'
    
    @api.depends('total_sqft', 'price_per_sqft')
    def _compute_total_sale_value(self):
        for record in self:
            record.total_sale_value = record.total_sqft * record.price_per_sqft
    
    @api.depends('property_sale_ids')
    def _compute_sale_count(self):
        for record in self:
            record.sale_count = len(record.property_sale_ids)
    
    @api.depends('property_sale_ids')
    def _compute_active_sale(self):
        for record in self:
            active_sales = record.property_sale_ids.filtered(lambda s: s.state in ['confirm', 'invoiced'])
            record.active_sale_id = active_sales[0] if active_sales else False
    
    @api.depends('active_sale_id', 'active_sale_id.property_sale_line_ids', 
                 'active_sale_id.property_sale_line_ids.collection_status')
    def _compute_payment_progress(self):
        for record in self:
            if record.active_sale_id:
                # Get all lines
                all_lines = record.active_sale_id.property_sale_line_ids
                if all_lines:
                    # Calculate paid percentage
                    total_amount = sum(all_lines.mapped('capital_repayment'))
                    paid_amount = sum(all_lines.filtered(lambda l: l.collection_status == 'paid').mapped('capital_repayment'))
                    
                    if total_amount > 0:
                        record.payment_progress = (paid_amount / total_amount) * 100
                    else:
                        record.payment_progress = 0.0
                else:
                    record.payment_progress = 0.0
            else:
                record.payment_progress = 0.0
    
    def _compute_payment_details(self):
        for prop in self:
            if prop.active_sale_id:
                # Get all payment lines
                all_lines = prop.active_sale_id.property_sale_line_ids
                
                # Calculate paid amount
                paid_lines = all_lines.filtered(lambda l: l.collection_status == 'paid')
                paid_amount = sum(paid_lines.mapped('capital_repayment'))
                total_amount = sum(all_lines.mapped('capital_repayment'))
                
                # Set values
                prop.total_invoiced = total_amount
                prop.total_paid = paid_amount
                prop.remaining_amount = prop.active_sale_id.total_selling_price - paid_amount
                prop.payment_progress = (paid_amount / total_amount) * 100 if total_amount else 0
            else:
                prop.total_invoiced = 0.0
                prop.total_paid = 0.0
                prop.remaining_amount = 0.0
                prop.payment_progress = 0.0
    
    @api.model
    def create(self, vals):
        return super(Property, self).create(vals)
    
    def write(self, vals):
        res = super(Property, self).write(vals)
        if 'state' in vals and vals['state'] == 'sold':
            property_sale = self.env['property.sale'].search([('property_id', '=', self.id), ('state', '=', 'confirm')], limit=1)
            if property_sale and property_sale.partner_id:
                self.write({'partner_id': property_sale.partner_id.id})
        return res
    
    def action_create_sale(self):
        """Create a new property sale from the property"""
        self.ensure_one()
        sale = self.env['property.sale'].create({
            'name': f"{self.name} - Sale",
            'property_id': self.id,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'start_date': fields.Date.today(),
            'state': 'draft'
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Property Sale',
            'res_model': 'property.sale',
            'view_mode': 'form',
            'res_id': sale.id,
            'target': 'current',
        }

    def action_view_sales(self):
        """View all sales related to this property"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Property Sales',
            'res_model': 'property.sale',
            'view_mode': 'tree,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
        }
    def action_view_related_properties(self):
        """View properties related to the same project"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Related Properties',
            'res_model': 'property.property',
            'view_mode': 'tree,form,kanban',
            'domain': [('project_name', '=', self.project_name), ('id', '!=', self.id)],
            'context': {'search_default_group_by_project': 1},
        }