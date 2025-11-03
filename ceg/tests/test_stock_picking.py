# -*- coding: utf-8 -*-
"""
Tests for Stock Picking model extensions
"""

from unittest.mock import patch, MagicMock
from odoo.tests.common import tagged

from .test_base import CEGTestBase


@tagged('ceg_stock', 'magento')
class TestStockPicking(CEGTestBase):
    """
    Test cases for Stock Picking model extensions in CEG module
    
    Tests the Magento integration functionality for stock pickings including
    status updates and picking list generation.
    """
    
    def setUp(self):
        super().setUp()
        
        # Create a sale order and picking for testing
        self.sale_order = self.create_sale_order()
        self.sale_order.action_confirm()
        
        # Create stock picking
        self.picking = self.create_stock_picking(sale_order=self.sale_order)
    
    def test_exported_to_picking_list_field(self):
        """Test exported_to_picking_list field exists and has correct default"""
        # Check field exists
        self.assertTrue(hasattr(self.picking, 'exported_to_picking_list'))
        
        # Check default value
        self.assertFalse(self.picking.exported_to_picking_list)
    
    @patch('requests.post')
    def test_button_validate_magento_picking(self, mock_post):
        """Test button_validate for Magento pickings"""
        # Setup mock response
        mock_post.return_value = self.mock_magento_api_response(200, '{"success": true}')
        
        # Add mock is_magento_picking attribute
        self.picking.is_magento_picking = True
        
        # Mock export_magento_shipment method
        with patch.object(self.picking, 'export_magento_shipment') as mock_export:
            # Confirm moves first
            self.picking.action_confirm()
            for move in self.picking.move_ids_without_package:
                move.quantity_done = move.product_uom_qty
            
            # Validate the picking
            self.picking.button_validate()
            
            # Verify export was called
            mock_export.assert_called_once()
    
    def test_button_validate_non_magento_picking(self):
        """Test button_validate for non-Magento pickings"""
        # Ensure it's not a Magento picking
        if hasattr(self.picking, 'is_magento_picking'):
            self.picking.is_magento_picking = False
        
        # Mock export_magento_shipment method to verify it's not called
        with patch.object(self.picking, 'export_magento_shipment', create=True) as mock_export:
            # Confirm moves first
            self.picking.action_confirm()
            for move in self.picking.move_ids_without_package:
                move.quantity_done = move.product_uom_qty
            
            # Validate the picking
            try:
                self.picking.button_validate()
            except AttributeError:
                # export_magento_shipment method might not exist, which is fine
                pass
            
            # Verify export was not called (if method exists)
            if hasattr(self.picking, 'export_magento_shipment'):
                mock_export.assert_not_called()
    
    def test_get_magento_instance_from_sale_id(self):
        """Test getting Magento instance from sale_id"""
        if not self.magento_instance:
            self.skipTest("Magento instance not available")
        
        # Test getting instance from sale_id
        instance = self.picking._get_magento_instance()
        
        # Should find the instance from the related sale order
        self.assertEqual(instance, self.magento_instance)
    
    def test_get_magento_instance_from_moves(self):
        """Test getting Magento instance from stock moves"""
        if not self.magento_instance:
            self.skipTest("Magento instance not available")
        
        # Remove direct sale_id link
        self.picking.sale_id = False
        
        # Ensure moves have sale_line_id
        for move in self.picking.move_ids_without_package:
            if not move.sale_line_id:
                move.sale_line_id = self.sale_order.order_line[0].id
        
        # Test getting instance from moves
        instance = self.picking._get_magento_instance()
        
        # Should find the instance from sale order via moves
        self.assertEqual(instance, self.magento_instance)
    
    def test_get_magento_instance_no_relation(self):
        """Test getting Magento instance when no relation exists"""
        # Remove all relations
        self.picking.sale_id = False
        for move in self.picking.move_ids_without_package:
            move.sale_line_id = False
        
        # Test getting instance
        instance = self.picking._get_magento_instance()
        
        # Should return False
        self.assertFalse(instance)
    
    def test_get_magento_order_id_from_sale_id(self):
        """Test getting Magento order ID from sale_id"""
        # Test getting order ID from sale_id
        order_id = self.picking._get_magento_order_id()
        
        # Should find the order ID from the related sale order
        self.assertEqual(order_id, 'TEST_MG_ORD_001')
    
    def test_get_magento_order_id_from_moves(self):
        """Test getting Magento order ID from stock moves"""
        # Remove direct sale_id link
        self.picking.sale_id = False
        
        # Ensure moves have sale_line_id
        for move in self.picking.move_ids_without_package:
            if not move.sale_line_id:
                move.sale_line_id = self.sale_order.order_line[0].id
        
        # Test getting order ID from moves
        order_id = self.picking._get_magento_order_id()
        
        # Should find the order ID from sale order via moves
        self.assertEqual(order_id, 'TEST_MG_ORD_001')
    
    def test_get_magento_order_id_no_relation(self):
        """Test getting Magento order ID when no relation exists"""
        # Remove all relations
        self.picking.sale_id = False
        for move in self.picking.move_ids_without_package:
            move.sale_line_id = False
        
        # Test getting order ID
        order_id = self.picking._get_magento_order_id()
        
        # Should return False
        self.assertFalse(order_id)
    
    def test_action_get_picking_list_single_picking(self):
        """Test action_get_picking_list for single picking"""
        # Call action method
        result = self.picking.action_get_picking_list()
        
        # Assertions
        self.assertEqual(result['type'], 'ir.actions.act_url')
        self.assertIn('/ceg/download_picking_list/', result['url'])
        self.assertIn(str(self.picking.id), result['url'])
        self.assertEqual(result['target'], 'new')
        
        # Verify exported flag is set
        self.assertTrue(self.picking.exported_to_picking_list)
    
    def test_action_get_picking_list_multiple_pickings(self):
        """Test action_get_picking_list for multiple pickings"""
        # Create second picking
        picking_2 = self.create_stock_picking(sale_order=self.sale_order)
        
        # Combine pickings
        combined_pickings = self.picking | picking_2
        
        # Call action method
        result = combined_pickings.action_get_picking_list()
        
        # Assertions
        self.assertEqual(result['type'], 'ir.actions.act_url')
        self.assertIn('/ceg/download_picking_list/', result['url'])
        self.assertIn(str(self.picking.id), result['url'])
        self.assertIn(str(picking_2.id), result['url'])
        
        # Verify exported flag is set for all pickings
        self.assertTrue(self.picking.exported_to_picking_list)
        self.assertTrue(picking_2.exported_to_picking_list)
    
    def test_picking_list_url_format(self):
        """Test that picking list URL is formatted correctly"""
        # Create additional pickings
        picking_2 = self.create_stock_picking(sale_order=self.sale_order)
        picking_3 = self.create_stock_picking(sale_order=self.sale_order)
        
        # Combine pickings
        combined_pickings = self.picking | picking_2 | picking_3
        
        # Call action method
        result = combined_pickings.action_get_picking_list()
        
        # Extract picking IDs from URL
        url = result['url']
        # URL format should be: /ceg/download_picking_list/id1,id2,id3
        picking_ids_part = url.split('/ceg/download_picking_list/')[1]
        picking_ids = picking_ids_part.split(',')
        
        # Verify all picking IDs are in the URL
        expected_ids = {str(self.picking.id), str(picking_2.id), str(picking_3.id)}
        actual_ids = set(picking_ids)
        self.assertEqual(expected_ids, actual_ids)
    
    def test_stock_picking_inheritance(self):
        """Test that stock picking properly inherits from mixin"""
        # Check that stock picking has the mixin methods
        self.assertTrue(hasattr(self.picking, 'send_status_to_magento'))
        self.assertTrue(hasattr(self.picking, 'send_administrative_status_to_magento'))
        self.assertTrue(hasattr(self.picking, '_build_status_request_data'))
        self.assertTrue(hasattr(self.picking, '_build_administrative_status_request_data'))
    
    def test_picking_with_multiple_products(self):
        """Test picking behavior with multiple products"""
        # Create sale order with multiple products
        products = [
            (self.product_1, 3, 100.0),
            (self.product_2, 2, 200.0),
        ]
        multi_product_sale_order = self.create_sale_order(products=products)
        multi_product_sale_order.action_confirm()
        
        # Create picking for this order
        multi_picking = self.create_stock_picking(sale_order=multi_product_sale_order)
        
        # Verify picking has correct number of moves
        product_moves = multi_picking.move_ids_without_package.filtered(
            lambda m: m.product_id.type == 'product'
        )
        self.assertEqual(len(product_moves), 2)
        
        # Test Magento integration methods
        self.assertEqual(multi_picking._get_magento_order_id(), 'TEST_MG_ORD_001')
        if self.magento_instance:
            self.assertEqual(multi_picking._get_magento_instance(), self.magento_instance)
    
    def test_picking_workflow_integration(self):
        """Test integration with picking workflow"""
        # Confirm picking
        self.picking.action_confirm()
        
        # Check state
        self.assertEqual(self.picking.state, 'confirmed')
        
        # Assign quantities
        self.picking.action_assign()
        
        # Set quantities done
        for move in self.picking.move_ids_without_package:
            move.quantity_done = move.product_uom_qty
        
        # Test that validation would work
        self.assertTrue(self.picking.move_ids_without_package)
        for move in self.picking.move_ids_without_package:
            self.assertGreater(move.quantity_done, 0)
    
    @patch('requests.post')
    def test_magento_status_update_from_picking(self, mock_post):
        """Test sending Magento status update from picking"""
        # Setup mock response
        mock_post.return_value = self.mock_magento_api_response(200, '{"success": true}')
        
        # Send status update
        result = self.picking.send_status_to_magento('shipped')
        
        # Verify API was called
        if self.magento_instance:
            self.assertTrue(mock_post.called)
            self.assertTrue(result)
        else:
            self.skipTest("Magento instance not available")
    
    def test_picking_without_sale_order(self):
        """Test picking behavior without sale order"""
        # Create picking without sale order
        standalone_picking = self.create_stock_picking()
        
        # Should still have basic functionality
        self.assertTrue(hasattr(standalone_picking, 'action_get_picking_list'))
        
        # But Magento methods should return False
        self.assertFalse(standalone_picking._get_magento_instance())
        self.assertFalse(standalone_picking._get_magento_order_id())
    
    def test_exported_flag_persistence(self):
        """Test that exported_to_picking_list flag persists correctly"""
        # Initially should be False
        self.assertFalse(self.picking.exported_to_picking_list)
        
        # After calling action_get_picking_list
        self.picking.action_get_picking_list()
        
        # Should be True
        self.assertTrue(self.picking.exported_to_picking_list)
        
        # Should remain True after refresh
        self.picking.invalidate_recordset()
        self.assertTrue(self.picking.exported_to_picking_list)