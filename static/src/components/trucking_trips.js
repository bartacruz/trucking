/** @odoo-module **/

import { Component, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useBus, useService } from "@web/core/utils/hooks";
import { useX2ManyCrud } from "@web/views/fields/relational_utils";
import { _lt, _t } from "@web/core/l10n/translation";

export class TruckingTripsField extends Component {
    static template = "trucking.TruckingTripsField";
    static props = {
        ...standardFieldProps,
    }
    static tripStates = {
        draft: _lt("DraftO"),
        assigned: _lt("Assigned"),
        confirmed: _lt("Confirmed"),
        started: _lt("Started"),
        arrived: _lt("Arrived"),
        completed: _lt("Completed"),
        cancelled: _lt("Cancelled"),
    }
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        const { saveRecord, updateRecord, removeRecord } = useX2ManyCrud(
            () => this.props.record.data[this.props.name],
            false
        );
        // this.refresh = useDebounced(this.refresh,1500);
        useBus(this.env.bus, "trucking:trip_changed", this.updateTrips);
        const searchModel = this.env.searchModel;

    }
    async assignTrip(trip, driver) {
        this.env.services.ui.block();
        const assigned = await this.orm.call('trucking.trip', "assign_driver", [trip, driver], {
            context: this.props.context,
        });
        console.debug("assigned", assigned);
        this.env.services.ui.unblock();
    };

    updateTrips(ev) {
        const detail = ev.detail;
        if (detail.order_id == this.props.record.resId) {
            this.refresh();
        }
    }
    async refresh() {
        await this.props.record.load();
    }
    getTrip(record) {
        var driver = record.data.driver_id ? record.data.driver_id[1] : false;
        var cpe = record.data.cpe_id ? record.data.cpe_id[1] : false;
        var vehicle = record.data.vehicle_id ? record.data.vehicle_id[1] : false;
        var trailer = record.data.trailer_id ? record.data.trailer_id[1] : false;
        const stateLabel = this.constructor.tripStates[record.data.state] || record.data.state;
        console.debug(record.data);
        return {
            id: record.id, // datapoint_X
            resId: record.resId,
            text: record.data.display_name,
            driver: driver,
            vehicle: vehicle,
            trailer: trailer,
            is_active: record.data.is_active,
            state: record.data.state,
            stateLabel:stateLabel,
            warnings: record.data.warnings,
            cpe: cpe,
        };

    }
    async onClick(ev) {
        ev.stopPropagation();
        var target = $(ev.target).closest('.o_trip');
        const trip = target.data("id");
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Viaje',
            target: 'current',
            res_id: trip,
            res_model: 'trucking.trip',
            views: [[false, 'form']],
        });
    }
    async onDragEnter(ev) {
        var target = $(ev.target);
        target.closest('.o_trip').addClass('o_sarasa');
    }

    onDragLeave(ev) {
        var target = $(ev.target);
        target.closest('.o_trip').removeClass('o_sarasa');
    }
    onDrop(ev, a, b) {
        var target = $(ev.target).closest('.o_trip');
        target.removeClass('o_sarasa');

        const driver_id = ev.dataTransfer.getData("text");
        const trip = target.data("id");
        this.assignTrip(trip, driver_id);
    }
    get trips() {
        return this.props.record.data[this.props.name].records.map((record) =>
            this.getTrip(record)
        );
    }
}
export const truckingTripsField = {
    component: TruckingTripsField,
    displayName: "Trips",
    supportedTypes: ["many2many"],
    relatedFields: (fieldInfo) => {
        return [
            { name: 'id', type: "int" },
            { name: "display_name", type: "char" },
            { name: "driver_id", type: "many2one" },
            { name: "vehicle_id", type: "many2one" },
            { name: "trailer_id", type: "many2one" },
            { name: "is_active", type: "bool" },
            {
                name: "state", type: "selection", selection: [
                    ["draft", _lt("DraftO")],
                    ["assigned", _lt("Assigned")],
                    ["confirmed", _lt("Confirmed")],
                    ["started", _lt("Started")],
                    ["arrived", _lt("Arrived")],
                    ["completed", _lt("Completed")],
                    ["cancelled", _lt("Cancelled")],
                ]
            },
            { name: "warnings", type: "char" },
            { name: "start_date", type: "date" },
            { name: "cpe_id", type: "many2one" },
        ];
    },

}
registry.category("fields").add("trucking_trips", truckingTripsField);
