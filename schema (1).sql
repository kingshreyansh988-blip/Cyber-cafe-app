-- Database Schema for Cyber Cafe Management System
-- Compatible with SQLite, PostgreSQL, and Supabase

CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY, -- In SQLite: INTEGER PRIMARY KEY AUTOINCREMENT
    job_no VARCHAR(50) UNIQUE NOT NULL,
    customer_name VARCHAR(150) NOT NULL,
    customer_phone VARCHAR(20) NOT NULL,
    service_category VARCHAR(100) NOT NULL,
    service_details TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'Pending',
    total_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    paid_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    due_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    payment_mode VARCHAR(50) DEFAULT 'Cash',
    payment_status VARCHAR(50) DEFAULT 'Unpaid',
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_jobs_phone ON jobs(customer_phone);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at);
