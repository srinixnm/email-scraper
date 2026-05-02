"""
Configuration management for email order scraper.
Loads settings from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""
    
    # Email Configuration
    EMAIL_HOST = os.getenv('EMAIL_HOST', 'imap.gmail.com')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', '993'))
    EMAIL_USERNAME = os.getenv('EMAIL_USERNAME', '')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
    
    # Output Configuration
    OUTPUT_EXCEL_FILE = os.getenv('OUTPUT_EXCEL_FILE', 'orders_summary.xlsx')
    PROCESSED_FOLDER = os.getenv('PROCESSED_FOLDER', 'Processed')
    ATTACHMENTS_FOLDER = os.getenv('ATTACHMENTS_FOLDER', 'attachments')
    
    # Processing Settings
    OCR_ENABLED = os.getenv('OCR_ENABLED', 'false').lower() == 'true'
    TESSERACT_CMD = os.getenv('TESSERACT_CMD', '/usr/bin/tesseract')
    
    # Email Search Settings
    EMAIL_FOLDER = os.getenv('EMAIL_FOLDER', 'INBOX')
    UNSEEN_ONLY = os.getenv('UNSEEN_ONLY', 'true').lower() == 'true'
    
    # Order Detection Keywords (case-insensitive)
    ORDER_KEYWORDS = [
        'order', 'invoice', 'bill', 'purchase', 'receipt', 
        'confirmation', 'po', 'purchase order'
    ]
    
    # Base directory for output files
    BASE_DIR = Path(__file__).parent.parent
    
    @classmethod
    def get_output_path(cls, filename):
        """Get full path for output file."""
        return cls.BASE_DIR / filename
    
    @classmethod
    def get_attachments_path(cls):
        """Get full path for attachments folder."""
        path = cls.BASE_DIR / cls.ATTACHMENTS_FOLDER
        path.mkdir(exist_ok=True)
        return path
    
    @classmethod
    def validate(cls):
        """Validate required configuration."""
        if not cls.EMAIL_USERNAME or not cls.EMAIL_PASSWORD:
            raise ValueError(
                "EMAIL_USERNAME and EMAIL_PASSWORD must be set in .env file"
            )
        return True
