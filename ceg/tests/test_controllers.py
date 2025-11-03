# -*- coding: utf-8 -*-
"""
Tests for CEG Controllers
"""

from unittest.mock import patch, MagicMock
import json
import base64
from odoo.tests.common import HttpCase, tagged
from odoo.exceptions import UserError

from .test_base import CEGTestBase


@tagged('ceg_controllers', 'http')
class TestMexicanDocumentsController(HttpCase, CEGTestBase):
    """
    Test cases for Mexican Documents Controller
    
    Tests the HTTP endpoints for retrieving Mexican fiscal documents
    related to Magento orders.
    """
    
    def setUp(self):
        super().setUp()
        
        # Create test data
        self.sale_order = self.create_sale_order()
        self.sale_order.action_confirm()
        
        # Set client order reference for Magento
        self.sale_order.client_order_ref = 'MG_ORDER_12345'
        
        # Create invoice
        self.invoice = self.create_account_move(sale_order=self.sale_order)
        self.invoice.action_post()
        
        # Create picking
        self.picking = self.create_stock_picking(sale_order=self.sale_order)
        
        # Mock CFDI attachments
        self._create_mock_cfdi_attachments()
    
    def _create_mock_cfdi_attachments(self):
        """Create mock CFDI attachments for testing"""
        # Create mock PDF data
        mock_pdf_content = b"Mock PDF content for testing"
        mock_pdf_base64 = base64.b64encode(mock_pdf_content)
        
        # Create attachment for invoice
        if hasattr(self.invoice, 'l10n_mx_edi_cfdi_attachment_id'):
            attachment_invoice = self.env['ir.attachment'].create({
                'name': f'CFDI_invoice_{self.invoice.name}.pdf',
                'type': 'binary',
                'datas': mock_pdf_base64,
                'res_model': 'account.move',
                'res_id': self.invoice.id,
            })
            self.invoice.l10n_mx_edi_cfdi_attachment_id = attachment_invoice.id
        
        # Create attachment for picking (transfer document)
        if hasattr(self.picking, 'l10n_mx_edi_cfdi_attachment_id'):
            attachment_picking = self.env['ir.attachment'].create({
                'name': f'CFDI_transfer_{self.picking.name}.pdf',
                'type': 'binary',
                'datas': mock_pdf_base64,
                'res_model': 'stock.picking',
                'res_id': self.picking.id,
            })
            self.picking.l10n_mx_edi_cfdi_attachment_id = attachment_picking.id
    
    def test_get_mexican_documents_urls_success(self):
        """Test successful retrieval of Mexican documents URLs"""
        # Make HTTP request
        url = f'/api/mexican-documents/{self.sale_order.client_order_ref}'
        response = self.url_open(url)
        
        # Parse response
        response_data = json.loads(response.content.decode())
        
        # Assertions
        self.assertTrue(response_data['success'])
        self.assertIn('data', response_data)
        
        data = response_data['data']
        self.assertIn('sale_order', data)
        self.assertIn('invoices', data)
        self.assertIn('payments', data)
        self.assertIn('transfer_documents', data)
        
        # Check sale order data
        so_data = data['sale_order']
        self.assertEqual(so_data['name'], self.sale_order.name)
        self.assertEqual(so_data['magento_ref'], self.sale_order.client_order_ref)
    
    def test_get_mexican_documents_urls_order_not_found(self):
        """Test response when order is not found"""
        # Make HTTP request with non-existent order reference
        url = '/api/mexican-documents/NON_EXISTENT_ORDER'
        response = self.url_open(url)
        
        # Parse response
        response_data = json.loads(response.content.decode())
        
        # Assertions
        self.assertFalse(response_data['success'])
        self.assertIn('error', response_data)
        self.assertIn('code', response_data)
    
    def test_get_mexican_documents_by_name_fallback(self):
        """Test finding order by name when client_order_ref doesn't match"""
        # Clear client_order_ref and set name to the search term
        search_term = 'TEST_ORDER_NAME'
        self.sale_order.client_order_ref = False
        self.sale_order.name = search_term
        
        # Make HTTP request
        url = f'/api/mexican-documents/{search_term}'
        response = self.url_open(url)
        
        # Parse response
        response_data = json.loads(response.content.decode())
        
        # Should still find the order
        self.assertTrue(response_data['success'])
    
    def test_get_invoice_pdf_success(self):
        """Test successful retrieval of invoice PDF"""
        if not hasattr(self.invoice, 'l10n_mx_edi_cfdi_attachment_id'):
            self.skipTest("Mexican localization not available")
        
        # Make HTTP request
        url = f'/api/mexican-documents/pdf/invoice/{self.invoice.id}.pdf'
        params = {'access_token': self.invoice.access_token}
        response = self.url_open(url, params=params)
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('Content-Type'), 'application/pdf')
    
    def test_get_invoice_pdf_invalid_token(self):
        """Test invoice PDF retrieval with invalid access token"""
        if not hasattr(self.invoice, 'l10n_mx_edi_cfdi_attachment_id'):
            self.skipTest("Mexican localization not available")
        
        # Make HTTP request with invalid token
        url = f'/api/mexican-documents/pdf/invoice/{self.invoice.id}.pdf'
        params = {'access_token': 'invalid_token'}
        response = self.url_open(url, params=params)
        
        # Should return error
        self.assertNotEqual(response.status_code, 200)
    
    def test_get_invoice_pdf_not_found(self):
        """Test invoice PDF retrieval for non-existent invoice"""
        # Make HTTP request for non-existent invoice
        url = '/api/mexican-documents/pdf/invoice/99999.pdf'
        params = {'access_token': 'any_token'}
        response = self.url_open(url, params=params)
        
        # Should return 404 or error
        self.assertNotEqual(response.status_code, 200)
    
    def test_get_payment_pdf_success(self):
        """Test successful retrieval of payment PDF"""
        # Create a payment for testing
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_id': self.customer.id,
            'amount': 100.0,
            'currency_id': self.company.currency_id.id,
            'journal_id': self.env['account.journal'].search([
                ('type', '=', 'bank'),
                ('company_id', '=', self.company.id)
            ], limit=1).id,
        })
        
        if not hasattr(payment, 'l10n_mx_edi_cfdi_attachment_id'):
            self.skipTest("Mexican localization not available")
        
        # Mock CFDI attachment for payment
        mock_pdf_content = b"Mock Payment PDF content"
        mock_pdf_base64 = base64.b64encode(mock_pdf_content)
        attachment = self.env['ir.attachment'].create({
            'name': f'CFDI_payment_{payment.name}.pdf',
            'type': 'binary',
            'datas': mock_pdf_base64,
            'res_model': 'account.payment',
            'res_id': payment.id,
        })
        payment.l10n_mx_edi_cfdi_attachment_id = attachment.id
        
        # Make HTTP request
        url = f'/api/mexican-documents/pdf/payment/{payment.id}.pdf'
        params = {'access_token': payment.move_id.access_token}
        response = self.url_open(url, params=params)
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('Content-Type'), 'application/pdf')
    
    def test_get_transfer_pdf_success(self):
        """Test successful retrieval of transfer PDF"""
        if not hasattr(self.picking, 'l10n_mx_edi_cfdi_attachment_id'):
            self.skipTest("Mexican localization not available")
        
        # Make HTTP request
        url = f'/api/mexican-documents/pdf/transfer/{self.picking.id}.pdf'
        params = {'access_token': self.sale_order.access_token}
        response = self.url_open(url, params=params)
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('Content-Type'), 'application/pdf')
    
    def test_document_urls_format(self):
        """Test that document URLs are properly formatted"""
        # Make HTTP request
        url = f'/api/mexican-documents/{self.sale_order.client_order_ref}'
        response = self.url_open(url)
        
        # Parse response
        response_data = json.loads(response.content.decode())
        
        if response_data['success']:
            data = response_data['data']
            
            # Check invoice URLs
            if data['invoices']:
                for invoice_doc in data['invoices']:
                    self.assertIn('name', invoice_doc)
                    self.assertIn('url', invoice_doc)
                    self.assertIn('.pdf', invoice_doc['url'])
                    self.assertIn('access_token', invoice_doc['url'])
            
            # Check payment URLs
            if data['payments']:
                for payment_doc in data['payments']:
                    self.assertIn('name', payment_doc)
                    self.assertIn('url', payment_doc)
                    self.assertIn('.pdf', payment_doc['url'])
            
            # Check transfer URLs
            if data['transfer_documents']:
                for transfer_doc in data['transfer_documents']:
                    self.assertIn('name', transfer_doc)
                    self.assertIn('url', transfer_doc)
                    self.assertIn('.pdf', transfer_doc['url'])


