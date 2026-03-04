/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";

export class AttachmentLinkField extends Many2OneField {
    static template = "trucking.AttachmentLinkField";

    get isPdf() {
        const name = this.fileName.toLowerCase();
        return name.endsWith('.pdf');
    }

    get fileName() {
        // En Many2one, el nombre suele venir en el segundo elemento de la tupla [id, name]
        // o directamente si ya fue procesado por el field
        const value = this.props.record.data[this.props.name];
        return value ? value[1] : "";
    }

    get fileUrl() {
        const value = this.props.record.data[this.props.name];
        const id = value ? value[0] : null;
        return id ? `/web/content/${id}` : "#";
    }

    get downloadUrl() {
        return `${this.fileUrl}?download=true`;
    }
}

registry.category("fields").add("attachment_link", {
    ...many2OneField,
    component: AttachmentLinkField,
});
