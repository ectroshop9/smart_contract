import os, time, hashlib, json, psycopg2
from psycopg2.extras import RealDictCursor

class Indexer:
    """
    VAULT V4.0 — Blockchain Indexer for PostgreSQL (Supabase)
    - SHA-256 Chaining (previous_hash)
    - PostgreSQL (Supabase) دائم
    - Genesis Block تلقائي
    """
    
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError("❌ DATABASE_URL غير موجود في متغيرات البيئة")
        self._init_db()
    
    def _get_conn(self):
        return psycopg2.connect(self.db_url)
    
    def _init_db(self):
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS blocks (
                        id SERIAL PRIMARY KEY,
                        mac TEXT NOT NULL,
                        previous_hash TEXT NOT NULL,
                        block_hash TEXT UNIQUE NOT NULL,
                        data_json TEXT NOT NULL,
                        signature_b64 TEXT,
                        nonce BIGINT,
                        timestamp BIGINT NOT NULL,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                conn.commit()
            
            # Genesis Block
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM blocks")
                count = cur.fetchone()[0]
                if count == 0:
                    genesis_hash = hashlib.sha256("GENESIS_BLOCK_AL_BARAKA_VAULT".encode()).hexdigest()
                    cur.execute("""
                        INSERT INTO blocks (mac, previous_hash, block_hash, data_json, nonce, timestamp)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        "00:00:00:00:00:00",
                        "0000000000000000000000000000000000000000000000000000000000000000",
                        genesis_hash,
                        json.dumps({"type": "genesis", "system": "al_baraka_vault", "version": "4.0"}),
                        0,
                        int(time.time())
                    ))
                    conn.commit()
    
    def get_last_hash(self, mac):
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT block_hash FROM blocks WHERE mac = %s ORDER BY id DESC LIMIT 1", (mac,))
                row = cur.fetchone()
                return row[0] if row else "0000000000000000000000000000000000000000000000000000000000000000"
    
    def save_to_ledger(self, mac, encrypted_payload, decrypted_data, signature_b64=None, nonce=None):
        ts = int(time.time())
        previous_hash = self.get_last_hash(mac)
        data_json = json.dumps(decrypted_data)
        block_content = f"{mac}|{previous_hash}|{data_json}|{nonce}|{ts}"
        block_hash = hashlib.sha256(block_content.encode()).hexdigest()
        
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO blocks (mac, previous_hash, block_hash, data_json, signature_b64, nonce, timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (mac, previous_hash, block_hash, data_json, signature_b64, nonce, ts))
                block_id = cur.fetchone()[0]
                conn.commit()
        
        return {"block_hash": block_hash, "block_id": block_id, "previous_hash": previous_hash, "timestamp": ts}
    
    def verify_block(self, block_hash):
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM blocks WHERE block_hash = %s", (block_hash,))
                row = cur.fetchone()
                if not row:
                    return {"status": "NOT_FOUND", "verified": False}
                return {
                    "status": "VERIFIED", "verified": True,
                    "block_hash": row["block_hash"], "mac": row["mac"],
                    "previous_hash": row["previous_hash"], "data": json.loads(row["data_json"]),
                    "nonce": row["nonce"], "timestamp": row["timestamp"]
                }
    
    def get_chain(self, mac=None, limit=50):
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                if mac:
                    cur.execute("SELECT block_hash, previous_hash, mac, nonce, timestamp FROM blocks WHERE mac = %s ORDER BY id DESC LIMIT %s", (mac, limit))
                else:
                    cur.execute("SELECT block_hash, previous_hash, mac, nonce, timestamp FROM blocks ORDER BY id DESC LIMIT %s", (limit,))
                rows = cur.fetchall()
                return [{"hash": r[0], "previous": r[1], "mac": r[2], "nonce": r[3], "timestamp": r[4]} for r in rows]