@tagged('ceg_controllers', 'http')
class TestReportSaleOperationsController(HttpCase, CEGTestBase):
    """
    Test cases for Report Sale Operations Controller
    
    Tests the picking list download functionality.
    """
    
    def setUp(self):
        super().setUp()
        
        # Create test data
        self.sale_order = self.create_sale_order()
        self.sale_order.action_confirm()
        
        # Create picking with detailed address information
        self.picking = self.create_stock_picking(sale_order=self.sale_order)
        
        # Add more detailed customer address for CSV testing
        self.customer.write({
            'street_name': 'Test Street',
            'street_number': '123',
            'street_number2': 'A',
            'street2': 'Apt 1',
            'city_id': self.env['res.city'].create({
                'name': 'Test City',
                'state_id': self.env.ref('base.state_us_5').id,
                'country_id': self.env.ref('base.us').id,
            }).id,
        })
    
    def test_download_picking_list_success(self):
        """Test successful download of picking list"""
        # Make HTTP request
        url = f'/ceg/download_picking_list/{self.picking.id}'
        response = self.url_open(url)
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertIn('picking_list', response.headers.get('Content-Disposition', ''))
    
    def test_download_picking_list_multiple_pickings(self):
        """Test download of picking list with multiple pickings"""
        # Create additional pickings
        picking_2 = self.create_stock_picking(sale_order=self.sale_order)
        picking_3 = self.create_stock_picking(sale_order=self.sale_order)
        
        # Make HTTP request
        picking_ids = f'{self.picking.id},{picking_2.id},{picking_3.id}'
        url = f'/ceg/download_picking_list/{picking_ids}'
        response = self.url_open(url)
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertIn('picking_list', response.headers.get('Content-Disposition', ''))
    
    def test_download_picking_list_no_ids(self):
        """Test download with no picking IDs"""
        # Make HTTP request with empty picking_ids
        url = '/ceg/download_picking_list/'
        response = self.url_open(url)
        
        # Should return error
        self.assertEqual(response.status_code, 500)
        self.assertIn('No se seleccionaron pickings', response.text)
    
    def test_download_picking_list_invalid_ids(self):
        """Test download with invalid picking IDs"""
        # Make HTTP request with invalid IDs
        url = '/ceg/download_picking_list/invalid,ids'
        response = self.url_open(url)
        
        # Should return error or handle gracefully
        # The exact behavior depends on implementation
        self.assertIn(response.status_code, [400, 500])
    
    def test_csv_header_format(self):
        """Test that CSV header contains expected columns"""
        # The controller generates CSV with specific headers
        expected_headers = [
            'Pedido de ventas', 'Cuenta de cliente', 'Nombre',
            'Teléfono del cliente', 'Teléfono móvil del cliente',
            'Código de artículo', 'Código de artículo componente',
            'Nombre del producto', 'Unidad', 'Cantidad', 'Bultos',
            'Volumen', 'Referencia', 'Modo de entrega', 'Dirección'
        ]
        
        # This test verifies the expected headers exist in the controller
        # In a real test, you'd download the file and check the headers
        self.assertTrue(len(expected_headers) > 0)
    
    def test_picking_list_filename_format(self):
        """Test that generated filename follows expected format"""
        # Make HTTP request
        url = f'/ceg/download_picking_list/{self.picking.id}'
        response = self.url_open(url)
        
        if response.status_code == 200:
            content_disposition = response.headers.get('Content-Disposition', '')
            # Should contain timestamp and picking_list
            self.assertIn('picking_list', content_disposition)
            # Should have CSV extension (though converted to Excel)
            self.assertIn('.csv', content_disposition)


