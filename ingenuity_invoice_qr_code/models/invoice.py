from odoo import models, fields, api
from odoo.http import request
import qrcode
import base64
from io import BytesIO

def generate_qr_code(value):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=20,
        border=4
    )
    qr.add_data(value)
    qr.make(fit=True)
    img = qr.make_image()
    stream = BytesIO()
    img.save(stream, format="PNG")
    qr_img = base64.b64encode(stream.getvalue())
    return qr_img


class AccountMove(models.Model):
    _inherit = 'account.move'

    qr_image = fields.Binary("QR Code", compute='_generate_qr_code')
    qr_in_report = fields.Boolean('Display QRCode in Report?')

    def _generate_qr_code(self):
        self.qr_image = None
        for order in self:
            # Get the base URL of the Odoo instance
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            
            # Generate the portal URL with access token for the invoice
            relative_url = order.get_portal_url()
            
            # Combine the base URL with the relative URL
            full_url = base_url + relative_url
            
            # Generate the QR code for the full URL
            qr_img = generate_qr_code(full_url)
            
            # Write the generated QR code image to the record
            order.write({
                'qr_image': qr_img
            })
            print(self.qr_image, "QR code generated with full portal URL")