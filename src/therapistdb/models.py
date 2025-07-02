

import uuid
from sqlalchemy import (
    CheckConstraint,
    Column,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    TIMESTAMP,
    func,
    text as sql_text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

# ----------------------------------------------------------------- Base
Base = declarative_base()

# ----------------------------------------------------------------- Models
class User(Base):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sql_text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    username = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)  # store *hashed* values only

    conversations = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sql_text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )


ContentType = Enum(
    "text", "image", "audio", "mixed", name="content_type_enum", create_type=True
)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )

    content_type = Column(ContentType, nullable=False)

    # Optional payload columns
    text = Column(Text)
    image_url = Column(String)
    audio_url = Column(String)

    # AI analysis + bot reply
    text_report = Column(Text)
    image_report = Column(Text)
    audio_report = Column(Text)
    bot_text = Column(Text)
    bot_audio_url = Column(String)

    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    conversation = relationship("Conversation", back_populates="messages")
    ratings = relationship(
        "Rating", back_populates="message", cascade="all, delete-orphan"
    )


class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(
        Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    rating = Column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_rating_range"),
    )

    message = relationship("Message", back_populates="ratings")

