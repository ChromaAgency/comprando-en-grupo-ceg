from odoo import models

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def _prepare_base_downpayment_line_values(self, order):
        vals = super()._prepare_base_downpayment_line_values(order)
        vals['product_id'] = self.env.ref('ceg.anticipo_product').id
        return vals
