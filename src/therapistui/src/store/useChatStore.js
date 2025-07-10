import { create } from "zustand";
import toast from "react-hot-toast";
import { axiosInstance } from "../lib/axios";
import { useAuthStore } from "./useAuthStore";

export const useChatStore = create((set, get) => ({
  messages: [],
  isMessagesLoading: false,
  isSending: false,
  sendRetryCount: 0,
  maxRetries: 3,

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

      const res = await axiosInstance.get(`/direct/messages/${user._id}`, {
        timeout: 30000, // 30 second timeout
      });

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

      // More detailed error handling
      let errorMessage = "Failed to load messages";
      if (e.code === "ECONNABORTED") {
        errorMessage = "Request timed out. Please try again.";
      } else if (e.response) {
        errorMessage =
          e.response.data?.message || `Server error: ${e.response.status}`;
      } else if (e.request) {
        errorMessage = "Network error. Please check your connection.";
      } else {
        errorMessage = e.message || "An unexpected error occurred";
      }

      toast.error(errorMessage);
    } finally {
      set({ isMessagesLoading: false });
    }
  },

  // Send a message with retry logic and better error handling
  sendMessage: async (payload) => {
    const { sendRetryCount, maxRetries } = get();

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

      // Prepare request config
      const config = {
        headers:
          payload instanceof FormData
            ? { "Content-Type": "multipart/form-data" }
            : { "Content-Type": "application/json" },
        timeout: 120000, // 2 minute timeout for file uploads
        transformRequest:
          payload instanceof FormData ? (data) => data : undefined,
      };

      // Send the message
      const response = await axiosInstance.post(
        `/direct/messages/send/${user._id}`,
        payload,
        config
      );

      console.log("Message sent successfully, response:", response.data);

      // Reset retry count on success
      set({ sendRetryCount: 0 });

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

      // Refresh messages to ensure consistency
      setTimeout(() => {
        get().getMessages();
      }, 1000);

      return true;
    } catch (e) {
      console.error("Error sending message:", e);

      // Detailed error logging
      if (e.response) {
        console.error("Error response:", e.response.data);
        console.error("Status:", e.response.status);
        console.error("Headers:", e.response.headers);
      } else if (e.request) {
        console.error("Request error:", e.request);
      }

      // Determine if we should retry
      let shouldRetry = false;
      let errorMessage = "Failed to send message";

      if (e.code === "ECONNABORTED") {
        errorMessage =
          "Request timed out. This might be due to slow processing.";
        shouldRetry = sendRetryCount < maxRetries;
      } else if (e.response) {
        const status = e.response.status;
        errorMessage = e.response.data?.message || `Server error: ${status}`;

        // Retry on server errors but not client errors
        shouldRetry = status >= 500 && sendRetryCount < maxRetries;
      } else if (e.request) {
        errorMessage = "Network error. Please check your connection.";
        shouldRetry = sendRetryCount < maxRetries;
      } else {
        errorMessage = e.message || "An unexpected error occurred";
      }

      // Handle retry logic
      if (shouldRetry) {
        const newRetryCount = sendRetryCount + 1;
        set({ sendRetryCount: newRetryCount });

        console.log(
          `Retrying send message (attempt ${newRetryCount}/${maxRetries})...`
        );
        toast.loading(`Retrying... (${newRetryCount}/${maxRetries})`, {
          duration: 2000,
        });

        // Wait before retrying
        await new Promise((resolve) => setTimeout(resolve, 2000));

        // Retry the send
        return get().sendMessage(payload);
      } else {
        // Reset retry count and show error
        set({ sendRetryCount: 0 });
        toast.error(errorMessage);
        return false;
      }
    } finally {
      set({ isSending: false });
    }
  },

  // Clear retry count
  clearRetryCount: () => {
    set({ sendRetryCount: 0 });
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

    // Enhanced socket event handling
    socket.on("connect", () => {
      console.log("Socket connected");
      // Clear any retry counts on successful connection
      set({ sendRetryCount: 0 });
    });

    socket.on("disconnect", (reason) => {
      console.log("Socket disconnected:", reason);
      if (reason === "io server disconnect") {
        // Server forcefully disconnected, try to reconnect
        socket.connect();
      }
    });

    socket.on("error", (error) => {
      console.error("Socket error:", error);
      toast.error("Real-time connection error. Some features may be limited.");
    });

    socket.on("reconnect", (attemptNumber) => {
      console.log("Socket reconnected after", attemptNumber, "attempts");
      toast.success("Connection restored!");
    });

    socket.on("reconnect_error", (error) => {
      console.error("Socket reconnection error:", error);
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
      socket.off("reconnect");
      socket.off("reconnect_error");
    }
  },
}));
