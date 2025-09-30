import json
from unittest.mock import patch
from datetime import datetime

from django.test import TestCase, Client
from django.urls import reverse

from api.models import Conversation, Message
from api.constants import SMS, EMAIL


class OutgoingMessageViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('outgoing_message_view', kwargs={'msg_type': SMS})
        self.payload = {
            'from': '+12016661234',
            'to': '+18045551234',
            'type': SMS,
            'body': 'Hello test',
            'attachments': None,
            'timestamp': '2024-11-01T14:00:00Z'
        }

    @patch('api.views.OutgoingMessageView._mock_provider_post_request')
    def test_post_creates_message_and_returns_201(self, mock_post):
        '''
        Test successful api response and created message
        '''
        mock_post.return_value.status_code = 200

        response = self.client.post(self.url, data=json.dumps(self.payload), content_type='application/json')

        self.assertEqual(response.status_code, 201)

        msg = Message.objects.get(id=response.json()['message_id'])
        msg_state = msg.__dict__.copy()
        del msg_state['_state']
        expected = {
            'id': msg.id,
            'conversation_id': msg.conversation.id,
            'msg_type': 'sms',
            'from_address': '+12016661234',
            'to_address': '+18045551234',
            'body': 'Hello test',
            'attachments': None,
            'timestamp': datetime(2024, 11, 1, 14, 0),
            'messaging_provider_id': None
        }

        self.assertDictEqual(expected, msg_state)

    @patch('api.views.OutgoingMessageView._mock_provider_post_request')
    def test_provider_rate_limit(self, mock_post):
        '''
        Test 429 response from provider
        '''
        mock_post.return_value.status_code = 429
        response = self.client.post(self.url, data=json.dumps(self.payload), content_type='application/json')
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json(), {'error': 'Rate limited by provider. Please retry later.'})

    @patch('api.views.OutgoingMessageView._mock_provider_post_request')
    def test_provider_internal_error(self, mock_post):
        mock_post.return_value.status_code = 500
        response = self.client.post(self.url, data=json.dumps(self.payload), content_type='application/json')
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {'error': 'Provider service unavailable.'})


class IncomingMessageWebhookViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.sms_url = reverse('incoming_message_webhook_view', kwargs={'msg_type': SMS})
        self.email_url = reverse('incoming_message_webhook_view', kwargs={'msg_type': EMAIL})

    def test_incoming_sms_stores_message_with_provider_id(self):
        '''
        Test a post request to our webhook creates a message properly
        '''
        payload = {
            'from': '+12016661234',
            'to': '+18045551234',
            'type': SMS,
            'body': 'Incoming SMS',
            'attachments': None,
            'timestamp': '2024-11-01T14:00:00Z',
            'messaging_provider_id': 'msg-123'
        }
        response = self.client.post(self.sms_url, data=json.dumps(payload), content_type='application/json')

        self.assertEqual(response.status_code, 201)

        msg = Message.objects.get(id=response.json()['message_id'])
        msg_state = msg.__dict__.copy()

        del msg_state['_state']
        expected = {
            'id': msg.id,
            'conversation_id': msg.conversation.id, 
            'msg_type': SMS,
            'from_address': '+12016661234', 
            'to_address': '+18045551234', 
            'body': 'Incoming SMS', 
            'attachments': None, 
            'timestamp': datetime(2024, 11, 1, 14, 0), 
            'messaging_provider_id': 'msg-123'
        }  

        self.assertDictEqual(expected, msg_state)

    def test_incoming_email_stores_message_with_xillio_id(self):
        '''
        Test a post request to our webhook creates an email message properly
        '''
        payload = {
            'from': 'user@example.com',
            'to': 'other@example.com',
            'type': EMAIL,
            'body': '<html><b>Email body</b></html>',
            'attachments': [],
            'timestamp': '2024-11-01T14:00:00Z',
            'xillio_id': 'email-999'
        }
        response = self.client.post(self.email_url, data=json.dumps(payload), content_type='application/json')

        self.assertEqual(response.status_code, 201)

        msg = Message.objects.get(id=response.json()['message_id'])
        msg_state = msg.__dict__.copy()

        del msg_state['_state']
        expected = {
            'id': msg.id,
            'conversation_id': msg.conversation.id,
            'msg_type': EMAIL,
            'from_address': 'user@example.com',
            'to_address': 'other@example.com',
            'body': '<html><b>Email body</b></html>',
            'attachments': [], 
            'timestamp': datetime(2024, 11, 1, 14, 0), 
            'messaging_provider_id': 'email-999'
        }

        self.assertDictEqual(expected, msg_state)


class ConversationListAndDetailTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.conversation = Conversation.get_or_create_conversation('a@test.com', 'b@test.com')
        self.msg = Message.objects.create(
            conversation=self.conversation,
            msg_type=EMAIL,
            from_address='a@test.com',
            to_address='b@test.com',
            body='test body',
            attachments=None,
            timestamp=datetime(2024, 11, 1, 14, 0, 0),
            messaging_provider_id='xillio-1',
        )

    def test_list_conversations_returns_data(self):
        '''
        If getting all conversations, return the proper serialized info
        '''
        url = reverse('conversation_list_view')
        response = self.client.get(url)

        expected = [
            {
                'participant_a': 'a@test.com',
                'participant_b': 'b@test.com',
                'messages': [
                    {
                        'id': self.msg.id,
                        'msg_type': EMAIL,
                        'from_address': 'a@test.com',
                        'to_address': 'b@test.com',
                        'body': 'test body',
                        'attachments': None,
                        'timestamp': '2024-11-01T14:00:00',
                    }
                ]
            }
        ]

        self.assertEqual(response.status_code, 200)
        self.assertListEqual(expected, response.json())

    def test_detail_conversation_returns_messages(self):
        '''
        If getting a conversation that exists, return the proper serialized info
        '''
        url = reverse('conversation_detail_view', kwargs={'cid': self.conversation.id})
        response = self.client.get(url)

        expected = [
            {
                'id': self.msg.id,
                'msg_type': EMAIL,
                'from_address': 'a@test.com',
                'to_address': 'b@test.com',
                'body': 'test body',
                'attachments': None,
                'timestamp': '2024-11-01T14:00:00',
            }
        ]

        self.assertEqual(response.status_code, 200)
        self.assertListEqual(expected, response.json())

    def test_detail_conversation_not_found(self):
        '''
        If getting a conversation that does not exist, return a 404
        '''
        url = reverse('conversation_detail_view', kwargs={'cid': 9999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)
