-- Table of members
CREATE TABLE IF NOT EXISTS members (
    email VARCHAR PRIMARY KEY,
    first_name VARCHAR,
    last_name VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    is_resident BOOLEAN NOT NULL,
    created_at DATE NOT NULL,
    start_balance NUMERIC(10, 2) DEFAULT 0.0
);

-- History of titles
CREATE TABLE IF NOT EXISTS title_history (
    id SERIAL PRIMARY KEY,
    member_email VARCHAR NOT NULL REFERENCES members(email) ON DELETE CASCADE,
    changed_at DATE NOT NULL,
    title VARCHAR NOT NULL
);

-- History of residency
CREATE TABLE IF NOT EXISTS resident_history (
    id SERIAL PRIMARY KEY,
    member_email VARCHAR NOT NULL REFERENCES members(email) ON DELETE CASCADE,
    changed_at DATE NOT NULL,
    is_resident BOOLEAN NOT NULL
);

-- Table of transactions
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    member_email VARCHAR NOT NULL REFERENCES members(email) ON DELETE CASCADE,
    date DATE NOT NULL,
    description TEXT NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    type INTEGER
);