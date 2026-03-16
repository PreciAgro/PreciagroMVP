-- Migration 002: Performance indexes and crop_calendar uniqueness constraint
-- Run after 001_init.sql is confirmed applied.

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_farmers_phone ON farmers(phone_number);
CREATE INDEX IF NOT EXISTS idx_fields_farmer ON fields(farmer_id);
CREATE INDEX IF NOT EXISTS idx_interactions_farmer ON interactions(farmer_id);
CREATE INDEX IF NOT EXISTS idx_interactions_created ON interactions(farmer_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_weather_expires ON weather_cache(expires_at);

-- Uniqueness constraint required by seed_calendar.py upsert
ALTER TABLE crop_calendar ADD CONSTRAINT uq_crop_region UNIQUE (crop_type, region);