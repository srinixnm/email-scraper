"""
Configuration management for email order scraper.
Loads environment variables and provides configuration access.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

class Config:
    """Application configuration manager."""
    
    def __init__(self):
        # Load environment variables from .env file
        env_path = Path(__file__).parent.parent / '.env'
        load_dotenv(env_path)
        
        # Email Configuration
        self.email_host = os.getenv('EMAIL_HOST', 'imap.gmail.com')
        self.email_port = int(os.getenv('EMAIL_PORT', '993'))
        self.email_username = os.getenv('EMAIL_USERNAME', '')
        self.email_password = os.getenv('EMAIL_PASSWORD', '')
        
        # Email Settings
        self.imap_folder = os.getenv('IMAP_FOLDER', 'INBOX')
        self.search_days = int(os.getenv('SEARCH_DAYS', '7'))
        self.keywords = [k.strip() for k in os.getenv('KEYWORDS', 'order,invoice,bill,purchase,receipt').split(',')]
        
        # Output Settings
        self.output_excel_file = os.getenv('OUTPUT_EXCEL_FILE', 'orders_summary.xlsx')
        self.csv_export_dir = Path(os.getenv('CSV_EXPORT_DIR', 'csv_export'))
        self.attachments_dir = Path(os.getenv('ATTACHMENTS_DIR', 'attachments'))
        self.logs_dir = Path(os.getenv('LOGS_DIR', 'logs'))
        
        # OCR Settings
        self.use_ocr = os.getenv('USE_OCR', 'false').lower() == 'true'
        self.ocr_language = os.getenv('OCR_LANGUAGE', 'eng')
        
        # Processing Settings
        self.batch_size = int(os.getenv('BATCH_SIZE', '50'))
        self.debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        for directory in [self.csv_export_dir, self.attachments_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def validate(self):
        """Validate required configuration."""
        errors = []
        
        if not self.email_username:
            errors.append("EMAIL_USERNAME is required")
        
        if not self.email_password:
            errors.append("EMAIL_PASSWORD is required")
        
        return len(errors) == 0, errors
    
    def __str__(self):
        return (f"Config(email_host={self.email_host}, "
                f"search_days={self.search_days}, "
                f"keywords={self.keywords}, "
                f"use_ocr={self.use_ocr})")


# Global config instance
config = Config()
