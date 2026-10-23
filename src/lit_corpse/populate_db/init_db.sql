
CREATE TABLE IF NOT EXISTS lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            start_pos TEXT NOT NULL,
            end_pos TEXT NOT NULL,
            ends_punct INTEGER NOT NULL,
            ends_terminal_punct INTEGER NOT NULL
        );

CREATE INDEX IF NOT EXISTS idx_start_pos ON lines(start_pos);
CREATE INDEX IF NOT EXISTS idx_end_pos ON lines(end_pos);
CREATE INDEX IF NOT EXISTS idx_ends_terminal_punct ON lines(ends_terminal_punct);