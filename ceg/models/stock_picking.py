# -*- coding: utf-8 -*-

from odoo import models


class StockPicking(models.Model):
    _inherit = ['stock.picking', 'magento.status.sender.mixin']
    _name = 'stock.picking'

    def _get_magento_instance(self):
        """
        Obtiene la instancia de Magento desde la orden de venta relacionada.
        """
        self.ensure_one()
        
        # Buscar la orden de venta relacionada
        if hasattr(self, 'sale_id') and self.sale_id:
            if hasattr(self.sale_id, 'magento_instance_id'):
                return self.sale_id.magento_instance_id
        
        # Buscar en los movimientos de stock
        for move in self.move_ids_without_package:
            if hasattr(move, 'sale_line_id') and move.sale_line_id:
                sale_order = move.sale_line_id.order_id
                if hasattr(sale_order, 'magento_instance_id') and sale_order.magento_instance_id:
                    return sale_order.magento_instance_id
        
        return False

    def _get_magento_order_id(self):
        """
        Obtiene el ID de orden de Magento desde la orden de venta relacionada.
        """
        self.ensure_one()
        
        # Buscar la orden de venta relacionada
        if hasattr(self, 'sale_id') and self.sale_id:
            if hasattr(self.sale_id, 'magento_order_id'):
                return self.sale_id.magento_order_id
        
        # Buscar en los movimientos de stock
        for move in self.move_ids_without_package:
            if hasattr(move, 'sale_line_id') and move.sale_line_id:
                sale_order = move.sale_line_id.order_id
                if hasattr(sale_order, 'magento_order_id') and sale_order.magento_order_id:
                    return sale_order.magento_order_id
        
        return False

    def _get_status_comment(self, status):
        """
        Personaliza el comentario para entregas.
        """
        picking_type_name = self.picking_type_id.name if self.picking_type_id else "Transferencia"
        return f"Estado de {picking_type_name.lower()} actualizado: {status} (Transferencia: {self.name})"

    def action_done(self):
        """
        Sobrescribe el método para enviar automáticamente el estado a Magento.
        """
        result = super().action_done()
        
        # Enviar estado a Magento si está configurado
        for picking in self:
            if picking._get_magento_instance() and picking._get_magento_order_id() and picking.picking_type_id.code == 'outgoing':
                picking.send_status_to_magento('impo_pre_local_prep')
        
        return result
