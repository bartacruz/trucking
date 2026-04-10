/** @odoo-module **/

import { Component, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useBus, useService } from "@web/core/utils/hooks";
import { useX2ManyCrud } from "@web/views/fields/relational_utils";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog"

export class TruckingTripsField extends Component {
    static template = "trucking.TruckingTripsField";
    static props = {
        ...standardFieldProps,
    }
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialogService = useService("dialog");
        const { saveRecord, updateRecord, removeRecord } = useX2ManyCrud(
            () => this.props.record.data[this.props.name],
            false
        );
        // this.refresh = useDebounced(this.refresh,1500);
        useBus(this.env.bus, "trucking:trip_changed", this.updateTrips);
        const searchModel = this.env.searchModel;

    }
    get tripStates() {
        return {
            draft: _t("Draft"),
            assigned: _t("Assigned"),
            confirmed: _t("Confirmed"),
            started: _t("Started"),
            arrived: _t("Arrived"),
            completed: _t("Completed"),
            cancelled: _t("Cancelled"),
        }
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
            this.refresh(detail.id);
        }
    }
    async refresh(trip_id) {
        //console.debug("refresh Starting");
        const data= this.props.record.data[this.props.name];
        const idx = data._currentIds.indexOf(trip_id);
        //console.debug("PAJAR",trip_id,data,idx);
        const record = data.records[idx];
        if (!record) {
            console.debug("Trip",trip_id,"don't have record");
            return;
        }
        //console.debug("AGUJA",record);
        const response = await record.load();
        const record2 = this.props.record.data[this.props.name].records[idx];
        //console.debug("refresh",response,record2);
        // await this.props.record.load();
    }
    getTrip(record) {
        var driver = record.data.driver_id ? record.data.driver_id[1] : false;
        var cpe = record.data.cpe_id ? record.data.cpe_id[1] : false;
        var vehicle = record.data.vehicle_id ? record.data.vehicle_id[1] : false;
        var trailer = record.data.trailer_id ? record.data.trailer_id[1] : false;
        const stateLabel = this.tripStates[record.data.state] || record.data.state;
        return {
            id: record.id, // datapoint_X
            resId: record.resId,
            text: record.data.display_name,
            driver: driver,
            vehicle: vehicle,
            trailer: trailer,
            is_active: record.data.is_active,
            verified: record.data.verified,
            state: record.data.state,
            stateLabel:stateLabel,
            warnings: record.data.warnings,
            cpe: cpe,
        };

    }
    async onClick(ev) {
        ev.stopPropagation();
        const target = ev.target.closest('.o_trip');
        if (!target) return;
        const tripId = parseInt(target.dataset.id);

        await this.action.doAction({
            type: 'ir.actions.act_window',
            name: _t('Viaje'), // Recordá usar _t para que sea traducible
            target: 'current',
            res_id: tripId,
            res_model: 'trucking.trip',
            views: [[false, 'form']],
        });
    }
    onDragEnter(ev) {
        const target = ev.target.closest('.o_trip');
        if (target) {
            target.classList.add('o_sarasa');
        }
    }

    onDragLeave(ev) {
        const target = ev.target.closest('.o_trip');
        if (target) {
            target.classList.remove('o_sarasa');
        }
    }

    onDrop(ev, a, b) {
        const target = ev.target.closest('.o_trip');
        if (target) {
            target.classList.remove('o_sarasa');
            
            const driver_id = ev.dataTransfer.getData("text");
            const trip = parseInt(target.dataset.id); // Usamos dataset.id en vez de data("id")
            
            const data = this.props.record.data[this.props.name];
            // En Odoo 18, verifica si records es un array o un objeto de relación
            const idx = data.records.findIndex(r => r.data.id === trip || r.resId === trip);
            
            const record = data.records[idx];
            
            if (record && record.data.driver_id) {
                // record.data.driver_id suele ser un array [id, nombre] o un objeto
                const driverName = Array.isArray(record.data.driver_id) ? record.data.driver_id[1] : record.data.driver_id.data.display_name;
                
                this.dialogService.add(ConfirmationDialog, {
                    title: _t("Confirmar reasignación"),
                    body: _t("El viaje ya está asignado a %s. ¿Estás seguro de que quieres cambiar el conductor?", driverName),
                    confirm: () => {
                        this.assignTrip(trip, driver_id);
                    },
                    cancel: () => {},
                    confirmLabel: _t("Reasignar"),
                    cancelLabel: _t("Cancelar"),
                });
            } else {
                this.assignTrip(trip, driver_id);
            }
        }
    }

    get trips() {
        //console.debug("get trips",this.props.record);
        return this.props.record.data[this.props.name].records.map((record) =>
            this.getTrip(record)
        );
    }
}
export const truckingTripsField = {
    component: TruckingTripsField,
    displayName: _t("Trips"),
    supportedTypes: ["many2many"],
    relatedFields: (fieldInfo) => {
        return [
            { name: 'id', type: "int" },
            { name: "display_name", type: "char" },
            { name: "driver_id", type: "many2one" },
            { name: "vehicle_id", type: "many2one" },
            { name: "trailer_id", type: "many2one" },
            { name: "is_active", type: "bool" },
            { name: "verified", type: "bool" },
            {
                name: "state", type: "selection", selection: [
                    ["draft", _t("Draft")],
                    ["assigned", _t("Assigned")],
                    ["confirmed", _t("Confirmed")],
                    ["started", _t("Started")],
                    ["arrived", _t("Arrived")],
                    ["completed", _t("Completed")],
                    ["cancelled", _t("Cancelled")],
                ]
            },
            { name: "warnings", type: "char" },
            { name: "start_date", type: "date" },
            { name: "cpe_id", type: "many2one" },
        ];
    },

}
registry.category("fields").add("trucking_trips", truckingTripsField);
