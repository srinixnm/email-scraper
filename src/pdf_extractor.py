"""
PDF content extraction module.
Handles various PDF formats and extracts structured data from order bills.
Supports both text-based and scanned PDFs (with OCR).
"""

import re
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

import pdfplumber
from PyPDF2 import PdfReader
import pandas as pd

from config import Config

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extract structured data from PDF order bills."""
    
    def __init__(self, ocr_enabled: bool = False):
        """
        Initialize PDF extractor.
        
        Args:
            ocr_enabled: Whether to use OCR for scanned PDFs
        """
        self.ocr_enabled = ocr_enabled or Config.OCR_ENABLED
        if self.ocr_enabled:
            self._setup_ocr()
    
    def _setup_ocr(self):
        """Setup OCR dependencies."""
        try:
            import pytesseract
            from pdf2image import convert_from_path
            from PIL import Image
            
            pytesseract.pytesseract.tesseract_cmd = Config.TESSERACT_CMD
            self.pytesseract = pytesseract
            self.convert_from_path = convert_from_path
            logger.info("OCR support enabled")
        except ImportError as e:
            logger.warning(f"OCR dependencies not available: {e}")
            self.ocr_enabled = False
    
    def extract_text(self, pdf_path: str) -> str:
        """
        Extract all text from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Extracted text content
        """
        text_content = ""
        
        try:
            # Try pdfplumber first (better for tables)
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_content += text + "\n"
            
            # If no text found and OCR is enabled, try OCR
            if not text_content.strip() and self.ocr_enabled:
                logger.info(f"No text found in {pdf_path}, attempting OCR...")
                text_content = self._extract_with_ocr(pdf_path)
            
            return text_content
            
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")
            return ""
    
    def _extract_with_ocr(self, pdf_path: str) -> str:
        """Extract text using OCR for scanned PDFs."""
        try:
            images = self.convert_from_path(pdf_path)
            text_content = ""
            
            for image in images:
                text = self.pytesseract.image_to_string(image)
                text_content += text + "\n"
            
            return text_content
            
        except Exception as e:
            logger.error(f"OCR extraction failed for {pdf_path}: {e}")
            return ""
    
    def extract_order_data(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract structured order data from a PDF.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary containing extracted order information
        """
        text = self.extract_text(pdf_path)
        
        if not text:
            logger.warning(f"No text extracted from {pdf_path}")
            return {"error": "No text could be extracted"}
        
        # Extract common order fields
        order_data = {
            "file_name": Path(pdf_path).name,
            "full_text": text,
            "vendor": self._extract_vendor(text),
            "order_number": self._extract_order_number(text),
            "order_date": self._extract_order_date(text),
            "total_amount": self._extract_total_amount(text),
            "currency": self._extract_currency(text),
            "items": self._extract_items(text, pdf_path),
            "customer_info": self._extract_customer_info(text),
            "shipping_address": self._extract_shipping_address(text),
        }
        
        return order_data
    
    def _extract_vendor(self, text: str) -> str:
        """Extract vendor/supplier name from text."""
        # Look for common patterns at the beginning of documents
        lines = text.split('\n')[:10]  # Check first 10 lines
        
        for line in lines:
            line = line.strip()
            if line and len(line) > 3:
                # Skip generic terms
                if not any(term in line.lower() for term in ['invoice', 'order', 'bill', 'date']):
                    return line
        
        return "Unknown Vendor"
    
    def _extract_order_number(self, text: str) -> str:
        """Extract order/invoice number from text."""
        patterns = [
            r'(?:order|po|purchase order)\s*(?:number|#|no\.?)?\s*[:\-]?\s*([A-Z0-9\-]+)',
            r'(?:invoice|inv)\s*(?:number|#|no\.?)?\s*[:\-]?\s*([A-Z0-9\-]+)',
            r'#\s*([A-Z0-9\-]+)',
            r'\b([A-Z]{2,}\d{4,})\b',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return "Not Found"
    
    def _extract_order_date(self, text: str) -> str:
        """Extract order date from text."""
        patterns = [
            r'(?:order|invoice|date)\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',
            r'(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return "Not Found"
    
    def _extract_total_amount(self, text: str) -> str:
        """Extract total amount from text."""
        patterns = [
            r'(?:total|amount|grand total)\s*[:\-]?\s*[\$€£]?([\d,]+\.?\d*)',
            r'[\$€£]([\d,]+\.?\d*)\b',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Return the largest amount (likely the total)
                amounts = []
                for match in matches:
                    try:
                        amount = float(match.replace(',', ''))
                        amounts.append(amount)
                    except ValueError:
                        continue
                
                if amounts:
                    return f"{max(amounts):.2f}"
        
        return "Not Found"
    
    def _extract_currency(self, text: str) -> str:
        """Extract currency symbol from text."""
        if '$' in text:
            return 'USD'
        elif '€' in text:
            return 'EUR'
        elif '£' in text:
            return 'GBP'
        elif '¥' in text:
            return 'JPY'
        else:
            return 'USD'  # Default
    
    def _extract_items(self, text: str, pdf_path: str) -> List[Dict[str, str]]:
        """Extract line items from PDF using table extraction."""
        items = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    
                    for table in tables:
                        if table and len(table) > 1:
                            parsed_items = self._parse_table_to_items(table)
                            items.extend(parsed_items)
        except Exception as e:
            logger.warning(f"Table extraction failed for {pdf_path}: {e}")
        
        # If no items found via tables, try text parsing
        if not items:
            items = self._parse_items_from_text(text)
        
        return items
    
    def _parse_table_to_items(self, table: List[List]) -> List[Dict[str, str]]:
        """Parse a table into item dictionaries."""
        items = []
        
        if len(table) < 2:
            return items
        
        # Assume first row is header
        header = [str(h).strip().lower() if h else '' for h in table[0]]
        
        # Find column indices
        desc_idx = -1
        qty_idx = -1
        price_idx = -1
        total_idx = -1
        
        for i, col in enumerate(header):
            if any(term in col for term in ['description', 'item', 'product', 'name']):
                desc_idx = i
            elif any(term in col for term in ['qty', 'quantity', 'units']):
                qty_idx = i
            elif any(term in col for term in ['price', 'rate', 'unit price']):
                price_idx = i
            elif any(term in col for term in ['total', 'amount', 'subtotal']):
                total_idx = i
        
        # Extract rows
        for row in table[1:]:
            if not row or all(not cell for cell in row):
                continue
            
            item = {}
            if desc_idx >= 0 and desc_idx < len(row) and row[desc_idx]:
                item['description'] = str(row[desc_idx]).strip()
            if qty_idx >= 0 and qty_idx < len(row) and row[qty_idx]:
                item['quantity'] = str(row[qty_idx]).strip()
            if price_idx >= 0 and price_idx < len(row) and row[price_idx]:
                item['unit_price'] = str(row[price_idx]).strip()
            if total_idx >= 0 and total_idx < len(row) and row[total_idx]:
                item['total_price'] = str(row[total_idx]).strip()
            
            if item:
                items.append(item)
        
        return items
    
    def _parse_items_from_text(self, text: str) -> List[Dict[str, str]]:
        """Parse items from plain text when table extraction fails."""
        items = []
        lines = text.split('\n')
        
        for line in lines:
            # Look for lines with quantities and prices
            match = re.search(r'(\d+)\s+.*?[\$€£]?([\d,]+\.?\d*)', line)
            if match:
                items.append({
                    'description': line.strip(),
                    'quantity': match.group(1),
                    'unit_price': match.group(2)
                })
        
        return items[:20]  # Limit to prevent excessive data
    
    def _extract_customer_info(self, text: str) -> str:
        """Extract customer information from text."""
        patterns = [
            r'(?:bill to|customer|client)\s*[:\-]?(.*?)(?:ship to|address|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()[:200]
        
        return "Not Found"
    
    def _extract_shipping_address(self, text: str) -> str:
        """Extract shipping address from text."""
        patterns = [
            r'(?:ship to|shipping|delivery)\s*[:\-]?(.*?)(?:terms|payment|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()[:200]
        
        return "Not Found"
