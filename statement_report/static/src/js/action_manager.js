/** @odoo-module */
import { registry } from "@web/core/registry";
import { download } from "@web/core/network/download";
import { BlockUI, unblockUI } from "@web/core/ui/block_ui";

// Action manager for xlsx report
registry.category('ir.actions.report_handlers').add('xlsx', async (action) => {
    if (action.report_type === 'xlsx') {
        // Check if the 'xlsx' handler is already registered
        const existingHandler = registry.category('ir.actions.report_handlers').get('xlsx');
        
        // If the handler is already registered, do not add it again
        if (existingHandler) {
            console.warn('Handler for "xlsx" report type already exists.');
            return;
        }

        // Block the UI
        BlockUI();
        
        try {
            await download({
                url: '/xlsx_report',
                data: action.data,
                error: (error) => self.call('crash_manager', 'rpc_error', error),
                complete: () => unblockUI(),
            });
        } catch (error) {
            console.error('An error occurred during the download process:', error);
        } finally {
            // Unblock the UI
            unblockUI();
        }
    }
});
