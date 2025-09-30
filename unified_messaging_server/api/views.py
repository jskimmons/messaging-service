import simplejson
import requests

from django.http import Http404, JsonResponse
from django.shortcuts import HttpResponse
from django.views import View

from .constants import MMS, SMS
from .models import Conversation, Message


class BaseMessageView(View):
    @staticmethod
    def _get_request_data(request, msg_type):
        '''
        Base function to handle getting the common info from the request body 
        for both the Send endpoint and the Recieve Webhook

        :param HttpRequest request: incoming request containing message info
        :param str msg_type: type of message contained in the request

        :return type: Dict
        :return: Dict of values from the request to be used to create a new `Message`
        '''
        post_data = simplejson.loads(request.body)
        from_address = post_data.get('from')
        to_address = post_data.get('to')

        conversation = Conversation.get_or_create_conversation(from_address=from_address, to_address=to_address)

        return {
            'conversation': conversation,
            'msg_type': post_data.get('type', msg_type),
            'from_address': from_address,
            'to_address': to_address,
            'body': post_data.get('body'),
            'attachments': post_data.get('attachments'),
            'timestamp': post_data.get('timestamp'),
        }


class OutgoingMessageView(BaseMessageView):
    @staticmethod
    def _mock_provider_post_request(response_status=200):
        '''
        This method is a mocked version of a very basic post request to a provider (like Twilio or Sendgrid)
        After a message is sent in our application, this function would be a call to post it to the provider API

        I am using it here to simulate different provider error codes
        '''
        return HttpResponse(status=response_status)

    def post(self, request, msg_type):
        '''
        Endpoint invoked by our application frontend when sending a message

        Deserializes, processes, and stores this `Message` and groups it into the proper `Conversation`

        :param HttpRequest request: request containing message info sent from our application
        :param str msg_type: type of message being sent

        :rtype HttpResponse:
        :return: response with execution status
        '''
        message_obj_vals = self._get_request_data(request, msg_type)

        message = Message.objects.create(**message_obj_vals)

        try:
            # I will assume at this point in the application we want to send this message info to our chosen provider
            response = self._mock_provider_post_request()
            if response.status_code == 429:
                return JsonResponse({'error': 'Rate limited by provider. Please retry later.'}, status=response.status_code)
            elif response.status_code == 500:
                return JsonResponse({'error': 'Provider service unavailable.'}, status=response.status_code)
            elif response.status_code == 200:
                return JsonResponse({'message_id': message.id}, status=201)
            else:
                return JsonResponse({'error': 'Unknown error ocurred.'}, status=response.status_code)

        except requests.exceptions.RequestException as e:
            return JsonResponse({"error": f"Failed to reach provider: {str(e)}"}, status=502)


class IncomingMessageWebhookView(BaseMessageView):
    def post(self, request, msg_type):
        '''
        Webhook invoked by the provider after a message has been received

        Deserializes, processes, and stores this `Message` and groups it into the proper `Conversation`

        :param HttpRequest request: incoming request containing message info
        :param str msg_type: type of message contained in the request

        :rtype HttpResponse:
        :return: response with execution status
        '''
        message_obj_vals = self._get_request_data(request, msg_type)

        post_data = simplejson.loads(request.body)
        if msg_type in (MMS, SMS):
            message_obj_vals['messaging_provider_id'] = post_data.get('messaging_provider_id')
        else:
            # email case
            message_obj_vals['messaging_provider_id'] = post_data.get('xillio_id')

        message = Message.objects.create(**message_obj_vals)

        return JsonResponse({'message_id': message.id}, status=201)


class ConversationListView(View):
    def get(self, request):
        '''
        :param HttpRequest request: incoming GET request for the conversations

        :rtype: JsonResponse
        :return: All `Conversation` objects serialized and formatted for json
        '''
        serialized_conversations = [conversation.serialize() for conversation in Conversation.objects.all()]

        return JsonResponse(serialized_conversations, content_type='application/json', safe=False)
    

class ConversationDetailView(View):
    def get(self, request, cid):
        '''
        Returns the list of messages grouped into the requested `Conversation`

        :param HttpRequest request: incoming GET request
        :param int cid: key for the requested `Conversation` object

        :rtype: JsonResponse
        :return: All `Conversation` objects serialized and formatted for json
        '''
        try:
            conversation = Conversation.objects.get(id=cid)
        except Conversation.DoesNotExist:
            raise Http404('Conversation not found')

        return JsonResponse(conversation.serialize_messages(), content_type='application/json', safe=False)
