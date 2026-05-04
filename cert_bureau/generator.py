import json
# سنستخدم مكتبة qrcode لاحقاً عند بناء الحاوية
# import qrcode 

class CertGenerator:
    def __init__(self, template="standard_honey_cert"):
        self.template = template

    def generate_qr_payload(self, tx_hash, device_id, status):
        # صياغة البيانات التي ستظهر عند مسح الـ QR
        payload = {
            "origin": "Algerian Honey (Al-Baraka)",
            "device": device_id,
            "blockchain_ref": tx_hash,
            "quality_status": status
        }
        return json.dumps(payload)

    def create_certificate(self, tx_hash):
        print(f"Generating Digital Certificate for Transaction: {tx_hash}...")
        # هنا يتم استدعاء كود توليد الـ PDF ودمج الـ QR
        return "Certificate_Ready.pdf"

if __name__ == "__main__":
    gen = CertGenerator()
    print(gen.generate_qr_payload("0xABC123", "BEEK-0003", "EXPORT_GRADE"))
