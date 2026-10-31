class OCRProvider:
    def extract_page(self, image_bytes: bytes) -> str:
        raise NotImplementedError

class DisabledOCRProvider(OCRProvider):
    """Safe default: no external OCR service and no outbound network calls."""
    def extract_page(self, image_bytes: bytes) -> str:
        return ""

ocr_provider = DisabledOCRProvider()
