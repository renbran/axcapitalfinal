# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import requests
import json
from odoo.http import request
from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    capture_manually = fields.Boolean(related='provider_id.capture_manually')

    #=== ACTION METHODS ===#
    def _get_tx_from_notification_data(self, provider_code, notification_data):
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'myfatoorah':
            return tx
        provider_id = request.env['payment.provider'].sudo().search([
            ('code', '=', 'myfatoorah')
        ], limit=1)
        api_key = provider_id.myfatoorah_token
        base_api_url = provider_id._myfatoorah_get_api_url()
        url = f"{base_api_url}/v2/GetPaymentStatus"
        payment_id = ''
        if notification_data.get('paymentId'):
            payment_id = notification_data.get('paymentId')
        else:
            payment_id = notification_data['Data']['PaymentId']
        payload = json.dumps({
            "Key": payment_id,
            "KeyType": "paymentId"
        })
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {api_key}',
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        response_data = response.json()
        _logger.info("MyFatoorah Payment Status: \n%s", response_data)
        payment_status = ''
        for transaction in response_data['Data']['InvoiceTransactions']:
            if transaction['PaymentId'] == payment_id:
                payment_status = transaction['TransactionStatus']
        customer_reference = response_data['Data']['CustomerReference']
        tx = self.sudo().search([
            ('provider_code', '=', 'myfatoorah'),
            ('reference', '=', customer_reference),
        ])
        notification_data.update({
            'invoice_status': response_data["Data"]["InvoiceStatus"],
            'payment_status': payment_status,
            'reference' : customer_reference
        })
        return tx
    
    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'myfatoorah':
            return res
        api_key = self.provider_id.myfatoorah_token
        api_url = "{}/v2/SendPayment".format(self.provider_id._myfatoorah_get_api_url())
        payload = self._prepare_myfatoorah_invoice_link_payload(processing_values)
        #Log MyFatoorah Payload
        _logger.info("Myfatoorah Payload is :\n%s", payload)
        headers = {"Content-Type": "application/json", "Authorization": "Bearer " + api_key}
        response = requests.post(api_url, data=json.dumps(payload), headers=headers)
        _logger.info("Myfatoorah Response is :\n%s", response)
        url = "https://portal.myfatoorah.com/Files/API/mf-config.json"
        mf_countries = requests.get(url).json()
        _logger.info("mf_countries: \n%s", mf_countries)
        invoice_url = '#'
        if response.status_code != 200:
            _logger.info("Failed on generating invoice with error:\n%s", response.json())
        if response.status_code == 200:
            response_data = response.json()
            self.provider_reference = response_data["Data"]["InvoiceId"]
            # self._set_pending("myfatoorah transaction pending invoice payment.")
            invoice_url = response_data["Data"]["InvoiceURL"]
        return {
            'invoice_link': invoice_url,
        }  

    def _process_notification_data(self, notification_data):
        super()._process_notification_data(notification_data)
        tx = self.search([
            ('provider_code', '=', 'myfatoorah'),
            ('reference', '=', notification_data['reference']),
        ])
        _logger.info("notification tx: \n%s", tx)
        if self.provider_code != 'myfatoorah':
            return
        else:
            if notification_data['invoice_status'] == 'Paid':
                self._set_done()
                order = tx.sale_order_ids
                _logger.info("Order ids: \n%s", order)
                order.action_confirm()
            else:
                if notification_data['invoice_status'] == 'Pending':
                    if notification_data['payment_status'] == 'Failed':
                        self._set_error(
                            "Myfatoorah: " + _("received invalid transaction status: %s",
                                               notification_data['payment_status']))
                    else:
                        self._set_pending()
                else:
                    self._set_pending()

    def _prepare_myfatoorah_invoice_link_payload(self, processing_values):
        odoo_base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        language = 'ar' if self.partner_lang == 'ar_001' or self.partner_lang == 'ar_SY' else 'en'
        payload = {
            # required fields
            "CustomerName": self.partner_name,
            "InvoiceValue": processing_values['amount'],
            "NotificationOption": "LNK",
            # optional fields
            "CustomerEmail": self.partner_email,  # Mandatory if the NotificationOption = EML or ALL
            "CustomerAddress": {
                "Block": "string",
                "Street": "string",
                "HouseBuildingNo": "string",
                "Address": self.partner_address,
                "AddressInstructions": self.partner_city
            },
            "CustomerReference": processing_values['reference'],
            "CallBackUrl": f"{odoo_base_url}/invoice_link/myfatoorah/process",
            "ErrorUrl": f"{odoo_base_url}/invoice_link/myfatoorah/process",
            "DisplayCurrencyIso": self.currency_id.name if self.currency_id.name else 'KWD',
            "Language": language
            # "MobileCountryCode": self,
            # "CustomerMobile": "12345678",  # Mandatory if the NotificationOption = SMS or ALL
        }

        #invoice_items = []
        #for order in self.sale_order_ids:
        #    for line in order.order_line:
        #        invoice_items.append({
        #            "ItemName": line.name,
        #            "Quantity": int(line.product_uom_qty),
        #            "UnitPrice": self.get_decimal_points(line.price_unit, self.currency_id.name)
        #        })
        #payload.update({
        #    "InvoiceItems": invoice_items
        #})
        return payload
