import os, base64, hashlib, json
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding, hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend

class CryptoEngine:
    """
    VAULT V4.0 — Crypto Engine
    - AES-256-CBC فك تشفير
    - ECDSA التحقق من التوقيع
    - Nonce منع إعادة الإرسال
    - MAC-Lock بصمة الجهاز
    """
    
    def __init__(self):
        # تحميل المفاتيح من بيئة النظام (Hex → Bytes)
        self.aes_key = bytes.fromhex(os.getenv('AES_KEY', 'A1B2C3D4E5F60718293A4B5C6D7E8F900112233445566778899AABBCCddeeff0'))
        self.ecdsa_public_hex = os.getenv('ECDSA_PUBLIC_KEY', '')
        
        # سجل Nonce لكل جهاز (MAC)
        self.nonce_registry = {}
    
    def _verify_ecdsa(self, payload: str, signature_b64: str) -> bool:
        """التحقق من توقيع ECDSA للحمولة"""
        if not self.ecdsa_public_hex:
            return True  # إذا لم يُحدد مفتاح عام، نقبل مؤقتاً
        
        try:
            signature = base64.b64decode(signature_b64)
            public_key = ec.EllipticCurvePublicKey.from_encoded_point(
                ec.SECP256R1(),
                bytes.fromhex(self.ecdsa_public_hex)
            )
            public_key.verify(
                signature,
                payload.encode(),
                ec.ECDSA(hashes.SHA256())
            )
            return True
        except (InvalidSignature, Exception):
            return False
    
    def _check_nonce(self, mac: str, nonce: int) -> bool:
        """التحقق من أن Nonce أكبر من آخر قيمة مسجلة"""
        if mac not in self.nonce_registry:
            self.nonce_registry[mac] = nonce
            return True
        
        if nonce > self.nonce_registry[mac]:
            self.nonce_registry[mac] = nonce
            return True
        
        return False
    
    def decrypt_data(self, encrypted_payload_b64: str, signature_b64: str = None, mac: str = None, nonce: int = None) -> dict:
        """
        فك تشفير الحمولة مع التحقق الكامل
        """
        try:
            # 0. التحقق من Nonce (منع إعادة الإرسال)
            if nonce is not None and mac:
                if not self._check_nonce(mac, nonce):
                    return {
                        "status": "REJECTED",
                        "reason": "NONCE_REPLAY",
                        "error": "Packet replay detected — nonce already used"
                    }
            
            # 1. التحقق من توقيع ECDSA
            if signature_b64 and not self._verify_ecdsa(encrypted_payload_b64, signature_b64):
                return {
                    "status": "REJECTED",
                    "reason": "INVALID_SIGNATURE",
                    "error": "ECDSA signature verification failed"
                }
            
            # 2. فك Base64
            decoded = base64.b64decode(encrypted_payload_b64)
            
            # 3. استخراج IV + Ciphertext
            iv = decoded[:16]
            ciphertext = decoded[16:]
            
            # 4. فك تشفير AES-256-CBC
            cipher = Cipher(algorithms.AES(self.aes_key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            padded_data = decryptor.update(ciphertext) + decryptor.finalize()
            
            # 5. إزالة PKCS7 Padding
            unpadder = padding.PKCS7(128).unpadder()
            plaintext = unpadder.update(padded_data) + unpadder.finalize()
            
            # 6. تحليل JSON الداخلي
            inner_data = json.loads(plaintext.decode('utf-8'))
            
            return {
                "status": "SUCCESS",
                "data": inner_data
            }
            
        except Exception as e:
            return {
                "status": "REJECTED",
                "reason": "DECRYPTION_FAILED",
                "error": str(e)
            }
