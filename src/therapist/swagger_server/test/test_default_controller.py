# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.inline_response202 import InlineResponse202  # noqa: E501
from swagger_server.models.message_status import MessageStatus  # noqa: E501
from swagger_server.models.stored_message import StoredMessage  # noqa: E501
from swagger_server.test import BaseTestCase


class TestDefaultController(BaseTestCase):
    """DefaultController integration test stubs"""

    def test_conversations_conversation_id_messages_get(self):
        """Test case for conversations_conversation_id_messages_get

        List all stored messages in a conversation
        """
        response = self.client.open(
            '/api/conversations/{conversationId}/messages'.format(conversation_id='conversation_id_example'),
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_messages_message_id_get(self):
        """Test case for messages_message_id_get

        Poll the status or result of a previously submitted message
        """
        response = self.client.open(
            '/api/messages/{messageId}'.format(message_id='message_id_example'),
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_messages_post(self):
        """Test case for messages_post

        Submit a new user message for AI processing
        """
        data = dict(user_id='user_id_example',
                    conversation_id='conversation_id_example',
                    timestamp='2013-10-20T19:20:30+01:00',
                    text='text_example',
                    voice='voice_example',
                    image='image_example')
        response = self.client.open(
            '/api/messages',
            method='POST',
            data=data,
            content_type='multipart/form-data')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
