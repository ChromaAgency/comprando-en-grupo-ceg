# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import json
from odoo import models, fields
from odoo.exceptions import UserError

key_list = ['vat']
key_list_without_company = ['name', 'street', 'street2', 'city', 'zip', 'phone', 'state_id', 'country_id', 'parent_id', 'type']
import logging
_logger = logging.getLogger(__name__)


class MagentoResPartnerEpt(models.Model):
    _inherit = "magento.res.partner.ept"

    @staticmethod
    def add_store_settings(address, data):
        address.update({'store_view': data.get('store_view' or False), 'store_id': data.get('store_id' or False)})
        return address  
    
    @staticmethod
    def __get_type(keys):
        address_type = 'other'
        if 'default_billing' in keys:
            address_type = 'invoice'
        elif 'default_shipping' in keys:
            address_type = 'delivery'
        elif 'contact' in keys:
            address_type = 'contact'
        return address_type
    @staticmethod
    def __merge_street(streets):
        street1 = street2 = ''
        if len(streets):
            street1 = streets[0]
            if len(streets) == 2:
                street2 = streets[1]
            elif len(streets) == 3:
                street2 = f"{streets[1]}, {streets[2]}"
            elif len(streets) == 4:
                street2 = f"{streets[1]}, {streets[2]}, {streets[3]}"
        return {
            'street': street1,
            'street2': street2
        }

    def _prepare_partner_values(self, data, instance, **kwargs):
        customer_group_id = data.get('customer_group_odoo_id')
        address_type = self.__get_type(list(data.keys()))
        street = self.__merge_street(data.get('street', []))
        magento_store = data.get('store_view') or self.env['magento.storeview'].search(
            [('magento_storeview_id', '=', data.get('store_id'))], limit=1)
        values = {
            'name': f"{data.get('firstname')} {data.get('lastname')}",
            'email': data.get('email'),
            'vat': data.get('vat_id', '') or data.get('taxvat', ''),
            'customer_rank': 1,
            'is_magento_customer': True,
            'street': street.get('street'),
            'street2': street.get('street2'),
            'city': data.get('city', ''),
            'phone': data.get('telephone', ''),
            'zip': data.get('postcode', ''),
            'lang': magento_store.lang_id.code,
            'type': address_type,
            'parent_id': kwargs.get('parent_id', False),
        }
        # if customer_group_id:
        #     values.update({'customer_group_id': customer_group_id})
        values.update(self._find_state_country(data))
        values = self.env['res.partner'].remove_special_chars_from_partner_vals(values)
        return values
    
    def _create_odoo_partner_from_email(self, data, instance):
        Partner = self.env['res.partner']
        partner = Partner.search([('email', '=ilike', data.get('email'))])
        if len(partner) > 1:
            # If we found more than 1 customer with same email then we are getting
            # any one customer from it which have not parent_id set.
            partner = Partner.search([('email', '=', data.get('email')),
                                      ('parent_id', '=', False)], limit=1)
        if not partner:
            # Add contact=True to identify the address type. Remove the keys from the contact
            # type customer to make the identification of customer easily.
            data.update({'contact': True})
            if 'default_billing' in list(data.keys()):
                del data['default_billing']
            if 'default_shipping' in list(data.keys()):
                del data['default_shipping']
            values = self._prepare_partner_values(data, instance)
            partner = Partner.with_context(skip_vat_check=True).create(values)
        return partner
    
    def _search_company_by_name(self, company_name):
        if company_name:
            return self.env['res.partner'].search([('name', '=', company_name), ('is_company', '=', True)], limit = 1)
        return self.env['res.partner']

    def _find_state_country(self, data):
        partner = self.env['res.partner']
        country = partner.get_country(data.get('country_id'))
        state_code = data.get('region', {}).get('region_code')
        if country.code == 'AR' and state_code and 'AR-' in state_code:
            state_code = state_code.split('-')[1]
        zip_code = data.get('postcode')
        state = partner.with_context(skip_vat_check=True).create_or_update_state_ept(data.get('country_id'), state_code, zip_code,
                                                   country_obj=country)
        return {
            'country_id': country.id,
            'state_id': state.id
        }
    
    def _get_l10n_latam_responsibility_type(self, taxpayer_type):
        taxpayer_types_xml_id = {
            'Responsable inscripto': 'l10n_ar.res_IVARI',
            'Sujeto Exento': 'l10n_ar.res_IVAE',
            'Monotributo': 'l10n_ar.res_RM',
            'Exterior': 'l10n_ar.res_EXT',
            'Tierra del Fuego': 'l10n_ar.res_IVA_LIB',
            'No Alcanzado': 'l10n_ar.res_IVA_NO_ALC',
        } 
        return self.env.ref(taxpayer_types_xml_id[taxpayer_type])

    def _upsert_company(self, address, partner, instance):
        Partner = self.env['res.partner']
        company_name = address.get('company')

        if not instance.import_customer_as_company:
            partner.with_context(skip_vat_check=True).write({'company_name': company_name})
            return False

        vat = address.get('vat_id', '').strip()
        
        if vat:
            company_partner = Partner.search([
                ('vat', '=', vat),
                ('is_company', '=', True),
                ('parent_id', '=', False),
            ], limit=1)
        else:
            company_partner = self._search_company_by_name(company_name)
        
        if not company_partner:
            company_partner = Partner.with_context(skip_vat_check=True).create({
                'name': company_name,
                'company_type': 'company',
                'is_magento_customer': True,
                'vat': vat
            })
        
        company_partner_vals = self._prepare_partner_values(address, instance)
        # l10n_ar_afip_responsibility_type_id = self._get_l10n_latam_responsibility_type(address.get('taxpayer_type'))
        # company_partner_vals.update({
        #     'l10n_ar_afip_responsibility_type_id': l10n_ar_afip_responsibility_type_id.id,
        #     'l10n_latam_identification_type_id': self.env.ref('l10n_ar.it_cuit').id, 
        #                              })
        company_partner_vals.pop('type', '')
        company_partner_vals.pop('parent_id', '')
        company_partner_vals.pop('name', '')

        # company_partner_vals.update({
        #     'customer_group_id': address.get('customer_group_odoo_id')
        # })

        company_partner.with_context(skip_vat_check=True).write(company_partner_vals)

        if partner != company_partner:
            partner.with_context(skip_vat_check=True).write({'parent_id': company_partner.id})

        return company_partner

         
    def _upsert_partner_address(self, address, parent_id, instance):
        Partner = self.env['res.partner']
        partner_type = 'contact'
        if 'default_billing' in address:
            partner_type = 'invoice'
        if 'default_shipping' in address:
            partner_type = 'delivery'        
       
        vat = address.get('vat_id', '').strip()
        if vat:
            existing_partner = Partner.search([('vat', '=', vat), ('parent_id','=',parent_id), ('type','=',partner_type)], limit=1)
            if existing_partner:
                return existing_partner 
       
        partner_values = self._prepare_partner_values(address, instance, parent_id=parent_id)
        partner_values.update(self._find_state_country(address))

        partner = Partner.with_context(skip_vat_check=True).create(partner_values)

        customer_group_id = address.get('customer_group_odoo_id')
        # partner.write({'customer_group_id': customer_group_id})

        return partner
            

    def _search_customer(self, id:str=None, email:str=None, child:bool=None, customer_id=None, instance_id=None ):
        if not instance_id: raise UserError("No instance Found")
        if id in ['Guest Customer', 'Customer Without Id']:
            if not email: raise UserError("No email found")
            return self.search([('partner_id.email', '=', email),
                                ('magento_instance_id', '=', instance_id)], limit=1)
        if child:
            if not id or not customer_id: raise UserError("Customer Id or ID were not found")
            return self.search([('magento_customer_id', '=', customer_id),
                                ('address_id', '=', id),
                                ('magento_instance_id', '=', instance_id)], limit=1)
        if not id: raise UserError("ID was not found")
        return self.search([('magento_customer_id', '=', id),
                                ('magento_instance_id', '=', instance_id)], limit=1)
    
    @staticmethod
    def _prepare_magento_customer_values(data=None, partner_id=None, customer_id=None, address_id='', instance=None):
        website = instance.magento_website_ids.filtered(
            lambda w: int(w.magento_website_id) == data.get('website_id'))
        return {
            'partner_id': partner_id,
            'magento_instance_id': instance.id,
            'magento_website_id': website and website.id,
            'magento_customer_id': customer_id,
            'address_id': address_id
        }
    
    def _upsert_customer_address(self, address, data, partner, instance ):
        customer = self._search_customer(child=True, id=address.get('id'), customer_id=address.get('customer_id'), instance_id=instance.id)
        if not customer:
            layer_values = self._prepare_magento_customer_values(instance=instance, data=data, customer_id=address.get('customer_id'),
                                                                address_id=address.get('id'), partner_id=partner.id)
            customer.with_context(skip_vat_check=True).create(layer_values)
        return customer 
    
    def _upsert_customer_address_partner(self, address, data, instance):
        customer_partner_id = data.get('parent_id')
        if 'taxvat' not in address and 'vat_id' not in address and data.get('taxvat'):
            address['taxvat'] = data.get('taxvat')
        address = self.add_store_settings(address, data)
        partner = self._upsert_partner_address(address, customer_partner_id, instance)
        customer = self._upsert_customer_address(address, data, partner, instance)
        data.update({partner.type: partner.id})
        return data 
    
    def create_magento_customer(self, line, is_order=False):
        if is_order:
            data = line
            instance = line.get('instance_id')
        else:
            data = json.loads(line.data)
            instance = line.instance_id
        customer = False
        if data.get('id'):
            customer = self._search_customer(id=data.get('id'), email=data.get('email'), instance_id=instance.id)
        if not customer:
            partner = self._create_odoo_partner_from_email(data, instance)
            values = self._prepare_magento_customer_values(partner_id=partner.id, instance=instance,
                                                           data=data, customer_id=data.get('id'))
            customer = self.with_context(skip_vat_check=True).create(values)
        customer_group_id = data.get('customer_odoo_id')
        data.update({'parent_id': customer.partner_id.id})
        # customer.partner_id.customer_group_id = customer_group_id
        for address in data.get('addresses'):
            if address.get('default_billing', False):
                billing_address = address.copy()
                billing_address['store_id'] = data.get('store_id')
                # billing_address.update({'customer_group_odoo_id': customer_group_id})
                self._upsert_company(billing_address, customer.partner_id, instance)
            # address.update({'customer_group_odoo_id': customer_group_id})
            data = self._upsert_customer_address_partner(address, data, instance)
        return data
