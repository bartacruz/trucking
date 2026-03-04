/** @odoo-module **/
import { registry } from "@web/core/registry";

export const truckingService = {
    dependencies: ["bus_service"],
    start(env, { bus_service }) {
        // Nos suscribimos al canal "trucking"
        bus_service.addChannel("trucking");

        bus_service.addEventListener("notification", ({ detail: notifications }) => {
            for (const { type, payload } of notifications) {
                // FILTRO DE SEGURIDAD: Solo reenviamos si el tipo empieza con trucking_
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
            }
        });
    },
};

registry.category("services").add("trucking_bus", truckingService);
