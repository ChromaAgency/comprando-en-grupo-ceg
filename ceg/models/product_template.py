from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    ceg_code = fields.Char(string='Código CEG', help='Código utilizado para identificar los productos en CEG')

    
