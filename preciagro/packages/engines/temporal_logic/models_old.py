"""SQLAlchemy async models for temporal logic engine."""
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, Dict, Any

Base = declarative_base()


class TemporalEvent(Base):
    """Represents an event in the temporal logic system."""
    
    __tablename__ = "temporal_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(100), nullable=False, index=True)
    source = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    metadata = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    triggered_schedules = relationship("ScheduledTask", back_populates="triggering_event")


class TemporalRule(Base):
    """Represents a temporal rule definition."""
    
    __tablename__ = "temporal_rules"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    conditions = Column(JSON, nullable=False)  # Predicate conditions
    actions = Column(JSON, nullable=False)     # Actions to take
    window_config = Column(JSON, nullable=False)  # Time window configuration
    enabled = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    schedules = relationship("ScheduledTask", back_populates="rule")


class ScheduledTask(Base):
    """Represents a scheduled task/job."""
    
    __tablename__ = "scheduled_tasks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(Integer, ForeignKey("temporal_rules.id"), nullable=False, index=True)
    triggering_event_id = Column(Integer, ForeignKey("temporal_events.id"), nullable=True, index=True)
    
    task_type = Column(String(50), nullable=False)  # message, webhook, etc.
    task_config = Column(JSON, nullable=False)      # Task-specific configuration
    
    scheduled_for = Column(DateTime(timezone=True), nullable=False, index=True)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    status = Column(String(20), default="pending", index=True)  # pending, running, completed, failed, cancelled
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    
    error_message = Column(Text, nullable=True)
    result = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    rule = relationship("TemporalRule", back_populates="schedules")
    triggering_event = relationship("TemporalEvent", back_populates="triggered_schedules")
    outcomes = relationship("TaskOutcome", back_populates="task")


class TaskOutcome(Base):
    """Represents the outcome/result of a task execution."""
    
    __tablename__ = "task_outcomes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("scheduled_tasks.id"), nullable=False, index=True)
    
    outcome_type = Column(String(50), nullable=False)  # success, failure, user_response, etc.
    outcome_data = Column(JSON, nullable=False)
    
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    source = Column(String(100), nullable=True)  # where the outcome came from
    
    # Relationships
    task = relationship("ScheduledTask", back_populates="outcomes")


class UserIntent(Base):
    """Represents user intents processed by NLP boundary."""
    
    __tablename__ = "user_intents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=False, index=True)
    channel = Column(String(50), nullable=False)  # whatsapp, sms, etc.
    
    raw_input = Column(Text, nullable=False)
    processed_intent = Column(JSON, nullable=False)
    confidence_score = Column(Integer, nullable=True)  # 0-100
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Context
    conversation_context = Column(JSON, default={})
    

class RateLimitBucket(Base):
    """Rate limiting buckets for users/channels."""
    
    __tablename__ = "rate_limit_buckets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=False, index=True)
    channel = Column(String(50), nullable=False)
    bucket_key = Column(String(200), nullable=False, index=True)  # composite key for rate limiting
    
    current_count = Column(Integer, default=0)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        # Unique constraint on user, channel, and bucket key
        {"sqlite_autoincrement": True}
    )
