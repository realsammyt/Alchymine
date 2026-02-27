-- ============================================================================
-- Alchymine Database Initialization
-- This script runs on first PostgreSQL container start via
-- /docker-entrypoint-initdb.d/
-- ============================================================================

-- Ensure the alchymine database exists (it is created by POSTGRES_DB env var,
-- but this handles the case where the container is reused with existing data)
SELECT 'CREATE DATABASE alchymine'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'alchymine')\gexec

-- Connect to the alchymine database
\c alchymine

-- ─── Extensions ──────────────────────────────────────────────────────────
-- UUID generation for primary keys
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Cryptographic functions for encryption at rest
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Trigram similarity for fuzzy text search
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ─── Schemas ─────────────────────────────────────────────────────────────
-- Public schema (default) — general application data
-- Already exists by default, but be explicit
CREATE SCHEMA IF NOT EXISTS public;
COMMENT ON SCHEMA public IS 'General application data: users, profiles, sessions, content';

-- Financial schema — isolated for wealth/financial data
-- Per ADR: "Financial data classified as Sensitive — encrypted, isolated, never sent to LLM"
CREATE SCHEMA IF NOT EXISTS financial;
COMMENT ON SCHEMA financial IS 'Isolated schema for wealth and financial data — encrypted, never exposed to LLM';

-- ─── Roles & Permissions ─────────────────────────────────────────────────
-- Application role for general access (used by the API)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'alchymine_app') THEN
        CREATE ROLE alchymine_app LOGIN;
    END IF;
END
$$;

-- Financial role with elevated access to the financial schema
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'alchymine_financial') THEN
        CREATE ROLE alchymine_financial LOGIN;
    END IF;
END
$$;

-- Grant permissions on public schema
GRANT USAGE ON SCHEMA public TO alchymine_app;
GRANT CREATE ON SCHEMA public TO alchymine_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO alchymine_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO alchymine_app;

-- Grant permissions on financial schema (restricted)
GRANT USAGE ON SCHEMA financial TO alchymine_financial;
GRANT CREATE ON SCHEMA financial TO alchymine_financial;
ALTER DEFAULT PRIVILEGES IN SCHEMA financial
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO alchymine_financial;
ALTER DEFAULT PRIVILEGES IN SCHEMA financial
    GRANT USAGE, SELECT ON SEQUENCES TO alchymine_financial;

-- The main alchymine user (from POSTGRES_USER) gets both roles
GRANT alchymine_app TO alchymine;
GRANT alchymine_financial TO alchymine;

-- ─── Search Path ─────────────────────────────────────────────────────────
-- Set the default search path so public is found first
ALTER DATABASE alchymine SET search_path TO public, financial;

-- ─── Audit Configuration ─────────────────────────────────────────────────
-- Create an updated_at trigger function for use by all tables
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_updated_at_column()
    IS 'Automatically sets updated_at to current timestamp on row update';

-- ─── Verification ────────────────────────────────────────────────────────
DO $$
BEGIN
    RAISE NOTICE 'Alchymine database initialization complete';
    RAISE NOTICE 'Schemas: public, financial';
    RAISE NOTICE 'Extensions: uuid-ossp, pgcrypto, pg_trgm';
    RAISE NOTICE 'Roles: alchymine_app, alchymine_financial';
END
$$;
