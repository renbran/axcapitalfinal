var myFatoorahPaymentMethodId = undefined;
var myFatoorahPaymentMethodCode = undefined;
var is_form_prepared = false;


function _getMfSessionScript(state, country_code, gateway){
        
    var subdomain = '';

    if(state == 'test'){
        subdomain = 'demo'
    }else{
        if(country_code == 'SAU'){
            subdomain = 'sa';
        }else if(country_code == 'QAT'){
            subdomain = 'qa'
        }else{
            subdomain = 'portal'
        }
    }
    var base_url = "https://" + subdomain + ".myfatoorah.com/";
    var endpoint = '';
    if(gateway == "google_pay"){
        endpoint = base_url +  "googlepay/v1/googlepay.js";
    }else if(gateway == "cardview"){
        endpoint = base_url +  "cardview/v2/session.js";
    }
    else if(gateway == "apple_pay"){
        endpoint = base_url +  "applepay/v3/applepay.js";
    }
    return endpoint
}

function _prepareGooglePay(country_code, state){
    var gpScript = document.createElement('script');
    gpScript.src = _getMfSessionScript(state, country_code, "google_pay");
    document.head.appendChild(gpScript);
}

function _prepareForm(country_code, state){
    var gpScript = document.createElement('script');
    gpScript.src = _getMfSessionScript(state, country_code, "cardview"); 
    document.head.appendChild(gpScript);
}

function _prepareApplePay(country_code, state){
    var gpScript = document.createElement('script');
    gpScript.src = _getMfSessionScript(state, country_code, "apple_pay"); 
    document.head.appendChild(gpScript);
}

async function _prepareCards(cards_payment_methods) {
    let mfRowContainer = document.getElementById('mf-cards');
  
    if(cards_payment_methods.length > 0){
      for (let i = 0; i < cards_payment_methods.length; i++) {
        let mfCard = cards_payment_methods[i];
        let mfCardTitle = mfCard.PaymentMethodEn;
        try {
          let cardsHtml = `
            <div class="mf-card-container mf-div-${mfCard.PaymentMethodCode}" onclick="mfCardSubmit(${mfCard.PaymentMethodId})">
                <div class="mf-row-container">
                    <img class="mf-payment-logo" src="${mfCard.ImageUrl}" alt="${mfCardTitle}">
                    <span class="mf-payment-text mf-card-title">${mfCardTitle}</span>
                </div>
                <span class="mf-payment-text">
                    ${mfCard.GatewayTotalAmount} ${mfCard.PaymentCurrencyIso}
                </span>
            </div>
          `;
          mfRowContainer.innerHTML += cardsHtml;
        } catch (error) {
          console.log(error);
        }
        
      }
    }else{
      document.getElementById('mf-sectionCard')?.remove();
    }
}
  
function mfCardSubmit(payment_method_id){
    myFatoorahPaymentMethodId = payment_method_id
    var button = document.querySelector("button[name='o_payment_submit_button']");
    if (button) {
        button.click();
    } else {
        console.error('Button not found');
    }
}

if (!window.ApplePaySession) {

    document.getElementById('mf-ap-element')?.remove();

    var mfGpElement = document.getElementById('mf-gp-element');
    if (!mfGpElement) {
        document.getElementById('mf-or-cardsDivider')?.remove();
    }

    let mfDivAps = document.querySelectorAll('.mf-div-ap');
    mfDivAps.forEach(element => {
         element.remove();
    });

    var mfCardContainer = document.querySelectorAll('.mf-card-container');
    if (!mfGpElement) {
        document.getElementById('mf-or-formDivider')?.remove();
    }  
}   
