/* @odoo-module */

import { MessengerRecipient } from "@us_messenger/core/web/messenger_recipient";

import { Component, useState } from "@odoo/owl";

/**
 * @typedef {Object} Props
 * @property {import("models").Thread} thread
 * @property {string} className
 * @property {string} styleString
 * @extends {Component<Props, Env>}
 */
export class MessengerRecipientsList extends Component {
    static template = "us_messenger.MessengerRecipientsList";
    static components = { MessengerRecipient };
    static props = ["thread", "className", "styleString"];

    setup() {
        this.state = useState({
            showMore: false,
        });
    }

    get messengerRecipients() {
        if (!this.state.showMore) {
            return this.props.thread.messengerRecipients.slice(0, 3);
        }
        return this.props.thread.messengerRecipients;
    }
}
