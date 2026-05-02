#!/usr/bin/env python3
"""
Email Order Scraper - Main Application

This application reads emails, identifies order-related messages with PDF attachments,
extracts content from PDF bills/invoices, and exports the data to Excel spreadsheets.

Usage:
    python main.py [--config PATH] [--output PATH] [--no-ocr] [--debug]
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from email_handler import EmailHandler
from pdf_extractor import PDFExtractor
from excel_exporter import ExcelExporter


def setup_logging(debug: bool = False):
    """Configure application logging."""
    level = logging.DEBUG if debug else logging.INFO
    
    # Create logs directory
    log_dir = Config.BASE_DIR / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / f'scraper_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)


def process_pdfs(pdf_paths: List[Path], extractor: PDFExtractor, 
                exporter: ExcelExporter, email_info: dict = None) -> int:
    """
    Process a list of PDF files and add extracted data to exporter.
    
    Args:
        pdf_paths: List of PDF file paths to process
        extractor: PDFExtractor instance
        exporter: ExcelExporter instance
        email_info: Optional email metadata
        
    Returns:
        Number of successfully processed PDFs
    """
    logger = logging.getLogger(__name__)
    success_count = 0
    
    for pdf_path in pdf_paths:
        try:
            logger.info(f"Processing PDF: {pdf_path.name}")
            
            # Extract order data
            order_data = extractor.extract_order_data(str(pdf_path))
            
            if 'error' not in order_data:
                exporter.add_order(order_data, email_info)
                exporter.increment_summary('pdfs_processed')
                success_count += 1
                
                logger.info(
                    f"Extracted order from {pdf_path.name}: "
                    f"Vendor={order_data.get('vendor', 'N/A')}, "
                    f"Order#={order_data.get('order_number', 'N/A')}, "
                    f"Total={order_data.get('total_amount', 'N/A')} {order_data.get('currency', '')}"
                )
            else:
                logger.warning(f"Failed to extract data from {pdf_path.name}: {order_data.get('error')}")
                exporter.increment_summary('errors')
                
        except Exception as e:
            logger.error(f"Error processing {pdf_path.name}: {e}")
            exporter.increment_summary('errors')
    
    return success_count


def run_scraper(output_path: Optional[str] = None, demo_mode: bool = False):
    """
    Run the email scraper application.
    
    Args:
        output_path: Optional custom output path for Excel file
        demo_mode: If True, run in demo mode without connecting to email
    """
    logger = setup_logging()
    logger.info("=" * 60)
    logger.info("Email Order Scraper Started")
    logger.info("=" * 60)
    
    start_time = datetime.now()
    
    # Validate configuration
    if not demo_mode:
        try:
            Config.validate()
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            logger.error("Please copy .env.example to .env and configure your email settings")
            return False
    
    # Initialize components
    email_handler = EmailHandler()
    pdf_extractor = PDFExtractor()
    
    # Set output path
    if output_path is None:
        output_path = Config.get_output_path(Config.OUTPUT_EXCEL_FILE)
    else:
        output_path = Path(output_path)
    
    exporter = ExcelExporter(str(output_path))
    
    if demo_mode:
        logger.info("Running in DEMO mode - skipping email connection")
        logger.info("Create a .env file with your email credentials to process real emails")
        
        # Demo with sample data
        demo_orders = [
            {
                'file_name': 'demo_invoice_001.pdf',
                'vendor': 'ABC Supplies Inc.',
                'order_number': 'PO-2024-001',
                'order_date': '01/15/2024',
                'total_amount': '1250.00',
                'currency': 'USD',
                'items': [
                    {'description': 'Office Chairs', 'quantity': '10', 'unit_price': '75.00', 'total_price': '750.00'},
                    {'description': 'Desk Lamps', 'quantity': '25', 'unit_price': '20.00', 'total_price': '500.00'},
                ],
                'customer_info': 'XYZ Company',
                'shipping_address': '123 Business St, City, State 12345',
            },
            {
                'file_name': 'demo_invoice_002.pdf',
                'vendor': 'Tech Parts Ltd.',
                'order_number': 'INV-2024-042',
                'order_date': '01/16/2024',
                'total_amount': '3450.50',
                'currency': 'USD',
                'items': [
                    {'description': 'Laptop Stand', 'quantity': '15', 'unit_price': '45.50', 'total_price': '682.50'},
                    {'description': 'Wireless Mouse', 'quantity': '50', 'unit_price': '25.00', 'total_price': '1250.00'},
                    {'description': 'Keyboard', 'quantity': '30', 'unit_price': '50.60', 'total_price': '1518.00'},
                ],
                'customer_info': 'XYZ Company',
                'shipping_address': '123 Business St, City, State 12345',
            },
        ]
        
        for order in demo_orders:
            exporter.add_order(order, {
                'from': 'vendor@example.com',
                'subject': f'Invoice - {order["order_number"]}',
                'date': datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000'),
            })
            exporter.increment_summary('pdfs_processed')
        
        exporter.increment_summary('order_emails', 2)
        exporter.increment_summary('total_emails', 2)
        
    else:
        # Connect to email server
        logger.info("Connecting to email server...")
        if not email_handler.connect():
            logger.error("Failed to connect to email server")
            return False
        
        try:
            # Search for emails
            logger.info("Searching for order-related emails...")
            email_ids = email_handler.search_emails()
            
            if not email_ids:
                logger.info("No emails found matching criteria")
            else:
                logger.info(f"Found {len(email_ids)} emails to process")
                exporter.increment_summary('total_emails', len(email_ids))
                
                # Setup directories
                attachments_dir = Config.get_attachments_path()
                
                # Process each email
                order_emails_count = 0
                all_pdf_paths = []
                
                for email_id in email_ids:
                    logger.debug(f"Processing email {email_id}")
                    
                    # Fetch email
                    email_data = email_handler.fetch_email(email_id)
                    
                    if not email_data:
                        continue
                    
                    # Check if order-related
                    if email_data['is_order_related']:
                        order_emails_count += 1
                        logger.info(
                            f"Order-related email #{order_emails_count}: "
                            f"From={email_data['from']}, Subject={email_data['subject'][:50]}"
                        )
                        
                        # Download attachments
                        if email_data['attachments']:
                            saved_files = email_handler.download_attachments(
                                email_data, attachments_dir
                            )
                            
                            # Filter for PDFs
                            pdf_files = [f for f in saved_files if f.suffix.lower() == '.pdf']
                            
                            if pdf_files:
                                all_pdf_paths.extend([(pdf, email_data) for pdf in pdf_files])
                        
                        # Mark as processed (optional)
                        # email_handler.mark_as_read(email_id)
                        # email_handler.move_to_folder(email_id, Config.PROCESSED_FOLDER)
                    
                    exporter.increment_summary('order_emails', 1 if email_data['is_order_related'] else 0)
                
                # Process all collected PDFs
                logger.info(f"Processing {len(all_pdf_paths)} PDF attachments...")
                for pdf_path, email_data in all_pdf_paths:
                    process_pdfs([pdf_path], pdf_extractor, exporter, email_data)
        
        finally:
            # Disconnect from email server
            email_handler.disconnect()
    
    # Set processing times
    end_time = datetime.now()
    exporter.set_processing_times(start_time, end_time)
    
    # Export to Excel
    logger.info("Exporting data to Excel...")
    if exporter.export():
        logger.info(f"Successfully exported to: {output_path}")
        
        # Also export CSV backup
        csv_dir = Config.BASE_DIR / 'csv_export'
        csv_files = exporter.export_to_csv(csv_dir)
        if csv_files:
            logger.info(f"CSV backups saved to: {csv_dir}")
    
    # Print summary
    logger.info("=" * 60)
    logger.info("PROCESSING SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total Emails Processed: {exporter.processing_summary['total_emails']}")
    logger.info(f"Order-Related Emails: {exporter.processing_summary['order_emails']}")
    logger.info(f"PDFs Processed: {exporter.processing_summary['pdfs_processed']}")
    logger.info(f"Orders Extracted: {len(exporter.all_orders)}")
    logger.info(f"Line Items Extracted: {len(exporter.all_items)}")
    logger.info(f"Errors: {exporter.processing_summary['errors']}")
    logger.info(f"Processing Time: {end_time - start_time}")
    logger.info("=" * 60)
    logger.info("Email Order Scraper Completed")
    logger.info("=" * 60)
    
    return True


def main():
    """Main entry point with command-line argument parsing."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Email Order Scraper - Extract order data from email PDF attachments'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Custom output path for Excel file'
    )
    parser.add_argument(
        '--demo', '-d',
        action='store_true',
        help='Run in demo mode without connecting to email'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    try:
        success = run_scraper(
            output_path=args.output,
            demo_mode=args.demo
        )
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
