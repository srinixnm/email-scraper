"""
PDF Extractor module for extracting content from PDF files.
Handles various PDF formats including scanned documents with OCR support.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

import pdfplumber
import PyPDF2

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extract structured data from PDF files."""
    
    def __init__(self, config):
        self.config = config
        self.supported_extensions = ['.pdf']
        
    def extract_from_file(self, file_path: str) -> Optional[Dict]:
        """
        Extract data from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary with extracted data or None if failed
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None
        
        if file_path.suffix.lower() not in self.supported_extensions:
            logger.warning(f"Unsupported file type: {file_path.suffix}")
            return None
        
        try:
            logger.info(f"Extracting data from: {file_path.name}")
            
            # Try standard extraction first
            data = self._extract_with_pdfplumber(file_path)
            
            # If no data found and OCR is enabled, try OCR
            if not data or not data.get('line_items'):
                if self.config.use_ocr:
                    logger.info("Standard extraction failed, trying OCR...")
                    data = self._extract_with_ocr(file_path)
                else:
                    logger.warning("No data extracted and OCR is disabled")
            
            # Add metadata
            if data:
                data['source_file'] = file_path.name
                data['extraction_date'] = datetime.now().isoformat()
            
            return data
            
        except Exception as e:
            logger.error(f"Error extracting from {file_path}: {str(e)}")
            return None
    
    def _extract_with_pdfplumber(self, file_path: Path) -> Optional[Dict]:
        """
        Extract data using pdfplumber (best for text-based PDFs).
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary with extracted data
        """
        extracted_data = {
            'vendor': None,
            'invoice_number': None,
            'invoice_date': None,
            'total_amount': None,
            'currency': 'USD',
            'line_items': [],
            'metadata': {}
        }
        
        try:
            with pdfplumber.open(file_path) as pdf:
                all_text = []
                all_tables = []
                
                # Process each page
                for page_num, page in enumerate(pdf.pages):
                    # Extract text
                    text = page.extract_text()
                    if text:
                        all_text.append(text)
                    
                    # Extract tables
                    tables = page.extract_tables()
                    if tables:
                        all_tables.extend(tables)
                
                # Combine all text
                full_text = '\n'.join(all_text)
                
                # Extract header information
                extracted_data.update(self._extract_header_info(full_text))
                
                # Extract line items from tables
                if all_tables:
                    line_items = self._extract_line_items_from_tables(all_tables)
                    if line_items:
                        extracted_data['line_items'] = line_items
                
                # If no tables found, try to extract from text
                if not extracted_data['line_items']:
                    extracted_data['line_items'] = self._extract_line_items_from_text(full_text)
                
                logger.debug(f"Extracted {len(extracted_data['line_items'])} line items")
                
        except Exception as e:
            logger.error(f"Error with pdfplumber extraction: {str(e)}")
        
        return extracted_data
    
    def _extract_with_ocr(self, file_path: Path) -> Optional[Dict]:
        """
        Extract data using OCR (for scanned PDFs).
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary with extracted data
        """
        try:
            import pytesseract
            from PIL import Image
            import fitz  # PyMuPDF
            
            extracted_data = {
                'vendor': None,
                'invoice_number': None,
                'invoice_date': None,
                'total_amount': None,
                'currency': 'USD',
                'line_items': [],
                'metadata': {}
            }
            
            # Open PDF with PyMuPDF
            doc = fitz.open(file_path)
            all_text = []
            
            # Convert each page to image and run OCR
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Higher resolution
                
                # Save to temporary file
                temp_img = file_path.parent / f"temp_page_{page_num}.png"
                pix.save(temp_img)
                
                # Run OCR
                img = Image.open(temp_img)
                text = pytesseract.image_to_string(img, lang=self.config.ocr_language)
                all_text.append(text)
                
                # Clean up temp file
                temp_img.unlink()
            
            doc.close()
            
            # Process OCR text
            full_text = '\n'.join(all_text)
            extracted_data.update(self._extract_header_info(full_text))
            extracted_data['line_items'] = self._extract_line_items_from_text(full_text)
            
            return extracted_data
            
        except ImportError as e:
            logger.error(f"OCR libraries not available: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error with OCR extraction: {str(e)}")
            return None
    
    def _extract_header_info(self, text: str) -> Dict:
        """
        Extract header information (vendor, invoice number, date, total) from text.
        
        Args:
            text: Full text from PDF
            
        Returns:
            Dictionary with header fields
        """
        header_info = {}
        
        # Extract vendor name (usually at the top, capitalized words)
        vendor_patterns = [
            r'^([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){1,3})',  # Company name at start
            r'(?:Invoice|Bill|Order)\s+(?:from|by)?\s*([A-Z][A-Za-z\s]+)',
        ]
        
        for pattern in vendor_patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                header_info['vendor'] = match.group(1).strip()
                break
        
        # Extract invoice number
        invoice_patterns = [
            r'(?:Invoice|INV|Invoice #|Invoice No\.?)[:\s]*([A-Z0-9\-]+)',
            r'Order[:\s]*#?([A-Z0-9\-]+)',
            r'BILL[:\s]*#?([A-Z0-9\-]+)',
        ]
        
        for pattern in invoice_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                header_info['invoice_number'] = match.group(1).strip()
                break
        
        # Extract date
        date_patterns = [
            r'(?:Date|Invoice Date|Order Date)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'(?:Date|Invoice Date|Order Date)[:\s]*(\w+\s+\d{1,2},?\s+\d{4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                header_info['invoice_date'] = match.group(1).strip()
                break
        
        # Extract total amount
        total_patterns = [
            r'(?:Total|Amount Due|Grand Total|Balance Due)[:\s]*\$?([\d,]+\.?\d*)',
            r'\$\s*([\d,]+\.?\d*)\s*(?:total|due)',
        ]
        
        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    header_info['total_amount'] = float(amount_str)
                except ValueError:
                    pass
                break
        
        # Extract currency
        if '$' in text:
            header_info['currency'] = 'USD'
        elif '€' in text or 'EUR' in text:
            header_info['currency'] = 'EUR'
        elif '£' in text or 'GBP' in text:
            header_info['currency'] = 'GBP'
        
        return header_info
    
    def _extract_line_items_from_tables(self, tables: List[List[List[str]]]) -> List[Dict]:
        """
        Extract line items from table structures.
        
        Args:
            tables: List of tables from PDF
            
        Returns:
            List of line item dictionaries
        """
        line_items = []
        
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            # Try to identify header row
            headers = [str(cell).lower() if cell else '' for cell in table[0]]
            
            # Look for common column names
            desc_idx = -1
            qty_idx = -1
            price_idx = -1
            amount_idx = -1
            
            for idx, header in enumerate(headers):
                if any(kw in header for kw in ['description', 'item', 'product', 'name']):
                    desc_idx = idx
                elif any(kw in header for kw in ['qty', 'quantity', 'units']):
                    qty_idx = idx
                elif any(kw in header for kw in ['price', 'unit price', 'rate']):
                    price_idx = idx
                elif any(kw in header for kw in ['amount', 'total', 'subtotal']):
                    amount_idx = idx
            
            # If we found at least description and amount columns
            if desc_idx >= 0 and amount_idx >= 0:
                for row in table[1:]:
                    if len(row) > max(desc_idx, amount_idx):
                        item = {
                            'description': str(row[desc_idx]).strip() if row[desc_idx] else '',
                            'quantity': None,
                            'unit_price': None,
                            'amount': None
                        }
                        
                        # Extract quantity
                        if qty_idx >= 0 and len(row) > qty_idx and row[qty_idx]:
                            try:
                                item['quantity'] = float(str(row[qty_idx]).replace(',', ''))
                            except ValueError:
                                pass
                        
                        # Extract unit price
                        if price_idx >= 0 and len(row) > price_idx and row[price_idx]:
                            try:
                                price_str = str(row[price_idx]).replace('$', '').replace(',', '')
                                item['unit_price'] = float(price_str)
                            except ValueError:
                                pass
                        
                        # Extract amount
                        if amount_idx >= 0 and len(row) > amount_idx and row[amount_idx]:
                            try:
                                amount_str = str(row[amount_idx]).replace('$', '').replace(',', '')
                                item['amount'] = float(amount_str)
                            except ValueError:
                                pass
                        
                        # Only add if we have meaningful data
                        if item['description'] and item['amount']:
                            line_items.append(item)
        
        return line_items
    
    def _extract_line_items_from_text(self, text: str) -> List[Dict]:
        """
        Extract line items from plain text (fallback when no tables).
        
        Args:
            text: Full text from PDF
            
        Returns:
            List of line item dictionaries
        """
        line_items = []
        
        # Pattern for typical line item format
        # Matches: Description ... Quantity x Price = Amount
        patterns = [
            r'(.{20,50}?)\s+(\d+(?:\.\d+)?)\s*[x×]\s*\$?([\d,]+\.?\d*)\s*=?\s*\$?([\d,]+\.?\d*)',
            r'(.{20,50}?)\s+\$?([\d,]+\.?\d*)\s+\$?([\d,]+\.?\d*)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                groups = match.groups()
                
                item = {
                    'description': groups[0].strip(),
                    'quantity': None,
                    'unit_price': None,
                    'amount': None
                }
                
                try:
                    if len(groups) == 4:
                        item['quantity'] = float(groups[1])
                        item['unit_price'] = float(groups[2].replace(',', ''))
                        item['amount'] = float(groups[3].replace(',', ''))
                    elif len(groups) == 3:
                        item['unit_price'] = float(groups[1].replace(',', ''))
                        item['amount'] = float(groups[2].replace(',', ''))
                    
                    if item['description'] and item['amount']:
                        line_items.append(item)
                except ValueError:
                    continue
        
        return line_items
    
    def validate_extraction(self, data: Dict) -> bool:
        """
        Validate that extracted data has minimum required fields.
        
        Args:
            data: Extracted data dictionary
            
        Returns:
            True if valid, False otherwise
        """
        if not data:
            return False
        
        # Must have at least some line items or a total amount
        has_line_items = bool(data.get('line_items'))
        has_total = data.get('total_amount') is not None
        
        return has_line_items or has_total
