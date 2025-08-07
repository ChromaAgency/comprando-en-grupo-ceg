# -*- coding: utf-8 -*-

import base64
import json
import logging
from werkzeug.exceptions import BadRequest, Unauthorized, NotFound

from odoo import http, _
from odoo.exceptions import AccessError, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class MexicanDocumentsController(http.Controller):

    def _validate_api_key(self, api_key):
        """Valida el API key utilizando el módulo auth_api_key"""
        if not api_key:
            raise Unauthorized(_("API key is required"))
        
        try:
            auth_api_key_model = request.env['auth.api.key'].sudo()
            api_key_record = auth_api_key_model._retrieve_api_key(api_key)
            if not api_key_record:
                raise Unauthorized(_("Invalid API key"))
            
            # Cambiar al usuario asociado con la API key
            request.uid = api_key_record.user_id.id
            return api_key_record
        except (AccessError, ValidationError) as e:
            raise Unauthorized(_("Invalid API key: %s") % str(e))

    def _get_sale_order_by_magento_ref(self, magento_order_ref):
        """Obtiene la orden de venta por referencia de Magento"""
        sale_order = request.env['sale.order'].sudo().search([
            ('client_order_ref', '=', magento_order_ref)
        ], limit=1)
        
        if not sale_order:
            # Buscar también por nombre o referencia interna
            sale_order = request.env['sale.order'].sudo().search([
                '|',
                ('name', 'ilike', magento_order_ref),
                ('origin', '=', magento_order_ref)
            ], limit=1)
            
        if not sale_order:
            raise NotFound(_("Sale order not found for Magento reference: %s") % magento_order_ref)
        
        return sale_order

    def _get_mexican_documents_for_sale(self, sale_order):
        """Obtiene los documentos mexicanos relacionados a una venta"""
        documents = {}
        
        # 1. Facturas (account.move con documentos CFDI)
        invoices = sale_order.invoice_ids.filtered(lambda inv: inv.state == 'posted')
        cfdi_invoices = []
        for invoice in invoices:
            if hasattr(invoice, 'l10n_mx_edi_cfdi_attachment_id') and invoice.l10n_mx_edi_cfdi_attachment_id:
                cfdi_invoices.append({
                    'id': invoice.id,
                    'name': invoice.name,
                    'amount_total': invoice.amount_total,
                    'cfdi_uuid': getattr(invoice, 'l10n_mx_edi_cfdi_uuid', ''),
                    'cfdi_state': getattr(invoice, 'l10n_mx_edi_cfdi_state', ''),
                })
        
        # 2. Complementos de pago (account.payment con documentos CFDI)
        payments = sale_order.invoice_ids.mapped('payment_ids')
        cfdi_payments = []
        for payment in payments:
            if hasattr(payment, 'l10n_mx_edi_cfdi_attachment_id') and payment.l10n_mx_edi_cfdi_attachment_id:
                cfdi_payments.append({
                    'id': payment.id,
                    'name': payment.name,
                    'amount': payment.amount,
                    'cfdi_uuid': getattr(payment, 'l10n_mx_edi_cfdi_uuid', ''),
                    'cfdi_state': getattr(payment, 'l10n_mx_edi_cfdi_state', ''),
                })
        
        # 3. Facturas de traslado (stock.picking con documentos CFDI)
        pickings = sale_order.picking_ids.filtered(lambda p: p.state == 'done')
        cfdi_pickings = []
        for picking in pickings:
            # Buscar si tiene documento CFDI de traslado
            if hasattr(picking, 'l10n_mx_edi_cfdi_attachment_id') and picking.l10n_mx_edi_cfdi_attachment_id:
                cfdi_pickings.append({
                    'id': picking.id,
                    'name': picking.name,
                    'cfdi_uuid': getattr(picking, 'l10n_mx_edi_cfdi_uuid', ''),
                    'cfdi_state': getattr(picking, 'l10n_mx_edi_cfdi_state', ''),
                })
        
        documents = {
            'sale_order': {
                'id': sale_order.id,
                'name': sale_order.name,
                'magento_ref': sale_order.client_order_ref,
                'amount_total': sale_order.amount_total,
            },
            'invoices': cfdi_invoices,
            'payments': cfdi_payments,
            'transfer_documents': cfdi_pickings,
        }
        
        return documents

    @http.route('/api/mexican-documents/<string:magento_order_ref>', 
                type='json', auth='none', methods=['GET'], csrf=False)
    def get_mexican_documents_urls(self, magento_order_ref, **kw):
        """Endpoint para obtener las URLs de documentos mexicanos por referencia de Magento"""
        try:
            # Validar API key
            api_key = request.httprequest.headers.get('X-API-Key')
            self._validate_api_key(api_key)
            
            # Buscar orden de venta
            sale_order = self._get_sale_order_by_magento_ref(magento_order_ref)
            
            # Obtener documentos mexicanos
            documents = self._get_mexican_documents_for_sale(sale_order)
            
            # Generar URLs para cada documento
            base_url = request.httprequest.host_url.rstrip('/')
            
            # URLs para facturas
            for invoice in documents['invoices']:
                invoice['pdf_url'] = f"{base_url}/api/mexican-documents/pdf/invoice/{invoice['id']}"
            
            # URLs para complementos de pago
            for payment in documents['payments']:
                payment['pdf_url'] = f"{base_url}/api/mexican-documents/pdf/payment/{payment['id']}"
            
            # URLs para documentos de traslado
            for picking in documents['transfer_documents']:
                picking['pdf_url'] = f"{base_url}/api/mexican-documents/pdf/transfer/{picking['id']}"
            
            return {
                'success': True,
                'data': documents
            }
            
        except (Unauthorized, NotFound) as e:
            return {
                'success': False,
                'error': str(e),
                'code': e.code if hasattr(e, 'code') else 400
            }
        except Exception as e:
            _logger.error("Error getting Mexican documents: %s", str(e))
            return {
                'success': False,
                'error': _("Internal server error"),
                'code': 500
            }

    @http.route('/api/mexican-documents/pdf/invoice/<int:invoice_id>', 
                type='http', auth='none', methods=['GET'], csrf=False)
    def get_invoice_pdf(self, invoice_id, **kw):
        """Endpoint para obtener el PDF de una factura CFDI"""
        try:
            # Validar API key
            api_key = request.httprequest.args.get('api_key') or request.httprequest.headers.get('X-API-Key')
            self._validate_api_key(api_key)
            
            # Buscar factura
            invoice = request.env['account.move'].sudo().browse(invoice_id)
            if not invoice.exists() or invoice.move_type not in ('out_invoice', 'out_refund'):
                raise NotFound(_("Invoice not found"))
            
            # Verificar que tenga documento CFDI
            if not hasattr(invoice, 'l10n_mx_edi_cfdi_attachment_id') or not invoice.l10n_mx_edi_cfdi_attachment_id:
                raise NotFound(_("CFDI document not found for this invoice"))
            
            # Obtener el PDF del attachment
            attachment = invoice.l10n_mx_edi_cfdi_attachment_id
            if not attachment or not attachment.datas:
                raise NotFound(_("CFDI PDF not found"))
            
            # Retornar el PDF
            pdf_data = base64.b64decode(attachment.datas)
            return request.make_response(
                pdf_data,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename="{attachment.name}"'),
                    ('Content-Length', len(pdf_data))
                ]
            )
            
        except (Unauthorized, NotFound) as e:
            return request.make_response(
                json.dumps({'error': str(e)}),
                status=e.code if hasattr(e, 'code') else 400,
                headers=[('Content-Type', 'application/json')]
            )
        except Exception as e:
            _logger.error("Error getting invoice PDF: %s", str(e))
            return request.make_response(
                json.dumps({'error': _("Internal server error")}),
                status=500,
                headers=[('Content-Type', 'application/json')]
            )

    @http.route('/api/mexican-documents/pdf/payment/<int:payment_id>', 
                type='http', auth='none', methods=['GET'], csrf=False)
    def get_payment_pdf(self, payment_id, **kw):
        """Endpoint para obtener el PDF de un complemento de pago CFDI"""
        try:
            # Validar API key
            api_key = request.httprequest.args.get('api_key') or request.httprequest.headers.get('X-API-Key')
            self._validate_api_key(api_key)
            
            # Buscar pago
            payment = request.env['account.payment'].sudo().browse(payment_id)
            if not payment.exists():
                raise NotFound(_("Payment not found"))
            
            # Verificar que tenga documento CFDI
            if not hasattr(payment, 'l10n_mx_edi_cfdi_attachment_id') or not payment.l10n_mx_edi_cfdi_attachment_id:
                raise NotFound(_("CFDI document not found for this payment"))
            
            # Obtener el PDF del attachment
            attachment = payment.l10n_mx_edi_cfdi_attachment_id
            if not attachment or not attachment.datas:
                raise NotFound(_("CFDI PDF not found"))
            
            # Retornar el PDF
            pdf_data = base64.b64decode(attachment.datas)
            return request.make_response(
                pdf_data,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename="{attachment.name}"'),
                    ('Content-Length', len(pdf_data))
                ]
            )
            
        except (Unauthorized, NotFound) as e:
            return request.make_response(
                json.dumps({'error': str(e)}),
                status=e.code if hasattr(e, 'code') else 400,
                headers=[('Content-Type', 'application/json')]
            )
        except Exception as e:
            _logger.error("Error getting payment PDF: %s", str(e))
            return request.make_response(
                json.dumps({'error': _("Internal server error")}),
                status=500,
                headers=[('Content-Type', 'application/json')]
            )

    @http.route('/api/mexican-documents/pdf/transfer/<int:picking_id>', 
                type='http', auth='none', methods=['GET'], csrf=False)
    def get_transfer_pdf(self, picking_id, **kw):
        """Endpoint para obtener el PDF de un documento de traslado CFDI"""
        try:
            # Validar API key
            api_key = request.httprequest.args.get('api_key') or request.httprequest.headers.get('X-API-Key')
            self._validate_api_key(api_key)
            
            # Buscar picking
            picking = request.env['stock.picking'].sudo().browse(picking_id)
            if not picking.exists():
                raise NotFound(_("Transfer document not found"))
            
            # Verificar que tenga documento CFDI
            if not hasattr(picking, 'l10n_mx_edi_cfdi_attachment_id') or not picking.l10n_mx_edi_cfdi_attachment_id:
                raise NotFound(_("CFDI document not found for this transfer"))
            
            # Obtener el PDF del attachment
            attachment = picking.l10n_mx_edi_cfdi_attachment_id
            if not attachment or not attachment.datas:
                raise NotFound(_("CFDI PDF not found"))
            
            # Retornar el PDF
            pdf_data = base64.b64decode(attachment.datas)
            return request.make_response(
                pdf_data,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename="{attachment.name}"'),
                    ('Content-Length', len(pdf_data))
                ]
            )
            
        except (Unauthorized, NotFound) as e:
            return request.make_response(
                json.dumps({'error': str(e)}),
                status=e.code if hasattr(e, 'code') else 400,
                headers=[('Content-Type', 'application/json')]
            )
        except Exception as e:
            _logger.error("Error getting transfer PDF: %s", str(e))
            return request.make_response(
                json.dumps({'error': _("Internal server error")}),
                status=500,
                headers=[('Content-Type', 'application/json')]
            )
