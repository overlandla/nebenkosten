-- Nebenkosten Configuration Database Schema
-- This database stores mutable configuration that can be edited via the Next.js UI
-- and read by both Dagster and Next.js services

-- Create the database (run this as postgres user)
-- CREATE DATABASE nebenkosten_config OWNER dagster;

-- Connect to the database
-- \c nebenkosten_config

-- Enable UUID extension for future use
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Meters table - stores all meter definitions
CREATE TABLE IF NOT EXISTS meters (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    meter_type VARCHAR(50) NOT NULL CHECK (meter_type IN ('electricity', 'gas', 'water', 'heat', 'solar')),
    category VARCHAR(50) NOT NULL CHECK (category IN ('physical', 'master', 'virtual')),
    unit VARCHAR(20) NOT NULL,
    installation_date DATE,
    deinstallation_date DATE,
    source_meters JSONB,              -- For master/virtual meters: list of source meter IDs
    calculation_config JSONB,         -- For virtual meters: calculation parameters
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Households table - stores household/unit definitions
CREATE TABLE IF NOT EXISTS households (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    floors TEXT[],                    -- Array of floor identifiers
    allocation_percentage DECIMAL(5,2) CHECK (allocation_percentage >= 0 AND allocation_percentage <= 100),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Household-Meter assignments - many-to-many relationship
CREATE TABLE IF NOT EXISTS household_meters (
    id SERIAL PRIMARY KEY,
    household_id VARCHAR(100) NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    meter_id VARCHAR(100) NOT NULL REFERENCES meters(id) ON DELETE CASCADE,
    allocation_type VARCHAR(50) CHECK (allocation_type IN ('direct', 'percentage', 'calculated')),
    allocation_value DECIMAL(5,2) CHECK (allocation_value >= 0 AND allocation_value <= 100),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(household_id, meter_id)
);

-- System settings - key-value store for global configuration
CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Users table - for future authentication and authorization
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    role VARCHAR(50) DEFAULT 'viewer' CHECK (role IN ('admin', 'editor', 'viewer')),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Audit log - track changes to configuration
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    record_id VARCHAR(100) NOT NULL,
    action VARCHAR(20) NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    old_data JSONB,
    new_data JSONB,
    user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_meters_type ON meters(meter_type);
CREATE INDEX IF NOT EXISTS idx_meters_category ON meters(category);
CREATE INDEX IF NOT EXISTS idx_meters_active ON meters(active);
CREATE INDEX IF NOT EXISTS idx_household_meters_household ON household_meters(household_id);
CREATE INDEX IF NOT EXISTS idx_household_meters_meter ON household_meters(meter_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_table_record ON audit_log(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at);

-- Insert default system settings
INSERT INTO settings (key, value, description) VALUES
('gas_conversion', '{"energy_content": 11.504, "z_factor": 0.8885}', 'Gas to energy conversion factors (kWh per m³)')
ON CONFLICT (key) DO NOTHING;

INSERT INTO settings (key, value, description) VALUES
('influxdb', '{"bucket_raw": "lampfi", "bucket_processed": "lampfi_processed"}', 'InfluxDB bucket names')
ON CONFLICT (key) DO NOTHING;

INSERT INTO settings (key, value, description) VALUES
('default_prices', '{"gas": 0.10, "water_cold": 2.50, "water_warm": 5.00, "heat": 100.00, "electricity": 0.30}', 'Default utility prices (EUR)')
ON CONFLICT (key) DO NOTHING;

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers to automatically update updated_at
CREATE TRIGGER update_meters_updated_at BEFORE UPDATE ON meters
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_households_updated_at BEFORE UPDATE ON households
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_settings_updated_at BEFORE UPDATE ON settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions to dagster user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO dagster;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO dagster;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO dagster;
