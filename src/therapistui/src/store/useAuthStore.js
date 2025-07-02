import { create } from "zustand";
import toast from "react-hot-toast";
import { io } from "socket.io-client";
import { axiosInstance } from "../lib/axios";

export const useAuthStore = create((set, get) => ({
  authUser: null,
  socket: null,
  isSigningUp: false,
  isLoggingIn: false,
  isUpdatingProfile: false,
  isCheckingAuth: true,

  connectSocket: () => {
    if (get().socket || !get().authUser) return;

    // Use import.meta.env instead of process.env for Vite
    const socket = io(
      import.meta.env.VITE_SOCKET_URL || "http://localhost:8080",
      {
        auth: { token: get().authUser.token },
      }
    );

    set({ socket });
  },

  disconnectSocket: () => {
    const socket = get().socket;
    if (socket) {
      socket.disconnect();
      set({ socket: null });
    }
  },

  checkAuth: async () => {
    try {
      // Try direct route first
      const res = await axiosInstance.get("/direct/auth/check").catch(() => {
        // Fall back to Connexion route if direct route fails
        return axiosInstance.get("/auth/check");
      });
      set({ authUser: res.data });
      get().connectSocket();
    } catch (error) {
      console.error("Auth check error:", error);
      set({ authUser: null });
    } finally {
      set({ isCheckingAuth: false });
    }
  },

  signup: async (data) => {
    set({ isSigningUp: true });
    try {
      // Try direct route first
      const res = await axiosInstance
        .post("/direct/auth/signup", data)
        .catch(() => {
          // Fall back to Connexion route if direct route fails
          return axiosInstance.post("/auth/signup", data);
        });
      set({ authUser: res.data });
      toast.success("Account created successfully");
      get().connectSocket();
    } catch (error) {
      console.error("Signup error:", error);
      toast.error(error.response?.data?.message || error.message);
    } finally {
      set({ isSigningUp: false });
    }
  },

  login: async (data) => {
    set({ isLoggingIn: true });
    try {
      // Try direct route first
      const res = await axiosInstance
        .post("/direct/auth/login", data)
        .catch((err) => {
          console.error("Direct login failed:", err);
          // Fall back to Connexion route if direct route fails
          return axiosInstance.post("/auth/login", data);
        });
      set({ authUser: res.data });
      toast.success("Logged in successfully");
      get().connectSocket();
    } catch (error) {
      console.error("Login error:", error);
      toast.error(error.response?.data?.message || error.message);
    } finally {
      set({ isLoggingIn: false });
    }
  },

  logout: async () => {
    try {
      // Try direct route first
      await axiosInstance.post("/direct/auth/logout").catch(() => {
        // Fall back to Connexion route if direct route fails
        return axiosInstance.post("/auth/logout");
      });
      get().disconnectSocket();
      set({ authUser: null });
      toast.success("Logged out successfully");
    } catch (error) {
      console.error("Logout error:", error);
      toast.error(error.response?.data?.message || error.message);
    }
  },
}));
