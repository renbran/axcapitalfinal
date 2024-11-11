from odoo import models


class Base(models.AbstractModel):
    _inherit = "base"

    # delete_my_code_new
    def set_link(self, relation_name, ref, bot_id, sync_date=None, allow_many2many=False):
        return self.env["us.messenger.link"]._set_link_odoo(
            self, relation_name, ref, bot_id, sync_date, allow_many2many)

    def search_links(self, relation_name, bot_id, refs=None):
        return (
            self.env["us.messenger.link"]
            .with_context(messenger_link_odoo_model=self._name)
            ._search_links_odoo(self, relation_name, bot_id, refs))

