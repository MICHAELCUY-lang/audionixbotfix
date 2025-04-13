from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from database import db

class User(db.Model):
    """User model for storing Telegram user data."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(20), unique=True, nullable=False)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    notifications_enabled = Column(Boolean, default=True)

    # Relationships
    subscriptions = relationship("ArtistSubscription", back_populates="user", cascade="all, delete-orphan")
    searches = relationship("SearchHistory", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.telegram_id}>"


class ArtistSubscription(db.Model):
    """Model for storing artist subscriptions for new release notifications."""
    __tablename__ = "artist_subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    artist_name = Column(String(200), nullable=False)
    platform = Column(String(20), nullable=False)  # "spotify" or "youtube"
    artist_id = Column(String(100), nullable=False)
    last_checked = Column(DateTime, default=datetime.utcnow)
    last_release_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="subscriptions")

    def __repr__(self):
        return f"<ArtistSubscription {self.artist_name}>"


class SearchHistory(db.Model):
    """Model for storing search history."""
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    query = Column(String(200), nullable=False)
    platform = Column(String(20), nullable=False)  # "spotify" or "youtube"
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="searches")

    def __repr__(self):
        return f"<SearchHistory {self.query}>"


class TrendingSong(db.Model):
    """Model for storing trending songs."""
    __tablename__ = "trending_songs"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    artist = Column(String(200), nullable=False)
    platform = Column(String(20), nullable=False)  # "spotify" or "youtube"
    track_id = Column(String(100), nullable=False)
    rank = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<TrendingSong {self.title} by {self.artist}>"