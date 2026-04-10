/** @odoo-module **/
import { registry } from "@web/core/registry";

export const truckingService = {
    dependencies: ["bus_service"],
    start(env, { bus_service }) {
        bus_service.addChannel("trucking");
        bus_service.subscribe("trucking", ([payload, type]) => {
            console.debug("[truckingbus]",type,payload);
            if (type && type.startsWith("trucking_")) {
                try {
                    // Cambiamos el guion bajo por dos puntos para estandarizar en Owl
                    const owlEventName = type.replace("trucking_", "trucking:");
                    env.bus.trigger(owlEventName, payload);
                    console.debug(`[TruckingBus] Evento validado y reenviado: ${owlEventName}`, payload);
                } catch (err) {
                    console.error(`[TruckingBus] Error en el listener del evento ${type}:`, err);
                }
            }
        });
        bus_service.start();
        console.debug("trucking_bus Service Loaded and started wildcard");
    },
};

registry.category("services").add("trucking_bus", truckingService);
