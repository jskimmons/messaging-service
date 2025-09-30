from django.urls import path, re_path

from .constants import EMAIL, MMS, SMS
from .views import ConversationListView, ConversationDetailView, IncomingMessageWebhookView, OutgoingMessageView


urlpatterns = [
    re_path(f'^messages/(?P<msg_type>{EMAIL}|{MMS}|{SMS})$', OutgoingMessageView.as_view(), name='outgoing_message_view'),

    re_path(f'^webhooks/(?P<msg_type>{EMAIL}|{MMS}|{SMS})$', IncomingMessageWebhookView.as_view(), name='incoming_message_webhook_view'),

    path('conversations', ConversationListView.as_view(), name='conversation_list_view'),

    path('conversations/<int:cid>/messages', ConversationDetailView.as_view(), name='conversation_detail_view'),
]
