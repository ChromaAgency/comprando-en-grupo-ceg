# -*- coding: utf-8 -*-

from odoo import models, fields
from odoo.addons.odoo_magento2_ept.models.sale_order import SaleOrder as MagentoSaleOrder



class SaleOrder(models.Model):
    _inherit = ['sale.order', 'magento.status.sender.mixin']
    _name = 'sale.order'

    magento_state = fields.Selection(
        selection=[
            ('impo_local_shipping', 'Entrega Local'),
            ('delivered', 'Entregado'),
        ],
        string='Estado de Magento')
    
    magento_currency_exchange_rate = fields.Float(string="Magento Currency Exchange Rate")

    def write(self, vals):
        """
        Sobrescribe el método write para enviar el estado a Magento al actualizar la orden.
        """
        res = super(SaleOrder, self).write(vals)
        
        # Si se actualiza el estado de Magento, enviarlo automáticamente
        if 'magento_state' in vals:
            for record in self:
                if record.magento_state and record._get_magento_instance():
                    mapping = {
                        'impo_local_shipping': 'impo_local_shipping',
                        'delivered': 'Entregado',
                    }
                    record.send_status_to_magento(mapping.get(record.magento_state))
        
        return res
    def _prepare_order_dict(self, item, instance):
        order_vals = super()._prepare_order_dict(item, instance)
        order_vals.update({
            'magento_currency_exchange_rate': item.get('extension_attributes').get('currency_rate'),
        })
        return order_vals

    def __update_partner_dict(self, item, instance):
        b_address = item.get('billing_address')
        b_address.update({
            'taxvat': item.get('customer_taxvat') or item.get('extension_attributes', {}).get('taxvat'),
            'company': item.get('extension_attributes', {}).get('company_name'),
            'taxpayer_type': item.get('extension_attributes', {}).get('taxpayer_type'),        
        })
        customers = super().__update_partner_dict(item, instance)
        customers.update({
            'taxvat': item.get('customer_taxvat') or item.get('extension_attributes', {}).get('taxvat'),
            'company': item.get('extension_attributes', {}).get('company_name'),
            'taxpayer_type': item.get('extension_attributes', {}).get('taxpayer_type'),
        })
        return customers

    def _upsert_currency_rate(self, currency_id, rate):
        """ 
            Search and create currency rate if not found
        """
        currency_rate = self.env['res.currency.rate']
        if not rate:
            return False
        domain = [('currency_id', '=', currency_id), ('name', '=', fields.Date.today())]
        currency_rate = currency_rate.search(domain)
        if not currency_rate:
            currency_rate = currency_rate.create({
                'currency_id': currency_id,
                'rate': 1/rate,
                'name': fields.Date.today()
            })
            return currency_rate
        currency_rate.write({
            'rate': 1/rate
        })
        return currency_rate

    def create_sale_order_ept(self, item, instance, log_line, line_id):
        is_processed = super().create_sale_order_ept(item, instance, log_line, line_id)
        if is_processed:
            order_currency_code = item.get('order_currency_code')
            curr = self.env['res.currency'].search([('name', '=', order_currency_code)])
            if curr:
                self._upsert_currency_rate(curr.id, item.get('extension_attributes',{}).get('currency_rate'))
                        
    @staticmethod
    def __update_partner_address_dict(item, addresses):
        vals = MagentoSaleOrder.__update_partner_address_dict(item, addresses)
        vals.update({
            'vat_id': addresses.get('taxvat', item.get("taxvat")),
            'taxvat': addresses.get('taxvat', item.get("taxvat")),
            'company': addresses.get('company', item.get('company')),
            'taxpayer_type': addresses.get('taxpayer_type', item.get('taxpayer_type')),
        })
        return vals

    def _get_magento_instance(self):
        """
        Sobrescribe el método para obtener la instancia de Magento directamente.
        """
        self.ensure_one()
        return self.magento_instance_id if hasattr(self, 'magento_instance_id') else False

    def _get_magento_order_ids(self):
        """
        Sobrescribe el método para obtener el ID de orden de Magento directamente.
        """
        self.ensure_one()
        yield self.magento_order_id if hasattr(self, 'magento_order_id') else False

    def _get_status_comment(self, status):
        """
        Personaliza el comentario para órdenes de venta.
        """
        return f"Estado de orden de venta actualizado: {status} (Orden: {self.name})"

    def action_send_status_to_magento(self, status):
        """
        Acción para enviar estado a Magento desde la interfaz.
        """
        if not status:
            return False
        
        result = self.batch_send_status_to_magento(status)
        
        if result['failed_count'] > 0:
            message = f"Se enviaron {result['success_count']} estados correctamente. "
            message += f"Fallaron {result['failed_count']} envíos."
        else:
            message = f"Se enviaron todos los estados correctamente ({result['success_count']})."
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Envío a Magento',
                'message': message,
                'type': 'success' if result['failed_count'] == 0 else 'warning',
                'sticky': False,
            }
        }
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _get_downpayment_line_price_unit(self, invoices):
        return self.price_unit
