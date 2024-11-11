/** @odoo-module */

import { registry } from "@web/core/registry";
import { KpiCard } from "./kpi_card/kpi_card";
import { ChartRenderer } from "./chart_renderer/chart_renderer";
import { loadJS } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";
const { Component, onWillStart, useRef, onMounted, useState } = owl;

export class OwlSalesDashboard extends Component {
    setup(){
        this.state = useState({
            quotations: { value:10, percentage:6 },
            period:90,
            currency: "AED", // Default currency setting
            year: new Date().getFullYear(), // Current year for the line chart
        });
        this.orm = useService("orm");
        this.actionService = useService("action");

        onWillStart(async () => {
            this.getDates();
            await this.getQuotations();
            await this.getOrders();
            await this.getMonthlyChartData();
            await this.getSalesTypeScores();
            await this.getDeveloperSalesRanking();
        });
    }

    async onChangePeriod(){
        this.getDates();
        await this.getQuotations();
        await this.getOrders();
    }

    getDates(){
        this.state.current_date = moment().subtract(this.state.period, 'days').format('YYYY-MM-DD');
        this.state.previous_date = moment().subtract(this.state.period * 2, 'days').format('YYYY-MM-DD');
    }

    async getQuotations(){
        let domain = [['state', 'in', ['sent', 'draft']]];
        if (this.state.period > 0){
            domain.push(['date_order','>', this.state.current_date]);
        }
        const data = await this.orm.searchCount("sale.order", domain);
        this.state.quotations.value = data;

        // Previous period calculations
        let prev_domain = [['state', 'in', ['sent', 'draft']]];
        if (this.state.period > 0){
            prev_domain.push(['date_order','>', this.state.previous_date], ['date_order','<=', this.state.current_date]);
        }
        const prev_data = await this.orm.searchCount("sale.order", prev_domain);
        const percentage = ((data - prev_data) / (prev_data || 1)) * 100;  // Prevent division by zero
        this.state.quotations.percentage = percentage.toFixed(2);
    }

    async getOrders(){
        let domain = [['state', 'in', ['sale', 'done']]];
        if (this.state.period > 0){
            domain.push(['date_order','>', this.state.current_date]);
        }
        const data = await this.orm.searchCount("sale.order", domain);

        // Previous period calculations for orders
        let prev_domain = [['state', 'in', ['sale', 'done']]];
        if (this.state.period > 0){
            prev_domain.push(['date_order','>', this.state.previous_date], ['date_order','<=', this.state.current_date]);
        }
        const prev_data = await this.orm.searchCount("sale.order", prev_domain);
        const percentage = ((data - prev_data) / (prev_data || 1)) * 100;

        // Current and previous revenue calculations with error checks
        const current_revenue = await this.orm.readGroup("sale.order", domain, ["amount_total:sum"], []);
        const prev_revenue = await this.orm.readGroup("sale.order", prev_domain, ["amount_total:sum"], []);

        // Check if current_revenue and prev_revenue have valid data and default to 0 if not
        const currentRevenueTotal = current_revenue.length > 0 && typeof current_revenue[0].amount_total === 'number'
            ? current_revenue[0].amount_total
            : 0;
        const prevRevenueTotal = prev_revenue.length > 0 && typeof prev_revenue[0].amount_total === 'number'
            ? prev_revenue[0].amount_total
            : 0;

        const revenue_percentage = prevRevenueTotal !== 0
            ? ((currentRevenueTotal - prevRevenueTotal) / prevRevenueTotal) * 100
            : 0;

        // Current and previous average calculations
        const current_average = await this.orm.readGroup("sale.order", domain, ["amount_total:avg"], []);
        const prev_average = await this.orm.readGroup("sale.order", prev_domain, ["amount_total:avg"], []);
        
        const currentAverageTotal = current_average.length > 0 && typeof current_average[0].amount_total === 'number'
            ? current_average[0].amount_total
            : 0;
        const prevAverageTotal = prev_average.length > 0 && typeof prev_average[0].amount_total === 'number'
            ? prev_average[0].amount_total
            : 0;
        
        const average_percentage = prevAverageTotal !== 0
            ? ((currentAverageTotal - prevAverageTotal) / prevAverageTotal) * 100
            : 0;

        // Set values in state, converting to AED
        this.state.orders = {
            value: data,
            percentage: percentage.toFixed(2),
            revenue: `AED ${(currentRevenueTotal).toFixed(2)}`,
            revenue_percentage: revenue_percentage.toFixed(2),
            average: `AED ${(currentAverageTotal).toFixed(2)}`,
            average_percentage: average_percentage.toFixed(2),
        };
    }

