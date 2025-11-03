# -*- coding: utf-8 -*-
"""
Tests for WhatsApp and Discuss Channel models
"""

from unittest.mock import patch, MagicMock
from odoo.tests.common import tagged

from .test_base import CEGTestBase


@tagged('ceg_whatsapp', 'discuss')
class TestDiscussChannel(CEGTestBase):
    """
    Test cases for Discuss Channel model extensions
    
    Tests the WhatsApp integration functionality for automatic
    channel member management.
    """
    
    def setUp(self):
        super().setUp()
        
        # Create test WhatsApp account
        self.wa_account = self._create_whatsapp_account()
        
        # Create test partner with user
        self.test_user = self.env['res.users'].create({
            'name': 'Test WhatsApp User',
            'login': 'test_wa_user',
            'email': 'test_wa_user@example.com',
            'partner_id': self.customer.id,
        })
        
        # Set user on customer
        self.customer.user_id = self.test_user.id
    
    def _create_whatsapp_account(self):
        """Create a test WhatsApp account"""
        if 'whatsapp.account' in self.env:
            return self.env['whatsapp.account'].create({
                'name': 'Test WhatsApp Account',
                'phone_number': '+1234567890',
                'app_id': 'test_app_id',
                'token': 'test_token',
            })
        return None
    
    def test_get_whatsapp_channel_with_partner_user(self):
        """Test getting WhatsApp channel and automatic member addition"""
        if not self.wa_account:
            self.skipTest("WhatsApp account model not available")
        
        whatsapp_number = '+1234567890'
        sender_name = 'Test Sender'
        
        # Mock the parent method to return a channel
        with patch.object(
            self.env['discuss.channel'].__class__, 
            '_get_whatsapp_channel'
        ) as mock_parent:
            
            # Create a mock channel
            mock_channel = self.env['discuss.channel'].create({
                'name': f'WhatsApp {whatsapp_number}',
                'channel_type': 'whatsapp',
                'whatsapp_partner_id': self.customer.id,
            })
            mock_parent.return_value = mock_channel
            
            # Call the method
            channel = self.env['discuss.channel']._get_whatsapp_channel(
                whatsapp_number, 
                self.wa_account.id, 
                sender_name, 
                create_if_not_found=True
            )
            
            # Verify channel was returned
            self.assertEqual(channel, mock_channel)
            
            # Verify that channel members were added
            member_partner_ids = channel.channel_member_ids.mapped('partner_id').ids
            self.assertIn(self.test_user.partner_id.id, member_partner_ids)
    
    def test_get_whatsapp_channel_with_commercial_partner_user(self):
        """Test getting WhatsApp channel with commercial partner user"""
        if not self.wa_account:
            self.skipTest("WhatsApp account model not available")
        
        # Create commercial partner with user
        commercial_partner = self.env['res.partner'].create({
            'name': 'Commercial Partner',
            'is_company': True,
        })
        
        commercial_user = self.env['res.users'].create({
            'name': 'Commercial User',
            'login': 'commercial_user',
            'email': 'commercial@example.com',
            'partner_id': commercial_partner.id,
        })
        
        # Set commercial partner
        self.customer.commercial_partner_id = commercial_partner.id
        commercial_partner.user_id = commercial_user.id
        
        whatsapp_number = '+1234567891'
        
        # Mock the parent method
        with patch.object(
            self.env['discuss.channel'].__class__, 
            '_get_whatsapp_channel'
        ) as mock_parent:
            
            # Create a mock channel
            mock_channel = self.env['discuss.channel'].create({
                'name': f'WhatsApp {whatsapp_number}',
                'channel_type': 'whatsapp',
                'whatsapp_partner_id': self.customer.id,
            })
            mock_parent.return_value = mock_channel
            
            # Call the method
            channel = self.env['discuss.channel']._get_whatsapp_channel(
                whatsapp_number, 
                self.wa_account.id, 
                create_if_not_found=True
            )
            
            # Verify that commercial partner user was added
            member_partner_ids = channel.channel_member_ids.mapped('partner_id').ids
            self.assertIn(commercial_user.partner_id.id, member_partner_ids)
    
    def test_get_whatsapp_channel_no_duplicate_members(self):
        """Test that duplicate members are not added"""
        if not self.wa_account:
            self.skipTest("WhatsApp account model not available")
        
        whatsapp_number = '+1234567892'
        
        # Mock the parent method
        with patch.object(
            self.env['discuss.channel'].__class__, 
            '_get_whatsapp_channel'
        ) as mock_parent:
            
            # Create a mock channel with existing member
            mock_channel = self.env['discuss.channel'].create({
                'name': f'WhatsApp {whatsapp_number}',
                'channel_type': 'whatsapp',
                'whatsapp_partner_id': self.customer.id,
            })
            
            # Add existing member
            self.env['discuss.channel.member'].create({
                'channel_id': mock_channel.id,
                'partner_id': self.test_user.partner_id.id,
            })
            
            mock_parent.return_value = mock_channel
            
            initial_member_count = len(mock_channel.channel_member_ids)
            
            # Call the method
            channel = self.env['discuss.channel']._get_whatsapp_channel(
                whatsapp_number, 
                self.wa_account.id, 
                create_if_not_found=True
            )
            
            # Verify no duplicate members were added
            final_member_count = len(channel.channel_member_ids)
            self.assertEqual(initial_member_count, final_member_count)
    
    def test_get_whatsapp_channel_no_user(self):
        """Test getting WhatsApp channel when partner has no user"""
        if not self.wa_account:
            self.skipTest("WhatsApp account model not available")
        
        # Create partner without user
        partner_no_user = self.env['res.partner'].create({
            'name': 'Partner Without User',
            'phone': '+1234567893',
        })
        
        whatsapp_number = '+1234567893'
        
        # Mock the parent method
        with patch.object(
            self.env['discuss.channel'].__class__, 
            '_get_whatsapp_channel'
        ) as mock_parent:
            
            # Create a mock channel
            mock_channel = self.env['discuss.channel'].create({
                'name': f'WhatsApp {whatsapp_number}',
                'channel_type': 'whatsapp',
                'whatsapp_partner_id': partner_no_user.id,
            })
            mock_parent.return_value = mock_channel
            
            # Call the method
            channel = self.env['discuss.channel']._get_whatsapp_channel(
                whatsapp_number, 
                self.wa_account.id, 
                create_if_not_found=True
            )
            
            # Should still return the channel but no new members added
            self.assertEqual(channel, mock_channel)


