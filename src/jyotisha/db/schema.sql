-- SQLite Schema for Jyotisha MCP (Standalone version)

CREATE TABLE IF NOT EXISTS charts (
    id TEXT PRIMARY KEY,
    name TEXT,
    datetime_utc TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    location_name TEXT,
    ayanamsha TEXT,
    house_system TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chart_cache (
    chart_id TEXT PRIMARY KEY REFERENCES charts(id),
    chart_json TEXT NOT NULL,
    computed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rules (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    category TEXT,
    school TEXT,
    dsl_definition TEXT NOT NULL,
    active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS predictions (
    id TEXT PRIMARY KEY,
    chart_id TEXT REFERENCES charts(id),
    question TEXT NOT NULL,
    consensus_json TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS remedies (
    id TEXT PRIMARY KEY,
    affliction_type TEXT,
    category TEXT,
    description TEXT NOT NULL,
    source_ref TEXT,
    confidence REAL
);
