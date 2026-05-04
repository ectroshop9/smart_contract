import os, sys
from flask import Flask, request, jsonify

# استدعاء ملفاتك الأصلية كـ Modules
try:
    from crypto_engine.decryptor import CryptoEngine
    from idx_manager.indexer import Indexer
except ImportError:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from crypto_engine.decryptor import CryptoEngine
    from idx_manager.indexer import Indexer

app = Flask(__name__)

# تشغيل المحركات
crypto = CryptoEngine()
db = Indexer()

@app.route('/ingest', methods=['POST'])
def ingest():
    """
    VAULT V4.0 — Ingestion Endpoint
    تستقبل: {payload (AES-256 مشفر), signature (ECDSA), mac (بصمة), nonce (رقم تسلسلي)}
    ترجع: {status, blockchain_hash, data}
    """
    try:
        content = request.json
        
        if not content:
            return jsonify({"status": "REJECTED", "reason": "Empty request"}), 400
        
        payload = content.get('payload', '')
        signature = content.get('signature', '')
        mac = content.get('mac', 'UNKNOWN')
        nonce = content.get('nonce', None)
        
        # 1. فك التشفير + التحقق من ECDSA + Nonce
        result = crypto.decrypt_data(payload, signature, mac, nonce)
        
        if result['status'] == 'REJECTED':
            return jsonify(result), 403
        
        # 2. تخزين في البلوكشين
        block_info = db.save_to_ledger(mac, payload, result['data'], signature, nonce)
        
        return jsonify({
            "status": "SECURED",
            "blockchain_hash": block_info['block_hash'],
            "block_id": block_info['block_id'],
            "previous_hash": block_info['previous_hash'],
            "data": result['data']
        }), 201
        
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

@app.route('/verify', methods=['GET'])
def verify():
    """التحقق من صحة كتلة"""
    block_hash = request.args.get('hash', '')
    if not block_hash:
        return jsonify({"status": "ERROR", "message": "Missing hash parameter"}), 400
    
    result = db.verify_block(block_hash)
    return jsonify(result), 200 if result['status'] == 'VERIFIED' else 404

@app.route('/chain', methods=['GET'])
def chain():
    """استعراض السلسلة"""
    mac = request.args.get('mac', None)
    limit = int(request.args.get('limit', 50))
    result = db.get_chain(mac, limit)
    return jsonify({"chain": result, "count": len(result)}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ALIVE", "system": "al_baraka_vault", "version": "4.0"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
