


/* @odoo-module */

import { Component } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

/**
 * @typedef {Object} Props
 * @property {import("models").Thread} thread
 * @property {import("@mail/core/web/suggested_recipient").SuggestedRecipient} recipient
 * @extends {Component<Props, Env>}
 */
export class MessengerRecipient extends Component {
    static template = "us_messenger.MessengerRecipients";
    static props = ["thread", "recipient"];

    setup() {
        this.dialogService = useService("dialog");
        this.threadService = useService("mail.thread");
    }

    get titleText() {
        return _t("Add as recipient and follower (reason: %s)", this.props.recipient.reason);
    }

    onChangeCheckbox(ev) {
        this.props.recipient.checked = !this.props.recipient.checked;
    }
}
