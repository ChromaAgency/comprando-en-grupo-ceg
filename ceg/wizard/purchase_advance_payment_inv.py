# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseAdvancePaymentInv(models.TransientModel):
    _name = 'purchase.advance.payment.inv'
    _description = "Purchase Advance Payment Invoice for Sale Orders"

    purchase_order_ids = fields.Many2many(
        'purchase.order', 
        default=lambda self: self.env.context.get('active_ids')
    )
    count = fields.Integer(string="Purchase Order Count", compute='_compute_count')
    sale_order_total = fields.Monetary(
        string="Sale Order Total", 
        compute='_compute_sale_order_total'
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        compute='_compute_currency_id',
        store=True
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        compute='_compute_company_id',
        store=True
    )

    #=== COMPUTE METHODS ===#

    @api.depends('purchase_order_ids')
    def _compute_count(self):
        for wizard in self:
            wizard.count = len(wizard.purchase_order_ids)

    @api.depends('purchase_order_ids')
    def _compute_sale_order_total(self):
        for wizard in self:
            total = 0.0
            sale_orders = self.env['sale.order']
            for po in wizard.purchase_order_ids:
                # Obtener las órdenes de venta relacionadas a través de las líneas de compra
                # que están vinculadas a líneas de venta
                for po_line in po.order_line:
                    if po_line.sale_line_id:
                        sale_orders |= po_line.sale_line_id.order_id
            
            # Eliminar duplicados y sumar totales
            for so in sale_orders:
                total += so.amount_total
            wizard.sale_order_total = total

    @api.depends('purchase_order_ids')
    def _compute_currency_id(self):
        for wizard in self:
            if wizard.count == 1:
                wizard.currency_id = wizard.purchase_order_ids.currency_id
            else:
                wizard.currency_id = False

    @api.depends('purchase_order_ids')
    def _compute_company_id(self):
        for wizard in self:
            if wizard.count == 1:
                wizard.company_id = wizard.purchase_order_ids.company_id
            else:
                wizard.company_id = False

    #=== ACTION METHODS ===#

    def create_sale_advance_payments(self):
        """Crear anticipos para las órdenes de venta relacionadas"""
        self.ensure_one()
        
        if not self.purchase_order_ids:
            raise UserError(_('No purchase orders selected.'))
        
        created_invoices = self.env['account.move']
        sale_orders = self.env['sale.order']
        
        # Recopilar todas las órdenes de venta relacionadas
        for po in self.purchase_order_ids:
            for po_line in po.order_line:
                if po_line.sale_line_id:
                    sale_orders |= po_line.sale_line_id.order_id
        
        # Filtrar solo órdenes confirmadas
        sale_orders = sale_orders.filtered(lambda so: so.state in ('sale', 'done'))
        
        if not sale_orders:
            raise UserError(_('No confirmed sale orders found related to the selected purchase orders.'))
                
        for sale_order in sale_orders:
            # Crear el wizard de anticipo de venta
            advance_wizard = self.env['sale.advance.payment.inv'].create({
                'advance_payment_method': 'percentage',
                'amount': 100.0,  # 100% del total de la venta
                'sale_order_ids': [(4, sale_order.id)],
            })
            
            # Crear la factura de anticipo
            invoice = advance_wizard._create_invoices(sale_order)
            if invoice:
                created_invoices |= invoice
                
                # Crear un mensaje en las órdenes de compra relacionadas
                related_pos = self.purchase_order_ids.filtered(
                    lambda po: any(
                        line.sale_line_id.order_id == sale_order 
                        for line in po.order_line 
                        if line.sale_line_id
                    )
                )
                for po in related_pos:
                    po.message_post(
                        body=_("Advance payment invoice created for related sale order %s: %s") % (
                            sale_order.name, 
                            invoice._get_html_link(title=_("Invoice"))
                        )
                    )
        
        if not created_invoices:
            raise UserError(_('No advance payment invoices were created. Please verify that the purchase orders have related sale orders.'))
        
        # Mostrar las facturas creadas
        if len(created_invoices) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Advance Payment Invoice'),
                'res_model': 'account.move',
                'res_id': created_invoices.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Advance Payment Invoices'),
                'res_model': 'account.move',
                'view_mode': 'list,form',
                'domain': [('id', 'in', created_invoices.ids)],
                'target': 'current',
            }

    def get_related_sale_orders(self):
        """Obtener información de las órdenes de venta relacionadas"""
        self.ensure_one()
        sale_orders_info = []
        sale_orders = self.env['sale.order']
        
        for po in self.purchase_order_ids:
            for po_line in po.order_line:
                if po_line.sale_line_id:
                    sale_orders |= po_line.sale_line_id.order_id
        
        for so in sale_orders:
            sale_orders_info.append({
                'order': so,
                'name': so.name,
                'partner': so.partner_id.name,
                'amount_total': so.amount_total,
                'state': so.state,
            })
        
        return sale_orders_info
