# -*- coding: utf-8 -*-

from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = ['sale.order', 'magento.status.sender.mixin']
    _name = 'sale.order'

    magento_state = fields.Selection(
        selection=[
            ('impo_local_shipping', 'Entrega Local'),
            ('delivered', 'Entregado'),
        ], string='Estado de Magento')
    

    def _get_magento_instance(self):
        """
        Sobrescribe el método para obtener la instancia de Magento directamente.
        """
        self.ensure_one()
        return self.magento_instance_id if hasattr(self, 'magento_instance_id') else False

    def _get_magento_order_id(self):
        """
        Sobrescribe el método para obtener el ID de orden de Magento directamente.
        """
        self.ensure_one()
        return self.magento_order_id if hasattr(self, 'magento_order_id') else False

    def _get_status_comment(self, status):
        """
        Personaliza el comentario para órdenes de venta.
        """
        return f"Estado de orden de venta actualizado: {status} (Orden: {self.name})"

    def action_send_status_to_magento(self, status):
        """
        Acción para enviar estado a Magento desde la interfaz.
        """
        if not status:
            return False
        
        result = self.batch_send_status_to_magento(status)
        
        if result['failed_count'] > 0:
            message = f"Se enviaron {result['success_count']} estados correctamente. "
            message += f"Fallaron {result['failed_count']} envíos."
        else:
            message = f"Se enviaron todos los estados correctamente ({result['success_count']})."
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Envío a Magento',
                'message': message,
                'type': 'success' if result['failed_count'] == 0 else 'warning',
                'sticky': False,
            }
        }
