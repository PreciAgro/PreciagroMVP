-- farmers
CREATE TABLE IF NOT EXISTS farmers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone_number VARCHAR UNIQUE NOT NULL,
  name VARCHAR,
  latitude FLOAT,
  longitude FLOAT,
  language VARCHAR DEFAULT 'en',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- fields
CREATE TABLE IF NOT EXISTS fields (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  farmer_id UUID REFERENCES farmers(id),
  name VARCHAR,
  crop_type VARCHAR,
  planting_date DATE,
  area_hectares FLOAT
);

-- interactions
CREATE TABLE IF NOT EXISTS interactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  farmer_id UUID REFERENCES farmers(id),
  field_id UUID REFERENCES fields(id),
  message_in TEXT,
  message_out TEXT,
  image_url TEXT,
  insight TEXT,
  action TEXT,
  confidence FLOAT,
  urgency VARCHAR,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- weather_cache
CREATE TABLE IF NOT EXISTS weather_cache (
  location_hash VARCHAR PRIMARY KEY,
  forecast_json JSONB,
  fetched_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ
);

-- crop_calendar
CREATE TABLE IF NOT EXISTS crop_calendar (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  crop_type VARCHAR,
  region VARCHAR,
  growth_stages JSONB,
  disease_risk_periods JSONB
);
