# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.addons.myfatoorah_gateway import const
import requests

_logger = logging.getLogger(__name__)

country_data = {
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
        "portal": "https://portal.myfatoorah.com",
        "v1": "https://apiqa.myfatoorah.com",
        "v2": "https://api.myfatoorah.com",
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

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('myfatoorah', "Myfatoorah")],
        ondelete={'myfatoorah': 'set default'}
    )
    myfatoorah_token = fields.Char(string='Token', help="Copy your access token from MyFatoorah portal")
    myfatoorah_country = fields.Selection(selection=[
        ('KWT', 'Kuwait'),
        ('SAU', 'Saudi Arabia'),
        ('ARE', 'United Arab Emirates'),
        ('QAT', 'Qatar'),
        ('BHR', 'Bahrain'),
        ('OMN', 'Oman'),
        ('JOD', 'Jordan'),
        ('EGY', 'Egypt'),
    ], required=False, string="Client Country", help="Chhose the country of your myfatoorah account")
    myfatoorah_webhook = fields.Char(string='Webhook Secret Key', help="Copy your webhook secret key from MyFatoorah portal")

    
    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()        
        res['myfatoorah'] = {'mode': 'unique', 'domain': [('type', '=', 'bank')]}
        return res
    
    
    def _myfatoorah_get_api_url(self):
        _logger.info("Myfatoorah Api url is :\n%s", self)
        if self:
            if self.state == 'enabled':
                return country_data[self.myfatoorah_country]['v2']
            else:
                return country_data[self.myfatoorah_country]['testv2']
        else:
            # Handle the case when the recordset is empty
            return None



    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'myfatoorah':
            return default_codes
        return const.DEFAULT_PAYMENT_METHODS_CODES
    

    @api.onchange('myfatoorah_token')
    def _check_provider_token(self):
        for record in self:
            if record.code == 'myfatoorah' and record.myfatoorah_token and record.myfatoorah_country and record.state not in('disabled'):
                base_api_url = self._myfatoorah_get_api_url()
                url = f"{base_api_url}/v2/InitiateSession"
                headers = {"Content-Type": "application/json", "Authorization": "Bearer " + record.myfatoorah_token}
                payload = {}
                response = requests.post(url, data=json.dumps(payload), headers=headers)
                if response.status_code == 401:
                    raise UserError("Invalid MyFatoorah token, Please contact your account manager")
        
        
    @api.onchange('state')
    def _check_provider_state(self):
        for record in self:
            if record.code == 'myfatoorah' and record.myfatoorah_token and record.state not in('disabled'):
                base_api_url = self._myfatoorah_get_api_url()
                url = f"{base_api_url}/v2/InitiateSession"
                headers = {"Content-Type": "application/json", "Authorization": "Bearer " + record.myfatoorah_token}
                payload = {}
                response = requests.post(url, data=json.dumps(payload), headers=headers)
                if response.status_code == 401:
                    raise UserError("Invalid MyFatoorah token, Please contact your account manager")
