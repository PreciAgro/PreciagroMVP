-- Geo Context Engine Database Schema
-- Initial migration for PostGIS-enabled spatial data

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Spatial reference systems table
CREATE TABLE IF NOT EXISTS spatial_reference_systems (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    srid INTEGER NOT NULL UNIQUE,
    proj4text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Weather stations table
CREATE TABLE IF NOT EXISTS weather_stations (
    id SERIAL PRIMARY KEY,
    station_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    elevation REAL,
    active BOOLEAN DEFAULT TRUE,
    data_sources TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Soil data table
CREATE TABLE IF NOT EXISTS soil_data (
    id SERIAL PRIMARY KEY,
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    ph REAL,
    organic_matter REAL,
    nitrogen REAL,
    phosphorus REAL,
    potassium REAL,
    soil_type VARCHAR(100),
    drainage VARCHAR(50),
    texture VARCHAR(50),
    depth_cm INTEGER,
    data_source VARCHAR(100),
    sample_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Climate data table
CREATE TABLE IF NOT EXISTS climate_data (
    id SERIAL PRIMARY KEY,
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    date DATE NOT NULL,
    temperature_avg REAL,
    temperature_min REAL,
    temperature_max REAL,
    precipitation REAL,
    humidity REAL,
    wind_speed REAL,
    solar_radiation REAL,
    growing_degree_days REAL,
    data_source VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Spatial context data
CREATE TABLE IF NOT EXISTS spatial_context (
    id SERIAL PRIMARY KEY,
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    elevation REAL,
    slope REAL,
    aspect REAL,
    land_use VARCHAR(100),
    administrative_region VARCHAR(255),
    nearest_weather_station_id INTEGER REFERENCES weather_stations(id),
    distance_to_water REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agricultural calendar events
CREATE TABLE IF NOT EXISTS calendar_events (
    id SERIAL PRIMARY KEY,
    region VARCHAR(255),
    crop_type VARCHAR(100),
    event_type VARCHAR(100), -- planting, harvesting, spraying, etc.
    recommended_date DATE,
    optimal_window_start DATE,
    optimal_window_end DATE,
    confidence REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Field context cache
CREATE TABLE IF NOT EXISTS field_context_cache (
    id SERIAL PRIMARY KEY,
    location_hash VARCHAR(64) NOT NULL,
    request_params_hash VARCHAR(64) NOT NULL,
    response_data JSONB NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create spatial indexes
CREATE INDEX IF NOT EXISTS idx_weather_stations_location ON weather_stations USING GIST (location);
CREATE INDEX IF NOT EXISTS idx_soil_data_location ON soil_data USING GIST (location);
CREATE INDEX IF NOT EXISTS idx_climate_data_location ON climate_data USING GIST (location);
CREATE INDEX IF NOT EXISTS idx_climate_data_date ON climate_data (date);
CREATE INDEX IF NOT EXISTS idx_spatial_context_location ON spatial_context USING GIST (location);
CREATE INDEX IF NOT EXISTS idx_calendar_events_crop_region ON calendar_events (crop_type, region);
CREATE INDEX IF NOT EXISTS idx_field_context_cache_hash ON field_context_cache (location_hash, request_params_hash);
CREATE INDEX IF NOT EXISTS idx_field_context_cache_expires ON field_context_cache (expires_at);

-- Sample data for testing
INSERT INTO weather_stations (station_id, name, location, elevation, active) VALUES
('PL_WARSAW_001', 'Warsaw Central', ST_GeogFromText('POINT(21.0122 52.2297)'), 106, true),
('ZW_MUREWA_001', 'Murewa Station', ST_GeogFromText('POINT(31.7833 -17.6333)'), 1200, true)
ON CONFLICT (station_id) DO NOTHING;

-- Sample climate data
INSERT INTO climate_data (location, date, temperature_avg, temperature_min, temperature_max, precipitation, humidity, data_source) VALUES
(ST_GeogFromText('POINT(21.0122 52.2297)'), '2024-03-15', 8.5, 2.1, 14.8, 2.3, 65, 'openweather'),
(ST_GeogFromText('POINT(31.7833 -17.6333)'), '2024-03-15', 24.2, 18.5, 29.8, 0.0, 55, 'local_station')
ON CONFLICT DO NOTHING;
