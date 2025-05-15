-- Table: members
CREATE TABLE IF NOT EXISTS members
(
    email         VARCHAR PRIMARY KEY,
    first_name    VARCHAR,
    last_name     VARCHAR NOT NULL,
    title         VARCHAR NOT NULL,
    is_resident   BOOLEAN NOT NULL,
    created_at    DATE    NOT NULL,
    start_balance NUMERIC(10, 2) DEFAULT 0.00
);

-- Table: title_changes (logs changes to 'title' field)
CREATE TABLE IF NOT EXISTS title_changes
(
    id           SERIAL PRIMARY KEY,
    member_email VARCHAR   NOT NULL REFERENCES members (email) ON DELETE CASCADE,
    changed_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    new_title    VARCHAR   NOT NULL,
    changed_by   VARCHAR   NOT NULL
);

-- Table: residency_changes (logs changes to 'is_resident' field)
CREATE TABLE IF NOT EXISTS residency_changes
(
    id           SERIAL PRIMARY KEY,
    member_email VARCHAR   NOT NULL REFERENCES members (email) ON DELETE CASCADE,
    changed_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    new_resident BOOLEAN   NOT NULL,
    changed_by   VARCHAR   NOT NULL
);

-- Table: transactions
CREATE TABLE IF NOT EXISTS transactions
(
    id               SERIAL PRIMARY KEY,
    member_email     VARCHAR        NOT NULL REFERENCES members (email) ON DELETE CASCADE,
    date             DATE           NOT NULL,
    description      TEXT           NOT NULL,
    amount           NUMERIC(10, 2) NOT NULL,
    transaction_type INTEGER        NOT NULL DEFAULT 1
);

-- Table: transaction_change_log
CREATE TABLE IF NOT EXISTS transaction_change_log
(
    id             SERIAL PRIMARY KEY,
    transaction_id INTEGER,
    action         VARCHAR   NOT NULL CHECK (action IN ('create', 'update', 'delete')),
    changed_by     VARCHAR   NOT NULL,
    changed_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description    TEXT
);

-- Table: reimbursement_items (одна строка заявки на возмещение)
CREATE TABLE IF NOT EXISTS reimbursement_items
(
    id               SERIAL PRIMARY KEY,
    member_email     VARCHAR        NOT NULL REFERENCES members (email) ON DELETE CASCADE,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description      TEXT           NOT NULL,
    date             TEXT           NOT NULL,
    amount           NUMERIC(10, 2) NOT NULL,
    receipt_filename TEXT
);

-- Table: bank_details (последние банковские данные участника)
CREATE TABLE IF NOT EXISTS bank_details
(
    id           SERIAL PRIMARY KEY,
    member_email VARCHAR NOT NULL REFERENCES members (email) ON DELETE CASCADE,
    bank_name    TEXT    NOT NULL,
    iban         TEXT    NOT NULL,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: beverage_reports (один отчёт = одна дата)
CREATE TABLE IF NOT EXISTS beverage_reports
(
    id          SERIAL PRIMARY KEY,
    report_date DATE      NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Table: beverage_report_prices (напитки и цены на момент отчёта)
CREATE TABLE IF NOT EXISTS beverage_report_prices
(
    report_id     INTEGER       NOT NULL REFERENCES beverage_reports (id) ON DELETE CASCADE,
    beverage_name TEXT          NOT NULL,
    price         NUMERIC(6, 2) NOT NULL,
    PRIMARY KEY (report_id, beverage_name)
);

-- Table: beverage_entries (потребление по участникам и мероприятиям)
CREATE TABLE IF NOT EXISTS beverage_entries
(
    id            SERIAL PRIMARY KEY,
    report_id     INTEGER NOT NULL REFERENCES beverage_reports (id) ON DELETE CASCADE,
    is_event      BOOLEAN NOT NULL,
    email         TEXT,
    event_title   TEXT,
    beverage_name TEXT    NOT NULL,
    count         INTEGER NOT NULL CHECK (count >= 0),
    CHECK (
        (is_event = FALSE AND email IS NOT NULL AND event_title IS NULL) OR
        (is_event = TRUE AND email IS NULL AND event_title IS NOT NULL)
        )
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_transactions_email ON transactions (member_email);
CREATE INDEX IF NOT EXISTS idx_title_changes_email ON title_changes (member_email);
CREATE INDEX IF NOT EXISTS idx_residency_changes_email ON residency_changes (member_email);
CREATE INDEX IF NOT EXISTS idx_bank_accounts_email ON bank_details (member_email);
CREATE INDEX IF NOT EXISTS idx_reimbursement_email ON reimbursement_items (member_email);
CREATE INDEX IF NOT EXISTS idx_beverage_entries_report ON beverage_entries (report_id);
CREATE INDEX IF NOT EXISTS idx_beverage_entries_email ON beverage_entries (email);
CREATE INDEX IF NOT EXISTS idx_beverage_prices_report ON beverage_report_prices (report_id);