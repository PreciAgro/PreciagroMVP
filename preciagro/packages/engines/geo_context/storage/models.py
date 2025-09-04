"""Database models for GeoContext caching and layer registry."""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, Text, Float, Integer, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()


class GeoContextCache(Base):
    """Cache table for geocontext resolution results."""
    __tablename__ = "geoctx_cache"

    # Primary key is the context hash
    context_hash = Column(String(16), primary_key=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    hit_count = Column(Integer, default=0)

    # Location info for analytics
    centroid_lat = Column(Float, nullable=False)
    centroid_lon = Column(Float, nullable=False)

    # Cached data
    fco_response = Column(JSONB, nullable=False)

    # Provenance tracking
    layer_versions = Column(JSONB, nullable=False)

    # Indexing for performance
    __table_args__ = (
        Index('idx_geoctx_cache_location', 'centroid_lat', 'centroid_lon'),
        Index('idx_geoctx_cache_expires', 'expires_at'),
        Index('idx_geoctx_cache_created', 'created_at'),
    )


class LayerRegistry(Base):
    """Registry of data layers and their versions."""
    __tablename__ = "layer_registry"

    # Layer identification
    # e.g., 'spatial', 'climate', 'soil'
    layer_name = Column(String(50), primary_key=True)

    # Version info
    current_version = Column(String(20), nullable=False)  # e.g., 'v1.0'

    # Metadata
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_by = Column(String(100), nullable=False)  # System or user

    # Layer configuration
    config = Column(JSONB, nullable=True)  # Resolution, sources, etc.

    # Status
    is_active = Column(Boolean, default=True)

    # Description
    description = Column(Text, nullable=True)


class GeoContextMetrics(Base):
    """Metrics for geocontext engine performance."""
    __tablename__ = "geoctx_metrics"

    # Unique identifier
    id = Column(String(32), primary_key=True)  # UUID or timestamp-based

    # Timing
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Request info
    context_hash = Column(String(16), nullable=False)
    request_size_bytes = Column(Integer, nullable=True)

    # Performance
    total_duration_ms = Column(Integer, nullable=False)
    cache_hit = Column(Boolean, default=False)

    # Component timing
    spatial_resolve_ms = Column(Integer, nullable=True)
    soil_resolve_ms = Column(Integer, nullable=True)
    climate_resolve_ms = Column(Integer, nullable=True)
    calendar_compose_ms = Column(Integer, nullable=True)

    # Result metadata
    response_size_bytes = Column(Integer, nullable=True)
    error_occurred = Column(Boolean, default=False)
    error_type = Column(String(50), nullable=True)

    # Indexing
    __table_args__ = (
        Index('idx_geoctx_metrics_timestamp', 'timestamp'),
        Index('idx_geoctx_metrics_context_hash', 'context_hash'),
        Index('idx_geoctx_metrics_duration', 'total_duration_ms'),
        Index('idx_geoctx_metrics_cache_hit', 'cache_hit'),
    )
