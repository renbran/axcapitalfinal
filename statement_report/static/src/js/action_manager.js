/** @odoo-module */
import { registry } from "@web/core/registry";
import { download } from "@web/core/network/download";
import { BlockUI, unblockUI } from "@web/core/ui/block_ui";

// Action manager for xlsx report
const xlsxHandler = async (action) => {
    if (action.report_type === 'xlsx') {
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
};

// Register the handler only if it's not already registered
if (!registry.category('ir.actions.report_handlers').get('xlsx')) {
    registry.category('ir.actions.report_handlers').add('xlsx', xlsxHandler);
} else {
    console.warn('Handler for "xlsx" report type already exists.');
}
