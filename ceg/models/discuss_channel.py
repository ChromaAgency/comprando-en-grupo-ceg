from odoo.models import Model
from odoo import api, models, fields
import re
import logging
import threading
from markupsafe import Markup, escape

from datetime import timedelta

from odoo import models, fields, api, _, Command
from odoo.addons.phone_validation.tools import phone_validation
from odoo.addons.whatsapp.tools import phone_validation as wa_phone_validation
from odoo.addons.whatsapp.tools.retryable_codes import WHATSAPP_RETRYABLE_ERROR_CODES
from odoo.addons.whatsapp.tools.bounced_codes import BOUNCED_ERROR_CODES
from odoo.addons.whatsapp.tools.whatsapp_api import WhatsAppApi
from odoo.addons.whatsapp.tools.whatsapp_exception import WhatsAppError
from odoo.exceptions import ValidationError, UserError
from odoo.tools import frozendict, groupby, html2plaintext
_logger = logging.getLogger(__name__)

class DiscussChannel(Model):
    _inherit = 'discuss.channel'

    @api.returns('self')
    def _get_whatsapp_channel(self, whatsapp_number, wa_account_id, sender_name=False, create_if_not_found=False, related_message=False):
        channel = super()._get_whatsapp_channel(whatsapp_number, wa_account_id, sender_name, create_if_not_found, related_message)
        users_to_notify = channel.whatsapp_partner_id.user_id or channel.whatsapp_partner_id.commercial_partner_id.user_id 
        channel.channel_member_ids = [Command.create({'partner_id':p}) for p in users_to_notify.partner_id.ids  if p not in channel.channel_member_ids.mapped('partner_id').ids]
        return channel
     