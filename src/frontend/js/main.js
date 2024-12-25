const attachBtn = document.getElementById("attachBtn");
const imageInput = document.getElementById("imageInput");
const imagePreview = document.getElementById("imagePreview");
const sendBtn = document.getElementById("sendBtn");
const userInput = document.getElementById("userInput");

// Fetch initial greeting message when the page loads
window.addEventListener("load", async () => {
  const initialResponse = await fetch("http://127.0.0.1:5000/init");
  const data = await initialResponse.json();
  appendTherapistResponse(document.querySelector(".chat"), data.response);
  document.querySelector(".chat").scrollTop = document.querySelector(".chat").scrollHeight;
});

attachBtn.addEventListener("click", () => {
  imageInput.click();
});

imageInput.addEventListener("change", () => {
  const file = imageInput.files[0];
  if (file && file.type.startsWith("image/")) {
    const reader = new FileReader();
    reader.onload = (event) => {
      imagePreview.innerHTML = `
        <div class="image-container">
          <img src="${event.target.result}" alt="Selected Image">
          <div class="remove-icon" onclick="removeImage()">&#10006;</div>
        </div>`;
    };
    reader.readAsDataURL(file);
  }
});

function removeImage() {
  imageInput.value = ""; // Clear the file input
  imagePreview.innerHTML = ""; // Remove the preview
}

sendBtn.addEventListener("click", sendMessage);

userInput.addEventListener("keydown", function (event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    const userMessage = userInput.value.trim();
    const file = imageInput.files[0];
    if (userMessage || file) {
      sendMessage();
    }
  }
});

async function sendMessage() {
  const userMessage = userInput.value.trim();
  const file = imageInput.files[0];
  const chatBox = document.querySelector(".chat");

  // Disable input and send button
  userInput.disabled = true;
  sendBtn.disabled = true;

  if (!userMessage && !file) {
    return;
  }

  // Display user message
  if (userMessage) {
    appendTextMessage(chatBox, userMessage);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  // Display image message first if it exists
  if (file) {
    const reader = new FileReader();
    reader.onload = (event) => {
      const imageElement = document.createElement("div");
      imageElement.classList.add("message", "user");
      imageElement.innerHTML = `<img src="${event.target.result}" alt="Uploaded Image" style="max-width: 100%; border-radius: 8px;">`;
      chatBox.appendChild(imageElement);
    };
    reader.readAsDataURL(file);
  }

  // Clear input and preview immediately after sending
  clearInput();

  // Show "loading..." message
  const loadingMessage = appendLoadingMessage(chatBox);

  // Send message to backend
  const response = await sendToBackend(userMessage);

  // Remove "loading..." message and display therapist response
  chatBox.removeChild(loadingMessage);
  appendTherapistResponse(chatBox, response);
  chatBox.scrollTop = chatBox.scrollHeight;

  // Re-enable input and send button after the response
  userInput.disabled = false;
  sendBtn.disabled = false;
}

async function sendToBackend(message) {
  try {
    const response = await fetch("http://127.0.0.1:5000/process", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ message })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data.response;
  } catch (error) {
    console.error("Error connecting to backend:", error);
    return "Oops! Something went wrong.";
  }
}

function appendTextMessage(chatBox, message) {
  const userMessageElement = document.createElement("div");
  userMessageElement.classList.add("message", "user");
  userMessageElement.textContent = message;
  chatBox.appendChild(userMessageElement);
}

function appendTherapistResponse(chatBox, response) {
  const therapistMessageElement = document.createElement("div");
  therapistMessageElement.classList.add("message", "therapist");
  therapistMessageElement.textContent = response;
  chatBox.appendChild(therapistMessageElement);
}

function appendLoadingMessage(chatBox) {
  const loadingMessageElement = document.createElement("div");
  loadingMessageElement.classList.add("message", "loading");
  loadingMessageElement.textContent = "Loading...";
  chatBox.appendChild(loadingMessageElement);
  return loadingMessageElement;
}

function clearInput() {
  userInput.value = ""; // Clear text input
  removeImage(); // Clear image preview
}
