odoo.define('real_estate_management.property_website', function (require) {

import { Component } from "@odoo/owl";
import { moment } from "moment";

export class OwlSalesDashboard extends Component {
    getDates() {
        // Use moment to manipulate and format dates
        let currentDate = moment().format('YYYY-MM-DD');
        console.log("Current Date: ", currentDate);
    }
}
