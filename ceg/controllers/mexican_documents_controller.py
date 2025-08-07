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


    def _get_sale_order_by_magento_ref(self, magento_order_ref):
        """Obtiene la orden de venta por referencia de Magento"""
        sale_order = request.env['sale.order'].sudo().search([
            ('client_order_ref', '=', magento_order_ref)
        ], limit=1)
        
        if not sale_order:
            # Buscar también por nombre o referencia interna
            sale_order = request.env['sale.order'].sudo().search([
                '|',
                '|',
                ('name', 'ilike', magento_order_ref),
                ('origin', '=', magento_order_ref),
                ('client_order_ref', 'ilike', magento_order_ref)
            ], limit=1)
            
        if not sale_order:
            raise NotFound(_("Sale order not found for Magento reference: %s") % magento_order_ref)
        
        return sale_order

    def _get_mexican_documents_for_sale(self, sale_order):
        """Obtiene los documentos mexicanos relacionados a una venta"""
        # 1. Facturas (account.move con documentos CFDI)
        invoices = sale_order.invoice_ids.filtered(lambda inv: inv.state == 'posted')
        cfdi_invoices = []
        base_url = request.httprequest.host_url.rstrip('/')
        for invoice in invoices:
            cfdi_invoices.append({
                'name': f"Factura anticipo {invoice.name}",
                'url': f"{base_url}/api/mexican-documents/pdf/invoice/{invoice.id}"
            })

        # 2. Complementos de pago (account.payment con documentos CFDI)
        payments = sale_order.invoice_ids.mapped('payment_ids')
        cfdi_payments = []
        for payment in payments:
            cfdi_payments.append({
                'name': f"Complemento de pago {payment.name}",
                'url': f"{base_url}/api/mexican-documents/pdf/payment/{payment.id}"
            })

        # 3. Facturas de traslado (stock.picking con documentos CFDI)
        pickings = sale_order.picking_ids.filtered(lambda p: p.state == 'done')
        cfdi_pickings = []
        for picking in pickings:
            cfdi_pickings.append({
                'name': f"Factura de traslado {picking.name}",
                'url': f"{base_url}/api/mexican-documents/pdf/transfer/{picking.id}"
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
                type='http', auth='none', methods=['GET'], csrf=False)
    def get_mexican_documents_urls(self, magento_order_ref, **kw):
        """Endpoint para obtener las URLs de documentos mexicanos por referencia de Magento"""
        try:
            
            
            # Buscar orden de venta
            sale_order = self._get_sale_order_by_magento_ref(magento_order_ref)
            
            # Obtener documentos mexicanos
            documents = self._get_mexican_documents_for_sale(sale_order)
            
            
            return http.Response(json.dumps({
                'success': True,
                'data': documents
            }))
            
        except (Unauthorized, NotFound) as e:
            return http.Response(json.dumps({
                'success': False,
                'error': str(e),
                'code': e.code if hasattr(e, 'code') else 400
            }))
        except Exception as e:
            _logger.error("Error getting Mexican documents: %s", str(e))
            return http.Response(json.dumps({
                'success': False,
                'error': _("Internal server error"),
                'code': 500
            }))

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
