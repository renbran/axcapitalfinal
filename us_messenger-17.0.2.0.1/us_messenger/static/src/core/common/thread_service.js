/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { ThreadService } from "@mail/core/common/thread_service";
import { patch } from "@web/core/utils/patch";

patch(ThreadService.prototype, {
    /**
    * @override
    */
    async post(
        thread,
        body,
        {
            attachments = [],
            isNote = false,
            parentId,
            mentionedChannels = [],
            mentionedPartners = [],
            cannedResponseIds,
        } = {}
    ) {
        const message = await super.post(thread, body, {attachments,isNote,parentId,mentionedChannels,mentionedPartners,cannedResponseIds});
        if (thread.type === 'chatter'){
             let params = await this.getMessagePostParams({
                attachments,
                body,
                cannedResponseIds,
                isNote,
                mentionedChannels,
                mentionedPartners,
                thread,
            });

            Object.assign(params.post_data, {document_message_id:message.id});
            Object.assign(params, {thread_model:'discuss.channel'});

            let model_name = thread.model_name;
            if (!model_name){
                model_name = await this.rpc(`/mail/get_model_name`, {model:thread.model});
                if (!model_name){
                    model_name = thread.model;
                }
            }

            params.post_data.body += `<b><a href="/web#id=${thread.id}&model=${thread.model}"><br/><br/>Link on model ${model_name} "${thread.name}". </a></b>`;

            let checked_recipients = thread.messengerRecipients.filter((recipient) => recipient.checked === true)
            let recipients_ids = checked_recipients.map((recipient) => recipient.persona?.id);

            let undefined_recpients = thread.messengerRecipients.filter((recipient) => !recipient.persona?.id);
            if (undefined_recpients.length > 0){
                let names = undefined_recpients.map((recipient) => recipient.name);
                this.env.services.notification.add(_t(names.join() + " hasn't partner"),{
                        type: 'warning',
                    });
                    return;
            }

            let userPartner = this.user.partnerId;

            let userPartnerS = await this.orm.call("res.partner", "search_read", [], {
                    domain: [
                        ["id", "=", userPartner],
                    ],
                },
            );

            let partners = await this.orm.call("res.partner", "search_read", [], {
                    domain: [
                        ["id", "in", recipients_ids],
                    ],
                },
            );


            for(let partner of partners){
                let intersectionChannels = partner.channel_ids.filter(value => userPartnerS[0].channel_ids.includes(value));
                if (intersectionChannels[0] === undefined){
                    this.env.services.notification.add(_t("The user is not attached to the channel"),{
                        type: 'warning',
                    });
                    return;
                }
                Object.assign(params, {thread_id:intersectionChannels[0]});
                await this.rpc(this.getMessagePostRoute(thread), params);
            }
        }
        return message;
    },
});
