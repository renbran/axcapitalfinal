from odoo import http
from odoo.http import request


class DiscussController(http.Controller):
    @http.route('/mail/get_model_name', methods=['POST'], type='json', auth='public')
    def get_model_name_of_model(self, model):
        return request.env[model]._description
    