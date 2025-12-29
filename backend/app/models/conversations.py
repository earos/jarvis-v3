"""
JARVIS v3 - Conversation Storage Models
SQLAlchemy async models for conversation persistence
"""
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.future import select

Base = declarative_base()

# Database engine and session factory
DATABASE_URL = "sqlite+aiosqlite:////opt/jarvis-v3/backend/data/conversations.db"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class Conversation(Base):
    """
    Conversation container - tracks an entire conversation thread
    """
    __tablename__ = 'conversations'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(500), nullable=True)  # Auto-generated from first message
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship to messages
    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "title": self.title or "New Conversation",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Message(Base):
    """
    Individual message within a conversation
    """
    __tablename__ = 'messages'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey('conversations.id'), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to conversation
    conversation = relationship("Conversation", back_populates="messages")

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def to_claude_message(self):
        """Convert to Claude API message format"""
        return {
            "role": self.role,
            "content": self.content
        }


# ============================================================================
# Database Helper Functions
# ============================================================================

async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db_session() -> AsyncSession:
    """Get async database session"""
    async with AsyncSessionLocal() as session:
        yield session


async def create_conversation(title: Optional[str] = None) -> Conversation:
    """Create a new conversation"""
    async with AsyncSessionLocal() as session:
        conversation = Conversation(
            id=str(uuid.uuid4()),
            title=title
        )
        session.add(conversation)
        await session.commit()
        await session.refresh(conversation)
        return conversation


async def get_conversation(conversation_id: str) -> Optional[Conversation]:
    """Get conversation by ID with all messages"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        
        if conversation:
            # Eagerly load messages
            await session.refresh(conversation, ['messages'])
        
        return conversation


async def list_conversations(limit: int = 50, offset: int = 0) -> List[Conversation]:
    """List all conversations ordered by most recent"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Conversation)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        conversations = result.scalars().all()
        return list(conversations)


async def add_message(
    conversation_id: str,
    role: str,
    content: str
) -> Message:
    """Add a message to a conversation"""
    async with AsyncSessionLocal() as session:
        message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content
        )
        session.add(message)
        
        # Update conversation's updated_at timestamp
        conversation = await session.get(Conversation, conversation_id)
        if conversation:
            conversation.updated_at = datetime.utcnow()
        
        await session.commit()
        await session.refresh(message)
        return message


async def get_conversation_messages(conversation_id: str) -> List[Message]:
    """Get all messages for a conversation in order"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        messages = result.scalars().all()
        return list(messages)


async def update_conversation_title(conversation_id: str, title: str) -> bool:
    """Update conversation title"""
    async with AsyncSessionLocal() as session:
        conversation = await session.get(Conversation, conversation_id)
        if conversation:
            conversation.title = title
            conversation.updated_at = datetime.utcnow()
            await session.commit()
            return True
        return False


async def delete_conversation(conversation_id: str) -> bool:
    """Delete a conversation and all its messages"""
    async with AsyncSessionLocal() as session:
        conversation = await session.get(Conversation, conversation_id)
        if conversation:
            await session.delete(conversation)
            await session.commit()
            return True
        return False
