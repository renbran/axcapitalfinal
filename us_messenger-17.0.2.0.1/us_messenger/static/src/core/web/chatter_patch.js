/** @odoo-module */

import { Chatter } from "@mail/core/web/chatter";
import { MessengerRecipientsList } from "@us_messenger/core/web/messenger_recipient_list";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Chatter, {
   components: { ...Chatter.components, MessengerRecipientsList },
});
