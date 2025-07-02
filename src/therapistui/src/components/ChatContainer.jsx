import React, { useEffect, useRef, useState } from "react";
import { useChatStore } from "../store/useChatStore";
import { useAuthStore } from "../store/useAuthStore";
import { Volume2, VolumeX, RefreshCw } from "lucide-react";
import MessageInput from "./MessageInput";
import MessageSkeleton from "./skeletons/MessageSkeleton";
import toast from "react-hot-toast";

// Fallback avatars
const DEFAULT_USER_AVATAR = "/avatar.png";
const DEFAULT_BOT_AVATAR = "/bot-avatar.png";

// ---------------------------------------------------------------------------
// Helper to build an absolute URL for media the backend returns. The backend
// sends relative paths such as "/uploads/images/abc123.png".  When the React
// dev‑server runs on http://localhost:5173 the browser would otherwise look at
// http://localhost:5173/uploads/… – which 404s.  Attach the API base so the
// request goes to the Flask server instead.
// ---------------------------------------------------------------------------
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8080";
const toAbs = (url) => {
  if (!url) return null;
  // already absolute → leave untouched
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  // ensure exactly one slash between base and path
  return `${API_BASE.replace(/\/$/, "")}${
    url.startsWith("/") ? "" : "/"
  }${url}`;
};

/**
 * ChatContainer renders the entire chat timeline for the current user.
 * Supports text, image and audio content inside a single message bubble.
 */
const ChatContainer = () => {
  const {
    messages,
    getMessages,
    isMessagesLoading,
    subscribeToMessages,
    unsubscribeFromMessages,
  } = useChatStore();

  const { authUser } = useAuthStore();

  const messageEndRef = useRef(null);
  const [autoPlayAudio, setAutoPlayAudio] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  // -------------------------------------------------- data loading
  useEffect(() => {
    loadMessages();
    subscribeToMessages();
    return () => unsubscribeFromMessages();
  }, []);

  const loadMessages = async () => {
    try {
      await getMessages();
    } catch (error) {
      console.error("Failed to load messages:", error);
    }
  };

  // Manual refresh function
  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await getMessages();
      toast.success("Messages refreshed");
    } catch (error) {
      console.error("Failed to refresh messages:", error);
      toast.error("Failed to refresh messages");
    } finally {
      setRefreshing(false);
    }
  };

  // -------------------------------------------------- auto–scroll
  useEffect(() => {
    if (messageEndRef.current) {
      messageEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  // -------------------------------------------------- auto–play audio
  useEffect(() => {
    if (!autoPlayAudio || !messages.length) return;
    const last = messages[messages.length - 1];
    const lastAudio = toAbs(last.audio);
    if (lastAudio) {
      const audio = new Audio(lastAudio);
      audio.play().catch(console.error);
    }
  }, [messages, autoPlayAudio]);

  // -------------------------------------------------- UI helpers
  const isWaitingResponse =
    messages.length > 0 &&
    messages[messages.length - 1]?.senderId === authUser?._id;

  if (isMessagesLoading && messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col overflow-auto">
        <MessageSkeleton />
        <MessageInput disabled />
      </div>
    );
  }

  // Format timestamp for display
  const formatTime = (timestamp) => {
    if (!timestamp) return "";

    const date = new Date(timestamp);
    if (isNaN(date.getTime())) return "";

    const hours = date.getHours().toString().padStart(2, "0");
    const mins = date.getMinutes().toString().padStart(2, "0");
    return `${hours}:${mins}`;
  };

  return (
    <div className="flex-1 flex flex-col overflow-auto">
      {/* ------------------------ controls */}
      <div className="p-2 flex justify-between">
        <button
          type="button"
          title={autoPlayAudio ? "Disable auto‑play" : "Enable auto‑play"}
          onClick={() => setAutoPlayAudio((v) => !v)}
          className="btn btn-sm btn-circle"
        >
          {autoPlayAudio ? <Volume2 size={20} /> : <VolumeX size={20} />}
        </button>

        <button
          type="button"
          title="Refresh messages"
          onClick={handleRefresh}
          className={`btn btn-sm btn-circle ${refreshing ? "loading" : ""}`}
          disabled={refreshing}
        >
          <RefreshCw size={20} />
        </button>
      </div>

      {/* ------------------------ messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center py-10 text-gray-500">
            No messages yet. Start a conversation!
          </div>
        ) : (
          messages.map((message, idx) => {
            const isUser = message.senderId === authUser?._id;
            const isLast = idx === messages.length - 1;

            // Convert relative backend URLs → absolute URLs we can actually fetch
            const messageText = message.text || "";
            const audioUrl = toAbs(message.audio || message.audioUrl);
            const imageUrl = toAbs(message.imageUrl);

            return (
              <div
                key={message._id || `msg-${idx}`}
                className={`chat ${isUser ? "chat-end" : "chat-start"}`}
                ref={isLast ? messageEndRef : undefined}
              >
                {/* avatar */}
                <div className="chat-image avatar">
                  <div className="w-10 h-10 rounded-full overflow-hidden border">
                    <img
                      src={
                        isUser
                          ? authUser?.profilePic || DEFAULT_USER_AVATAR
                          : DEFAULT_BOT_AVATAR
                      }
                      alt={isUser ? "You" : "Bot"}
                    />
                  </div>
                </div>

                {/* header (timestamp) */}
                <div className="chat-header mb-1">
                  <time className="text-xs opacity-50 ml-1">
                    {formatTime(message.timestamp || message.createdAt)}
                  </time>
                </div>

                {/* bubble content */}
                <div className="chat-bubble flex flex-col">
                  {/* Image (if present) */}
                  {imageUrl && (
                    <div className="mb-2">
                      <img
                        src={imageUrl}
                        alt="Attachment"
                        className="rounded-lg max-w-xs"
                        onError={(e) => {
                          console.error("Error loading image:", imageUrl, e);
                          e.target.src = "/placeholder-image.png"; // Fallback image
                          e.target.alt = "Image could not be loaded";
                        }}
                      />
                    </div>
                  )}

                  {/* Audio (if present) */}
                  {audioUrl && (
                    <div className="mb-2">
                      <audio
                        controls
                        src={audioUrl}
                        className="w-full"
                        onError={(e) => {
                          console.error("Error loading audio:", audioUrl, e);
                        }}
                      />
                    </div>
                  )}

                  {/* Text (if present) */}
                  {messageText && <p>{messageText}</p>}

                  {/* If no content was successfully rendered, show a fallback */}
                  {!messageText && !imageUrl && !audioUrl && (
                    <p className="text-gray-400 italic">
                      {isUser
                        ? "You sent media content"
                        : "Bot sent a response"}
                    </p>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* ------------------------ input */}
      <MessageInput disabled={isWaitingResponse} />
    </div>
  );
};

export default ChatContainer;
