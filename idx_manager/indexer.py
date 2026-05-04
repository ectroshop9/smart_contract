import sqlite3, time, hashlib, os, json

class Indexer:
    """
    VAULT V4.0 — Blockchain Indexer
    - SHA-256 Chaining (previous_hash)
    - SQLite3 WAL Mode
    - Genesis Block تلقائي
    - استعلام عن أي كتلة
    """
    
    def __init__(self, db_path=None):
        if db_path:
            self.db_path = db_path
        else:
            self.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vault_chain.db")
        self._init_db()
    
    def _init_db(self):
        """تهيئة قاعدة البيانات مع Genesis Block"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS blocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mac TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    block_hash TEXT NOT NULL UNIQUE,
                    data_json TEXT NOT NULL,
                    signature_b64 TEXT,
                    nonce INTEGER,
                    timestamp INTEGER NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # إنشاء Genesis Block إذا كانت القاعدة فارغة
            count = conn.execute("SELECT COUNT(*) FROM blocks").fetchone()[0]
            if count == 0:
                genesis_hash = hashlib.sha256("GENESIS_BLOCK_AL_BARAKA_VAULT".encode()).hexdigest()
                conn.execute("""
                    INSERT INTO blocks (mac, previous_hash, block_hash, data_json, nonce, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    "00:00:00:00:00:00",
                    "0000000000000000000000000000000000000000000000000000000000000000",
                    genesis_hash,
                    json.dumps({"type": "genesis", "system": "al_baraka_vault", "version": "4.0"}),
                    0,
                    int(time.time())
                ))
    
    def get_last_hash(self, mac: str) -> str:
        """جلب آخر هاش لجهاز معين"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT block_hash FROM blocks WHERE mac = ? ORDER BY id DESC LIMIT 1",
                (mac,)
            ).fetchone()
            return row[0] if row else "0000000000000000000000000000000000000000000000000000000000000000"
    
    def save_to_ledger(self, mac: str, encrypted_payload: str, decrypted_data: dict, signature_b64: str = None, nonce: int = None) -> dict:
        """
        تخزين كتلة جديدة في السلسلة
        """
        ts = int(time.time())
        previous_hash = self.get_last_hash(mac)
        
        # بناء محتوى الكتلة
        data_json = json.dumps(decrypted_data)
        block_content = f"{mac}|{previous_hash}|{data_json}|{nonce}|{ts}"
        block_hash = hashlib.sha256(block_content.encode()).hexdigest()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO blocks (mac, previous_hash, block_hash, data_json, signature_b64, nonce, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (mac, previous_hash, block_hash, data_json, signature_b64, nonce, ts))
            
            block_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        
        return {
            "block_hash": block_hash,
            "block_id": block_id,
            "previous_hash": previous_hash,
            "timestamp": ts
        }
    
    def verify_block(self, block_hash: str) -> dict:
        """التحقق من وجود وسلامة كتلة"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM blocks WHERE block_hash = ?",
                (block_hash,)
            ).fetchone()
            
            if not row:
                return {"status": "NOT_FOUND", "verified": False}
            
            return {
                "status": "VERIFIED",
                "verified": True,
                "block_hash": row["block_hash"],
                "mac": row["mac"],
                "previous_hash": row["previous_hash"],
                "data": json.loads(row["data_json"]),
                "nonce": row["nonce"],
                "timestamp": row["timestamp"]
            }
    
    def get_chain(self, mac: str = None, limit: int = 50) -> list:
        """استرجاع السلسلة كاملة أو لجهاز معين"""
        with sqlite3.connect(self.db_path) as conn:
            if mac:
                rows = conn.execute(
                    "SELECT block_hash, previous_hash, mac, nonce, timestamp FROM blocks WHERE mac = ? ORDER BY id DESC LIMIT ?",
                    (mac, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT block_hash, previous_hash, mac, nonce, timestamp FROM blocks ORDER BY id DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            
            chain = []
            for row in rows:
                chain.append({
                    "hash": row[0],
                    "previous": row[1],
                    "mac": row[2],
                    "nonce": row[3],
                    "timestamp": row[4]
                })
            return chain
