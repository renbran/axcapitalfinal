from odoo import http
from odoo.http import request
from datetime import datetime

class DynamicDashboard(http.Controller):
    """Class to search and filter values in dashboard"""

    @http.route('/custom_dashboard/search_input_chart', type='json',
                auth="public", website=True)
    def dashboard_search_input_chart(self, search_input, start_date=None, end_date=None):
        """Function to filter search input in dashboard"""
        
        # Initialize domain for search
        domain = [('name', 'ilike', search_input)]
        
        # Add date filtering if provided
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()  # Ensure date format is correct
            domain.append(('x_deal_date', '>=', start_date))
        
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()  # Ensure date format is correct
            domain.append(('x_deal_date', '<=', end_date))
        
        # Search for records based on the constructed domain
        records = request.env['dashboard.block'].search(domain)
        
        # Return IDs or any other relevant information as needed
        return {
            'ids': records.ids,
            'names': records.mapped('name'),  # Example of returning names as well
            'dates': records.mapped('x_deal_date')  # Example of returning deal dates
        }