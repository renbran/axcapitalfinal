from odoo import api, fields, models

class DashboardMenu(models.Model):
    """Class to create new dashboard menu"""
    _name = "dashboard.menu"
    _description = "Dashboard Menu"

    name = fields.Char(string="Name", ondelete='cascade',
                       help="Enter a name for the dashboard menu")
    menu_id = fields.Many2one('ir.ui.menu', string="Parent Menu",
                              help="Parent Menu Location of New Dashboard",
                              ondelete='cascade')
    group_ids = fields.Many2many('res.groups', string='Groups',
                                 related='menu_id.groups_id',
                                 help="User need to be at least in one of "
                                      "these groups to see the menu")
    client_action_id = fields.Many2one('ir.actions.client',
                                       string="Client Action",
                                       help="Client action of the "
                                            "corresponding dashboard menu")

    @api.model
    def create(self, vals):
        """Function to create new dashboard menu"""
        action_id = self.env['ir.actions.client'].create({
            'name': vals.get('name'),
            'tag': 'AdvancedDynamicDashboard',
        })
        vals['client_action_id'] = action_id.id
        
        # Create menu item
        menu_item = self.env['ir.ui.menu'].create({
            'name': vals['name'],
            'parent_id': vals.get('menu_id'),
            'action': 'ir.actions.client,%d' % (action_id.id,)
        })
        
        return super(DashboardMenu, self).create(vals)

    def write(self, vals):
        """Function to save edited data in dashboard menu"""
        for rec in self:
            if rec.client_action_id:
                client_act_id = rec.client_action_id.id
                self.env['ir.ui.menu'].search([
                    ('parent_id', '=', rec.menu_id.id),
                    ('action', '=', f'ir.actions.client,{client_act_id}')
                ]).write({
                    'name': vals.get('name', rec.name),
                    'parent_id': vals.get('menu_id', rec.menu_id),
                    'action': f'ir.actions.client,{client_act_id}'
                })
        return super(DashboardMenu, self).write(vals)

    def unlink(self):
        """Delete dashboard along with menu item"""
        for rec in self:
            menu_item = self.env['ir.ui.menu'].search([
                ('parent_id', '=', rec.menu_id.id),
                ('action', '=', f'ir.actions.client,{rec.client_action_id.id}')
            ])
            if menu_item:
                menu_item.unlink()
        return super(DashboardMenu, self).unlink()