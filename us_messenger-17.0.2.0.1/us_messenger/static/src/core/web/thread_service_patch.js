/* @odoo-module */

import { ThreadService } from "@mail/core/common/thread_service";
import { nextId } from "@mail/core/web/thread_service_patch";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

let nextRecipientId = 1;
patch(ThreadService.prototype, {
    /**
     * @override
     */
    async fetchData(
        thread,
        requestList = ["activities", "followers", "attachments", "messages", "suggestedRecipients"]
    ) {
        const result = await super.fetchData(...arguments);
        if ("followers" in result || "suggestedRecipients" in result) {
            await this.insertMessengerRecipients(thread, thread.suggestedRecipients, thread.followers);
        }
        return result;
    },
    /**
     * @param {import("models").Thread} thread
     * @param {import("@mail/core/web/suggested_recipient").SuggestedRecipient[]} dataRecipients
     * @param {import("models").Follower} dataFollowers
     */
    async insertMessengerRecipients(thread, dataRecipients, dataFollowers) {
        const recipients = [];
        const partners = [];
        dataRecipients.map((recipent) => partners.push(recipent.persona?.id));
        dataFollowers.map((follower) => partners.push(follower.partner?.id));

        let partnerIds = await this.orm.call("res.partner", "search_read", [], {
                    domain: [
                         "|",
                        ["parent_id", "in", partners],
                        ["id", "in", partners],
                    ],
                },
        );
        partnerIds = partnerIds.filter( partner => !partner.user_ids.length);
        for (const partner of partnerIds) {
            if (partner && partner.type_messenger && partner.type_messenger !== "none") {
                recipients.push({
                    id: nextRecipientId++,
                    name: partner.name,
                    persona: partner.id ? { type: "partner", id: partner.id } : false,
                    type_messenger: partner.type_messenger,
                    checked: false,
                });
            }
        }
        thread.messengerRecipients = recipients;
    },
});