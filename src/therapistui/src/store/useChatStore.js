import { create } from "zustand";
import toast from "react-hot-toast";
import { axiosInstance } from "../lib/axios";
import { useAuthStore } from "./useAuthStore";

/**
 * Chat store – handles message fetching and sending
 */
export const useChatStore = create((set, get) => ({
  messages: [],
  isMessagesLoading: false,
  isSending: false,

  // Fetch all messages for the current user
  getMessages: async () => {
    set({ isMessagesLoading: true });
    try {
      const user = useAuthStore.getState().authUser;
      if (!user) {
        console.error("No authenticated user");
        return;
      }

      console.log("Fetching messages for user:", user._id);
      const res = await axiosInstance.get(`/direct/messages/${user._id}`);
      console.log("Received messages:", res.data);

      // Check and log each message's media content
      res.data.forEach((msg, idx) => {
        console.log(`Message ${idx + 1}:`, {
          id: msg._id,
          sender: msg.senderId,
          text:
            msg.text?.substring(0, 20) + (msg.text?.length > 20 ? "..." : ""),
          audio: msg.audio,
          imageUrl: msg.imageUrl,
        });
      });

      set({ messages: res.data });
    } catch (e) {
      console.error("Error fetching messages:", e);
      toast.error(
        e.response?.data?.message || e.message || "Failed to load messages"
      );
    } finally {
      set({ isMessagesLoading: false });
    }
  },

  // Send a message and then immediately fetch all messages to ensure UI is updated
  sendMessage: async (payload) => {
    set({ isSending: true });
    try {
      const user = useAuthStore.getState().authUser;
      if (!user) {
        throw new Error("No authenticated user");
      }

      // Log what we're sending
      console.log("Sending message payload:");
      if (payload instanceof FormData) {
        console.log("FormData payload - entries:");
        for (let [key, value] of payload.entries()) {
          console.log(
            `- ${key}: ${
              value instanceof Blob
                ? `Blob[${value.type}, ${value.size} bytes]`
                : value
            }`
          );
        }
      } else {
        console.log("JSON payload:", payload);
      }

      // Send the message
      const response = await axiosInstance.post(
        `/direct/messages/send/${user._id}`,
        payload,
        {
          headers:
            payload instanceof FormData
              ? { "Content-Type": "multipart/form-data" }
              : { "Content-Type": "application/json" },
          // Prevent axios from modifying FormData
          transformRequest:
            payload instanceof FormData ? (data) => data : undefined,
        }
      );

      console.log("Message sent successfully, response:", response.data);

      // Check if the response is a single message or an array
      if (Array.isArray(response.data)) {
        // Add all messages to the state
        set((state) => ({
          messages: [...state.messages, ...response.data],
        }));
      } else {
        // Add the single message to the state
        set((state) => ({
          messages: [...state.messages, response.data],
        }));
      }

      // Immediately fetch all messages to update the UI
      await get().getMessages();

      return true;
    } catch (e) {
      console.error("Error sending message:", e);
      if (e.response) {
        console.error("Error response:", e.response.data);
        console.error("Status:", e.response.status);
      }
      toast.error(
        e.response?.data?.message || e.message || "Failed to send message"
      );
      return false;
    } finally {
      set({ isSending: false });
    }
  },

  // Subscribe to socket.io messages
  subscribeToMessages: () => {
    const socket = useAuthStore.getState().socket;
    if (!socket) {
      console.warn("No socket connection available for message subscription");
      return;
    }

    socket.on("newMessage", (message) => {
      console.log("Received new message via socket:", message);

      // Add the message to the state
      set((state) => ({
        messages: [...state.messages, message],
      }));
    });

    // Debug socket connection
    socket.on("connect", () => {
      console.log("Socket connected");
    });

    socket.on("disconnect", () => {
      console.log("Socket disconnected");
    });

    socket.on("error", (error) => {
      console.error("Socket error:", error);
    });
  },

  // Unsubscribe from socket.io messages
  unsubscribeFromMessages: () => {
    const socket = useAuthStore.getState().socket;
    if (socket) {
      socket.off("newMessage");
      socket.off("connect");
      socket.off("disconnect");
      socket.off("error");
    }
  },
}));
