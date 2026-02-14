import sqlite3
import datetime
import os

class SessionManager:
    """
    The Black Box.
    Manages a local SQLite database to persist audit results immediately.
    Follows 'Zero-Server' policy: Data stays on the M4 Silicon.
    """
    
    def __init__(self, db_name="aura_logs.db"):
        # db is created in the project root
        self.db_path = os.path.join(os.getcwd(), db_name)
        self._init_db()

    def _init_db(self):
        """Creates the table schema if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Schema: Optimized for reporting
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                intern_name TEXT,
                folder_id TEXT,
                file_name TEXT,
                utr TEXT,
                amount REAL,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def log_transaction(self, intern_name: str, folder_id: str, file_name: str, 
                       utr: str, amount: float, status: str):
        """
        Atomic Write Operation.
        Logs a single scan result to the database.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # ISO 8601 Timestamp
        ts = datetime.datetime.now().isoformat()
        
        # Handle None/Null values safely
        safe_utr = str(utr) if utr else "N/A"
        safe_amt = float(amount) if amount else 0.0
        
        cursor.execute('''
            INSERT INTO audit_logs (timestamp, intern_name, folder_id, file_name, utr, amount, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (ts, intern_name, folder_id, file_name, safe_utr, safe_amt, status))
        
        conn.commit()
        conn.close()

    def get_session_stats(self, folder_id: str):
        """Returns a quick summary for the active session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT status, COUNT(*), SUM(amount) 
            FROM audit_logs 
            WHERE folder_id = ? 
            GROUP BY status
        ''', (folder_id,))
        
        rows = cursor.fetchall()
        conn.close()
        return rows