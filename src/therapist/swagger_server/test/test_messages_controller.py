# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.error_response import ErrorResponse  # noqa: E501
from swagger_server.models.message import Message  # noqa: E501
from swagger_server.test import BaseTestCase


class TestMessagesController(BaseTestCase):
    """MessagesController integration test stubs"""

    def test_messages_send_user_id_post(self):
        """Test case for messages_send_user_id_post

        Send a message to the bot (text, audio, optional image)
        """
        data = dict(text='text_example',
                    audio='audio_example',
                    image='image_example')
        response = self.client.open(
            '/messages/send/{userId}'.format(user_id='user_id_example'),
            method='POST',
            data=data,
            content_type='multipart/form-data')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_messages_user_id_get(self):
        """Test case for messages_user_id_get

        Get chat messages for a user (text, audio, image)
        """
        response = self.client.open(
            '/messages/{userId}'.format(user_id='user_id_example'),
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
