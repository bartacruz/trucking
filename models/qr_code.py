import logging
from odoo import api, fields, models,_
_logger = logging.getLogger(__name__)

class QRCode(models.Model):
    _name="qr.code"
    
    message_id = fields.Many2one('mail.message')
    attachment_id = fields.Many2one('ir.attachment', ondelete="set null")
    code = fields.Char()
    qr_type = fields.Char()