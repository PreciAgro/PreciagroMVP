-- Migration 003: Replace PostGIS geography columns with plain lat/lng floats.
--
-- Background: Railway PostgreSQL does not have PostGIS installed.
-- GEOGRAPHY(POINT) and GEOGRAPHY(POLYGON) columns cannot be used.
-- This migration adds simple lat/lng columns to farmers and replaces
-- the boundary column in fields with JSONB storage.
--
-- Run after 001_init.sql.

-- Farmers: add plain lat/lng columns
ALTER TABLE farmers ADD COLUMN IF NOT EXISTS lat  DOUBLE PRECISION;
ALTER TABLE farmers ADD COLUMN IF NOT EXISTS lng  DOUBLE PRECISION;

-- Fields: add JSONB boundary column
ALTER TABLE fields  ADD COLUMN IF NOT EXISTS boundary_json JSONB;
