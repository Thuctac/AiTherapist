import connexion
import six

from swagger_server.models.inline_response202 import InlineResponse202  # noqa: E501
from swagger_server.models.message_status import MessageStatus  # noqa: E501
from swagger_server.models.stored_message import StoredMessage  # noqa: E501
from swagger_server import util


def conversations_conversation_id_messages_get(conversation_id):  # noqa: E501
    """List all stored messages in a conversation

     # noqa: E501

    :param conversation_id: Unique identifier of the conversation
    :type conversation_id: str

    :rtype: List[StoredMessage]
    """
    return 'do some magic!'


def messages_message_id_get(message_id):  # noqa: E501
    """Poll the status or result of a previously submitted message

     # noqa: E501

    :param message_id: ID returned by POST /messages
    :type message_id: str

    :rtype: MessageStatus
    """
    return 'do some magic!'


def messages_post(user_id, conversation_id, timestamp, text, voice, image):  # noqa: E501
    """Submit a new user message for AI processing

    Send a message with at least one modality (text, voice, image). Returns immediately with a messageId to poll for the result.  # noqa: E501

    :param user_id: 
    :type user_id: str
    :param conversation_id: 
    :type conversation_id: str
    :param timestamp: 
    :type timestamp: str
    :param text: 
    :type text: str
    :param voice: 
    :type voice: strstr
    :param image: 
    :type image: strstr

    :rtype: InlineResponse202
    """
    timestamp = util.deserialize_datetime(timestamp)
    return 'do some magic!'