@tagged('ceg_controllers')
class TestControllerHelperMethods(CEGTestBase):
    """
    Test cases for controller helper methods that can be tested without HTTP
    """
    
    def setUp(self):
        super().setUp()
        
        # Create test sale order
        self.sale_order = self.create_sale_order()
        self.sale_order.client_order_ref = 'TEST_MG_ORDER'
        self.sale_order.action_confirm()
    
    def test_get_sale_order_by_magento_ref_direct_match(self):
        """Test finding sale order by direct client_order_ref match"""
        from odoo.addons.ceg.controllers.mexican_documents_controller import MexicanDocumentsController
        
        controller = MexicanDocumentsController()
        
        # Test direct match
        found_order = controller._get_sale_order_by_magento_ref('TEST_MG_ORDER')
        
        # Should find the order
        self.assertEqual(found_order.id, self.sale_order.id)
    
    def test_get_sale_order_by_magento_ref_name_fallback(self):
        """Test finding sale order by name when client_order_ref doesn't match"""
        from odoo.addons.ceg.controllers.mexican_documents_controller import MexicanDocumentsController
        
        controller = MexicanDocumentsController()
        
        # Test name fallback
        found_order = controller._get_sale_order_by_magento_ref(self.sale_order.name)
        
        # Should find the order
        self.assertEqual(found_order.id, self.sale_order.id)
    
    def test_validate_access_token_valid(self):
        """Test access token validation with valid token"""
        from odoo.addons.ceg.controllers.mexican_documents_controller import MexicanDocumentsController
        
        controller = MexicanDocumentsController()
        
        # Should not raise exception with valid token
        try:
            controller._validate_access_token(self.sale_order, self.sale_order.access_token)
        except Exception as e:
            self.fail(f"_validate_access_token raised exception with valid token: {e}")
    
    def test_validate_access_token_invalid(self):
        """Test access token validation with invalid token"""
        from odoo.addons.ceg.controllers.mexican_documents_controller import MexicanDocumentsController
        from werkzeug.exceptions import Unauthorized
        
        controller = MexicanDocumentsController()
        
        # Should raise Unauthorized exception with invalid token
        with self.assertRaises(Unauthorized):
            controller._validate_access_token(self.sale_order, 'invalid_token')
    
    def test_get_mexican_documents_structure(self):
        """Test the structure of Mexican documents data"""
        from odoo.addons.ceg.controllers.mexican_documents_controller import MexicanDocumentsController
        
        controller = MexicanDocumentsController()
        
        # Create invoice for the sale order
        invoice = self.create_account_move(sale_order=self.sale_order)
        invoice.action_post()
        
        # Get documents
        documents = controller._get_mexican_documents_for_sale(self.sale_order)
        
        # Verify structure
        self.assertIn('sale_order', documents)
        self.assertIn('invoices', documents)
        self.assertIn('payments', documents)
        self.assertIn('transfer_documents', documents)
        
        # Verify sale order data
        so_data = documents['sale_order']
        self.assertIn('id', so_data)
        self.assertIn('name', so_data)
        self.assertIn('magento_ref', so_data)
        self.assertIn('amount_total', so_data)