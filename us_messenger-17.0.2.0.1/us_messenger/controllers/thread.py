from odoo.addons.mail.controllers.thread import ThreadController


class ThreadController(ThreadController):

    def _get_allowed_message_post_params(self):
        res = super(ThreadController, self)._get_allowed_message_post_params()
        res.add('document_message_id')
        return res
