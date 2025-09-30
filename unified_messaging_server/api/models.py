from django.db import models

from .constants import EMAIL, MMS, SMS


class Conversation(models.Model):
    '''
    At this moment, a "participant" would just be an email address or phone number.
    We could add a `Participant` model if we wanted to link any user to both a phone number and/or an email,
    and group `Conversation` objects that way.
    '''
    participant_a = models.CharField(max_length=255)
    participant_b = models.CharField(max_length=255)

    @classmethod
    def get_or_create_conversation(cls, from_address, to_address):
        participants = sorted([from_address, to_address])  # sort so we can be agnostic to to/from
        
        conversation, _ = cls.objects.get_or_create(
            participant_a=participants[0],
            participant_b=participants[1],
        )

        return conversation
    
    def serialize_messages(self):
        return [message.serialize() for message in self.messages.order_by('timestamp')]
    
    def serialize(self):
        return {
            'participant_a': self.participant_a,
            'participant_b': self.participant_b,
            'messages': self.serialize_messages(),
        }


class Message(models.Model):
    MESSAGE_TYPES = (
        (EMAIL, "Email"),
        (MMS, "MMS"),
        (SMS, "SMS"),
    )

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    msg_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    from_address = models.CharField(max_length=255)
    to_address = models.CharField(max_length=255)
    body = models.TextField()
    attachments = models.JSONField(blank=True, null=True)
    timestamp = models.DateTimeField()

    # specific to the messages created via webhook, also holds `xillio_id` in the case of an incoming email
    messaging_provider_id = models.CharField(max_length=255, blank=True, null=True)

    def serialize(self):
        return {
            'id': self.id,
            'msg_type': self.msg_type,
            'from_address': self.from_address,
            'to_address': self.to_address,
            'body': self.body,
            'attachments': self.attachments,
            'timestamp': self.timestamp.isoformat(),
        }