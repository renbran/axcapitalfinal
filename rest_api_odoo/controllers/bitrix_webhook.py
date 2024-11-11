from odoo import http
from odoo.http import request

class Bitrix24WebhookController(http.Controller):

    @http.route('/bitrix/webhook', type='json', auth='public', methods=['POST'], csrf=False)
    def handle_webhook(self):
        # Extract incoming data
        data = request.jsonrequest

        # Initialize response
        response = {'status': 'success'}

        # Check if required fields are present
        deal_name = data.get('deal_name')
        deal_amount = data.get('amount')
        partner_name = data.get('contact_name')

        if not all([deal_name, deal_amount, partner_name]):
            response['status'] = 'error'
            response['message'] = 'Missing required fields'
            return response

        # Fetch or create the partner in Odoo
        partner = request.env['res.partner'].sudo().search([('name', '=', partner_name)], limit=1)
        if not partner:
            partner = request.env['res.partner'].sudo().create({'name': partner_name})

        # Create a sales order based on the incoming deal data
        sales_order = request.env['sale.order'].sudo().create({
            'partner_id': partner.id,
            'name': deal_name,
            'amount_total': deal_amount,
        })

        # Return the sales order ID in the response
        response['sales_order_id'] = sales_order.id
        return response
