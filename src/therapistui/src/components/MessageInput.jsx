import React, { useEffect, useRef, useState } from "react";
import { useChatStore } from "../store/useChatStore";
import { Image, Send, X, Mic, StopCircle } from "lucide-react";
import toast from "react-hot-toast";

const MessageInput = ({ disabled = false }) => {
  // ----------------------------- state & refs -----------------------------
  const [text, setText] = useState("");
  const [imagePreview, setImagePreview] = useState(null); // string (dataURL)
  const [imageFile, setImageFile] = useState(null); // actual File object
  const [audioPreview, setAudioPreview] = useState(null); // { blob, url }
  const [isRecording, setIsRecording] = useState(false);
  const [isSending, setIsSending] = useState(false);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const fileInputRef = useRef(null);

  const { sendMessage } = useChatStore();

  // ----------------------------- microphone ------------------------------
  useEffect(() => {
    if (!navigator.mediaDevices?.getUserMedia) {
      console.log("Media devices API not supported");
      return;
    }

    navigator.mediaDevices
      .getUserMedia({ audio: true })
      .then((stream) => {
        console.log("Microphone access granted");

        // Note: Browsers typically don't support direct MP3 recording
        // Using WebM/OGG and converting server-side is recommended
        const mimeType = MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : "audio/ogg";

        console.log(`Using mime type: ${mimeType}`);

        const mr = new MediaRecorder(stream, { mimeType });

        mr.ondataavailable = (e) => {
          console.log(`Data available: ${e.data.size} bytes`);
          audioChunksRef.current.push(e.data);
        };

        mr.onstop = () => {
          if (!audioChunksRef.current.length) {
            console.log("No audio data recorded");
            return;
          }

          console.log(
            `Recording stopped. Chunks: ${audioChunksRef.current.length}`
          );

          const blob = new Blob(audioChunksRef.current, { type: mr.mimeType });
          console.log(`Created blob: ${blob.size} bytes, type: ${blob.type}`);

          const url = URL.createObjectURL(blob);
          setAudioPreview({ blob, url });
          audioChunksRef.current = [];
        };

        mediaRecorderRef.current = mr;
      })
      .catch((err) => {
        console.error("Microphone access error:", err);
        toast.error("Microphone access denied");
      });
  }, []);

  // ----------------------------- image helpers ---------------------------
  const handleImageChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) {
      console.log("No file selected");
      return;
    }

    if (!file.type.startsWith("image/")) {
      console.log(`Invalid file type: ${file.type}`);
      toast.error("Please select an image file");
      return;
    }

    console.log(
      `Image selected: ${file.name}, ${file.size} bytes, type: ${file.type}`
    );

    // Store the actual file for FormData
    setImageFile(file);

    // Create preview
    const reader = new FileReader();
    reader.onloadend = () => {
      console.log("Image preview created");
      setImagePreview(reader.result);
    };
    reader.onerror = (err) => {
      console.error("FileReader error:", err);
      toast.error("Error loading image");
    };
    reader.readAsDataURL(file);
  };

  const removeImage = () => {
    console.log("Removing image");
    setImagePreview(null);
    setImageFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // ----------------------------- audio helpers ---------------------------
  const removeAudio = () => {
    console.log("Removing audio");
    setAudioPreview(null);
  };

  const toggleRecording = () => {
    const mr = mediaRecorderRef.current;
    if (!mr) {
      console.warn("MediaRecorder not initialized");
      return;
    }

    if (isRecording) {
      console.log("Stopping recording");
      mr.stop();
      setIsRecording(false);
    } else {
      console.log("Starting recording");
      audioChunksRef.current = [];
      mr.start(1000); // Collect data every second
      setIsRecording(true);
    }
  };

  // ----------------------------- send ------------------------------------
  const handleSendMessage = async (e) => {
    e.preventDefault();

    // Input validation
    const textTrimmed = text.trim();
    const hasImage = Boolean(imageFile);
    const hasAudio = Boolean(audioPreview);

    if (!textTrimmed && !hasImage && !hasAudio) {
      console.log("No content to send");
      return;
    }

    setIsSending(true);
    console.log(
      `Sending message - Text: ${Boolean(
        textTrimmed
      )}, Image: ${hasImage}, Audio: ${hasAudio}`
    );

    try {
      // Create FormData for the message
      const formData = new FormData();

      // Add text if provided
      if (textTrimmed) {
        console.log(`Adding text: ${textTrimmed}`);
        formData.append("text", textTrimmed);
      }

      // Add image if provided
      if (hasImage && imageFile) {
        console.log(
          `Adding image: ${imageFile.name}, ${imageFile.size} bytes, type: ${imageFile.type}`
        );
        formData.append("image", imageFile);
      }

      // Add audio if provided
      if (hasAudio && audioPreview?.blob) {
        console.log(
          `Adding audio: blob size: ${audioPreview.blob.size} bytes, type: ${audioPreview.blob.type}`
        );

        // Note: The server expects MP3 files now
        // If you're recording in WebM/OGG format, you have three options:
        // 1. Convert to MP3 client-side (requires library like lamejs)
        // 2. Send WebM/OGG and convert server-side (recommended)
        // 3. Use a separate MP3 recording library

        // For now, sending the recorded format with .mp3 extension
        // The server should handle conversion if needed
        formData.append(
          "audio",
          audioPreview.blob,
          `recording-${Date.now()}.mp3`
        );
      }

      // Debug log FormData contents
      console.log("FormData entries:");
      for (let [key, value] of formData.entries()) {
        console.log(
          `- ${key}: ${
            value instanceof Blob
              ? `Blob[${value.type}, ${value.size} bytes]`
              : value
          }`
        );
      }

      // Send the message
      const success = await sendMessage(formData);
      console.log("Message sent, success:", success);

      if (success) {
        // Reset UI on success
        setText("");
        setImagePreview(null);
        setImageFile(null);
        setAudioPreview(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
      }
    } catch (error) {
      console.error("Send message error:", error);
      toast.error("Failed to send message. Please try again.");
    } finally {
      setIsSending(false);
    }
  };

  // Determine if the send button should be enabled
  const canSend =
    Boolean(text.trim() || imagePreview || audioPreview) &&
    !disabled &&
    !isSending;

  // ----------------------------- render ----------------------------------
  return (
    <div className="p-4 w-full">
      {/* preview section */}
      {(imagePreview || audioPreview) && (
        <div className="mb-3 flex items-center gap-2">
          {imagePreview && (
            <div className="relative">
              <img
                src={imagePreview}
                alt="Preview"
                className="w-20 h-20 object-cover rounded-lg border"
              />
              <button
                type="button"
                aria-label="Remove image"
                onClick={removeImage}
                className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-base-300 flex items-center justify-center"
              >
                <X className="size-3" />
              </button>
            </div>
          )}

          {audioPreview && (
            <div className="relative flex items-center">
              <audio controls src={audioPreview.url} className="mr-2" />
              <button
                type="button"
                aria-label="Remove audio"
                onClick={removeAudio}
                className="w-5 h-5 rounded-full bg-base-300 flex items-center justify-center"
              >
                <X className="size-3" />
              </button>
            </div>
          )}
        </div>
      )}

      {/* input line */}
      <form onSubmit={handleSendMessage} className="flex items-center gap-2">
        <div className="flex-1 flex gap-2">
          <input
            type="text"
            aria-label="Message text"
            className="w-full input input-bordered rounded-lg input-sm sm:input-md"
            placeholder="Type a message..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={disabled || isSending}
          />

          {/* hidden file picker */}
          <input
            type="file"
            accept="image/*"
            ref={fileInputRef}
            className="hidden"
            onChange={handleImageChange}
            disabled={disabled || isSending}
          />

          {/* image button */}
          <button
            type="button"
            aria-label="Attach image"
            onClick={() => fileInputRef.current?.click()}
            className={`hidden sm:flex btn btn-circle ${
              imagePreview ? "text-emerald-500" : "text-zinc-400"
            }`}
            disabled={disabled || isSending}
          >
            <Image size={20} />
          </button>

          {/* mic button */}
          <button
            type="button"
            aria-label={isRecording ? "Stop recording" : "Record audio"}
            onClick={toggleRecording}
            className={`sm:flex btn btn-circle ${
              audioPreview
                ? "text-emerald-500"
                : isRecording
                ? "text-red-500"
                : "text-zinc-400"
            }`}
            disabled={disabled || isSending || (isRecording && audioPreview)}
          >
            {isRecording ? (
              <StopCircle size={20} className="animate-pulse" />
            ) : (
              <Mic size={20} />
            )}
          </button>
        </div>

        {/* send button */}
        <button
          type="submit"
          aria-label="Send message"
          className={`btn btn-sm btn-circle ${isSending ? "loading" : ""}`}
          disabled={!canSend}
        >
          {!isSending && <Send size={22} />}
        </button>
      </form>
    </div>
  );
};

export default MessageInput;
