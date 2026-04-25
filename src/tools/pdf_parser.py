import fitz  # PyMuPDF
from src.utils.logger import logger

class PDFParser:
    @staticmethod
    def extract_text_from_pdf(pdf_path: str) -> str:
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except Exception as e:
            logger.error(f"Error parsing PDF {pdf_path}: {e}")
            return ""

    @staticmethod
    def extract_text_from_stream(pdf_stream) -> str:
        try:
            doc = fitz.open(stream=pdf_stream, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except Exception as e:
            logger.error(f"Error parsing PDF stream: {e}")
            return ""
