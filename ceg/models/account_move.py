# -*- coding: utf-8 -*-

from odoo import models, api


class AccountMove(models.Model):
    _inherit = ['account.move', 'magento.status.sender.mixin']
    _name = 'account.move'

    @property
    def is_anticipo_1(self):
        return len(self.invoice_line_ids.sale_line_ids.order_id.invoice_ids) == 1

    def action_post(self):
        """
        Sobrescribe el método action_post para enviar el estado a Magento al confirmar la orden de compra.
        """
        res = super(AccountMove, self).action_post()
        for rec in self.filtered(lambda m: m.is_magento_invoice):
            if not rec.is_anticipo_1:
                continue
            rec.export_invoice_magento(wizard=False)
        return res

    def _update_magento_admin_status(self):
        for rec in self:
            if rec.payment_state in ['paid', 'in_payment']:
                rec.action_send_no_debt_status_to_magento()
            else: 
                rec.action_send_in_debt_status_to_magento()

    def _mark_as_exported_if_not_anticipo_1(self):
        for rec in self:
            if not rec.is_anticipo_1:
                rec.is_exported_to_magento = True
                
    @api.model
    def create(self, vals):
        res = super(AccountMove, self).create(vals)
        res._update_magento_admin_status()
        res._mark_as_exported_if_not_anticipo_1()
        return res

    def write(self, vals):
        """
        Sobrescribe el método write para enviar el estado a Magento al actualizar la factura.
        """
        res = super(AccountMove, self).write(vals)
        self._update_magento_admin_status()
        return res
    
    def action_send_in_debt_status_to_magento(self):
        """
        Acción específica para enviar estado de compra a Magento.
        """

        return self.send_administrative_status_to_magento('1')
    
    def action_send_due_debt_status_to_magento(self):
        """
        Acción específica para enviar estado de compra a Magento.
        """
        return self.send_administrative_status_to_magento('2')
    
    def action_send_no_debt_status_to_magento(self):
        """
        Acción específica para enviar estado de compra a Magento.
        """
        return self.send_administrative_status_to_magento('0')

    def action_send_cancelled_status_to_magento(self):
        """
        Acción específica para enviar estado de compra a Magento.
        """
        return self.send_administrative_status_to_magento('3')

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

    def _get_magento_order_ids(self):
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
                            yield sale_line.order_id.magento_order_id
        
        yield False

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
