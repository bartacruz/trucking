import logging
from markupsafe import Markup
from odoo import _,api, fields, models,SUPERUSER_ID
from pyzbar.pyzbar import decode
from PIL import Image
import base64
import io
_logger = logging.getLogger(__name__)

class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    qr_codes = fields.One2many('qr.code','attachment_id')
    qr_scanned = fields.Boolean()
    
            
    def _prepare_qr_vals(self):
        vals = []
        for record in self:
            print("_prepare_qr_vals",record)
            
            if 'image' in record.mimetype:
                image = Image.open(io.BytesIO(base64.b64decode(record.datas)))
                decoded = decode(image)
                print("decoded",decoded)
                for r in decoded:
                    vals.append({
                        'attachment_id': record.id,
                        'code':r.data.decode('utf-8'),
                        'qr_type':r.type
                    })
        return vals
    
    def _extract_qr_codes(self):
        for record in self:
            print("_extract_qr_codes",record)
            
            if 'image' in record.mimetype:
                image = Image.open(io.BytesIO(base64.b64decode(record.datas)))
                decoded = decode(image)
                print("decoded",decoded)
                for r in decoded:
                    qr = record.qr_codes.create({
                        'attachment_id': record.id,
                        'code':r.data.decode('utf-8'),
                        'qr_type':r.type
                    })
                    _logger.info("Decoded attachment %s: %s %s",qr.attachment_id,qr.qr_type,qr.code)
            record.qr_scanned = True
    
class MailMessage(models.Model):
    _inherit = 'mail.message'
    
    qr_code_ids = fields.One2many('qr.code', 'message_id')
    qr_codes_count = fields.Integer(compute="_compute_qr_codes", store=True)
    trucking_trip_id = fields.Many2one('trucking.trip','Related Trucking Trip')
    partner_ids = fields.Many2many('res.partner', string='Recipients', context={'active_test': False}, compute='_compute_discuss_members', store=True, copy=False)
    token = fields.Char(compute="_compute_token", store=True)
    
    @api.depends('res_id','model')
    def _compute_token(self):
        for record in self:
            if record.model == 'discuss.channel':
                origin = self.env[record.model].browse(record.res_id)
                record.token = origin.gateway_channel_token
            else:
                record.token = False
    
    @api.depends('res_id')
    def _compute_discuss_members(self):
        for record in self:
            print(record.model,record.res_id)
            if record.model != 'discuss.channel':
                record.partner_ids = record.partner_ids or False
                continue
            channel = self.env[record.model].browse(record.res_id)
            print("channel",channel,channel.channel_member_ids)
            record.partner_ids = channel.channel_member_ids.partner_id
            
            
    def _process_qr_code(self,qr):
        self.ensure_one()
        # MIG 18
        if qr:
            return
        self.env[self.model].browse(self.res_id).message_post(
            author_id=SUPERUSER_ID,
            body=f'QR Code: {qr.code}',
            date=self.date,
            subtype_xmlid="mail.mt_comment",
            message_type="comment",
            gateway_notifications=[],
        )
        
        
        # CPE DETECTION
        if len(qr.code) == 11 and qr.code.startswith('1'):
            # CPE
            order = self.author_id.active_trucking_trip_id
            if not order:
                _logger.warning("Received CPE #%s from %s but there's no active trip to attach to.",qr.code,self.author_id)
                return
            print("Es CPE y la orden está activa!",qr.code,order)
            _logger.warning("CPE %s de orden activa %s. att=%s",qr.code,order,self.attachment_ids)
            order.message_post(
                author_id=self.author_id.id,
                body=f'{self.body}\n\nQR Code: {qr.code}',
                date=self.date,
                attachment_ids=self.attachment_ids.ids,
                gateway_notifications=[],  # Avoid sending notifications
            )
            if not order.cpe_id:
                cpe = self.env['afip.cpe'].search([ '|',('ctg_number','=',qr.code),('name','=',qr.code) ],limit=1)
                print("Cpe: ",cpe)
                if not cpe:
                    print("Creando CPE",qr.code)
                    cpe = self.env['afip.cpe'].create({
                        'name':qr.code,
                    })
                    order.cpe_id = cpe
                else:        
                    order.cpe_id = cpe
                    cpe.action_update_cpe(force=True)
                
                message1 = _(
                    "Carta de porte %s recibida por QR",
                    Markup(
                        f"""<a href=# data-oe-model=afip.cpe data-oe-id={cpe.id}"""
                        f""">{cpe.name}</a>"""
                    ),
                )                
                order.with_user(SUPERUSER_ID).message_post(body=message1)

                message2 = Markup(f'<p>La carta de porte {qr.code} ha sido recibida y asignada al viaje {order.name}.<br/>Muchas gracias.</p>')
                self.with_user(SUPERUSER_ID).env[self.model].browse(self.res_id).message_post(author_id=SUPERUSER_ID,body=message2, gateway_notifications=[],subtype_xmlid="mail.mt_comment",
                message_type="comment",)
                
    @api.depends('attachment_ids')
    def _compute_qr_codes(self):
        for record in self:
            for a in record.attachment_ids:
                _logger.info("computing QR codes for %s of %s",a, record)
                if not a.qr_scanned:
                    vals_list = a._prepare_qr_vals()
                    for vals in vals_list:
                        existing = record.qr_code_ids.filtered(lambda q: q.code == vals['code'])
                        if not existing:
                            _logger.info('Processing QR %s for attachment %s of message %s',
                                         vals['code'],
                                         a.id,
                                         record.id)
                            vals['message_id']=record.id
                            qr = record.qr_code_ids.create(vals)
                            record.sudo()._process_qr_code(qr)
                        else:
                            _logger.info('NOT Processing QR %s for attachment %s of message %s. Already scanned on attachment %s',
                                         vals['code'],
                                         a.id,
                                         record.id,
                                         existing.attachment_id.id)
                    a.qr_scanned=True
            record.qr_codes_count=len(record.qr_code_ids)
                
    # def write(self, vals):
    #     ret = super().write(vals)
    #     if 'gateway_message_id' in vals and 'body' in vals and self.body.find("Button:"):
    #         _logger.info('WA write: %s detecte un boton %s || %s',self,vals['gateway_message_id'],self.gateway_message_id)
    #         template_message = self.gateway_message_id
    #         _logger.info('WA write: el mensaje es %s',template_message)
    #         trip = template_message.trucking_trip_id
    #         if not trip:
    #             return
    #         _logger.info('WA write: la orden es %s',trip)
    #         # Check if the author is still the trip driver!
    #         if self.author_id  != trip.driver_id:
    #             _logger.warning('WA write: el autor %s ya no es el conductor del viaje %s (ahora es %s)',self.author_id.name,trip.name,trip.driver_id.name)
    #             return
    #         trip_vals = self._get_gateway_thread_message_vals()
    #         trip_vals['author_id']=self.author_id.id
            
    #         trip.message_post(**trip_vals)
            
    #         if "Confirmar" in self.body:
    #             trip.driver_response = 'confirmed'
    #             body = 'Confirmación recibida.\nNos estaremos contactando para mas detalles.'
    #         else:
    #             trip.driver_response = 'rejected'
    #             body = 'Cancelación recibida.'
    #         trip._send_whatsapp(self.author_id,body=body)
    #     return ret
        