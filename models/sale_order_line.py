from odoo import _, api, fields, models
from datetime import timedelta
from odoo.exceptions import UserError

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    trucking_trip_id = fields.Many2one(
        'trucking.trip', 
        string="Trip",
        ondelete='cascade',
    )
    trucking_trip_state = fields.Selection(related="trucking_trip_id.state")
    has_trucking_product = fields.Boolean(compute='_compute_has_trucking_product')
    cloned_line_id = fields.Many2one('sale.order.line')
    distance = fields.Float(string="Distance (km)")
    cpe = fields.Char(string="CPE", related="trucking_trip_id.cpe_id.name")
    order_partner_invoice_id = fields.Many2one('res.partner', related="order_id.partner_invoice_id", store=True, index=True,)
    verified = fields.Boolean(string=_("Trip Verified"), related="trucking_trip_id.verified")
    
    
    invoice_ids = fields.Many2many('account.move', compute="_compute_invoice_ids", string=_("Invoices"), store=True)
    invoice_ids_count = fields.Integer(string=_("Invoice Count"), compute="_compute_invoice_ids")
    
    
    _sql_constraints = [
        ('trucking_trip_unique', 'unique(trucking_trip_id)', '¡Este viaje ya está asignado a otra línea de pedido!')
    ]
    
    def create(self, vals_list):
        records = super().create(vals_list)
        records_with_trips = records.filtered(lambda L: L.product_id.trucking_trip and not L.trucking_trip_id)
        print("records_with_trips",records_with_trips)
        records_with_trips._create_associated_trip()
            
    def write(self, vals):
        res = super(SaleOrderLine, self).write(vals)

        if 'product_id' in vals:
            for line in self:
                if not line.product_id.trucking_trip and line.trucking_trip_id:
                    line.trucking_trip_id.unlink()
                elif line.product_id.trucking_trip and not line.trucking_trip_id:
                    line._create_associated_trip()
        # check trips > confirmed vs PO and PO lines.
        self.filtered(lambda L : L.trucking_trip_id)._check_purchase_order()
        return res
    
    def _create_associated_trip(self):
        created_trips = self.env['trucking.trip']
        for record in self:
            vals = record._prepare_trucking_values()
            print("creating trip",record, record.order_id,vals)
            trip = record.trucking_trip_id.create([vals])
            record.order_id._post_trip_message(trip)
    
    def _compute_invoice_ids(self):
        for line in self:
            line.invoice_ids = line.invoice_lines.move_id
            line.invoice_ids_count = len(line.invoice_ids)
            
    @api.depends('product_id')
    def _compute_has_trucking_product(self):
        for record in self:
            record.has_trucking_product = record.product_id.trucking_trip
    
    @api.depends('state', 'product_uom_qty', 'qty_delivered', 'qty_to_invoice', 'qty_invoiced', 'trucking_trip_id.state','trucking_trip_id.verified')
    def _compute_invoice_status(self):
        super()._compute_invoice_status()
        for line in self:
            # Avoid modifying already invoiced lines.
            if line.invoice_lines:
                line.invoice_status = 'invoiced'
                continue
            if line.trucking_trip_id:
                trip = line.trucking_trip_id
                if trip.is_invoiceable():
                    line.invoice_status = 'to invoice'
                else:
                    line.invoice_status = "no"
                
                if not line.purchase_line_count:
                    line._purchase_service_generation()    
                
    @api.depends('pricelist_item_id','order_id.pricelist_discount', 'product_uom_qty', 'distance')
    def _compute_price_unit(self):
        super()._compute_price_unit()
        for line in self:
            if line.order_id.trucking_fixed_price:
                line.price_unit = line.order_id.trucking_fixed_price
            elif line.pricelist_item_id and line.order_id.pricelist_discount != 0:
                discount = 1 - (line.order_id.pricelist_discount/100)
                line.price_unit = line.price_unit * discount
                print("computed price_unit of ",line,line.price_unit,"with discount",line.order_id.pricelist_discount)
            
        
        
    @api.depends('order_id.pricelist_id', 'distance', 'product_uom_qty')
    def _compute_pricelist_item_id(self):
        self.env['l10n_latam.identification.type']
        for line in self:
            qty_field=line.order_id.pricelist_id.qty_field or 'product_uom_qty'
            quantity = getattr(line, qty_field ) or 1
            print("checking pricelist_item of",line,"with product:",line.product_id,"|",line.product_template_id,"qty_field:",qty_field," quantity:",quantity)
            line.pricelist_item_id = line.order_id.pricelist_id._get_product_rule(
                line.product_id,
                quantity=quantity,
                date=line._get_order_date(),
            )
            
                
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
            "distance": self.distance,
        }
    
    def action_open_trucking_trip(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'trucking.trip', 
            'res_id': self.trucking_trip_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    ### Invoicing methods ###
    
    def _prepare_invoice_line(self, **optional_values):
        ret = super()._prepare_invoice_line(**optional_values)
        print("_prepare_invoice_line",self,self.has_trucking_product,self.trucking_trip_id)
        if self.has_trucking_product and self.trucking_trip_id.cpe_id:
            trip = self.trucking_trip_id
            ret['name']=f'{trip.cpe_id.name}  {trip.origin_locality_id.name.title()} - {trip.destination_locality_id.name.title()}'
        return ret
    
    def action_invoice_selected_lines(self):
        
        non_billable = self.filtered(lambda l: l.invoice_status != 'to invoice')
        if non_billable:
            pedidos = ", ".join(non_billable.mapped('order_id.name'))
            raise UserError(_("Hay líneas que no están listas para facturar (Pedidos: %s).") % pedidos)

        # 2. Validar que todas tengan el mismo Partner de Factura
        invoice_partners = self.mapped('order_id.partner_invoice_id')
        if len(invoice_partners) > 1:
            raise UserError(_("No podés consolidar líneas de distintos clientes de factura."))

        partner = invoice_partners[0]
        
        # 3. Preparar cabecera de la factura
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_origin': ", ".join(list(set(self.mapped('order_id.name')))),
            'invoice_line_ids': [],
        }

        # 4. Generar líneas usando tu método _prepare_invoice_line() ya personalizado
        for line in self:
            vals = line._prepare_invoice_line()
            invoice_vals['invoice_line_ids'].append((0, 0, vals))

        # 5. Crear la factura en borrador
        new_invoice = self.env['account.move'].create(invoice_vals)

        # 6. Abrir la factura creada para que el usuario la revise
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': new_invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('id', 'in', self.invoice_ids.ids)],
            'context': {
                'default_partner_id': self.order_id.partner_invoice_id.id,
                'default_invoice_line_ids': [(0, 0, line._prepare_invoice_line()) for line in self],
            }
        }
    
    ### Purchase methods ###
    
    def _check_purchase_order(self):
        # Si no tengo trip, salgo
        # si tengo trip pero está < confirmed, no tengo que tener PO.
        # Si el trip esta >= confirmed Deberia tener 1 PO al driver (o invoice_partner) 
        # con 1 linea con los datos del servicio.
        # Si la orden está completada, confirmar la PO
        #
        for line in self:
            if not line.trucking_trip_id:
                continue
            trip = line.trucking_trip_id
            if trip.state in ['draft','assigned','cancelled']:
                line.purchase_line_ids.unlink()
                continue
        
            if line.purchase_line_count == 0:
                # NO. O chequear subcontract
                #print("ACA CREARIA LA LINEA??",line)
                continue
            
            p_line = line.purchase_line_ids[0]
            # remove excess lines
            (line.purchase_line_ids - p_line).unlink()
            name = f'{trip.cpe_id.ctg_number or trip.name} {trip.origin_locality_id.name} - {trip.destination_locality_id.name}' 
                
            vals = {
                    'name': name,
                    'product_id': line.product_id.id,
                    'product_qty': line.product_uom_qty,
                    'price_unit': line.price_unit,
                }
            print('++++++_check_purchase_order', line, "updating",p_line,vals)
            p_line.write(vals)
            if line.trucking_trip_id.state == 'completed':
                p_line.qty_received = p_line.product_uom_qty
                # if p_line.order_id.state not in ['purchase','']:
                #     p_line.order_id.order_line.filtered(lambda L: L.sta)
                
            
                
    def _purchase_service_generation(self):
        # Remove lines with trucking trip that don't have the driver confirmed.
        lines_with_trip_unconfirmed = self.filtered(lambda l: l.trucking_trip_id and not l.trucking_trip_id.state in ['confirmed','started','arrived','completed'])
        lines_to_process = self-lines_with_trip_unconfirmed
        print("_purchase_service_generation",self,lines_with_trip_unconfirmed)
        return super(SaleOrderLine,lines_to_process)._purchase_service_generation()
    
    def _purchase_service_create(self, quantity=False):
        print("_purchase_service_create",quantity)
        sale_line_purchase_map = {}
        for line in self:
            sale_line_purchase_map.setdefault(line, line.env['purchase.order.line'])
            p_line = line.purchase_line_ids.filtered(lambda x: x.product_id.trucking_trip)
            if p_line and line.trucking_trip_id:
                trip = line.trucking_trip_id
                name = f'{trip.cpe_id.ctg_number or trip.name} {trip.origin_locality_id.name} - {trip.destination_locality_id.name}' 
                vals = {
                    'name': name,
                    'product_id': line.product_id.id,
                    'product_qty': quantity or line.product_uom_qty,
                    'price_unit': line.price_unit,
                    'discount': line.discount,
                    'trucking_trip_id': line.trucking_trip_id.id
                }
                print("_purchase_service_create",line,"updating",p_line,vals)
                p_line.write(vals)
                sale_line_purchase_map[line] |= p_line
            else:
                print("_purchase_service_create",line,"calling super")
                sale_line_purchase_map |= super(SaleOrderLine, line)._purchase_service_create(quantity=quantity)
                
        return sale_line_purchase_map
    
    def _purchase_service_match_purchase_order(self, partner, company=False):
        return super()._purchase_service_match_purchase_order(partner, company)

    def _purchase_service_match_supplier(self, warning=True):
        #print("_purchase_service_match_supplier",self, self.trucking_trip_id)
        if self.product_id.trucking_trip and self.trucking_trip_id:
            if self.trucking_trip_id.driver_id:
                #print("_purchase_service_match_supplier generating",self.order_id,self.trucking_trip_id.name,self.trucking_trip_id.driver_id)
                driver_id = self.trucking_trip_id.driver_id
                # Select purchase and invoicing partner, via parent, invoice partner or driver
                partner_id = driver_id.parent_id or driver_id.invoice_partner_id or driver_id
                supplier_info = self.env['product.supplierinfo'].search([('product_tmpl_id','=',self.product_template_id.id),('partner_id','=',partner_id.id)])
                vals = {
                    'partner_id': partner_id.id,
                    'product_id': self.product_id.id,
                    'product_tmpl_id': self.product_template_id.id,
                    'price': self.price_unit,
                    'min_qty':0,
                    'discount': partner_id.purchase_general_discount
                    }
                if supplier_info:
                    # Clean garbage
                    if len(supplier_info) > 1:
                        print("cleaning supplier info garbage",supplier_info)
                        supplier_info[1:].unlink()
                        supplier_info = supplier_info[0]
                
                    supplier_info.write(vals)
                    #print("_purchase_service_match_supplier creating",self.order_id,partner_id,vals)
                else:
                    supplier_info =self.env['product.supplierinfo'].create([vals])
                
                print("_purchase_service_match_supplier returning",self,supplier_info.partner_id,supplier_info.price)
                return supplier_info
            print("_purchase_service_match_supplier MOFO FAILIN'",self.order_id)
            raise UserError(_(
                "Could not generate a trucking purchase for %s since it doesn't "
                "have a driver assigned.",
                self.trucking_trip_id.name
                ))            
        return super()._purchase_service_match_supplier(warning)
    
    def _purchase_service_prepare_line_values(self, purchase_order, quantity=False):
        ret = super()._purchase_service_prepare_line_values(purchase_order, quantity)
        ret |= {'trucking_trip_id': self.trucking_trip_id.id}
        
        print("_purchase_service_prepare_line_values", self, ret)
        return ret
        