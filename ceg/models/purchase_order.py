# -*- coding: utf-8 -*-

from odoo import models, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

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
