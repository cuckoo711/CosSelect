from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Space(Base):
    __tablename__ = "spaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)
    invite_code: Mapped[str] = mapped_column(String(8), nullable=False)
    manage_key: Mapped[str] = mapped_column(String(64), nullable=False)
    require_approval: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expire_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_access_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    categories: Mapped[list["Category"]] = relationship(
        back_populates="space", cascade="all, delete-orphan"
    )
    participants: Mapped[list["Participant"]] = relationship(
        back_populates="space", cascade="all, delete-orphan"
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    space_id: Mapped[int] = mapped_column(
        ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    space: Mapped["Space"] = relationship(back_populates="categories")
    photos: Mapped[list["Photo"]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    upload_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    category: Mapped["Category"] = relationship(back_populates="photos")


class Participant(Base):
    __tablename__ = "participants"
    __table_args__ = (UniqueConstraint("space_id", "nickname", name="uq_space_nickname"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    space_id: Mapped[int] = mapped_column(
        ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    # approval status: pending / approved / rejected
    status: Mapped[str] = mapped_column(String(16), default="approved", nullable=False)
    join_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    space: Mapped["Space"] = relationship(back_populates="participants")


class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = (
        UniqueConstraint("photo_id", "participant_id", name="uq_photo_participant_rating"),
        CheckConstraint("score >= 0.5 AND score <= 5.0", name="ck_score_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    photo_id: Mapped[int] = mapped_column(
        ForeignKey("photos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    participant_id: Mapped[int] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[float] = mapped_column(Numeric(2, 1), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    photo_id: Mapped[int] = mapped_column(
        ForeignKey("photos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    participant_id: Mapped[int | None] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    is_leader: Mapped[bool] = mapped_column(Boolean, default=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    likes_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    participant: Mapped["Participant | None"] = relationship()


class CommentLike(Base):
    __tablename__ = "comment_likes"
    __table_args__ = (
        UniqueConstraint("comment_id", "participant_id", name="uq_comment_participant_like"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    comment_id: Mapped[int] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    participant_id: Mapped[int] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("photo_id", "participant_id", name="uq_photo_participant_fav"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    photo_id: Mapped[int] = mapped_column(
        ForeignKey("photos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    participant_id: Mapped[int] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
