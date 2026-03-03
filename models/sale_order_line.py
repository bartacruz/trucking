from odoo import _, api, fields, models
from datetime import timedelta
from odoo.exceptions import UserError

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    trucking_trip_id = fields.Many2one(
        'trucking.trip', 
        string="Viaje",
        ondelete='cascade',
        help="Viaje vinculado a esta línea de pedido.",
    )

    cloned_line_id = fields.Many2one('sale.order.line')
    distance = fields.Float(string="Distancia (km)")

    
    _sql_constraints = [
        ('trucking_trip_unique', 'unique(trucking_trip_id)', '¡Este viaje ya está asignado a otra línea de pedido!')
    ]
    
    def write(self, vals):
        # 1. El super() procesa el cambio de producto o datos
        res = super(SaleOrderLine, self).write(vals)

        # 2. Lógica reactiva al cambio de producto
        if 'product_id' in vals:
            for line in self:
                # Si el nuevo producto NO es de transporte, el viaje debe morir
                if not line.product_id.trucking_trip and line.trucking_trip_id:
                    line.trucking_trip_id.unlink()
                
                # Si es de transporte y estaba vacío, nace el viaje
                elif line.product_id.trucking_trip and not line.trucking_trip_id:
                    line._create_associated_trip()
        return res
    
    def _prepare_trucking_values(self, **kwargs):
        """
        Prepare the values to create a new Trucking Trip from a sale order line.
        """
        self.ensure_one()

        return {
            "sale_line_id": self.id,
            "state": 'draft',
            "company_id": self.company_id.id,
            "origin_locality_id": self.order_id.origin_locality_id.id or None,
            "destination_locality_id": self.order_id.destination_locality_id.id or None,
            "commitment_date": self.order_id.commitment_date,
        }
    