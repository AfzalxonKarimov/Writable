"""
SQLAlchemy models. Mirrors the schema we designed:
users -> submissions -> (assessments | generated_samples)

current_state and pending_data on User implement the resumable FSM:
every step of the conversation flow writes here so a server restart
or a multi-day gap doesn't lose the user's progress.
"""
from datetime import datetime
from sqlalchemy import (
    String, Integer, Float, Text, ForeignKey, DateTime, JSON
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # --- Resumable FSM state, persisted to DB (not memory) on purpose ---
    current_state: Mapped[str] = mapped_column(String(64), default="IDLE")
    pending_data: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    submissions: Mapped[list["Submission"]] = relationship(back_populates="user")


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    mode: Mapped[str] = mapped_column(String(16))         # 'write' | 'assess'
    task_type: Mapped[str] = mapped_column(String(16))    # 'task1' | 'task2'

    # Task 1 chart/graph/map image. We store Telegram's file_id (see decision:
    # the channel post is the real long-term archive, file_id is just for
    # quick re-use within the bot itself).
    prompt_image_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Task 2 essay topic, or AI-extracted description of the Task 1 image
    prompt_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Only populated in 'assess' mode -- the user's own writing
    user_answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    ai_model_used: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    # 'pending' | 'processing' | 'completed' | 'failed'

    # Channel message ids, so we can always jump from DB -> exact channel post
    log_summary_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    log_detail_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="submissions")
    assessment: Mapped["Assessment"] = relationship(
        back_populates="submission", uselist=False, cascade="all, delete-orphan"
    )
    generated_sample: Mapped["GeneratedSample"] = relationship(
        back_populates="submission", uselist=False, cascade="all, delete-orphan"
    )


class Assessment(Base):
    """Created only when submission.mode == 'assess'."""
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.id"), unique=True, index=True
    )

    band_task_achievement: Mapped[float] = mapped_column(Float)   # TA (T1) / TR (T2)
    band_coherence_cohesion: Mapped[float] = mapped_column(Float)
    band_lexical_resource: Mapped[float] = mapped_column(Float)
    band_grammatical_range: Mapped[float] = mapped_column(Float)
    band_overall: Mapped[float] = mapped_column(Float)

    feedback_text: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    submission: Mapped["Submission"] = relationship(back_populates="assessment")


class GeneratedSample(Base):
    """Created only when submission.mode == 'write'."""
    __tablename__ = "generated_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.id"), unique=True, index=True
    )

    sample_text: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    submission: Mapped["Submission"] = relationship(back_populates="generated_sample")
