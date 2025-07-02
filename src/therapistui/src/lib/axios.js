// lib/axios.js
import axios from "axios";

// Create the axios instance with interceptors for debugging
export const axiosInstance = axios.create({
  baseURL: "http://localhost:8080",
  withCredentials: true,
});

// Request interceptor for debugging
axiosInstance.interceptors.request.use(
  (config) => {
    console.log(`🚀 Request: ${config.method.toUpperCase()} ${config.url}`, {
      headers: config.headers,
      data: config.data instanceof FormData ? "[FormData]" : config.data,
    });
    return config;
  },
  (error) => {
    console.error("❌ Request error:", error);
    return Promise.reject(error);
  }
);

// Response interceptor for debugging
axiosInstance.interceptors.response.use(
  (response) => {
    console.log(`✅ Response from ${response.config.url}:`, {
      status: response.status,
      data: response.data,
    });
    return response;
  },
  (error) => {
    console.error("❌ Response error:", error);
    if (error.response) {
      console.error("Error data:", error.response.data);
      console.error("Error status:", error.response.status);
    } else if (error.request) {
      console.error("No response received:", error.request);
    }
    return Promise.reject(error);
  }
);
