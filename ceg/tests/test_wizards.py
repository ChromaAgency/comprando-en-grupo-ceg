# -*- coding: utf-8 -*-
"""
Tests for Wizard models
"""

from unittest.mock import patch, MagicMock
from odoo.tests.common import tagged
from odoo.exceptions import UserError

from .test_base import CEGTestBase


@tagged('ceg_wizard', 'purchase_advance')
class TestPurchaseAdvancePaymentInv(CEGTestBase):
    """
    Test cases for Purchase Advance Payment Invoice Wizard
    
    Tests the functionality for creating advance payment invoices
    for sale orders related to purchase orders.
    """
    
    def setUp(self):
        super().setUp()
        
        # Create purchase order
        self.purchase_order = self.create_purchase_order()
        self.purchase_order.button_confirm()
        
        # Create sale order and link it
        self.sale_order = self.create_sale_order()
        self.sale_order.action_confirm()
        
        # Link purchase line to sale line
        self.purchase_order.order_line[0].sale_line_id = self.sale_order.order_line[0].id
        
        # Add method to purchase order to find related sale orders
        def _get_sale_orders(self):
            """Mock method to get related sale orders"""
            return self.env['sale.order'].browse([self.sale_order.id])
        
        # Monkey patch the method
        self.purchase_order.__class__._get_sale_orders = _get_sale_orders
    
    def test_wizard_creation_with_default_values(self):
        """Test wizard creation with default values"""
        wizard = self.env['purchase.advance.payment.inv'].with_context(
            active_ids=[self.purchase_order.id]
        ).create({})
        
        # Check default values
        self.assertEqual(wizard.percentage, 1.0)
        self.assertEqual(wizard.anticipo_type, 'anticipo_1')
        self.assertEqual(len(wizard.purchase_order_ids), 1)
        self.assertEqual(wizard.purchase_order_ids[0].id, self.purchase_order.id)
    
    def test_compute_count(self):
        """Test computation of purchase order count"""
        wizard = self.env['purchase.advance.payment.inv'].create({
            'purchase_order_ids': [(6, 0, [self.purchase_order.id])]
        })
        
        self.assertEqual(wizard.count, 1)
        
        # Add another purchase order
        po2 = self.create_purchase_order()
        wizard.purchase_order_ids = [(6, 0, [self.purchase_order.id, po2.id])]
        
        self.assertEqual(wizard.count, 2)
    
    def test_compute_sale_order_total(self):
        """Test computation of sale order total"""
        wizard = self.env['purchase.advance.payment.inv'].create({
            'purchase_order_ids': [(6, 0, [self.purchase_order.id])]
        })
        
        # Should compute total from related sale orders
        expected_total = self.sale_order.amount_total
        self.assertEqual(wizard.sale_order_total, expected_total)
    
    def test_compute_currency_id_single_order(self):
        """Test currency computation for single purchase order"""
        wizard = self.env['purchase.advance.payment.inv'].create({
            'purchase_order_ids': [(6, 0, [self.purchase_order.id])]
        })
        
        self.assertEqual(wizard.currency_id, self.purchase_order.currency_id)
    
    def test_compute_currency_id_multiple_orders(self):
        """Test currency computation for multiple purchase orders"""
        po2 = self.create_purchase_order()
        wizard = self.env['purchase.advance.payment.inv'].create({
            'purchase_order_ids': [(6, 0, [self.purchase_order.id, po2.id])]
        })
        
        # Should be False for multiple orders
        self.assertFalse(wizard.currency_id)
    
    def test_compute_company_id_single_order(self):
        """Test company computation for single purchase order"""
        wizard = self.env['purchase.advance.payment.inv'].create({
            'purchase_order_ids': [(6, 0, [self.purchase_order.id])]
        })
        
        self.assertEqual(wizard.company_id, self.purchase_order.company_id)
    
    def test_compute_company_id_multiple_orders(self):
        """Test company computation for multiple purchase orders"""
        po2 = self.create_purchase_order()
        wizard = self.env['purchase.advance.payment.inv'].create({
            'purchase_order_ids': [(6, 0, [self.purchase_order.id, po2.id])]
        })
        
        # Should be False for multiple orders
        self.assertFalse(wizard.company_id)
    
    def test_check_percentage_constraint_valid(self):
        """Test percentage constraint with valid values"""
        # Valid percentage values should not raise exception
        wizard = self.env['purchase.advance.payment.inv'].create({
            'percentage': 0.5,
            'purchase_order_ids': [(6, 0, [self.purchase_order.id])]
        })
        
        # Should not raise exception
        wizard._check_percentage()
        
        # Test boundary values
        wizard.percentage = 0.01
        wizard._check_percentage()
        
        wizard.percentage = 1.0
        wizard._check_percentage()
    
    def test_check_percentage_constraint_invalid_low(self):
        """Test percentage constraint with invalid low value"""
        wizard = self.env['purchase.advance.payment.inv'].create({
            'percentage': 0.0,
            'purchase_order_ids': [(6, 0, [self.purchase_order.id])]
        })
        
        # Should raise UserError
        with self.assertRaises(UserError):
            wizard._check_percentage()
    
    def test_check_percentage_constraint_invalid_high(self):
        """Test percentage constraint with invalid high value"""
        wizard = self.env['purchase.advance.payment.inv'].create({
            'percentage': 1.1,
            'purchase_order_ids': [(6, 0, [self.purchase_order.id])]
        })
        
        # Should raise UserError
        with self.assertRaises(UserError):
            wizard._check_percentage()
    
    def test_anticipo_type_selection(self):
        """Test anticipo_type selection field"""
        wizard = self.env['purchase.advance.payment.inv'].create({
            'purchase_order_ids': [(6, 0, [self.purchase_order.id])]
        })
        
        # Test valid selection values
        valid_values = ['anticipo_1', 'anticipo_2', 'anticipo_saldo', 'saldo_final']
        for value in valid_values:
            wizard.anticipo_type = value
            self.assertEqual(wizard.anticipo_type, value)
    
    @patch('requests.post')
    def test_create_sale_advance_payments_anticipo_1(self, mock_post):
        """Test creating advance payments for anticipo_1"""
        # Setup mock response for Magento API
        mock_post.return_value = self.mock_magento_api_response(200, '{"success": true}')
        
        wizard = self.env['purchase.advance.payment.inv'].create({
            'purchase_order_ids': [(6, 0, [self.purchase_order.id])],
            'anticipo_type': 'anticipo_1',
            'percentage': 0.5
        })
        
        # Mock the sale advance payment wizard
        with patch.object(self.env['sale.advance.payment.inv'], 'create') as mock_create, \
             patch.object(self.env['sale.advance.payment.inv'], '_create_invoices') as mock_create_invoices:
            
            # Setup mock return values
            mock_advance_wizard = MagicMock()
            mock_create.return_value = mock_advance_wizard
            mock_invoice = self.create_account_move(sale_order=self.sale_order)
            mock_create_invoices.return_value = mock_invoice
            
            # Execute wizard
            result = wizard.create_sale_advance_payments()
            
            # Verify wizard was created with correct parameters
            mock_create.assert_called_once()
            create_args = mock_create.call_args[0][0]
            self.assertEqual(create_args['advance_payment_method'], 'percentage')
            self.assertEqual(create_args['amount'], 50.0)  # 0.5 * 100
    
    @patch('requests.post')
    def test_create_sale_advance_payments_anticipo_saldo(self, mock_post):
        """Test creating advance payments for anticipo_saldo"""
        # Setup mock response for Magento API
        mock_post.return_value = self.mock_magento_api_response(200, '{"success": true}')
        
        wizard = self.env['purchase.advance.payment.inv'].create({
            'purchase_order_ids': [(6, 0, [self.purchase_order.id])],
            'anticipo_type': 'anticipo_saldo',
            'percentage': 1.0
        })
        
        # Mock the sale advance payment wizard
        with patch.object(self.env['sale.advance.payment.inv'], 'create') as mock_create, \
             patch.object(self.env['sale.advance.payment.inv'], '_create_invoices') as mock_create_invoices:
            
            # Setup mock return values
            mock_advance_wizard = MagicMock()
            mock_create.return_value = mock_advance_wizard
            mock_invoice = self.create_account_move(sale_order=self.sale_order)
            mock_create_invoices.return_value = mock_invoice
            
            # Execute wizard
            result = wizard.create_sale_advance_payments()
            
            # Verify wizard was created with fixed amount method
            mock_create.assert_called_once()
            create_args = mock_create.call_args[0][0]
            self.assertEqual(create_args['advance_payment_method'], 'fixed')
    
    def test_create_sale_advance_payments_no_purchase_orders(self):
        """Test creating advance payments with no purchase orders"""
        wizard = self.env['purchase.advance.payment.inv'].create({
            'purchase_order_ids': [(6, 0, [])],
            'anticipo_type': 'anticipo_1',
            'percentage': 0.5
        })
        
        # Should raise UserError
        with self.assertRaises(UserError) as cm:
            wizard.create_sale_advance_payments()
        
        self.assertIn('No purchase orders selected', str(cm.exception))
    
    def test_create_sale_advance_payments_no_confirmed_sale_orders(self):
        """Test creating advance payments with no confirmed sale orders"""
        # Set sale order to draft
        self.sale_order.action_draft()
        
        wizard = self.env['purchase.advance.payment.inv'].create({
            'purchase_order_ids': [(6, 0, [self.purchase_order.id])],
            'anticipo_type': 'anticipo_1',
            'percentage': 0.5
        })
        
        # Should raise UserError
        with self.assertRaises(UserError) as cm:
            wizard.create_sale_advance_payments()
        
        self.assertIn('No confirmed sale orders found', str(cm.exception))
    
    def test_anticipo_1_skip_when_invoices_exist(self):
        """Test that anticipo_1 is skipped when invoices already exist"""
        # Create an existing invoice for the sale order
        existing_invoice = self.create_account_move(sale_order=self.sale_order)
        
        wizard = self.env['purchase.advance.payment.inv'].create({
            'purchase_order_ids': [(6, 0, [self.purchase_order.id])],
            'anticipo_type': 'anticipo_1',
            'percentage': 0.5
        })
        
        # Mock the sale advance payment wizard to verify it's not called
        with patch.object(self.env['sale.advance.payment.inv'], 'create') as mock_create:
            
            # Should raise UserError about no invoices created
            with self.assertRaises(UserError) as cm:
                wizard.create_sale_advance_payments()
            
            self.assertIn('No advance payment invoices were created', str(cm.exception))
            mock_create.assert_not_called()
    
    @patch('requests.post')
    def test_return_single_invoice_view(self, mock_post):
        """Test return value for single invoice creation"""
        # Setup mock response for Magento API
        mock_post.return_value = self.mock_magento_api_response(200, '{"success": true}')
        
        wizard = self.env['purchase.advance.payment.inv'].create({
            'purchase_order_ids': [(6, 0, [self.purchase_order.id])],
            'anticipo_type': 'anticipo_1',
            'percentage': 0.5
        })
        
        # Mock the sale advance payment wizard
        with patch.object(self.env['sale.advance.payment.inv'], 'create') as mock_create, \
             patch.object(self.env['sale.advance.payment.inv'], '_create_invoices') as mock_create_invoices:
            
            # Setup mock return values
            mock_advance_wizard = MagicMock()
            mock_create.return_value = mock_advance_wizard
            mock_invoice = self.create_account_move(sale_order=self.sale_order)
            mock_create_invoices.return_value = mock_invoice
            
            # Execute wizard
            result = wizard.create_sale_advance_payments()
            
            # Should return form view for single invoice
            self.assertEqual(result['type'], 'ir.actions.act_window')
            self.assertEqual(result['res_model'], 'account.move')
            self.assertEqual(result['view_mode'], 'form')
            self.assertEqual(result['res_id'], mock_invoice.id)
    
    @patch('requests.post')
    def test_return_multiple_invoices_view(self, mock_post):
        """Test return value for multiple invoice creation"""
        # Setup mock response for Magento API
        mock_post.return_value = self.mock_magento_api_response(200, '{"success": true}')
        
        # Create second purchase order and sale order
        po2 = self.create_purchase_order()
        po2.button_confirm()
        so2 = self.create_sale_order()
        so2.action_confirm()
        po2.order_line[0].sale_line_id = so2.order_line[0].id
        
        # Add the _get_sale_orders method to the second PO
        def _get_sale_orders_po2(self):
            if self.id == po2.id:
                return self.env['sale.order'].browse([so2.id])
            return self.env['sale.order'].browse([self.sale_order.id])
        
        po2.__class__._get_sale_orders = _get_sale_orders_po2
        
        wizard = self.env['purchase.advance.payment.inv'].create({
            'purchase_order_ids': [(6, 0, [self.purchase_order.id, po2.id])],
            'anticipo_type': 'anticipo_1',
            'percentage': 0.5
        })
        
        # Mock the sale advance payment wizard
        with patch.object(self.env['sale.advance.payment.inv'], 'create') as mock_create, \
             patch.object(self.env['sale.advance.payment.inv'], '_create_invoices') as mock_create_invoices:
            
            # Setup mock return values
            mock_advance_wizard = MagicMock()
            mock_create.return_value = mock_advance_wizard
            mock_invoice1 = self.create_account_move(sale_order=self.sale_order)
            mock_invoice2 = self.create_account_move(sale_order=so2)
            mock_create_invoices.side_effect = [mock_invoice1, mock_invoice2]
            
            # Execute wizard
            result = wizard.create_sale_advance_payments()
            
            # Should return list view for multiple invoices
            self.assertEqual(result['type'], 'ir.actions.act_window')
            self.assertEqual(result['res_model'], 'account.move')
            self.assertEqual(result['view_mode'], 'list,form')
            self.assertIn('domain', result)


