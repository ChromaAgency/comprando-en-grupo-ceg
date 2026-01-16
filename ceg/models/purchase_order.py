# -*- coding: utf-8 -*-

from odoo import models, _, fields
import logging
_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = ['purchase.order', 'magento.status.sender.mixin']
    _name = 'purchase.order'

    magento_state = fields.Selection(
        selection=[
            ('in_prod', 'En Produccion'),
            ('in_transit', 'En transito internacional'),
            ('in_customs', 'En aduanas'),
        ],
        string='State',
        help='State of the order in Magento'
    )
    def write(self, vals):
        """
        Sobrescribe el método write para enviar el estado a Magento al actualizar la orden de compra.
        """
        res = super(PurchaseOrder, self).write(vals)
        if 'magento_state' in vals:
            status = vals['magento_state']
            if status in ['in_prod', 'in_transit', 'in_customs']:
                status_mapping = {
                    'in_prod': 'impo_in_prod',
                    'in_transit': 'impo_shipped',
                    'in_customs': 'impo_ua_clearence',
                }
                self.send_status_to_magento(status_mapping.get(status))
        return res

    def _get_magento_instance(self):
        """
        Para órdenes de compra, buscar la instancia en las órdenes de venta relacionadas.
        """
        self.ensure_one()
        
        _logger.info("Checking %s for magento_instance_id", self.name)
        for sale_order in self.order_line.move_dest_ids.picking_id.sale_id:
            _logger.info("Checking sale order %s for magento_instance_id", sale_order.name)
            # Verificar si hay una relación indirecta a través de movimientos de stock
            if (hasattr(sale_order, 'magento_instance_id') and 
                sale_order.magento_instance_id):
                return sale_order.magento_instance_id
        
        return super()._get_magento_instance()

    def _get_magento_order_id(self):
        """
        Para órdenes de compra, buscar el ID de Magento en las órdenes de venta relacionadas.
        """
        self.ensure_one()
        last_magento_order_id = False
        for sale_order in self.order_line.move_dest_ids.picking_id.sale_id:
            _logger.info("Checking sale order %s for magento_order_id", sale_order.name)
            # Verificar si hay una relación indirecta a través de movimientos de stock
            if (hasattr(sale_order, 'magento_order_id') and sale_order.magento_order_id):
                last_magento_order_id = sale_order.magento_order_id
                yield last_magento_order_id 
        
        yield super()._get_magento_order_id()

    def _get_status_comment(self, status):
        """
        Personaliza el comentario para órdenes de compra.
        """
        return f"Estado de orden de compra actualizado: {status} (Compra: {self.name})"

    def action_send_purchase_status_to_magento(self):
        """
        Acción específica para enviar estado de compra a Magento.
        """

        return self.send_administrative_status_to_magento('impo_anticipo_pending')
    

    
    def action_create_sale_advance_payment(self):
        """Abrir wizard para crear anticipos de órdenes de venta relacionadas"""
        return {
            'name': _('Create Advance Payment for Sale Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.advance.payment.inv',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_purchase_order_ids': [(6, 0, self.ids)],
                'active_ids': self.ids,
            }
        }
