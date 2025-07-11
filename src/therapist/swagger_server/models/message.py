# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server import util


class Message(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """
    def __init__(self, id: str=None, sender_id: str=None, conversation_id: str=None, text: str=None, audio: str=None, image_url: str=None, created_at: datetime=None):  # noqa: E501
        """Message - a model defined in Swagger

        :param id: The id of this Message.  # noqa: E501
        :type id: str
        :param sender_id: The sender_id of this Message.  # noqa: E501
        :type sender_id: str
        :param conversation_id: The conversation_id of this Message.  # noqa: E501
        :type conversation_id: str
        :param text: The text of this Message.  # noqa: E501
        :type text: str
        :param audio: The audio of this Message.  # noqa: E501
        :type audio: str
        :param image_url: The image_url of this Message.  # noqa: E501
        :type image_url: str
        :param created_at: The created_at of this Message.  # noqa: E501
        :type created_at: datetime
        """
        self.swagger_types = {
            'id': str,
            'sender_id': str,
            'conversation_id': str,
            'text': str,
            'audio': str,
            'image_url': str,
            'created_at': datetime
        }

        self.attribute_map = {
            'id': '_id',
            'sender_id': 'senderId',
            'conversation_id': 'conversationId',
            'text': 'text',
            'audio': 'audio',
            'image_url': 'imageUrl',
            'created_at': 'createdAt'
        }
        self._id = id
        self._sender_id = sender_id
        self._conversation_id = conversation_id
        self._text = text
        self._audio = audio
        self._image_url = image_url
        self._created_at = created_at

    @classmethod
    def from_dict(cls, dikt) -> 'Message':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The Message of this Message.  # noqa: E501
        :rtype: Message
        """
        return util.deserialize_model(dikt, cls)

    @property
    def id(self) -> str:
        """Gets the id of this Message.


        :return: The id of this Message.
        :rtype: str
        """
        return self._id

    @id.setter
    def id(self, id: str):
        """Sets the id of this Message.


        :param id: The id of this Message.
        :type id: str
        """
        if id is None:
            raise ValueError("Invalid value for `id`, must not be `None`")  # noqa: E501

        self._id = id

    @property
    def sender_id(self) -> str:
        """Gets the sender_id of this Message.


        :return: The sender_id of this Message.
        :rtype: str
        """
        return self._sender_id

    @sender_id.setter
    def sender_id(self, sender_id: str):
        """Sets the sender_id of this Message.


        :param sender_id: The sender_id of this Message.
        :type sender_id: str
        """
        if sender_id is None:
            raise ValueError("Invalid value for `sender_id`, must not be `None`")  # noqa: E501

        self._sender_id = sender_id

    @property
    def conversation_id(self) -> str:
        """Gets the conversation_id of this Message.


        :return: The conversation_id of this Message.
        :rtype: str
        """
        return self._conversation_id

    @conversation_id.setter
    def conversation_id(self, conversation_id: str):
        """Sets the conversation_id of this Message.


        :param conversation_id: The conversation_id of this Message.
        :type conversation_id: str
        """

        self._conversation_id = conversation_id

    @property
    def text(self) -> str:
        """Gets the text of this Message.


        :return: The text of this Message.
        :rtype: str
        """
        return self._text

    @text.setter
    def text(self, text: str):
        """Sets the text of this Message.


        :param text: The text of this Message.
        :type text: str
        """
        if text is None:
            raise ValueError("Invalid value for `text`, must not be `None`")  # noqa: E501

        self._text = text

    @property
    def audio(self) -> str:
        """Gets the audio of this Message.

        URL of audio attachment  # noqa: E501

        :return: The audio of this Message.
        :rtype: str
        """
        return self._audio

    @audio.setter
    def audio(self, audio: str):
        """Sets the audio of this Message.

        URL of audio attachment  # noqa: E501

        :param audio: The audio of this Message.
        :type audio: str
        """
        if audio is None:
            raise ValueError("Invalid value for `audio`, must not be `None`")  # noqa: E501

        self._audio = audio

    @property
    def image_url(self) -> str:
        """Gets the image_url of this Message.

        URL of image attachment (user messages only)  # noqa: E501

        :return: The image_url of this Message.
        :rtype: str
        """
        return self._image_url

    @image_url.setter
    def image_url(self, image_url: str):
        """Sets the image_url of this Message.

        URL of image attachment (user messages only)  # noqa: E501

        :param image_url: The image_url of this Message.
        :type image_url: str
        """

        self._image_url = image_url

    @property
    def created_at(self) -> datetime:
        """Gets the created_at of this Message.


        :return: The created_at of this Message.
        :rtype: datetime
        """
        return self._created_at

    @created_at.setter
    def created_at(self, created_at: datetime):
        """Sets the created_at of this Message.


        :param created_at: The created_at of this Message.
        :type created_at: datetime
        """
        if created_at is None:
            raise ValueError("Invalid value for `created_at`, must not be `None`")  # noqa: E501

        self._created_at = created_at
