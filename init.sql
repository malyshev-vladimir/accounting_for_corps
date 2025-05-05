-- Table: members
CREATE TABLE IF NOT EXISTS members (
    email VARCHAR PRIMARY KEY,
    first_name VARCHAR,
    last_name VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    is_resident BOOLEAN NOT NULL,
    created_at DATE NOT NULL,
    start_balance NUMERIC(10, 2) DEFAULT 0.00
);

-- Table: title_changes (logs changes to 'title' field)
CREATE TABLE IF NOT EXISTS title_changes (
    id SERIAL PRIMARY KEY,
    member_email VARCHAR NOT NULL REFERENCES members(email) ON DELETE CASCADE,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    new_title VARCHAR NOT NULL,
    changed_by VARCHAR NOT NULL
);

-- Table: residency_changes (logs changes to 'is_resident' field)
CREATE TABLE IF NOT EXISTS residency_changes (
    id SERIAL PRIMARY KEY,
    member_email VARCHAR NOT NULL REFERENCES members(email) ON DELETE CASCADE,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    new_resident BOOLEAN NOT NULL,
    changed_by VARCHAR NOT NULL
);

-- Table: transactions
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    member_email VARCHAR NOT NULL REFERENCES members(email) ON DELETE CASCADE,
    date DATE NOT NULL,
    description TEXT NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    transaction_type INTEGER NOT NULL DEFAULT 1
);

-- Table: transaction_change_log
CREATE TABLE IF NOT EXISTS transaction_change_log (
    id SERIAL PRIMARY KEY,
    transaction_id INTEGER,
    action VARCHAR NOT NULL CHECK (action IN ('create', 'update', 'delete')),
    changed_by VARCHAR NOT NULL,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);