# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import json
import hashlib, base64, hmac
import math
from odoo import http
from odoo.http import request
import requests
from odoo.exceptions import AccessError
from werkzeug.exceptions import abort
from werkzeug.exceptions import BadRequest
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)


country_data = {
}

class MyfatoorahController(http.Controller):

    def __init__(self, *args, **kwargs):
        super(MyfatoorahController, self).__init__(*args, **kwargs)
        self.country_data = self._fetch_countries_data()

    def _fetch_countries_data(self):
        url = "https://portal.myfatoorah.com/Files/API/mf-config.json"
        countries_response = requests.get(url, headers={"Content-Type":"application/json"})

        if countries_response.status_code == 200:
            try:
                countries_data = json.loads(countries_response.text)
                return countries_data
            except json.JSONDecodeError as e:
                _logger.error("Error decoding JSON response: %s", e)
        else:
            _logger.error("Error fetching countries data. Status code: %d", countries_response.status_code)
        #Return default values if request is empty or not working
        return {
            "KWT": {
                "portal": "https://portal.myfatoorah.com",
                "v1": "https://apikw.myfatoorah.com",
                "v2": "https://api.myfatoorah.com",
                "testPortal": "https://demo.myfatoorah.com",
                "testv1": "https://apidemo.myfatoorah.com",
                "testv2": "https://apitest.myfatoorah.com",
                "countryNameAr": "الكويت",
                "countryNameEn": "Kuwait"
            },
            "SAU": {
                "portal": "https://sa.myfatoorah.com",
                "v1": "https://apisa.myfatoorah.com",
                "v2": "https://api-sa.myfatoorah.com",
                "testPortal": "https://demo.myfatoorah.com",
                "testv1": "https://apidemo.myfatoorah.com",
                "testv2": "https://apitest.myfatoorah.com",
                "countryNameAr": "السعودية",
                "countryNameEn": "Saudi Arabia"
            },
            "ARE": {
                "portal": "https://portal.myfatoorah.com",
                "v1": "https://apiae.myfatoorah.com",
                "v2": "https://api.myfatoorah.com",
                "testPortal": "https://demo.myfatoorah.com",
                "testv1": "https://apidemo.myfatoorah.com",
                "testv2": "https://apitest.myfatoorah.com",
                "countryNameAr": "الإمارات العربية المتحدة",
                "countryNameEn": "United Arab Emirates"
            },
            "QAT": {
                "portal": "https://qa.myfatoorah.com",
                "v1": "https://apiqa.myfatoorah.com",
                "v2": "https://api-qa.myfatoorah.com",
                "testPortal": "https://demo.myfatoorah.com",
                "testv1": "https://apidemo.myfatoorah.com",
                "testv2": "https://apitest.myfatoorah.com",
                "countryNameAr": "قطر",
                "countryNameEn": "Qatar"
            },
            "BHR": {
                "portal": "https://portal.myfatoorah.com",
                "v1": "https://apibh.myfatoorah.com",
                "v2": "https://api.myfatoorah.com",
                "testPortal": "https://demo.myfatoorah.com",
                "testv1": "https://apidemo.myfatoorah.com",
                "testv2": "https://apitest.myfatoorah.com",
                "countryNameAr": "البحرين",
                "countryNameEn": "Bahrain"
            },
            "OMN": {
                "portal": "https://portal.myfatoorah.com",
                "v1": "https://apiom.myfatoorah.com",
                "v2": "https://api.myfatoorah.com",
                "testPortal": "https://demo.myfatoorah.com",
                "testv1": "https://apidemo.myfatoorah.com",
                "testv2": "https://apitest.myfatoorah.com",
                "countryNameAr": "عمان",
                "countryNameEn": "Oman"
            },
            "JOD": {
                "portal": "https://portal.myfatoorah.com",
                "v1": "https://apijo.myfatoorah.com",
                "v2": "https://api.myfatoorah.com",
                "testPortal": "https://demo.myfatoorah.com",
                "testv1": "https://apidemo.myfatoorah.com",
                "testv2": "https://apitest.myfatoorah.com",
                "countryNameAr": "اﻷردن",
                "countryNameEn": "Jordan"
            },
            "EGY": {
                "portal": "https://portal.myfatoorah.com",
                "v1": "https://apieg.myfatoorah.com",
                "v2": "https://api.myfatoorah.com",
                "testPortal": "https://demo.myfatoorah.com",
                "testv1": "https://apidemo.myfatoorah.com",
                "testv2": "https://apitest.myfatoorah.com",
                "countryNameAr": "مصر",
                "countryNameEn": "Egypt"
            }
        }

    @http.route("/invoice_link/myfatoorah/callback", type='http', auth='public', methods=['GET', 'POST'])
    def invoice_link_myfatoorah_return_url(self, **data):
        _logger.info("Received Myfatoorah return data:\n%s", data)
        request.env['payment.transaction']._handle_notification_data('myfatoorah', data)
        return request.redirect('/payment/status')

    @http.route("/invoice_link/myfatoorah/process", type='http', auth='public', methods=['GET', 'POST'])
    def invoice_link_myfatoorah_loading_page(self, **kw):
        odoo_base_url = request.httprequest.host_url
        payment_id = kw.get('paymentId')
        callback_url = f"{odoo_base_url}/invoice_link/myfatoorah/callback?paymentId={payment_id}"

        html_code = """
        <html lang="en-US">
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {
                        font-family: sans-serif;
                    }
                    .loader {
                      border: 13px solid #f3f3f3;
                      border-radius: 50%;
                      border-top: 13px solid #3498db;
                      width: 50px;
                      height: 50px;
                      -webkit-animation: spin 2s linear infinite; /* Safari */
                      animation: spin 2s linear infinite;
                    }

                    /* Safari */
                    @-webkit-keyframes spin {
                      0% { -webkit-transform: rotate(0deg); }
                      100% { -webkit-transform: rotate(360deg); }
                    }

                    @keyframes spin {
                      0% { transform: rotate(0deg); }
                      100% { transform: rotate(360deg); }
                    }
                </style>
            </head>
            <body>
                <center style="margin:10%">
                    Please wait while your transaction <b>{payment_id}</b> is processing...
                    <br/><br/>Please do not refresh or close the window
                    <br/><br/>
                    Callback url: {callback_url}
                    <div class="loader"></div>
                </center>
                <script>window.location = "{callback_url}";</script>
            </body>
        </html>
        """.replace("{payment_id}", payment_id).replace("{callback_url}", callback_url)


        # Return the HTML code as the response
        return html_code

    @http.route("/invoice_link/myfatoorah/webhook", type='json', auth='public', methods=['GET', 'POST'], website=False)
    def invoice_link_myfatoorah_webhook(self, **data):
        provider = http.request.env['payment.provider'].sudo().search([('code', '=', 'myfatoorah')], limit=1)
        secret_key = provider.myfatoorah_webhook
        # Validate MyFatoorah-Signature
        mf_signature = http.request.httprequest.headers.get('MyFatoorah-Signature')
        if not mf_signature:
            return http.Response(status=404)

        # Validate input
        body = http.request.httprequest.data
        input_data = json.loads(body)
        if not input_data.get('Data') or not input_data.get('EventType') or input_data.get('EventType') != 1:
            return http.Response(status=404)

        #Validate Signature
        if not self.is_signature_valid(input_data, secret_key, mf_signature, input_data.get('EventType')):
            return http.Response(status=404)
        return http.request.env['payment.transaction'].sudo()._handle_notification_data('myfatoorah', input_data)

    @staticmethod
    def is_signature_valid(json_data, secret_key, mf_signature, event_type):
        if json_data['Event'] == 'RefundStatusChanged':
            del json_data['Data']['GatewayReference']

        # Get the unordered array
        un_ordered_array = json_data['Data']

        # 1- Order all data properties in alphabetic and case insensitive.
        ordered_array = sorted(un_ordered_array.keys(), key=lambda x: x.lower())

        # 2- Create one string from the data after ordering its key to be like that key=value,key2=value2 ...
        ordered_string = ",".join(f"{key}={un_ordered_array[key] if un_ordered_array[key] else ''}" for key in ordered_array)

        # 4- Encrypt the string using HMAC SHA-256 with the secret key in binary mode.
        result = hmac.new(secret_key.encode('utf-8'), ordered_string.encode('utf-8'), hashlib.sha256).digest()

        # 5- Encode the result from the previous point with base64.
        hash_result = base64.b64encode(result).decode('utf-8')

        # The 'result' variable now contains the binary representation of the HMAC-SHA-256 hash
        if mf_signature == hash_result:
            return True
        else:
            return False

    @http.route("/payment/myfatoorah/initiate-session",  type='json', auth='public', methods=['GET', 'POST'], website=False)
    def myfatoorah_initiate_session(self, **data):
        provider = http.request.env['payment.provider'].sudo().search([('code', '=', 'myfatoorah')], limit=1)
        api_key = provider.myfatoorah_token
        base_api_url = ''
        state = provider.state
        country = provider.myfatoorah_country

        if state == 'enabled':
            base_api_url = self.country_data[country]['v2']
        else:
            base_api_url = self.country_data[country]['testv2']
        url = f"{base_api_url}/v2/InitiateSession"
        headers = {"Content-Type": "application/json", "Authorization": "Bearer " + api_key}
        # payload = {
        #     "CustomerIdentifier": "123123"
        # }
        payload = {}
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        dd = {
            "response" : json.loads(response.text),
            "base_api_url" : api_key
        }
        return dd

    @http.route("/payment/myfatoorah/initiate-payment",  type='json', auth='public', methods=['GET', 'POST'], website=True)
    def myfatoorah_initiate_payment(self, **data):
        try:
            request_data = json.loads(http.request.httprequest.data.decode('utf-8'))
            params = request_data.get('params')
            # Check if there is invoice id sent from frontend
            if params is not None and 'invoice_id' in params and params['invoice_id'] is not None:
                invoice_id = params['invoice_id']
                invoice = request.env['account.move'].sudo().search([
                    ('id', '=', invoice_id)
                ], limit=1)
                if invoice:
                    amount = invoice.amount_total
                    currency_iso = invoice.currency_id.name
                else:
                    return {
                        "success" : False,
                        "message" : "Invalid Invoice id"
                    }
            # Check if there is order_id saved in session
            else:
                order_id = request.session.get('sale_order_id')
                order = request.env['sale.order'].sudo().search([
                    ('id', '=', order_id),
                    ('state', '=', 'draft')
                ], limit=1)

                if order:
                    amount = order.amount_total
                    currency_iso = order.currency_id.name
                else:
                    return {
                        "success" : False,
                        "message" : "Invalid order details, please try again"
                    }

            provider = http.request.env['payment.provider'].sudo().search([('code', '=', 'myfatoorah')], limit=1)
            api_key = provider.myfatoorah_token
            state = provider.state
            country = provider.myfatoorah_country

            if state == 'enabled':
                base_api_url = self.country_data[country]['v2']
            else:
                base_api_url = self.country_data[country]['testv2']


            url = f"{base_api_url}/v2/InitiatePayment"
            headers = {"Content-Type": "application/json", "Authorization": "Bearer " + api_key}
            payload = {
                "InvoiceAmount" : amount,
                "CurrencyIso"   : currency_iso
            }
            mf_response = requests.post(url, data=json.dumps(payload), headers=headers)
            gateways = json.loads(mf_response.text)


            #Get Currency Rates
            currency_rates = self.get_currency_exchange_rates()
            rates = json.loads(currency_rates)
            currency_rate = self.get_one_currency_rate(currency_iso, rates)

            #Add total amount to loop
            mf_gateways = gateways['Data']['PaymentMethods']
            checkoutGateways = {'all': [], 'cards': [], 'form': [], 'ap': [], 'gp': []}
            for gateway in mf_gateways:
                gateway['GatewayTotalAmount'] = self.get_payment_total_amount(gateway, rates, currency_rate)
                if gateway['PaymentMethodCode'] == "gp":
                    checkoutGateways['gp'] = gateway
                    checkoutGateways['all'].append(gateway)
                elif gateway['PaymentMethodCode'] == "ap":
                    checkoutGateways['ap'] = gateway
                    checkoutGateways['all'].append(gateway)
                else:
                    if gateway['IsEmbeddedSupported']:
                        checkoutGateways['form'].append(gateway)
                    elif not gateway['IsDirectPayment']:
                        checkoutGateways['cards'].append(gateway)
                    checkoutGateways['all'].append(gateway)

            response = {
                "success" : True,
                "mf_response" : gateways,
                "currency_code" : currency_iso,
                "country_code" : provider.myfatoorah_country,
                "state" : state,
                "amount" : amount,
                "checkout_gateways" : checkoutGateways
            }

            return response
        except AccessError:
            return "Access denied"

    @http.route("/payment/myfatoorah/execute-payment", type='json', auth='public', methods=['POST'], website=False)
    def myfatoorah_execute_payment(self, **kw):
        request_data = json.loads(http.request.httprequest.data.decode('utf-8'))
        params = request_data.get('params')
        if params is not None and 'SessionId' in params:
            session_id = params['SessionId']
        else:
            session_id = None

        if params is not None and 'PaymentMethodId' in params:
            payment_method_id = params['PaymentMethodId']
        else:
            payment_method_id = None

        if not session_id and not payment_method_id:
            return {
                "success" : False,
                "status_code" : 422,
                "message" : "Session id and payment method id cannot be empty"
            }

        # for key,value in request.session.items():
        #     _logger.info("Myfatoorah key: %s value: %s ", key, value)

        tarnsaction_id = request.session.get('__payment_monitored_tx_id__')
        customer_reference = ''
        transaction = ''
        if tarnsaction_id:
            transaction = request.env['payment.transaction'].sudo().search([
                ('id', '=', tarnsaction_id),
                ('state', '=', 'draft')
            ], limit=1)
            if transaction:
                customer_reference = transaction.reference
            else:
                return {
                    "status_code" : 422,
                    "message" : "Invalid Transaction"
                }

        odoo_base_url = request.httprequest.host_url

        provider = http.request.env['payment.provider'].sudo().search([('code', '=', 'myfatoorah')], limit=1)
        api_key = provider.myfatoorah_token
        base_api_url = ''
        state = provider.state
        country = provider.myfatoorah_country

        if state == 'enabled':
            base_api_url = self.country_data[country]['v2']
        else:
            base_api_url = self.country_data[country]['testv2']

        url = f"{base_api_url}/v2/ExecutePayment"
        headers = {"Content-Type": "application/json", "Authorization": "Bearer " + api_key}

        store_currency = transaction.currency_id.name
        amount =  transaction.amount

        payload = {
            "InvoiceValue": amount,
            "DisplayCurrencyIso" : store_currency,
            "CallBackUrl": f"{odoo_base_url}/invoice_link/myfatoorah/process",
            "ErrorUrl": f"{odoo_base_url}/invoice_link/myfatoorah/process",
            "CustomerReference" : customer_reference
        }

        if session_id:
            payload['SessionId'] = session_id
        elif payment_method_id:
            payload['PaymentMethodId'] = payment_method_id
        else:
            return {
                "success" : False,
                "status_code" : 422,
                "message" : "Invalid Payload"
            }

        _logger.info("Myfatoorah payload:\n%s", payload)

        response = requests.post(url,  json=payload, headers=headers)
        return {
            "success" : True,
            "status_code" : 200,
            "message" : "success",
            "data" : response.text
        }

    @http.route("/payment/myfatoorah/get-currency-rates",  type='json', auth='public', methods=['GET', 'POST'], website=False)
    def get_currency_exchange_rates(self, **kw):
        provider = http.request.env['payment.provider'].sudo().search([('code', '=', 'myfatoorah')], limit=1)
        country = provider.myfatoorah_country
        state = provider.state
        api_key = provider.myfatoorah_token

        headers = {"Content-Type": "application/json", "Authorization": "Bearer " + api_key}

        if state == 'enabled':
            base_api_url = self.country_data[country]['v2']
        else:
            base_api_url = self.country_data[country]['testv2']
        url = f"{base_api_url}/v2/GetCurrenciesExchangeList"
        response = requests.get(url, headers = headers)
        return response.text

    @http.route("/payment/myfatoorah/get-one_currency_rate",  type='json', auth='public', methods=['GET', 'POST'], website=False)
    def get_one_currency_rate(self, displayCurrencyIso, allRates):
        for rate in allRates:
            if rate['Text'] == displayCurrencyIso:
                return float(rate['Value'])

    @http.route("/payment/myfatoorah/get-payment_total_amount",  type='json', auth='public', methods=['GET', 'POST'], website=False)
    def get_payment_total_amount(self, paymentMethod, allRates, currencyRate):
        if paymentMethod['PaymentCurrencyIso'] == paymentMethod['CurrencyIso']:
            return math.ceil(math.trunc(paymentMethod['TotalAmount'] * 1000) / 10) / 100
        #baseTotalAmount = math.trunc(paymentMethod['TotalAmount'] / currencyRate * 100) / 100
        dueAmount = round(paymentMethod['TotalAmount'] / currencyRate, 3)
        baseTotalAmount = math.ceil(math.trunc(paymentMethod['TotalAmount'] / currencyRate * 1000) / 10) / 100
        paymentCurrencyRate = self.get_one_currency_rate(paymentMethod['PaymentCurrencyIso'], allRates)
        if paymentCurrencyRate != 1:
            return math.ceil(baseTotalAmount * paymentCurrencyRate * 100) / 100
        return baseTotalAmount

    @http.route("/payment/myfatoorah/get-currency-iso",  type='json', auth='public', methods=['GET', 'POST'], website=False)
    def myfatoorah_currency_currency_iso(self, currency_id=None):
        if not currency_id:
            return {"error": "No currency ID provided"}
        currency = request.env['res.currency'].sudo().browse(currency_id)
        if currency.exists():
            return {"iso_code": currency.name}
        return {"error": "Currency not found"}