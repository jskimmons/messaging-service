import datetime
from django.test import TestCase
from django.utils.timezone import datetime

from api.models import Conversation, Message
from api.constants import SMS, MMS, EMAIL


class ConversationModelTests(TestCase):
    def test_get_or_create_conversation_creates_new(self):
        '''
        Test a conversation is created when one with the proper participants does not exist yet
        '''
        self.assertFalse(Conversation.objects.filter(participant_a='+1723-456-7899').exists())

        conv = Conversation.get_or_create_conversation('+1723-456-7899', '+4756-789-1234')

        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(conv.participant_a, '+1723-456-7899')
        self.assertEqual(conv.participant_b, '+4756-789-1234')

    def test_get_or_create_conversation_reuses_existing(self):
        '''
        Test a conversation is not created when one exists with the proper participants
        '''
        conv1 = Conversation.get_or_create_conversation('+123', '+456')
        conv2 = Conversation.get_or_create_conversation('+123', '+456')
        self.assertEqual(conv1.id, conv2.id)
        self.assertEqual(Conversation.objects.count(), 1)

    def test_get_or_create_conversation_reuses_existing_reversed(self):
        '''
        Test a conversation is not created when one exists with the proper participants, in the reversed case
        '''
        conv1 = Conversation.get_or_create_conversation('user1@gmail.com', 'user2@hatch.com')
        conv2 = Conversation.get_or_create_conversation('user2@hatch.com', 'user1@gmail.com')  # reversed
        self.assertEqual(conv1.id, conv2.id)
        self.assertEqual(Conversation.objects.count(), 1)

    def test_conversation_serialize(self):
        self.maxDiff = None
        '''
        Test proper output of the Conversation.serialize function
        '''
        conv = Conversation.get_or_create_conversation('+111', '+222')
        m1 = Message.objects.create(
            conversation=conv,
            msg_type=SMS,
            from_address='+111',
            to_address='+222',
            body='First',
            attachments=[],
            timestamp=datetime(2024, 11, 1, 14, 0, 0),
        )
        m2 = Message.objects.create(
            conversation=conv,
            msg_type=MMS,
            from_address='+222',
            to_address='+111',
            body='Reply',
            attachments=None,
            timestamp=datetime(2025, 11, 1, 14, 0, 0),
        )
        serialized = conv.serialize()
        expected = {
            'participant_a': '+111', 
            'participant_b': '+222', 
            'messages': [
                {
                    'id': m1.id,
                    'msg_type': 'sms',
                    'from_address': '+111',
                    'to_address': '+222',
                    'body': 'First',
                    'attachments': [],
                    'timestamp': '2024-11-01T14:00:00',
                }, 
                {
                    'id': m2.id,
                    'msg_type': 'mms', 
                    'from_address': '+222', 
                    'to_address': '+111', 
                    'body': 'Reply',
                    'attachments': None, 
                    'timestamp': '2025-11-01T14:00:00',
                }
            ]
        }
        
        self.assertDictEqual(serialized, expected)

class MessageModelTests(TestCase):
    def test_message_with_attachments_serializes_properly(self):
        '''
        Test the `Message.serialize` function works as expected
        '''
        conv = Conversation.get_or_create_conversation('user@example.com', 'other@example.com')
        msg = Message.objects.create(
            conversation=conv,
            msg_type=EMAIL,
            from_address='user@example.com',
            to_address='other@example.com',
            body='<html><b>Email</b></html>',
            attachments=['http://file.url'],
            timestamp=datetime(2024, 11, 1, 14, 0, 0),
            messaging_provider_id='message-5',
        )
        serialized = msg.serialize()
        expected={
            'id': msg.id, 
            'msg_type': 'email', 
            'from_address': 'user@example.com', 
            'to_address': 'other@example.com', 
            'body': '<html><b>Email</b></html>', 
            'attachments': ['http://file.url'], 
            'timestamp': '2024-11-01T14:00:00',
        }

        self.assertDictEqual(serialized, expected)