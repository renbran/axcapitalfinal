/** @odoo-module **/

import paymentForm from '@payment/js/payment_form';
import { jsonrpc, RPCError } from "@web/core/network/rpc_service";
import { _t } from "@web/core/l10n/translation";

paymentForm.include({

    myFatoorahSessionId: undefined,

    // #=== DOM MANIPULATION ===#

    /**
     * Prepare the inline form of myfatoorah for direct payment.
     *
     * @override method from @payment/js/payment_form
     * @private
     * @param {number} providerId - The id of the selected payment option's provider.
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The online payment flow of the selected payment option.
     * @return {void}
     */
    async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
        if(is_form_prepared){
            return;
        }
        if (providerCode !== 'myfatoorah') {
            this._super(...arguments);
            return;
        } else if (flow === 'token') {
            return;
        }
        this._setPaymentFlow('direct');

        var is_google_pay_enabled = false;
        var is_apple_pay_enabled = false;
        var is_card_view_enabled = false;
        var invoice_id = null;
        var currentURL = window.location.href;
        if(currentURL.includes("invoices")){
            var match = currentURL.match(/invoices\/(\d+)/);
            invoice_id = match[1];
        }
        jsonrpc('/payment/myfatoorah/initiate-payment', {
            "invoice_id" : invoice_id
        }).then((initiatePaymentResult) =>
        {
            if (!initiatePaymentResult.success){
                this._displayErrorDialog(_t("Validation Error"), initiatePaymentResult.message);
                this._enableButton();
                return;
            }
            const country_code = initiatePaymentResult.country_code;
            const state = initiatePaymentResult.state;
            const checkout_gateways = initiatePaymentResult.checkout_gateways;
            const cards_payment_methods = checkout_gateways?.cards;
            if(checkout_gateways.gp){
                is_google_pay_enabled = true;
            }

            if(checkout_gateways.ap && window.ApplePaySession){
                is_apple_pay_enabled = true;
            }

            if(checkout_gateways.form.length > 0){
                is_card_view_enabled = true;
            }

            if(!is_google_pay_enabled){
                document.getElementById('mf-sectionGP')?.remove();
                if(!is_apple_pay_enabled && window.ApplePaySession){
                    document.getElementById('mf-or-cardsDivider')?.remove();
                }
            }

            if(!is_apple_pay_enabled && window.ApplePaySession){
                document.getElementById('mf-sectionAP')?.remove();
            }

            if(!is_card_view_enabled){
                document.getElementById('mf-cardView')?.remove();
            }

            if(cards_payment_methods.length === 0){
                document.getElementById('mf-sectionCard')?.remove();
                if(!is_google_pay_enabled && !is_apple_pay_enabled && window.ApplePaySession){
                    document.getElementById('mf-or-formDivider')?.remove();
                }
            }

            if(!is_google_pay_enabled
                && (!is_apple_pay_enabled)
                && !is_card_view_enabled
                && cards_payment_methods.length === 0){
                document.getElementById('mf-paymentGateways')?.remove();
                document.getElementById('mf-noPaymentGateways').style.display = 'block';
            }

            if(is_google_pay_enabled){
                _prepareGooglePay(country_code, state);
            }

            if(is_apple_pay_enabled){
                _prepareApplePay(country_code, state);
            }

            if(is_card_view_enabled){
                _prepareForm(country_code, state);
            }

            if(cards_payment_methods.length > 0){
                _prepareCards(cards_payment_methods);
            }

            jsonrpc('/payment/myfatoorah/initiate-session', {}).then((initiateSessionResponse) =>
            {
                var sessionId = initiateSessionResponse?.response.Data?.SessionId;

                // Load Google Pay
                if(is_google_pay_enabled){
                    //_loadGooglePay(checkout_gateways.gp.GatewayTotalAmount, country_code, checkout_gateways.gp.PaymentCurrencyIso, sessionId)
                    var gpConfig = {
                        sessionId: sessionId,
                        amount: `${checkout_gateways.gp.GatewayTotalAmount}`,
                        currencyCode: checkout_gateways.gp.PaymentCurrencyIso,
                        countryCode: country_code,
                        cardViewId: "mf-gp-element",
                        callback: this._onClickPayment.bind(this),
                        style: {
                            frameHeight: 51,
                            button: {
                                height: "40px",
                                text: "Pay", // Accepted texts: ["book", "buy", "checkout", "donate", "order", "pay", "plain", "subscribe"]
                                borderRadius: "8px",
                                color: "black", // Accepted colors: ["black", "white", "default"]
                                language: "en"
                            }
                        }
                    };

                    myFatoorahGP.init(gpConfig);
                    window.addEventListener("message", myFatoorahGP.recievedMessage);
                }

                // Load Apple pay
                if(is_apple_pay_enabled){
                    var apConfig = {
                    sessionId: sessionId,
                    countryCode: country_code,
                    currencyCode: checkout_gateways.ap.PaymentCurrencyIso,
                    amount: `${checkout_gateways.ap.GatewayTotalAmount}`,
                    cardViewId: "mf-ap-element",
                    callback: this._onClickPayment.bind(this),
                    };
                    myFatoorahAP.init(apConfig);
                    window.addEventListener("message", myFatoorahAP.recievedMessage);
                }

                if(is_card_view_enabled){
                    var config = {
                        countryCode: country_code,
                        sessionId: sessionId,
                        cardViewId: "mf-form-element",
                        style: {
                            direction: "ltr",
                            error:
                            {
                                borderRadius: "0px"
                            },
                            input: {
                                inputMargin: "-1px",
                                borderRadius: "0px"
                            }
                        },
                    };
                    myFatoorah.init(config);
                    window.addEventListener("message", myFatoorah.recievedMessage);
                }
                is_form_prepared = true;
                return;
            });
        })
        .catch(error => {
            if (error instanceof RPCError) {
                this._displayErrorDialog(_t("Payment processing failed"), "Ops! Something went wrong on initiating MyFatoorah Payment, Please contact admin");
                this._enableButton?.(); // This method doesn't exists in Express Checkout form.
            } else {
                return Promise.reject(error);
            }
        });
    },

    // #=== PAYMENT FLOW ===#

    /**
     * Simulate a feedback from a payment provider and redirect the customer to the status page.
     *
     * @override method from payment.payment_form
     * @private
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {object} processingValues - The processing values of the transaction.
     * @return {void}
     */
    async _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== 'myfatoorah') {
            this._super(...arguments);
            return;
        }
        if(myFatoorahPaymentMethodId != undefined){ /* Cards */
            return this._myfatoorahExecutePayment(null, myFatoorahPaymentMethodId);
        }else if(this.myFatoorahSessionId != undefined){ /*Google and Apple pay*/
            return this._myfatoorahExecutePayment(this.myFatoorahSessionId);
        } else{ /* Card view */
            myFatoorah.submit()
                .then((response) => {
                    var sessionId = response.sessionId;
                    return this._myfatoorahExecutePayment(sessionId);
                }).catch((error) => {
                    this._displayErrorDialog(_t("Payment processing failed"), error);
                    this._enableButton?.();
                });
        }
    },

    _onClickPayment: function(response) {
        var button = document.querySelector("button[name='o_payment_submit_button']");
        if (button) {
            this.myFatoorahSessionId = response.sessionId;
            button.click();
        } else {
            console.error('Button not found');
        }
    },

    _myfatoorahExecutePayment: function(session_id = null, payment_method_id = null){
        if(session_id == null && payment_method_id == null){
            this._displayErrorDialog(_t("Missing Data"), "Session and payment method cannot be null");
            this._enableButton();
            return;
        }

        return jsonrpc('/payment/myfatoorah/execute-payment', {
            SessionId: session_id,
            PaymentMethodId: payment_method_id,
        }).then((data) => {
            if (!data.success){
                this._displayErrorDialog(_t("Validation Error"), data.message);
                this._enableButton();
                return;
            }
            var mf_response = JSON.parse(data.data)
            if (mf_response.IsSuccess) {
                var paymentUrl = mf_response.Data.PaymentURL;
                window.location = paymentUrl;
            } else {
                var errorMessage = '';
                if (mf_response.ValidationErrors && mf_response.ValidationErrors.length > 0) {
                    mf_response.ValidationErrors.forEach((error) => {
                        errorMessage = error.Error; // Print each error message
                    });
                }
                this._displayErrorDialog(_t("Payment processing failed"), errorMessage);
                this._enableButton();
            }
        }).catch((error) => {
            this._displayErrorDialog(_t("Payment processing failed"), error);
            this._enableButton?.();
        });;
    },
});
