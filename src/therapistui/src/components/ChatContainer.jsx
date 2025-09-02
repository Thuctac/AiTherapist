import React, { useEffect, useRef, useState } from "react";
import { useChatStore } from "../store/useChatStore";
import { useAuthStore } from "../store/useAuthStore";
import { Volume2, VolumeX, RefreshCw, Play, Pause } from "lucide-react";
import MessageInput from "./MessageInput";
import MessageSkeleton from "./skeletons/MessageSkeleton";
import StarRating from "./StarRating";
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
 * AudioPlayer component for bot TTS audio with play/pause button
 */
const AudioPlayer = ({ audioUrl, autoPlay = false, className = "" }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const audioRef = useRef(null);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleLoadStart = () => setIsLoading(true);
    const handleLoadedData = () => setIsLoading(false);
    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);
    const handleEnded = () => setIsPlaying(false);
    const handleError = (e) => {
      console.error("Audio playback error:", e);
      setIsLoading(false);
      setIsPlaying(false);
      toast.error("Failed to play audio");
    };

    audio.addEventListener("loadstart", handleLoadStart);
    audio.addEventListener("loadeddata", handleLoadedData);
    audio.addEventListener("play", handlePlay);
    audio.addEventListener("pause", handlePause);
    audio.addEventListener("ended", handleEnded);
    audio.addEventListener("error", handleError);

    return () => {
      audio.removeEventListener("loadstart", handleLoadStart);
      audio.removeEventListener("loadeddata", handleLoadedData);
      audio.removeEventListener("play", handlePlay);
      audio.removeEventListener("pause", handlePause);
      audio.removeEventListener("ended", handleEnded);
      audio.removeEventListener("error", handleError);
    };
  }, []);

  useEffect(() => {
    if (autoPlay && audioRef.current) {
      playAudio();
    }
  }, [autoPlay]);

  const playAudio = async () => {
    const audio = audioRef.current;
    if (!audio) return;

    try {
      await audio.play();
    } catch (error) {
      console.error("Failed to play audio:", error);
      toast.error("Failed to play audio");
    }
  };

  const pauseAudio = () => {
    const audio = audioRef.current;
    if (audio) {
      audio.pause();
    }
  };

  const togglePlayback = () => {
    if (isPlaying) {
      pauseAudio();
    } else {
      playAudio();
    }
  };

  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      <button
        onClick={togglePlayback}
        disabled={isLoading}
        className="btn btn-circle btn-sm"
        title={isPlaying ? "Pause" : "Play"}
      >
        {isLoading ? (
          <div className="loading loading-spinner loading-xs"></div>
        ) : isPlaying ? (
          <Pause size={16} />
        ) : (
          <Play size={16} />
        )}
      </button>
      <audio
        ref={audioRef}
        src={audioUrl}
        preload="metadata"
        className="hidden"
      />
      <span className="text-xs text-gray-500">
        {isLoading ? "Loading..." : isPlaying ? "Playing..." : "Bot response"}
      </span>
    </div>
  );
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
    rateMessage,
  } = useChatStore();

  const { authUser } = useAuthStore();

  const messageEndRef = useRef(null);
  const [autoPlayAudio, setAutoPlayAudio] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [lastBotMessageId, setLastBotMessageId] = useState(null);

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

  // Handle rating
  const handleRating = async (messageId, rating) => {
    try {
      await rateMessage(messageId, rating);
      toast.success("Thank you for your feedback!");
    } catch (error) {
      console.error("Failed to submit rating:", error);
      toast.error("Failed to submit rating");
    }
  };

  // -------------------------------------------------- auto–scroll
  useEffect(() => {
    if (messageEndRef.current) {
      messageEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  // -------------------------------------------------- auto–play bot TTS audio
  useEffect(() => {
    if (!autoPlayAudio || !messages.length) return;

    const lastMessage = messages[messages.length - 1];

    // Check if this is a new bot message with audio
    if (
      lastMessage?.senderId === "bot" &&
      lastMessage.audio &&
      lastMessage._id !== lastBotMessageId
    ) {
      setLastBotMessageId(lastMessage._id);

      // Small delay to ensure the audio element is rendered
      setTimeout(() => {
        const audioUrl = toAbs(lastMessage.audio);
        if (audioUrl) {
          const audio = new Audio(audioUrl);
          audio.play().catch((error) => {
            console.error("Auto-play failed:", error);
            // Auto-play might be blocked by browser, that's okay
          });
        }
      }, 100);
    }
  }, [messages, autoPlayAudio, lastBotMessageId]);

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
          title={
            autoPlayAudio
              ? "Disable auto‑play of bot responses"
              : "Enable auto‑play of bot responses"
          }
          onClick={() => setAutoPlayAudio((v) => !v)}
          className={`btn btn-sm btn-circle ${
            autoPlayAudio ? "btn-primary" : "btn-ghost"
          }`}
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
            const isBot = message.senderId === "bot";
            const isLast = idx === messages.length - 1;

            // Convert relative backend URLs → absolute URLs we can actually fetch
            const messageText = message.text || "";
            const audioUrl = toAbs(message.audio || message.audioUrl);
            const imageUrl = toAbs(message.imageUrl);

            // Extract the database message ID from the compound ID (e.g., "123-bot" -> "123")
            const dbMessageId = message._id?.split("-")[0];

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

                  {/* User Audio (if present) - show full controls */}
                  {audioUrl && isUser && (
                    <div className="mb-2">
                      <audio
                        controls
                        src={audioUrl}
                        className="w-full"
                        onError={(e) => {
                          console.error(
                            "Error loading user audio:",
                            audioUrl,
                            e
                          );
                        }}
                      />
                    </div>
                  )}

                  {/* Bot Audio (if present) - show custom player */}
                  {audioUrl && isBot && (
                    <div className="mb-2">
                      <AudioPlayer
                        audioUrl={audioUrl}
                        autoPlay={false} // Don't auto-play individual components
                        className="bg-base-200 rounded-lg p-2"
                      />
                    </div>
                  )}

                  {/* Text (if present) */}
                  {messageText && (
                    <p className="whitespace-pre-wrap">{messageText}</p>
                  )}

                  {/* If no content was successfully rendered, show a fallback */}
                  {!messageText && !imageUrl && !audioUrl && (
                    <p className="text-gray-400 italic">
                      {isUser
                        ? "You sent media content"
                        : "Bot sent a response"}
                    </p>
                  )}

                  {/* Rating component for bot messages */}
                  {isBot && dbMessageId && (
                    <div className="mt-2 pt-2 border-t border-base-300">
                      <StarRating
                        messageId={dbMessageId}
                        currentRating={message.rating}
                        onRate={handleRating}
                      />
                    </div>
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
