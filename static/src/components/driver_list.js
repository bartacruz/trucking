/** @odoo-module */

import { useBus,useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState,useRef } from "@odoo/owl";
import { KeepLast } from "@web/core/utils/concurrency";
import { fuzzyLookup } from "@web/core/utils/search";
import { Pager } from "@web/core/pager/pager";

export class DriverList extends Component {
    static components = { Pager };
    static template = "trucking.DriverList";
    static props = {
        selectDriver: {
            type: Function,
        },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.partners = useState({ data: [] });
        this.root = useRef('root');
        this.pager = useState({ offset: 0, limit: 15 });
        this.keepLast = new KeepLast();
        this.state = useState({
            searchString: "",
            displayActiveDrivers: false,
            lastSearch: "",
            folded:false,
        })
        useBus(this.env.bus, "driver_changed", this.updateDrivers);
        onWillStart(async () => {
            await this.updateDrivers();
        })
        this.onDrag = function(ev){
            console.debug("onDrag",this,ev);
            const driver_id = ev.srcElement.dataset.driverId;
            ev.dataTransfer.setData("text",driver_id);
            ev.dataTransfer.dropEffect = "move";
            ev.dataTransfer.effectAllowed = "move";
        }
        this.onDrop = function(ev){
            console.debug("onDrop drivers",this,ev);
        }
    }
    async selectDriver(ev) {
        const td = $(ev.srcElement).closest('.driver');
        const driver_id = td.data("driverId");
        
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Driver',
            target: 'current',
            res_id: driver_id,
            res_model: 'res.partner',
            views: [[false, 'form']],
        });
    }
    get displayedPartners() {
        if (this.state.searchString != this.state.lastSearch) {
            this.updateDrivers();
        }
        return this.partners.data;
    }

    async updateDrivers() {
        const { length, records } = await this.loadDrivers();
        this.partners.data = records;
        this.pager.total = length;
    }

    async onChangeActiveDrivers(ev) {
        this.state.displayActiveDrivers = ev.target.checked;
        this.updateDrivers();
    }
    
    filterDrivers(name) {
        console.debug("filterDrivers",name);
        if (name) {
            return fuzzyLookup(name, this.partners.data, (partner) => partner.display_name);
        } else {
            return this.partners.data;
        }
    }

    loadDrivers() {
        const { limit, offset } = this.pager;
        const domain = [['truck_driver','=',true]];
        if (this.state.displayActiveDrivers) {
            domain.push(["trucking_state", "!=", 'unavailable' ]);
        } 
        if (this.state.searchString.length > 2) {
            domain.push(['name','ilike',this.state.searchString]);
        }
        this.state.lastSearch = this.state.searchString;
        // console.debug("loading drivers", domain);
        
        return this.orm.webSearchRead("res.partner", domain, {
            specification: {
                "display_name": {},
                "trucking_state": {},
            },
            order: "trucking_state, trucking_sequence,name",
            limit,
            offset,
        })
    }


    async onUpdatePager(newState) {
        Object.assign(this.pager, newState);
        const { records } = await this.loadDrivers();
        this.partners.data = records;
    }
}