    // Method to fetch monthly chart data for current year based on `x_deal_date` and `amount_total`
    async getMonthlyChartData(){
        const currentYear = this.state.year;
        const domain = [['x_deal_date', '>=', `${currentYear}-01-01`], ['x_deal_date', '<=', `${currentYear}-12-31`]];
        
        const monthlyData = await this.orm.readGroup("sale.order", domain, ["amount_total:sum"], ["x_deal_date:month"]);
        
        // Process data for chart rendering, converting to AED
        this.state.monthly_chart = monthlyData.map(entry => ({
            month: entry.x_deal_date,
            amount: `AED ${(entry.amount_total).toFixed(2)}`
        }));
    }

    // Method to get the score for each sales type
    async getSalesTypeScores(){
        const data = await this.orm.readGroup("sale.order", [], ["x_sale_value:sum"], ["x_sale_type"]);
        this.state.sales_scores = data.map(entry => ({
            type: entry.x_sale_type,
            value: `AED ${(entry.x_sale_value).toFixed(2)}`
        }));
    }

    // Method to get ranking for developers (partner_id) and salespersons (referrer_id)
    async getDeveloperSalesRanking(){
        const developer_data = await this.orm.readGroup("sale.order", [], ["amount_total:sum", "id:count"], ["partner_id"]);
        const salesperson_data = await this.orm.readGroup("sale.order", [], ["amount_total:sum", "id:count"], ["referrer_id"]);
        
        // Format ranking data in tables
        this.state.developer_ranking = developer_data.map(entry => ({
            developer: entry.partner_id[1],
            count: entry.id_count,
            total: `AED ${(entry.amount_total).toFixed(2)}`
        }));

        this.state.salesperson_ranking = salesperson_data.map(entry => ({
            salesperson: entry.referrer_id[1],
            count: entry.id_count,
            total: `AED ${(entry.amount_total).toFixed(2)}`
        }));
    }

    async viewQuotations(){
        let domain = [['state', 'in', ['sent', 'draft']]];
        if (this.state.period > 0){
            domain.push(['date_order','>', this.state.current_date]);
        }

        let list_view = await this.orm.searchRead("ir.model.data", [['name', '=', 'view_quotation_tree_with_onboarding']], ['res_id']);

        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Quotations",
            res_model: "sale.order",
            domain,
            views: [
                [list_view.length > 0 ? list_view[0].res_id : false, "list"],
                [false, "form"],
            ]
        });
    }

    viewOrders(){
        let domain = [['state', 'in', ['sale', 'done']]];
        if (this.state.period > 0){
            domain.push(['date_order','>', this.state.current_date]);
        }

        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Orders",
            res_model: "sale.order",
            domain,
            context: {group_by: ['date_order']},
            views: [
                [false, "list"],
                [false, "form"],
            ]
        });
    }

    viewRevenues(){
        let domain = [['state', 'in', ['sale', 'done']]];
        if (this.state.period > 0){
            domain.push(['date_order','>', this.state.current_date]);
        }

        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Revenues",
            res_model: "sale.order",
            domain,
            context: {group_by: ['date_order']},
            views: [
                [false, "pivot"],
                [false, "form"],
            ]
        });
    }
}

OwlSalesDashboard.template = "owl.OwlSalesDashboard";
OwlSalesDashboard.components = { KpiCard, ChartRenderer };

registry.category("actions").add("owl.sales_dashboard", OwlSalesDashboard);
