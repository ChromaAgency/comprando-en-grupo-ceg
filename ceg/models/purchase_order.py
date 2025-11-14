# -*- coding: utf-8 -*-

from odoo import models, _, fields


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
        default="in_prod",
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
        
        # Buscar órdenes de venta que puedan estar relacionadas con esta orden de compra
        # Esto puede variar según la implementación específica del proyecto
        sale_orders = self.env['sale.order'].search([
            ('procurement_group_id', '!=', False),
            ('state', 'not in', ['draft', 'cancel'])
        ])
        
        for sale_order in sale_orders:
            # Verificar si hay una relación indirecta a través de movimientos de stock
            if (hasattr(sale_order, 'magento_instance_id') and 
                sale_order.magento_instance_id):
                return sale_order.magento_instance_id
        
        return False

    def _get_magento_order_id(self):
        """
        Para órdenes de compra, buscar el ID de Magento en las órdenes de venta relacionadas.
        """
        self.ensure_one()
        
        # Similar al método anterior, buscar órdenes de venta relacionadas
        sale_orders = self.env['sale.order'].search([
            ('procurement_group_id', '!=', False),
            ('state', 'not in', ['draft', 'cancel'])
        ])
        
        for sale_order in sale_orders:
            if (hasattr(sale_order, 'magento_order_id') and 
                sale_order.magento_order_id):
                return sale_order.magento_order_id
        
        return False

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
