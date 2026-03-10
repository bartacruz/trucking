/** @odoo-module **/

import { SearchModel } from "@web/search/search_model";
import { patch } from "@web/core/utils/patch";

patch(SearchModel.prototype, {
    async load(config) {
        await super.load(...arguments);

        this.shouldRemember = this.context && this.context.remember_filters;
        const actionId = this.context.action || 'default';
        this.sessionStorageKey = `odoo_filters_${this.resModel}_${actionId}`;

        if (this.shouldRemember) {
            const savedState = sessionStorage.getItem(this.sessionStorageKey);
            if (savedState) {
                try {
                    const parsedState = JSON.parse(savedState);
                    // Solo restauramos si los searchItems actuales contienen lo que guardamos
                    // Esto evita el error de "searchItemId is undefined"
                    const validQuery = parsedState.query.filter(q => 
                        this.searchItems[q.searchItemId]
                    );
                    
                    if (validQuery.length > 0) {
                        this.query = validQuery;
                        this._notify();
                    }
                } catch (e) {
                    console.warn("Error al aplicar filtros guardados:", e);
                }
            }
        }
    },

    _notify() {
        super._notify(...arguments);
        if (this.shouldRemember && this.query) {
            // Guardamos la query solo si tiene elementos para evitar ciclos infinitos
            const stateToSave = {
                query: this.query,
            };
            sessionStorage.setItem(this.sessionStorageKey, JSON.stringify(stateToSave));
        }
    },
});
