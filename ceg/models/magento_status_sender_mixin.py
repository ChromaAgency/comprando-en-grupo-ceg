# -*- coding: utf-8 -*-

import json
import logging
import requests
from datetime import datetime
from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MagentoStatusSenderMixin(models.AbstractModel):
    """
    Mixin para enviar estados a Magento desde diferentes modelos.
    Puede ser utilizado por sale.order, purchase.order, stock.picking y account.move.
    """
    _name = 'magento.status.sender.mixin'
    _description = 'Magento Status Sender Mixin'

    def _build_administrative_status_request_data(self, status, magento_order_id):
        """
        Construye los datos de la petición para enviar a Magento.
        Este método debe ser sobrescrito en cada modelo que use el mixin.
        
        :param status: Estado a enviar
        :type status: str
        :return: Tupla con (url, headers, data)
        :rtype: tuple
        """
        self.ensure_one()
        
        # Obtener instancia de Magento
        magento_instance = self._get_magento_instance()
        if not magento_instance:
            raise UserError(_("No se encontró instancia de Magento para este registro"))
        
        # Obtener token de acceso
        instance_token = magento_instance.access_token
        if not instance_token:
            raise UserError(_("Token de acceso no configurado en la instancia de Magento"))
        
        # Construir headers
        headers = self._get_headers(instance_token)
        
        # Obtener URL base y ID de orden
        instance_url = magento_instance.magento_url
        if not instance_url:
            raise UserError(_("URL de Magento no configurada en la instancia"))
        
        if not magento_order_id:
            raise UserError(_("ID de orden de Magento no encontrado para este registro"))
        
        # Construir URL del endpoint
        url = f"{instance_url}/rest/V1/orders"
        
        # Construir datos del request
        data = json.dumps({
            "entity": {
                "entity_id": magento_order_id,
                "extension_attributes": {
                    "ceg_status": status
                }
            }
        })
        
        return url, headers, data
    def _log_message(self, message, post_to_chatter=True):
        """
        Registra un mensaje de error en el log.
        
        :param message: Mensaje de error a registrar
        :type message: str
        """
        _logger.error(message)
        if post_to_chatter and hasattr(self, 'message_post'):
            self.message_post(body=message)

    def send_administrative_status_to_magento(self, status):
        """
        Envía un estado a Magento para el registro actual.
        
        :param status: Estado a enviar a Magento
        :type status: str
        :return: True si se envió correctamente, False en caso contrario
        :rtype: bool
        """
        for rec in self:
            try:
                ids = rec._get_magento_order_ids()
                if not ids:
                    continue
                response = None
                for magento_order_id in ids:
                    url, headers, data = rec._build_administrative_status_request_data(status, magento_order_id)
                    response = requests.post(url, headers=headers, data=data)
                    
                    if response.status_code != 200:
                        rec._log_message("Error al enviar el estado administrativo '%s' a Magento para %s ID %s. Status code: %s. Response: %s" % (status, rec._name, magento_order_id, response.status_code, response.text))
                        continue
                    rec._log_message("Estado administrativo '%s' enviado exitosamente a Magento para %s ID %s" % (status, rec._name, magento_order_id))
                
                
            except Exception as e:
                rec._log_message("Excepción al enviar estado administrativo '%s' a Magento para %s ID %s: %s" % (status, rec._name, magento_order_id, str(e)))
                return False


    def send_status_to_magento(self, status):
        """
        Envía un estado a Magento para el registro actual.
        
        :param status: Estado a enviar a Magento
        :type status: str
        :return: True si se envió correctamente, False en caso contrario
        :rtype: bool
        """
        for rec in self:
            try:
                ids = rec._get_magento_order_ids()
                if not ids:
                    continue
                response = None
                for magento_order_id in ids:
                    _logger.info("Sending status '%s' to Magento for %s ID %s with Magento Order ID %s", status, rec._name, rec.id, magento_order_id)
                    url, headers, data = rec._build_status_request_data(status, magento_order_id)
                    response = requests.post(url, headers=headers, data=data)

                    if response or response.status_code != 200:
                        rec._log_message("Error al enviar el estado '%s' a Magento para %s ID %s. Status code: %s. Response: %s" % (status, rec._name, magento_order_id, response.status_code, response.text))
                        return False
                    
                    rec._log_message("Estado '%s' enviado exitosamente a Magento para %s ID %s" % (status, rec._name, magento_order_id))
                    return True
                
            except Exception as e:
                rec._log_message("Excepción al enviar estado '%s' a Magento para %s ID %s: %s" % (status, rec._name, magento_order_id, str(e)))
                return False

    def _build_status_request_data(self, status, magento_order_id):
        """
        Construye los datos de la petición para enviar a Magento.
        Este método debe ser sobrescrito en cada modelo que use el mixin.
        
        :param status: Estado a enviar
        :type status: str
        :return: Tupla con (url, headers, data)
        :rtype: tuple
        """
        self.ensure_one()
        
        # Obtener instancia de Magento
        magento_instance = self._get_magento_instance()
        if not magento_instance:
            raise UserError(_("No se encontró instancia de Magento para este registro"))
        
        # Obtener token de acceso
        instance_token = magento_instance.access_token
        if not instance_token:
            raise UserError(_("Token de acceso no configurado en la instancia de Magento"))
        
        # Construir headers
        headers = self._get_headers(instance_token)
        
        # Obtener URL base y ID de orden
        instance_url = magento_instance.magento_url
        if not instance_url:
            raise UserError(_("URL de Magento no configurada en la instancia"))
        
        # Obtener ID de orden de Magento
        if not magento_order_id:
            raise UserError(_("ID de orden de Magento no encontrado para este registro"))
        
        # Construir URL del endpoint
        url = f"{instance_url}/rest/V1/orders/{magento_order_id}/comments"
        
        # Construir datos del request
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = json.dumps({
            "statusHistory": {
                "comment": self._get_status_comment(status),
                "created_at": date,
                "entity_name": "order",
                "is_customer_notified": 0,
                "is_visible_on_front": 0,
                "parent_id": magento_order_id,
                "status": status
            }
        })
        
        return url, headers, data

    def _get_headers(self, token):
        """
        Obtiene los headers para la petición HTTP.
        
        :param token: Token de acceso de Magento
        :type token: str
        :return: Diccionario con headers
        :rtype: dict
        """
        return {
            'Accept': '*/*',
            'Content-Type': 'application/json',
            'User-Agent': 'Odoo Magento Integration 1.0',
            'Authorization': f'Bearer {token}'
        }

    def _get_magento_instance(self):
        """
        Obtiene la instancia de Magento relacionada al registro.
        Este método debe ser sobrescrito en cada modelo.
        
        :return: Registro de magento.instance
        :rtype: recordset
        """
        _logger.info("Default _get_magento_instance called for %s ID %s", self._name, self.id)
        # Implementación por defecto que busca el campo magento_instance_id
        if hasattr(self, 'magento_instance_id') and self.magento_instance_id:
            return self.magento_instance_id
        
        # Si no tiene campo directo, intentar obtenerlo de la orden de venta relacionada
        if hasattr(self, 'sale_id') and self.sale_id and hasattr(self.sale_id, 'magento_instance_id'):
            return self.sale_id.magento_instance_id
        
        # Para otros casos específicos, se debe sobrescribir este método
        return False

    def _get_magento_order_ids(self):
        """
        Obtiene el ID de orden de Magento para el registro.
        Este método debe ser sobrescrito en cada modelo según su estructura.
        
        :return: ID de orden de Magento
        :rtype: str
        """
        # Implementación por defecto que busca el campo magento_order_id
        if hasattr(self, 'magento_order_id') and self.magento_order_id:
            yield self.magento_order_id

        
        # Si no tiene campo directo, intentar obtenerlo de la orden de venta relacionada
        if hasattr(self, 'sale_id') and self.sale_id and hasattr(self.sale_id, 'magento_order_id'):
            yield self.sale_id.magento_order_id
        
        # Para modelos como account.move, buscar en las órdenes de venta relacionadas
        if hasattr(self, 'invoice_line_ids'):
            for line in self.invoice_line_ids:
                if hasattr(line, 'sale_line_ids'):
                    for sale_line in line.sale_line_ids:
                        if (hasattr(sale_line.order_id, 'magento_order_id') and 
                            sale_line.order_id.magento_order_id):
                            yield sale_line.order_id.magento_order_id

    def _get_status_comment(self, status):
        """
        Obtiene el comentario a enviar con el estado.
        Puede ser sobrescrito para personalizar el comentario según el modelo.
        
        :param status: Estado que se está enviando
        :type status: str
        :return: Comentario para el estado
        :rtype: str
        """
        model_name = self._description or self._name
        return f"Estado actualizado desde {model_name}: {status}"

    def batch_send_status_to_magento(self, status):
        """
        Envía estado a Magento para múltiples registros de forma eficiente.
        
        :param status: Estado a enviar
        :type status: str
        :return: Diccionario con resultados de envío
        :rtype: dict
        """
        successful_records = self.env[self._name]
        failed_records = self.env[self._name]
        
        for record in self:
            if record.send_status_to_magento(status):
                successful_records |= record
            else:
                failed_records |= record
        
        return {
            'successful': successful_records,
            'failed': failed_records,
            'success_count': len(successful_records),
            'failed_count': len(failed_records)
        }

    def batch_send_admin_status_to_magento(self, status):
        """
        Envía estado a Magento para múltiples registros de forma eficiente.
        
        :param status: Estado a enviar
        :type status: str
        :return: Diccionario con resultados de envío
        :rtype: dict
        """
        successful_records = self.env[self._name]
        failed_records = self.env[self._name]
        
        for record in self:
            if record.send_administrative_status_to_magento(status):
                successful_records |= record
            else:
                failed_records |= record
        
        return {
            'successful': successful_records,
            'failed': failed_records,
            'success_count': len(successful_records),
            'failed_count': len(failed_records)
        }
