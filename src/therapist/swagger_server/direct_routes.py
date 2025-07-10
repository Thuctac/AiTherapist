from flask import request, jsonify, current_app
import os
import uuid
import jwt
from datetime import datetime, timedelta, timezone
from pathlib import Path
import traceback
from sqlalchemy import select

from swagger_server.db import engine, users, conversations, messages
from logic.therapy import TherapySession
from swagger_server.audio_converter import save_and_convert_audio

# ---------------------------------------------------------------------------
# File-system config
# ---------------------------------------------------------------------------
UPLOAD_ROOT = Path(os.getenv("UPLOAD_DIR", "/tmp/uploads"))
IMAGE_DIR = UPLOAD_ROOT / "images"
AUDIO_DIR = UPLOAD_ROOT / "audio"
for _d in (IMAGE_DIR, AUDIO_DIR):
    _d.mkdir(parents=True, exist_ok=True)

REPORT_DIR = Path("report")

# ---------------------------------------------------------------------------
# Authentication config
# ---------------------------------------------------------------------------
JWT_SECRET     = os.getenv("JWT_SECRET", "change_this_secret")
JWT_ALGORITHM  = "HS256"
JWT_EXPIRES_IN = 7 * 24 * 3600  # one week

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def debug_file_path(file_path, prefix="File"):
    """Print debugging information about a file path."""
    if not file_path:
        print(f"{prefix} path is None")
        return
    
    print(f"{prefix} full path: {file_path}")
    
    # Check if file exists
    exists = os.path.exists(file_path)
    print(f"{prefix} exists: {exists}")
    
    if exists:
        # Check file size
        size = os.path.getsize(file_path)
        print(f"{prefix} size: {size} bytes")
        
        # Check permissions
        readable = os.access(file_path, os.R_OK)
        writable = os.access(file_path, os.W_OK)
        print(f"{prefix} permissions: readable={readable}, writable={writable}")
        
        # Check owner and group
        stat_info = os.stat(file_path)
        print(f"{prefix} owner/group: {stat_info.st_uid}/{stat_info.st_gid}")
    
    # Get the file name
    filename = os.path.basename(file_path)
    print(f"{prefix} filename: {filename}")
    
    # Construct the expected public URL
    public_url = get_public_url(file_path)
    print(f"{prefix} expected public URL: {public_url}")

def _save(storage, directory: Path, ext: str):
    """Persist an uploaded FileStorage; return the relative path or None."""
    if storage is None:
        return None
    name = f"{uuid.uuid4().hex}{ext}"
    dest = directory / name
    storage.save(dest)
    return str(dest)


def _read_report(name: str):
    """Read a report file, return None if not found."""
    try:
        return (REPORT_DIR / name).read_text("utf-8")
    except FileNotFoundError:
        return None


def _ensure_conversation(conn, uid):
    """Return an existing conversation ID or create a new one for user `uid`."""
    row = conn.execute(
        select(conversations).where(conversations.c.user_id == uid)
    ).first()
    if row:
        return row.id
    res = conn.execute(conversations.insert().values(user_id=uid))
    return res.inserted_primary_key[0]


def get_public_url(file_path):
    """
    Convert an internal file path to a public URL that can be accessed by the frontend.
    
    Args:
        file_path: Internal file path (e.g., "/tmp/uploads/images/abc123.png")
        
    Returns:
        Public URL (e.g., "/uploads/images/abc123.png")
    """
    if not file_path:
        return None
    
    # Convert to Path object for easier manipulation
    path = Path(file_path)
    upload_root = Path(os.getenv("UPLOAD_DIR", "/tmp/uploads"))
    
    try:
        # Get the relative path from upload root
        relative_path = path.relative_to(upload_root)
        # Return the public URL with the relative path
        return f"/uploads/{relative_path.as_posix()}"
    except ValueError:
        # If the path is not relative to upload_root, just return the filename
        return f"/uploads/{path.name}"


