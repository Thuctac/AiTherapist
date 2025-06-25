import { useEffect, useRef, useState } from "react";
import { useChatStore } from "../store/useChatStore";
import MessageInput from "./MessageInput";
import MessageSkeleton from "./skeletons/MessageSkeleton";
import { useAuthStore } from "../store/useAuthStore";
import { formatMessageTime } from "../lib/utils";
import { Volume2, VolumeX } from "lucide-react";

const DEFAULT_USER_AVATAR = "/avatar.png";
const DEFAULT_BOT_AVATAR = "/bot-avatar.png";

const ChatContainer = () => {
  const {
    messages,
    getMessages,
    isMessagesLoading,
    subscribeToMessages,
    unsubscribeFromMessages,
  } = useChatStore();
  const { authUser } = useAuthStore();
  const messageEndRef = useRef < HTMLDivElement > null;
  const [autoPlayAudio, setAutoPlayAudio] = useState(false);

  // Load messages and subscribe on mount
  useEffect(() => {
    getMessages();
    subscribeToMessages();
    return () => unsubscribeFromMessages();
  }, [getMessages, subscribeToMessages, unsubscribeFromMessages]);

  // Scroll to bottom on new messages
  useEffect(() => {
    if (messageEndRef.current && messages.length) {
      messageEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  // Auto-play audio when a new message arrives
  useEffect(() => {
    if (!autoPlayAudio || !messages.length) return;
    const last = messages[messages.length - 1];
    if (last.audioUrl) {
      const audio = new Audio(last.audioUrl);
      audio.play().catch((err) => console.error("Audio play failed:", err));
    }
  }, [messages, autoPlayAudio]);

  if (isMessagesLoading) {
    return (
      <div className="flex-1 flex flex-col overflow-auto">
        <MessageSkeleton />
        <MessageInput />
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-auto">
      {/* Auto-play toggle */}
      <div className="p-2">
        <button
          onClick={() => setAutoPlayAudio((v) => !v)}
          className="btn btn-sm btn-circle"
          title={autoPlayAudio ? "Disable auto-play" : "Enable auto-play"}
        >
          {autoPlayAudio ? <Volume2 size={20} /> : <VolumeX size={20} />}
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message._id}
            className={`chat ${
              message.senderId === authUser._id ? "chat-end" : "chat-start"
            }`}
            ref={messageEndRef}
          >
            <div className="chat-image avatar">
              <div className="w-10 h-10 rounded-full overflow-hidden border">
                <img
                  src={
                    message.senderId === authUser._id
                      ? authUser.profilePic || DEFAULT_USER_AVATAR
                      : DEFAULT_BOT_AVATAR
                  }
                  alt={message.senderId === authUser._id ? "You" : "Bot"}
                />
              </div>
            </div>
            <div className="chat-header mb-1">
              <time className="text-xs opacity-50 ml-1">
                {formatMessageTime(message.createdAt)}
              </time>
            </div>
            <div className="chat-bubble flex flex-col">
              {message.image && (
                <img
                  src={message.image}
                  alt="Attachment"
                  className="sm:max-w-[200px] rounded-md mb-2"
                />
              )}
              {message.audioUrl && (
                <audio controls src={message.audioUrl} className="mb-2" />
              )}
              {message.text && <p>{message.text}</p>}
            </div>
          </div>
        ))}
      </div>

      <MessageInput />
    </div>
  );
};

export default ChatContainer;
