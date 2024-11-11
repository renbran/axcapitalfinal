from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import timedelta


class PropertySale(models.Model):
    _name = 'property.sale'
    _description = 'Sale of the Property'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

    name = fields.Char(string='Reference', readonly=True, copy=False, default='New')
    property_id = fields.Many2one(
        'property.property', required=True,
        domain="[('state', '=', 'available'), ('sale_rent', '=', 'for_sale')]",
        string="Property Name"
    )
    partner_id = fields.Many2one('res.partner', string="Customer", required=True)
    order_date = fields.Date(string="Order Date", default=fields.Date.context_today)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
    ], default='draft', string="State", tracking=True)
    invoice_id = fields.Many2one('account.move', readonly=True, string="Invoice")
    invoiced = fields.Boolean(string='Invoiced', default=False)
    sale_price = fields.Monetary(
        string="Sale Price", related='property_id.unit_price', readonly=False, store=True
    )
    currency_id = fields.Many2one(
        'res.currency', 'Currency', required=True,
        readonly=True, default=lambda self: self.env.ref('base.AED'), store=True
    )
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company, required=True
    )

    # Down Payment and DLD Fees
    down_payment = fields.Monetary(string="Down Payment", help="Initial payment to start the installment plan.")
    remaining_balance = fields.Monetary(string="Remaining Balance", compute="_compute_remaining_balance", store=True)
    dld_fee = fields.Monetary(string="DLD Fee", compute="_compute_dld_fee", store=True, help="4% of the sale price.")
    desired_years = fields.Integer(string="Desired Years to Complete Installment", default=1)

    # Installment Information
    no_of_installments = fields.Integer(
        string="Number of Installments", compute="_compute_installments_count", store=True
    )
    amount_per_installment = fields.Float(
        string="Amount Per Installment", compute="_compute_installment_amount", store=True
    )
    property_sale_line_ids = fields.One2many(
        'property.sale.line', 'property_sale_id', string="Installment Payments", auto_join=True
    )

    @api.model
    def create(self, vals):
        """Generate Reference for the sale order."""
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('property.sale') or 'New'
        return super(PropertySale, self).create(vals)

    @api.depends('sale_price')
    def _compute_dld_fee(self):
        """Calculate DLD fee as 4% of the sale price."""
        for rec in self:
            rec.dld_fee = rec.sale_price * 0.04

    @api.depends('sale_price', 'down_payment', 'dld_fee')
    def _compute_remaining_balance(self):
        """Calculate remaining balance after down payment and DLD fee."""
        for rec in self:
            rec.remaining_balance = rec.sale_price - rec.down_payment - rec.dld_fee

    @api.depends('desired_years')
    def _compute_installments_count(self):
        """Calculate the total number of installments based on the desired years."""
        for rec in self:
            rec.no_of_installments = rec.desired_years * 12  # Monthly installments for each year

    @api.depends('remaining_balance', 'no_of_installments')
    def _compute_installment_amount(self):
        """Calculate installment amount based on remaining balance and number of installments."""
        for rec in self:
            if rec.no_of_installments > 0:
                rec.amount_per_installment = rec.remaining_balance / rec.no_of_installments
            else:
                rec.amount_per_installment = 0.0

    def compute_remaining_installments(self):
        """Compute and generate remaining installment lines based on desired years."""
        self.ensure_one()
        self.property_sale_line_ids = [(5, 0, 0)]  # Clear previous installments
        installment_date = fields.Date.context_today(self)

        for i in range(1, self.no_of_installments + 1):
            self.property_sale_line_ids = [(0, 0, {
                'serial_number': i,
                'capital_repayment': self.amount_per_installment,
                'remaining_capital': self.remaining_balance - (self.amount_per_installment * (i - 1)),
                'collection_date': installment_date,
            })]
            installment_date += timedelta(days=30)  # Advance by one month for each installment

    def action_confirm(self):
        """Confirm the sale order."""
        for record in self:
            record.state = 'confirm'

    roperty_id = fields.Many2one('property.property', string='Property')
    product_id = fields.Many2one('product.product', string='Product', required=True)

    @api.model
    def default_get(self, fields_list):
        res = super(PropertySale, self).default_get(fields_list)
        default_product = self._get_default_product()
        res.update({'product_id': default_product.id})  # Set the default product ID
        return res

    def _get_default_product(self):
        # Get the product "Primary Commission" (assuming it's the default)
        primary_commission_product = self.env['product.product'].search([('name', '=', 'Primary Commission')], limit=1)

        if not primary_commission_product:
            raise UserError('The "Primary Commission" product is not defined.')

        # Optionally, if the property has a size (or difficulty to paint) that requires a different product