def _build_conversation_log(conn, conversation_id):
    """
    Build a conversation log string from the database history.
    
    Format:
    therapist: text
    user: text/audio path/image path
    
    Args:
        conn: Database connection
        conversation_id: The conversation ID to fetch history for
        
    Returns:
        String containing the formatted conversation history
    """
    rows = conn.execute(
        select(messages)
        .where(messages.c.conversation_id == conversation_id)
        .order_by(messages.c.id)
    ).fetchall()
    
    conversation_log = []
    
    for row in rows:
        # Add user message if present
        user_parts = []
        if row.text:
            user_parts.append(row.text)
        if row.audio_url:
            user_parts.append(f"[audio: {row.audio_url}]")
        if row.image_url:
            user_parts.append(f"[image: {row.image_url}]")
        
        if user_parts:
            conversation_log.append(f"user: {' '.join(user_parts)}")
        
        # Add therapist response if present
        if row.bot_text:
            conversation_log.append(f"therapist: {row.bot_text}")
    
    return '\n'.join(conversation_log)


def _generate_token(user_id) -> str:
    """Generate a JWT token for the given user ID."""
    payload = {
        "user_id": str(user_id),  # ← serializing the UUID
        "exp":     datetime.now(timezone.utc) + timedelta(seconds=JWT_EXPIRES_IN),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def _decode_token(token: str):
    """Decode a JWT token, returning (payload, None) or (None, error_message)."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM]), None
    except jwt.ExpiredSignatureError:
        return None, "Token expired. Please log in again."
    except jwt.InvalidTokenError:
        return None, "Invalid token. Please log in again."

def broadcast_new_message(message_data, user_id):
    """Broadcast a new message via Socket.IO."""
    try:
        # Access the Socket.IO instance
        socketio = current_app.extensions.get('socketio')
        if socketio:
            print(f"Broadcasting new message to user {user_id}")
            # Emit to the room/user
            socketio.emit('newMessage', message_data, room=f"user_{user_id}")
        else:
            print("SocketIO not available")
    except Exception as e:
        print(f"Error broadcasting message: {str(e)}")
        traceback.print_exc()

# ---------------------------------------------------------------------------
# Direct routes
# ---------------------------------------------------------------------------

def register_direct_routes(app):
    """Register direct Flask routes that bypass Connexion."""
    
    # ---------------------------------------------------------------------------
    # Message routes
    # ---------------------------------------------------------------------------
    
    @app.route('/direct/messages/send/<user_id>', methods=['POST'])
    def direct_send_message(user_id):
        """Handle message submission directly, bypassing Connexion."""
        try:
            print(f"\n{'=' * 50}")
            print(f"DIRECT ROUTE HIT: POST /direct/messages/send/{user_id}")
            print(f"Request content type: {request.content_type}")
            print(f"Form keys: {list(request.form.keys()) if request.form else 'None'}")
            print(f"Files keys: {list(request.files.keys()) if request.files else 'None'}")
            
            # Detailed info about files
            for key, file_storage in request.files.items():
                print(f"File '{key}' details:")
                print(f"  - Filename: {file_storage.filename}")
                print(f"  - Content type: {file_storage.content_type}")
                print(f"  - Content length: {request.headers.get('Content-Length')}")
            
            # Get message content
            user_text = request.form.get("text", "").strip() or None
            audio_storage = request.files.get("audio")
            image_storage = request.files.get("image")
            
            print(f"Text content: {'Present' if user_text else 'Not present'}")
            if user_text:
                print(f"  - Text preview: {user_text[:50]}...")
            
            print(f"Audio: {'Present' if audio_storage else 'Not present'}")
            if audio_storage:
                print(f"  - Filename: {audio_storage.filename}")
                print(f"  - Content type: {audio_storage.content_type}")
            
            print(f"Image: {'Present' if image_storage else 'Not present'}")
            if image_storage:
                print(f"  - Filename: {image_storage.filename}")
                print(f"  - Content type: {image_storage.content_type}")
            
            # Validate
            if not any([user_text, audio_storage, image_storage]):
                print("ERROR: No content provided")
                return jsonify({
                    "message": "Provide at least one of: text, audio, or image."
                }), 400
            
            # Save files with detailed logging
            audio_path = None
            if audio_storage:
                try:
                    # Store the original name and content type for debugging
                    original_filename = audio_storage.filename
                    content_type = audio_storage.content_type
                    
                    # Save the file with a .webm extension
                    audio_path = save_and_convert_audio(audio_storage, AUDIO_DIR, target_ext=".wav")
                    
                    print(f"Audio saved:")
                    print(f"  - Original filename: {original_filename}")
                    print(f"  - Content type: {content_type}")
                    print(f"  - Saved to: {audio_path}")
                    print(f"  - Public URL: {get_public_url(audio_path)}")
                    
                    # Debug the file path
                    debug_file_path(audio_path, "Audio")
                except Exception as e:
                    print(f"ERROR saving audio: {str(e)}")
                    traceback.print_exc()
            
            image_path = None
            if image_storage:
                try:
                    # Store the original name and content type for debugging
                    original_filename = image_storage.filename
                    content_type = image_storage.content_type
                    
                    # Save the file with appropriate extension
                    ext = ".png"
                    if content_type == "image/jpeg" or original_filename.lower().endswith(('.jpg', '.jpeg')):
                        ext = ".jpg"
                    elif content_type == "image/gif" or original_filename.lower().endswith('.gif'):
                        ext = ".gif"
                    
                    image_path = _save(image_storage, IMAGE_DIR, ext)
                    
                    print(f"Image saved:")
                    print(f"  - Original filename: {original_filename}")
                    print(f"  - Content type: {content_type}")
                    print(f"  - Saved to: {image_path}")
                    print(f"  - Public URL: {get_public_url(image_path)}")
                    
                    # Debug the file path
                    debug_file_path(image_path, "Image")
                except Exception as e:
                    print(f"ERROR saving image: {str(e)}")
                    traceback.print_exc()
            
            # Check user exists and get conversation history
            with engine.begin() as conn:
                if not conn.execute(select(users.c.id).where(users.c.id == user_id)).first():
                    return jsonify({"message": "User not found"}), 404
                conv_id = _ensure_conversation(conn, user_id)
                
                # Build conversation log
                conversation_log = _build_conversation_log(conn, conv_id)
                print(f"Conversation log preview: {conversation_log[:200]}..." if conversation_log else "No conversation history")
            
            # Process with AI
            therapy = TherapySession()
            bot_reply = therapy.run(
                user_text=user_text,
                image_path=image_path,
                audio_path=audio_path,
                conversation_log=conversation_log,
            )
            
            print(f"Bot reply: {bot_reply[:100]}..." if bot_reply else "No bot reply")
            
            # Get reports
            text_rep = _read_report("text_report.md")
            img_rep = _read_report("image_report.md")
            aud_rep = _read_report("audio_report.md")
            
            # Determine content type
            user_supplied = {
                "text": bool(user_text),
                "audio": bool(audio_path),
                "image": bool(image_path),
            }
            if sum(user_supplied.values()) > 1:
                content_type = "mixed"
            elif user_supplied["audio"]:
                content_type = "audio"
            elif user_supplied["image"]:
                content_type = "image"
            else:
                content_type = "text"
            
            print(f"Content type: {content_type}")
            
            # Save to database
            with engine.begin() as conn:
                ins = conn.execute(
                    messages.insert().values(
                        conversation_id=conv_id,
                        content_type=content_type,
                        text=user_text,
                        image_url=image_path,
                        audio_url=audio_path,
                        text_report=text_rep,
                        image_report=img_rep,
                        audio_report=aud_rep,
                        bot_text=bot_reply,
                        bot_audio_url=None,
                    )
                )
                row = conn.execute(
                    select(messages).where(messages.c.id == ins.inserted_primary_key[0])
                ).first()
                
                # Print detailed info about what was saved
                print("\n----- DATABASE RECORD DEBUG -----")
                print(f"Message ID: {row.id}")
                print(f"User text: {row.text}")
                print(f"Image path: {row.image_url}")
                print(f"Audio path: {row.audio_url}")
                print(f"Bot text length: {len(row.bot_text) if row.bot_text else 0}")
                print(f"Bot text preview: {row.bot_text[:50]}..." if row.bot_text else "None")
                print("----- END DEBUG -----\n")
            
            print("Message saved successfully")
            
            # Return both the user message and bot response
            # Create the response with both messages and convert file paths to public URLs
            timestamp = row.timestamp.isoformat()
            response = []
            
            # Add user message
            user_message = {
                "_id": f"{row.id}-user",
                "senderId": str(user_id),
                "conversationId": str(row.conversation_id),
                "text": row.text,
                "audio": get_public_url(row.audio_url),
                "imageUrl": get_public_url(row.image_url),
                "createdAt": timestamp,
            }
            response.append(user_message)
            
            # Add bot response if present
            if row.bot_text:
                bot_message = {
                    "_id": f"{row.id}-bot",
                    "senderId": "bot",
                    "conversationId": str(row.conversation_id),
                    "text": row.bot_text,
                    "audio": get_public_url(row.bot_audio_url),
                    "imageUrl": None,
                    "createdAt": timestamp,
                }
                response.append(bot_message)
            
            print(f"Response with public URLs: {response}")
            print(f"Response status: 201 Created")
            print(f"{'=' * 50}\n")
            
            return jsonify(response), 201
            
        except Exception as e:
            print(f"ERROR in direct_send_message: {str(e)}")
            traceback.print_exc()
            print(f"{'=' * 50}\n")
            return jsonify({"message": f"Server error: {str(e)}"}), 500
    
    @app.route('/direct/messages/<user_id>', methods=['GET'])
    def direct_get_messages(user_id):
        """Get messages for a user directly, bypassing Connexion.
        
        This version correctly handles the database schema where each row
        contains both a user message and bot response, returning them as
        separate message objects.
        """
        try:
            print(f"Direct route hit for getting messages, user_id: {user_id}")
            
            with engine.connect() as conn:
                conv = conn.execute(
                    select(conversations.c.id).where(conversations.c.user_id == user_id)
                ).first()
                if not conv:
                    print("No conversation found for user")
                    return jsonify([]), 200
                
                rows = conn.execute(
                    select(messages)
                    .where(messages.c.conversation_id == conv.id)
                    .order_by(messages.c.id)
                ).fetchall()
            
            # Debug file paths from database
            for idx, row in enumerate(rows):
                print(f"\nDebugging file paths for message {idx + 1}:")
                if row.audio_url:
                    debug_file_path(row.audio_url, "Database Audio")
                if row.image_url:
                    debug_file_path(row.image_url, "Database Image")
            
            # Convert rows to message objects, splitting each row into user message and bot response
            result = []
            for row in rows:
                # Add user message if there's any user content
                if row.text or row.audio_url or row.image_url:
                    user_message = {
                        "_id": f"{row.id}-user",
                        "senderId": str(user_id),
                        "conversationId": str(row.conversation_id),
                        "text": row.text,
                        "audio": get_public_url(row.audio_url),
                        "imageUrl": get_public_url(row.image_url),
                        "createdAt": row.timestamp.isoformat(),
                    }
                    result.append(user_message)
                
                # Add bot response if present
                if row.bot_text:
                    bot_message = {
                        "_id": f"{row.id}-bot",
                        "senderId": "bot",
                        "conversationId": str(row.conversation_id),
                        "text": row.bot_text,
                        "audio": get_public_url(row.bot_audio_url),
                        "imageUrl": None,
                        "createdAt": row.timestamp.isoformat(),
                    }
                    result.append(bot_message)
            
            print(f"Found {len(result)} messages (including bot responses)")
            
            # Debug log for media URLs
            for idx, msg in enumerate(result):
                audio_url = msg.get('audio')
                image_url = msg.get('imageUrl')
                if audio_url or image_url:
                    print(f"Message {idx + 1} media:")
                    if audio_url:
                        print(f"  - Audio URL: {audio_url}")
                    if image_url:
                        print(f"  - Image URL: {image_url}")
            
            return jsonify(result), 200
            
        except Exception as e:
            print(f"Error in direct_get_messages: {str(e)}")
            traceback.print_exc()
            return jsonify({"message": f"Server error: {str(e)}"}), 500
    
    @app.route('/direct/messages/test/<user_id>', methods=['POST'])
    def direct_test_message(user_id):
        """Test endpoint that always returns a fixed response."""
        try:
            print(f"Test endpoint hit for user_id: {user_id}")
            
            # Get message content
            user_text = request.form.get("text", "").strip() or None
            print(f"User text: {user_text}")
            
            # Check user exists
            with engine.begin() as conn:
                if not conn.execute(select(users.c.id).where(users.c.id == user_id)).first():
                    return jsonify({"message": "User not found"}), 404
                conv_id = _ensure_conversation(conn, user_id)
            
            # Fixed bot reply
            bot_reply = "This is a test response from the server. If you're seeing this message in the UI, then the issue isn't with message display."
            
            # Save to database
            with engine.begin() as conn:
                ins = conn.execute(
                    messages.insert().values(
                        conversation_id=conv_id,
                        content_type="text",
                        text=user_text,
                        image_url=None,
                        audio_url=None,
                        text_report=None,
                        image_report=None,
                        audio_report=None,
                        bot_text=bot_reply,
                        bot_audio_url=None,
                        timestamp=datetime.now(timezone.utc)
                    )
                )
                
                # Get the inserted row
                message_id = ins.inserted_primary_key[0]
                row = conn.execute(
                    select(messages).where(messages.c.id == message_id)
                ).first()
                
                # Print debug info
                print("\n----- TEST ENDPOINT DEBUG -----")
                print(f"Message ID: {row.id}")
                print(f"User text: {row.text}")
                print(f"Bot text: {row.bot_text}")
                print(f"Timestamp: {row.timestamp}")
                print("----- END DEBUG -----\n")
            
            # Return both the user message and the bot response
            timestamp = row.timestamp.isoformat()
            response = [
                # User message
                {
                    "_id": f"{row.id}-user",
                    "senderId": str(user_id),
                    "conversationId": str(row.conversation_id),
                    "text": row.text,
                    "audio": None,
                    "imageUrl": None,
                    "createdAt": timestamp,
                },
                # Bot response
                {
                    "_id": f"{row.id}-bot",
                    "senderId": "bot",
                    "conversationId": str(row.conversation_id),
                    "text": row.bot_text,
                    "audio": None,
                    "imageUrl": None,
                    "createdAt": timestamp,
                }
            ]
            
            print(f"Returning response: {response}")
            return jsonify(response), 201
            
        except Exception as e:
            print(f"Error in test endpoint: {str(e)}")
            traceback.print_exc()
            return jsonify({"message": f"Server error: {str(e)}"}), 500
    
    # Add a route to test direct file access
    @app.route('/direct/test-file/<filename>', methods=['GET'])
    def direct_test_file(filename):
        """Test direct file access."""
        try:
            upload_dir = os.getenv("UPLOAD_DIR", "/tmp/uploads")
            file_path = os.path.join(upload_dir, filename)
            
            print(f"Testing direct file access: {file_path}")
            debug_file_path(file_path, "Test File")
            
            # Detect content type based on file extension
            content_type = None
            if filename.endswith('.webm'):
                content_type = 'audio/webm'
            elif filename.endswith('.ogg'):
                content_type = 'audio/ogg'
            elif filename.endswith('.png'):
                content_type = 'image/png'
            elif filename.endswith('.jpg') or filename.endswith('.jpeg'):
                content_type = 'image/jpeg'
            
            if os.path.exists(file_path):
                response = current_app.send_file(file_path)
                if content_type:
                    response.headers['Content-Type'] = content_type
                return response
            else:
                return jsonify({"message": f"File {filename} not found"}), 404
        except Exception as e:
            print(f"Error in direct_test_file: {str(e)}")
            traceback.print_exc()
            return jsonify({"message": f"Server error: {str(e)}"}), 500
    
    # ---------------------------------------------------------------------------
    # Authentication routes
    # ---------------------------------------------------------------------------
    
    @app.route('/direct/auth/signup', methods=['POST'])
    def direct_auth_signup():
        """Handle user signup."""
        try:
            print("Direct signup route hit")
            data = request.get_json()
            
            if not data:
                return jsonify({"message": "No data provided"}), 400
                
            print(f"Signup data: {data}")
            
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
            
            if not username or not email or not password:
                return jsonify({"message": "Missing required fields"}), 400
            
            with engine.begin() as conn:
                # check email uniqueness
                existing = conn.execute(
                    users.select().where(users.c.email == email)
                ).first()
                
                if existing:
                    return jsonify({"message": "Email already registered"}), 409
                
                # insert user
                result = conn.execute(
                    users.insert().values(
                        username=username,
                        email=email,
                        password=password,
                    )
                )
                user_id = result.inserted_primary_key[0]
                
                # create conversation for new user
                conn.execute(
                    conversations.insert().values(
                        user_id=user_id
                    )
                )
            
            token = _generate_token(user_id)
            
            return jsonify({
                "_id": str(user_id),
                "username": username,
                "email": email,
                "token": token
            }), 201
            
        except Exception as e:
            print(f"Error in direct_auth_signup: {str(e)}")
            traceback.print_exc()
            return jsonify({"message": f"Server error: {str(e)}"}), 500
    
    @app.route('/direct/auth/login', methods=['POST'])
    def direct_auth_login():
        """Handle user login."""
        try:
            print("Direct login route hit")
            data = request.get_json()
            
            if not data:
                return jsonify({"message": "No data provided"}), 400
                
            print(f"Login data: {data}")
            
            email = data.get('email')
            password = data.get('password')
            
            if not email or not password:
                return jsonify({"message": "Email and password required"}), 400
            
            with engine.connect() as conn:
                row = conn.execute(
                    users.select()
                        .where(users.c.email == email)
                        .where(users.c.password == password)
                ).first()
            
            if not row:
                return jsonify({"message": "Invalid credentials"}), 401
            
            token = _generate_token(row.id)
            
            return jsonify({
                "_id": str(row.id),
                "username": row.username,
                "email": row.email,
                "token": token
            })
            
        except Exception as e:
            print(f"Error in direct_auth_login: {str(e)}")
            traceback.print_exc()
            return jsonify({"message": f"Server error: {str(e)}"}), 500
    
    @app.route('/direct/auth/check', methods=['GET'])
    def direct_auth_check():
        """Check authentication status."""
        try:
            print("Direct auth check route hit")
            
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return jsonify({"message": "Missing Bearer token"}), 401
            
            token = auth_header.split(" ", 1)[1]
            payload, error = _decode_token(token)
            
            if error:
                return jsonify({"message": error}), 401
                
            user_id = payload.get("user_id")
            
            with engine.connect() as conn:
                row = conn.execute(
                    users.select().where(users.c.id == user_id)
                ).first()
            
            if not row:
                return jsonify({"message": "User not found"}), 404
            
            return jsonify({
                "_id": str(row.id),
                "username": row.username,
                "email": row.email,
                "token": token
            })
            
        except Exception as e:
            print(f"Error in direct_auth_check: {str(e)}")
            traceback.print_exc()
            return jsonify({"message": f"Server error: {str(e)}"}), 500
    
    @app.route('/direct/auth/logout', methods=['POST'])
    def direct_auth_logout():
        """Log out current user."""
        return "", 204