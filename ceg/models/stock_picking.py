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

