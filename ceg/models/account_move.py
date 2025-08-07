# -*- coding: utf-8 -*-

from odoo import models


class AccountMove(models.Model):
    _inherit = ['account.move', 'magento.status.sender.mixin']
    _name = 'account.move'
    
    def write(self, vals):
        """
        Sobrescribe el método write para enviar el estado a Magento al actualizar la factura.
        """
        res = super(AccountMove, self).write(vals)
        
        if 'payment_state' in vals:
            status = vals['payment_state']
            if status in ['paid', 'in_payment']:
                self.action_send_purchase_status_to_magento(status)
        
        return res
    
    def action_send_purchase_status_to_magento(self):
        """
        Acción específica para enviar estado de compra a Magento.
        """

        return self.send_administrative_status_to_magento('impo_anticipo_complete')

    def _get_magento_instance(self):
        """
        Obtiene la instancia de Magento desde la orden de venta relacionada.
        """
        self.ensure_one()
        
        # Para facturas, buscar en las líneas de factura que tengan líneas de venta
        if self.move_type in ('out_invoice', 'out_refund'):
            for line in self.invoice_line_ids:
                if hasattr(line, 'sale_line_ids'):
                    for sale_line in line.sale_line_ids:
                        if (hasattr(sale_line.order_id, 'magento_instance_id') and 
                            sale_line.order_id.magento_instance_id):
                            return sale_line.order_id.magento_instance_id
        
        return False

    def _get_magento_order_id(self):
        """
        Obtiene el ID de orden de Magento desde la orden de venta relacionada.
        """
        self.ensure_one()
        
        # Para facturas, buscar en las líneas de factura que tengan líneas de venta
        if self.move_type in ('out_invoice', 'out_refund'):
            for line in self.invoice_line_ids:
                if hasattr(line, 'sale_line_ids'):
                    for sale_line in line.sale_line_ids:
                        if (hasattr(sale_line.order_id, 'magento_order_id') and 
                            sale_line.order_id.magento_order_id):
                            return sale_line.order_id.magento_order_id
        
        return False

    def _get_status_comment(self, status):
        """
        Personaliza el comentario para facturas.
        """
        if self.move_type == 'out_invoice':
            return f"Estado de factura actualizado: {status} (Factura: {self.name})"
        elif self.move_type == 'out_refund':
            return f"Estado de nota de crédito actualizado: {status} (Nota: {self.name})"
        else:
            return f"Estado de asiento contable actualizado: {status} (Asiento: {self.name})"

    def action_send_invoice_status_to_magento(self):
        """
        Acción específica para enviar estado de factura a Magento.
        """
        status_mapping = {
            'draft': 'pending',
            'posted': 'processing',
            'cancel': 'canceled'
        }
        
        status = status_mapping.get(self.state, self.state)
        return self.send_status_to_magento(status)
