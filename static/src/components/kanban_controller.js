/** @odoo-module  */

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { DriverList } from "./driver_list";
import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";

export class TruckingKanbanController extends KanbanController {
    static components = { ...KanbanController.components, DriverList}
    static template = "trucking.TruckingKanbanController";

    setup() {
        super.setup();
        this.searchKey = Symbol("isFromTruckingKanban");
    }
    toggleFold() {
        
        $(this.rootRef.el).find(".o_trucking_kanban_sidebar").toggleClass("folded");
    }
    selectDriver(partner_id, partner_name) {
        const driverFilters = this.env.searchModel.getSearchItems((searchItem) =>
            searchItem[this.searchKey]
        );
        for (const driverFilter of driverFilters) {
            if (driverFilter.isActive) {
                this.env.searchModel.toggleSearchItem(driverFilter.id);
            }
        }
        this.env.searchModel.createNewFilters([{
            description: partner_name,
            domain: [["partner_id", "=", partner_id]],
            [this.searchKey]: true,
        }])
    }
}
const truckingKanbanController = {
    ...kanbanView,
    Controller: TruckingKanbanController,
};

registry.category("views").add("trucking_kanban", truckingKanbanController);