@tagged('ceg_whatsapp')
class TestWhatsappAccount(CEGTestBase):
    """
    Test cases for WhatsApp Account model extensions
    
    Tests the message processing functionality and automatic
    channel member management.
    """
    
    def setUp(self):
        super().setUp()
        
        # Create test WhatsApp account
        self.wa_account = self._create_whatsapp_account()
        
        # Create test user and partner
        self.test_user = self.env['res.users'].create({
            'name': 'Test WhatsApp User',
            'login': 'test_wa_user2',
            'email': 'test_wa_user2@example.com',
            'partner_id': self.customer.id,
        })
        
        self.customer.user_id = self.test_user.id
    
    def _create_whatsapp_account(self):
        """Create a test WhatsApp account"""
        if 'whatsapp.account' in self.env:
            return self.env['whatsapp.account'].create({
                'name': 'Test WhatsApp Account 2',
                'phone_number': '+1234567891',
                'app_id': 'test_app_id_2',
                'token': 'test_token_2',
            })
        return None
    
    def test_process_messages_with_members_addition(self):
        """Test processing messages and adding channel members"""
        if not self.wa_account:
            self.skipTest("WhatsApp account model not available")
        
        # Mock message data
        message_data = {
            'messages': [{
                'id': 'msg_123',
                'from': '+1234567890',
                'type': 'text',
                'text': {'body': 'Test message'},
                'timestamp': '1234567890'
            }],
            'contacts': [{
                'profile': {'name': 'Test Contact'},
                'wa_id': '+1234567890'
            }]
        }
        
        # Mock _find_active_channel method
        with patch.object(self.wa_account, '_find_active_channel') as mock_find_channel:
            
            # Create a mock channel
            mock_channel = self.env['discuss.channel'].create({
                'name': 'WhatsApp +1234567890',
                'channel_type': 'whatsapp',
                'whatsapp_partner_id': self.customer.id,
            })
            mock_find_channel.return_value = mock_channel
            
            # Mock parent _process_messages method
            with patch.object(
                self.wa_account.__class__.__bases__[0], 
                '_process_messages'
            ) as mock_parent:
                mock_parent.return_value = True
                
                # Call the method
                result = self.wa_account._process_messages(message_data)
                
                # Verify that channel members were updated
                member_partner_ids = mock_channel.channel_member_ids.mapped('partner_id').ids
                self.assertIn(self.test_user.partner_id.id, member_partner_ids)
    
    def test_process_messages_with_whatsapp_business_api_data(self):
        """Test processing messages with whatsapp_business_api_data wrapper"""
        if not self.wa_account:
            self.skipTest("WhatsApp account model not available")
        
        # Mock message data with wrapper
        message_data = {
            'whatsapp_business_api_data': {
                'messages': [{
                    'id': 'msg_124',
                    'from': '+1234567891',
                    'type': 'text',
                    'text': {'body': 'Test message 2'},
                    'timestamp': '1234567891'
                }],
                'contacts': [{
                    'profile': {'name': 'Test Contact 2'},
                    'wa_id': '+1234567891'
                }]
            }
        }
        
        # Mock _find_active_channel method
        with patch.object(self.wa_account, '_find_active_channel') as mock_find_channel:
            
            # Create a mock channel
            mock_channel = self.env['discuss.channel'].create({
                'name': 'WhatsApp +1234567891',
                'channel_type': 'whatsapp',
                'whatsapp_partner_id': self.customer.id,
            })
            mock_find_channel.return_value = mock_channel
            
            # Mock parent _process_messages method
            with patch.object(
                self.wa_account.__class__.__bases__[0], 
                '_process_messages'
            ) as mock_parent:
                mock_parent.return_value = True
                
                # Call the method
                result = self.wa_account._process_messages(message_data)
                
                # Verify that the wrapped data was processed
                mock_parent.assert_called_once()
    
    def test_process_messages_with_context_reply(self):
        """Test processing messages with context (reply to previous message)"""
        if not self.wa_account:
            self.skipTest("WhatsApp account model not available")
        
        # Create existing WhatsApp message
        if 'whatsapp.message' in self.env:
            existing_msg = self.env['whatsapp.message'].create({
                'msg_uid': 'previous_msg_123',
                'body': 'Previous message',
                'state': 'sent',
            })
        else:
            self.skipTest("WhatsApp message model not available")
        
        # Mock message data with context
        message_data = {
            'messages': [{
                'id': 'msg_125',
                'from': '+1234567892',
                'type': 'text',
                'text': {'body': 'Reply message'},
                'context': {'id': 'previous_msg_123'},
                'timestamp': '1234567892'
            }],
            'contacts': [{
                'profile': {'name': 'Test Contact 3'},
                'wa_id': '+1234567892'
            }]
        }
        
        # Mock parent _process_messages method
        with patch.object(
            self.wa_account.__class__.__bases__[0], 
            '_process_messages'
        ) as mock_parent:
            mock_parent.return_value = True
            
            # Call the method
            result = self.wa_account._process_messages(message_data)
            
            # Verify that parent method was called
            mock_parent.assert_called_once()
    
    def test_process_messages_commercial_partner_user(self):
        """Test processing messages with commercial partner user"""
        if not self.wa_account:
            self.skipTest("WhatsApp account model not available")
        
        # Create commercial partner with user
        commercial_partner = self.env['res.partner'].create({
            'name': 'Commercial Partner 2',
            'is_company': True,
        })
        
        commercial_user = self.env['res.users'].create({
            'name': 'Commercial User 2',
            'login': 'commercial_user2',
            'email': 'commercial2@example.com',
            'partner_id': commercial_partner.id,
        })
        
        # Set commercial partner on customer
        self.customer.commercial_partner_id = commercial_partner.id
        commercial_partner.user_id = commercial_user.id
        
        # Mock message data
        message_data = {
            'messages': [{
                'id': 'msg_126',
                'from': '+1234567893',
                'type': 'text',
                'text': {'body': 'Commercial test message'},
                'timestamp': '1234567893'
            }],
            'contacts': [{
                'profile': {'name': 'Commercial Contact'},
                'wa_id': '+1234567893'
            }]
        }
        
        # Mock _find_active_channel method
        with patch.object(self.wa_account, '_find_active_channel') as mock_find_channel:
            
            # Create a mock channel
            mock_channel = self.env['discuss.channel'].create({
                'name': 'WhatsApp +1234567893',
                'channel_type': 'whatsapp',
                'whatsapp_partner_id': self.customer.id,
            })
            mock_find_channel.return_value = mock_channel
            
            # Mock parent _process_messages method
            with patch.object(
                self.wa_account.__class__.__bases__[0], 
                '_process_messages'
            ) as mock_parent:
                mock_parent.return_value = True
                
                # Call the method
                result = self.wa_account._process_messages(message_data)
                
                # Verify that commercial partner user was added
                member_partner_ids = mock_channel.channel_member_ids.mapped('partner_id').ids
                self.assertIn(commercial_user.partner_id.id, member_partner_ids)
    
    def test_process_messages_no_duplicate_members(self):
        """Test that duplicate members are not added during message processing"""
        if not self.wa_account:
            self.skipTest("WhatsApp account model not available")
        
        # Mock message data
        message_data = {
            'messages': [{
                'id': 'msg_127',
                'from': '+1234567894',
                'type': 'text',
                'text': {'body': 'Duplicate test message'},
                'timestamp': '1234567894'
            }],
            'contacts': [{
                'profile': {'name': 'Duplicate Contact'},
                'wa_id': '+1234567894'
            }]
        }
        
        # Mock _find_active_channel method
        with patch.object(self.wa_account, '_find_active_channel') as mock_find_channel:
            
            # Create a mock channel with existing member
            mock_channel = self.env['discuss.channel'].create({
                'name': 'WhatsApp +1234567894',
                'channel_type': 'whatsapp',
                'whatsapp_partner_id': self.customer.id,
            })
            
            # Add existing member
            self.env['discuss.channel.member'].create({
                'channel_id': mock_channel.id,
                'partner_id': self.test_user.partner_id.id,
            })
            
            mock_find_channel.return_value = mock_channel
            initial_member_count = len(mock_channel.channel_member_ids)
            
            # Mock parent _process_messages method
            with patch.object(
                self.wa_account.__class__.__bases__[0], 
                '_process_messages'
            ) as mock_parent:
                mock_parent.return_value = True
                
                # Call the method
                result = self.wa_account._process_messages(message_data)
                
                # Verify no duplicate members were added
                final_member_count = len(mock_channel.channel_member_ids)
                self.assertEqual(initial_member_count, final_member_count)