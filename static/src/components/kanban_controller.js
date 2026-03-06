/** @odoo-module  */

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { DriverList } from "./driver_list";
import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { onRendered, onMounted } from "@odoo/owl";

export class TruckingKanbanController extends KanbanController {
    static components = { ...KanbanController.components, DriverList}
    static template = "trucking.TruckingKanbanController";

    setup() {
        super.setup();
        this.searchKey = Symbol("isFromTruckingKanban");
        // this.kanban = $(".o_kanban_renderer");
        // console.debug("kanban on setup",this.kanban);
        // onMounted(async () => {
        //     console.debug("kanban before mounted",this.kanban);
        //     this.kanban = $(".o_kanban_renderer");
        //     this.kanban.css('margin-left','250px');
        //     console.debug("kanban after mounted",this.kanban);
        // });
    }
    toggleFold() {
        const el = $(this.rootRef.el).find(".o_trucking_kanban_sidebar");
        el.toggleClass("folded");
        // var kanban = $(".o_kanban_renderer");
        // console.debug("kanban on toggle",this.kanban);
        // console.debug("kanban private on toggle",kanban);
        // if (el.hasClass("folded")) {
        //     kanban.css('margin-left','60px');
        // } else {
        //     kanban.css('margin-left','250px');
        // }

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