#!/usr/bin/env python3
import os
import jwt
from flask import Flask, send_from_directory, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from swagger_server.direct_routes import register_direct_routes

# Set up upload directories
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "images"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "audio"), exist_ok=True)

# JWT Secret (should match your auth routes)
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Enable CORS for your React frontend
    CORS(
        app,
        origins=["http://localhost:5173"],  # or your actual frontend URL
        supports_credentials=True,
    )
    
    # Initialize Socket.IO
    socketio = SocketIO(
        app,
        cors_allowed_origins=["http://localhost:5173"],
        logger=True,
        engineio_logger=True,
        ping_timeout=60,
        ping_interval=25
    )
    
    # Store connected users
    connected_users = {}
    
    # Socket.IO Authentication Helper
    def authenticate_socket(auth_data):
        """Authenticate socket connection using JWT token."""
        try:
            if not auth_data or 'token' not in auth_data:
                return None
            
            token = auth_data['token']
            # Decode JWT token (adjust according to your JWT implementation)
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            return payload.get('user_id') or payload.get('id')
        except jwt.InvalidTokenError:
            print("Invalid JWT token for socket connection")
            return None
        except Exception as e:
            print(f"Socket auth error: {e}")
            return None
    
    # Socket.IO Event Handlers
    @socketio.on('connect')
    def handle_connect(auth):
        """Handle client connection."""
        print(f"Socket connection attempt with auth: {auth}")
        
        user_id = authenticate_socket(auth)
        if not user_id:
            print("Socket connection rejected: Invalid authentication")
            disconnect()
            return False
        
        # Store user connection
        connected_users[request.sid] = user_id
        
        # Join user to their personal room
        join_room(f"user_{user_id}")
        
        print(f"User {user_id} connected with session {request.sid}")
        emit('connected', {
            'status': 'Connected to server',
            'user_id': user_id
        })
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        user_id = connected_users.pop(request.sid, None)
        if user_id:
            leave_room(f"user_{user_id}")
            print(f"User {user_id} disconnected")
    
    @socketio.on('join_chat')
    def handle_join_chat(data):
        """Handle user joining a chat room."""
        user_id = connected_users.get(request.sid)
        if not user_id:
            emit('error', {'message': 'Not authenticated'})
            return
        
        chat_id = data.get('chat_id')
        if chat_id:
            join_room(f"chat_{chat_id}")
            emit('joined_chat', {'chat_id': chat_id})
            print(f"User {user_id} joined chat {chat_id}")
    
    @socketio.on('leave_chat')
    def handle_leave_chat(data):
        """Handle user leaving a chat room."""
        user_id = connected_users.get(request.sid)
        if not user_id:
            return
        
        chat_id = data.get('chat_id')
        if chat_id:
            leave_room(f"chat_{chat_id}")
            print(f"User {user_id} left chat {chat_id}")
    
    # Function to emit new messages to connected clients
    def emit_new_message(user_id, message_data):
        """Emit a new message to the user's room."""
        socketio.emit('new_message', message_data, room=f"user_{user_id}")
        print(f"Emitted new message to user {user_id}")
    
    # Make emit_new_message available to other modules
    app.emit_new_message = emit_new_message
    
    # Set up file serving for uploads
    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        """Serve uploaded files with proper headers."""
        print(f"Serving file: {filename}")
        
        # Detect content type based on file extension
        content_type = None
        if filename.endswith('.webm'):
            content_type = 'audio/webm'
        elif filename.endswith('.ogg'):
            content_type = 'audio/ogg'
        elif filename.endswith('.wav'):
            content_type = 'audio/wav'
        elif filename.endswith('.png'):
            content_type = 'image/png'
        elif filename.endswith('.jpg') or filename.endswith('.jpeg'):
            content_type = 'image/jpeg'
        elif filename.endswith('.gif'):
            content_type = 'image/gif'
        
        response = send_from_directory(UPLOAD_DIR, filename)
        if content_type:
            response.headers['Content-Type'] = content_type
        return response
    
    # Register all direct routes
    register_direct_routes(app)
    
    # Add a health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        """Simple health check endpoint."""
        return {"status": "healthy"}, 200
    
    # Add Socket.IO status endpoint
    @app.route('/socket-status', methods=['GET'])
    def socket_status():
        """Check Socket.IO status and connected users."""
        return {
            "socket_io": "active",
            "connected_users": len(connected_users),
            "sessions": list(connected_users.keys())
        }, 200
    
    # Add API documentation route (optional)
    @app.route('/api-docs', methods=['GET'])
    def api_docs():
        """Return a simple API documentation."""
        return {
            "endpoints": {
                "auth": {
                    "POST /direct/auth/signup": "Sign up a new user",
                    "POST /direct/auth/login": "Log in existing user",
                    "GET /direct/auth/check": "Check authentication status",
                    "POST /direct/auth/logout": "Log out current user"
                },
                "messages": {
                    "POST /direct/messages/send/{userId}": "Send a message",
                    "GET /direct/messages/{userId}": "Get all messages for a user",
                    "POST /direct/messages/test/{userId}": "Test endpoint"
                },
                "files": {
                    "GET /uploads/{path}": "Serve uploaded files"
                },
                "websocket": {
                    "connect": "Connect to Socket.IO with JWT token",
                    "join_chat": "Join a specific chat room",
                    "leave_chat": "Leave a chat room",
                    "new_message": "Receive new message events"
                }
            }
        }, 200
    
    return app, socketio

import os
import sys
import logging
from transformers import WhisperModel, WhisperProcessor
import torch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_environment():
    """Setup and optimize the Docker environment"""
    
    # 1. Check PyTorch installation
    logger.info(f"PyTorch version: {torch.__version__}")
    logger.info(f"CUDA available: {torch.cuda.is_available()}")
    logger.info(f"CPU threads: {torch.get_num_threads()}")
    
    # 2. Pre-download Whisper models
    logger.info("Pre-downloading Whisper models...")
    try:
        model = WhisperModel.from_pretrained("openai/whisper-base")
        processor = WhisperProcessor.from_pretrained("openai/whisper-base")
        logger.info("Whisper models downloaded successfully")
        
        # Clear memory
        del model
        del processor
        torch.cuda.empty_cache() if torch.cuda.is_available() else None
        
    except Exception as e:
        logger.error(f"Failed to download Whisper models: {e}")
        sys.exit(1)
    
    # 3. Create necessary directories
    directories = [
        "/media/uploads/audio",
        "/media/uploads/images",
        "/usr/src/app/report",
        "/root/.cache/huggingface",
        "/usr/src/app/fine_tuned_whisper-base"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Created directory: {directory}")
    
    # 4. Set optimal environment variables
    env_vars = {
        "TRANSFORMERS_CACHE": "/root/.cache/huggingface",
        "HF_HOME": "/root/.cache/huggingface",
        "PYTORCH_CUDA_ALLOC_CONF": "max_split_size_mb:512",
        "TOKENIZERS_PARALLELISM": "false"
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
        logger.info(f"Set {key}={value}")
    
    logger.info("Setup completed successfully!")

def main():
    """Run the Flask application with Socket.IO."""
    app, socketio = create_app()
    
    # Use socketio.run instead of app.run for Socket.IO support
    socketio.run(
        app, 
        host="0.0.0.0", 
        port=8080, 
        debug=False,
        allow_unsafe_werkzeug=True  # For development only
    )

if __name__ == "__main__":
    setup_environment()
    main()