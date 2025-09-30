import fitz  # PyMuPDF
import json
import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class PDFParser:
    """Utility class for parsing PDF files and extracting text content."""

    def __init__(self):
        pass

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text content from a PDF file.

        Args:
            pdf_path (str): Path to the PDF file

        Returns:
            str: Extracted text content
        """
        try:
            doc = fitz.open(pdf_path)
            text_content = ""

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text_content += page.get_text()
                text_content += "\n\n"  # Add page separator

            doc.close()
            return text_content.strip()

        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {str(e)}")

    def extract_text_from_bytes(self, pdf_bytes: bytes, request_id: Optional[str] = None) -> str:
        """
        Extract text content from PDF bytes.

        Args:
            pdf_bytes (bytes): PDF content as bytes
            request_id (Optional[str]): Request ID for tracking

        Returns:
            str: Extracted text content
        """
        req_id = request_id or "unknown"
        start_time = time.time()

        try:
            logger.info(f"📄 [REQ:{req_id}] Opening PDF document ({len(pdf_bytes)} bytes)...")
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            page_count = len(doc)
            logger.info(f"📄 [REQ:{req_id}] PDF loaded successfully - {page_count} pages found")

            text_content = ""
            for page_num in range(page_count):
                page_start = time.time()
                page = doc.load_page(page_num)
                page_text = page.get_text()
                text_content += page_text
                text_content += "\n\n"  # Add page separator

                page_time = time.time() - page_start
                logger.debug(f"📄 [REQ:{req_id}] Page {page_num + 1}/{page_count} processed in {page_time:.2f}s ({len(page_text)} chars)")

            doc.close()

            total_time = time.time() - start_time
            final_content = text_content.strip()
            logger.info(f"✅ [REQ:{req_id}] PDF text extraction completed in {total_time:.2f}s")
            logger.info(f"📊 [REQ:{req_id}] Extracted {len(final_content)} characters from {page_count} pages")

            return final_content

        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"❌ [REQ:{req_id}] PDF extraction failed after {total_time:.2f}s: {str(e)}")
            raise Exception(f"Error extracting text from PDF bytes: {str(e)}")

    def validate_pdf(self, pdf_path: str) -> bool:
        """
        Validate if the file is a valid PDF.

        Args:
            pdf_path (str): Path to the PDF file

        Returns:
            bool: True if valid PDF, False otherwise
        """
        try:
            doc = fitz.open(pdf_path)
            doc.close()
            return True
        except:
            return False

    def get_pdf_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract metadata from PDF file.

        Args:
            pdf_path (str): Path to the PDF file

        Returns:
            Dict[str, Any]: PDF metadata
        """
        try:
            doc = fitz.open(pdf_path)
            metadata = doc.metadata
            page_count = len(doc)
            doc.close()

            return {
                "page_count": page_count,
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "creator": metadata.get("creator", ""),
                "producer": metadata.get("producer", ""),
                "creation_date": metadata.get("creationDate", ""),
                "modification_date": metadata.get("modDate", "")
            }

        except Exception as e:
            raise Exception(f"Error extracting PDF metadata: {str(e)}")