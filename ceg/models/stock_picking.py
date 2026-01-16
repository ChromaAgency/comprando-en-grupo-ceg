# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = ['stock.picking', 'magento.status.sender.mixin']
    _name = 'stock.picking'
    exported_to_picking_list = fields.Boolean(string="Exportado a lista de picking", default=False)

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        for rec in self.filtered(lambda p: p.is_magento_picking):
            rec.export_magento_shipment()
        return res

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

    def _get_magento_order_ids(self):
        """
        Obtiene el ID de orden de Magento desde la orden de venta relacionada.
        """
        self.ensure_one()
        
        # Buscar la orden de venta relacionada
        if hasattr(self, 'sale_id') and self.sale_id:
            if hasattr(self.sale_id, 'magento_order_id'):
                yield self.sale_id.magento_order_id
        
        # Buscar en los movimientos de stock
        for move in self.move_ids_without_package:
            if hasattr(move, 'sale_line_id') and move.sale_line_id:
                sale_order = move.sale_line_id.order_id
                if hasattr(sale_order, 'magento_order_id') and sale_order.magento_order_id:
                    yield sale_order.magento_order_id
        

    def action_get_picking_list(self):
        picking_ids_map = map(lambda picking_id: str(picking_id), self.ids)
        picking_ids = ",".join(picking_ids_map)
        self.exported_to_picking_list = True
        return {
            "type": "ir.actions.act_url",
            "url": "/ceg/download_picking_list/%s" % (picking_ids),
            "target": "new",
        }