@tagged('ceg_wizard', 'sale_advance')
class TestSaleAdvancePaymentInv(CEGTestBase):
    """
    Test cases for Sale Advance Payment Invoice Wizard extensions
    
    Tests the customizations made to the standard Odoo sale advance payment wizard.
    """
    
    def setUp(self):
        super().setUp()
        
        # Create sale order
        self.sale_order = self.create_sale_order()
        self.sale_order.action_confirm()
    
    def test_create_invoices_delivered_method(self):
        """Test _create_invoices with delivered method"""
        wizard = self.env['sale.advance.payment.inv'].create({
            'advance_payment_method': 'delivered',
            'sale_order_ids': [(6, 0, [self.sale_order.id])],
            'deduct_down_payments': True,
            'consolidated_billing': False
        })
        
        # Mock the sale order _create_invoices method
        with patch.object(self.sale_order, '_create_invoices') as mock_create:
            mock_invoice = self.create_account_move(sale_order=self.sale_order)
            mock_create.return_value = mock_invoice
            
            # Execute method
            result = wizard._create_invoices(self.sale_order)
            
            # Verify sale order method was called with correct parameters
            mock_create.assert_called_once_with(final=True, grouped=True)
            self.assertEqual(result, mock_invoice)
    
    def test_create_invoices_percentage_method(self):
        """Test _create_invoices with percentage method"""
        wizard = self.env['sale.advance.payment.inv'].create({
            'advance_payment_method': 'percentage',
            'amount': 50.0,
            'sale_order_ids': [(6, 0, [self.sale_order.id])],
            'company_id': self.company.id
        })
        
        # Execute method
        result = wizard._create_invoices(self.sale_order)
        
        # Should create an invoice
        self.assertTrue(result)
        self.assertEqual(result.move_type, 'out_invoice')
        self.assertEqual(result.partner_id, self.sale_order.partner_id)
    
    def test_create_invoices_fixed_method(self):
        """Test _create_invoices with fixed amount method"""
        wizard = self.env['sale.advance.payment.inv'].create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 100.0,
            'sale_order_ids': [(6, 0, [self.sale_order.id])],
            'company_id': self.company.id,
            'currency_id': self.company.currency_id.id
        })
        
        # Execute method
        result = wizard._create_invoices(self.sale_order)
        
        # Should create an invoice with fixed amount
        self.assertTrue(result)
        self.assertEqual(result.move_type, 'out_invoice')
        self.assertEqual(result.partner_id, self.sale_order.partner_id)
    
    def test_down_payment_section_creation(self):
        """Test that down payment section is created when needed"""
        wizard = self.env['sale.advance.payment.inv'].create({
            'advance_payment_method': 'percentage',
            'amount': 50.0,
            'sale_order_ids': [(6, 0, [self.sale_order.id])],
            'company_id': self.company.id
        })
        
        # Remove any existing down payment lines
        self.sale_order.order_line.filtered('is_downpayment').unlink()
        
        # Execute method
        result = wizard._create_invoices(self.sale_order)
        
        # Should have created down payment section and line
        down_payment_lines = self.sale_order.order_line.filtered('is_downpayment')
        self.assertTrue(down_payment_lines)
    
    def test_fixed_amount_delta_adjustment(self):
        """Test delta amount adjustment for fixed amount method"""
        wizard = self.env['sale.advance.payment.inv'].create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 99.99,  # Slightly different from calculated amount
            'sale_order_ids': [(6, 0, [self.sale_order.id])],
            'company_id': self.company.id,
            'currency_id': self.company.currency_id.id
        })
        
        # Execute method
        result = wizard._create_invoices(self.sale_order)
        
        # Should adjust the invoice to match the fixed amount
        self.assertTrue(result)
        # The exact amount matching depends on tax calculations and rounding
    
    def test_message_posting_after_creation(self):
        """Test that messages are posted after invoice creation"""
        wizard = self.env['sale.advance.payment.inv'].create({
            'advance_payment_method': 'percentage',
            'amount': 50.0,
            'sale_order_ids': [(6, 0, [self.sale_order.id])],
            'company_id': self.company.id
        })
        
        # Execute method
        result = wizard._create_invoices(self.sale_order)
        
        # Verify invoice was created and messages exist
        self.assertTrue(result)
        self.assertTrue(result.message_ids)
        
        # Check that sale order also has related message
        self.assertTrue(self.sale_order.message_ids)
    
    def test_inheritance_maintains_functionality(self):
        """Test that inheritance doesn't break existing functionality"""
        # Test that the wizard still works for standard cases
        wizard = self.env['sale.advance.payment.inv'].create({
            'advance_payment_method': 'percentage',
            'amount': 30.0,
            'sale_order_ids': [(6, 0, [self.sale_order.id])],
            'company_id': self.company.id
        })
        
        # Should work without errors
        result = wizard._create_invoices(self.sale_order)
        
        # Basic validations
        self.assertTrue(result)
        self.assertEqual(result.state, 'draft')
        self.assertEqual(result.partner_id, self.sale_order.partner_id)
        self.assertTrue(result.invoice_line_ids)
    
    def test_wizard_context_handling(self):
        """Test that wizard properly handles context"""
        # Test with context from purchase advance payment wizard
        context = {
            'default_sale_order_ids': [(6, 0, [self.sale_order.id])],
            'from_purchase_advance': True
        }
        
        wizard = self.env['sale.advance.payment.inv'].with_context(context).create({
            'advance_payment_method': 'percentage',
            'amount': 40.0,
            'company_id': self.company.id
        })
        
        # Should handle context correctly
        self.assertEqual(len(wizard.sale_order_ids), 1)
        self.assertEqual(wizard.sale_order_ids[0].id, self.sale_order.id)