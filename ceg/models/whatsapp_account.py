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
   
class WhatsappAccount(Model):
    _inherit = 'whatsapp.account'

    def _process_messages(self, value):
        """
            This method is used for processing messages with the values received via webhook.
            If any whatsapp message template has been sent from this account then it will find the active channel or
            create new channel with last template message sent to that number and post message in that channel.
            And if channel is not found then it will create new channel with notify user set in account and post message.
            Supported Messages
             => Text Message
             => Attachment Message with caption
             => Location Message
             => Contact Message
             => Message Reactions
        """
        if 'messages' not in value and value.get('whatsapp_business_api_data', {}).get('messages'):
            value = value['whatsapp_business_api_data']

        wa_api = WhatsAppApi(self)

        for messages in value.get('messages', []):
            parent_msg_id = False
            parent_id = False
            channel = False
            sender_name = value.get('contacts', [{}])[0].get('profile', {}).get('name')
            sender_mobile = messages['from']
            message_type = messages['type']
            if 'context' in messages and messages['context'].get('id'):
                parent_whatsapp_message = self.env['whatsapp.message'].sudo().search([('msg_uid', '=', messages['context']['id'])])
                if parent_whatsapp_message:
                    parent_msg_id = parent_whatsapp_message.id
                    parent_id = parent_whatsapp_message.mail_message_id
                if parent_id:
                    channel = self.env['discuss.channel'].sudo().search([('message_ids', 'in', parent_id.id)], limit=1)

            if not channel:
                channel = self._find_active_channel(sender_mobile, sender_name=sender_name, create_if_not_found=True)
            users_to_notify = channel.whatsapp_partner_id.user_id or channel.whatsapp_partner_id.commercial_partner_id.user_id 
            _logger.info("%s %s",users_to_notify.partner_id.ids, channel.channel_member_ids.partner_id.ids)
            new_members = [Command.create({'partner_id':p}) for p in users_to_notify.partner_id.ids if p not in channel.channel_member_ids.partner_id.ids]
            _logger.info(new_members)
            channel.channel_member_ids = new_members
        res = super()._process_messages(value)
        return res