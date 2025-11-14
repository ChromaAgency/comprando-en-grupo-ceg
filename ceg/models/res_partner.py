from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    @api.constrains('vat', 'country_id')
    def check_vat(self):
        if self.env.context.get('skip_vat_check'):
            return 
        super(ResPartner, self).check_vat()