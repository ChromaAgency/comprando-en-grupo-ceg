# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseAdvancePaymentInv(models.TransientModel):
    _name = 'purchase.advance.payment.inv'
    _description = "Purchase Advance Payment Invoice for Sale Orders"

    purchase_order_ids = fields.Many2many(
        'purchase.order', 
        default=lambda self: self.env.context.get('active_ids') or self.ids
    )
    count = fields.Integer(string="Purchase Order Count", compute='_compute_count')
    sale_order_total = fields.Monetary(
        string="Sale Order Total", 
        compute='_compute_sale_order_total'
    )
    percentage = fields.Float(
        string="Percentage",
        default=1.0,
        help="Percentage of the sale order amount to be invoiced as advance payment"
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

    anticipo_type = fields.Selection([
        ('anticipo_1', 'Anticipo 1'),
        ('anticipo_2', 'Anticipo 2'),
        ('saldo_final', 'Saldo Final'),
    ], string="Tipo de Anticipo", default='anticipo_1', required=True)

    #=== COMPUTE METHODS ===#

    @api.depends('purchase_order_ids')
    def _compute_count(self):
        for wizard in self:
            wizard.count = len(wizard.purchase_order_ids)

    @api.depends('purchase_order_ids')
    def _compute_sale_order_total(self):
        for wizard in self:
            total = 0.0
            sale_orders = self.purchase_order_ids._get_sale_orders()
            
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

    @api.constrains('percentage')
    def _check_percentage(self):
        for wizard in self:
            if wizard.percentage <= 0 or wizard.percentage > 1:
                raise UserError(_('Percentage must be between 1 and 100.'))

    #=== ACTION METHODS ===#

    def create_sale_advance_payments(self):
        """Crear anticipos para las órdenes de venta relacionadas"""
        self.ensure_one()
        
        if not self.purchase_order_ids:
            raise UserError(_('No purchase orders selected.'))
        
        created_invoices = self.env['account.move']
        sale_orders = self.purchase_order_ids._get_sale_orders()
        
        # Filtrar solo órdenes confirmadas
        sale_orders = sale_orders.filtered(lambda so: so.state in ('sale', 'done'))
        
        if not sale_orders:
            raise UserError(_('No confirmed sale orders found related to the selected purchase orders.'))
                
        for sale_order in sale_orders:
            if self.anticipo_type == 'anticipo_1' and len(sale_order.invoice_ids) > 0:
                continue
            if self.anticipo_type == 'anticipo_2' and len(sale_order.invoice_ids) > 1:
                continue
            if self.anticipo_type == 'saldo_final' and len(sale_order.invoice_ids) > 2:
                continue

            # Crear el wizard de anticipo de venta
            advance_wizard = self.env['sale.advance.payment.inv'].create({
                'advance_payment_method': 'percentage',
                'amount': self.percentage*100,  # Usar el porcentaje configurado en el wizard
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
                        body=_("Advance payment invoice created for related sale order %s (%.1f%%): %s") % (
                            sale_order.name,
                            self.percentage,
                            invoice._get_html_link(title=_("Invoice"))
                        )
                    )
            self.purchase_order_ids.action_send_purchase_status_to_magento()
        
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
