"""
Main application entry point for email order scraper.
Processes emails, extracts PDF attachments, and exports to Excel.
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from config import Config, config
from email_handler import EmailHandler
from pdf_extractor import PDFExtractor
from excel_exporter import ExcelExporter


def setup_logging(config):
    """Configure application logging."""
    log_file = config.logs_dir / f"scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.DEBUG if config.debug_mode else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)


def process_emails(config, logger):
    """
    Process emails and extract order data from PDF attachments.
    
    Args:
        config: Application configuration
        logger: Logger instance
        
    Returns:
        List of extracted order data
    """
    orders_data = []
    
    # Initialize components
    email_handler = EmailHandler(config)
    pdf_extractor = PDFExtractor(config)
    
    try:
        # Connect to email server
        logger.info("Connecting to email server...")
        if not email_handler.connect():
            logger.error("Failed to connect to email server")
            return orders_data
        
        # Search for relevant emails
        logger.info(f"Searching for emails from the last {config.search_days} days...")
        email_ids = email_handler.search_emails()
        
        if not email_ids:
            logger.info("No matching emails found")
            return orders_data
        
        logger.info(f"Found {len(email_ids)} emails to process")
        
        # Process each email
        processed_count = 0
        for email_id in email_ids:
            logger.debug(f"Processing email {email_id}")
            
            # Fetch email
            email_data = email_handler.fetch_email(email_id)
            if not email_data:
                logger.warning(f"Failed to fetch email {email_id}")
                continue
            
            # Look for PDF attachments
            pdf_attachments = [
                att for att in email_data.get('attachments', [])
                if att['filename'].lower().endswith('.pdf')
            ]
            
            if not pdf_attachments:
                logger.debug(f"No PDF attachments in email {email_id}")
                continue
            
            logger.info(f"Found {len(pdf_attachments)} PDF attachment(s) in email {email_id}")
            
            # Extract data from each PDF
            for attachment in pdf_attachments:
                logger.info(f"Extracting data from: {attachment['filename']}")
                
                extracted_data = pdf_extractor.extract_from_file(attachment['path'])
                
                if extracted_data and pdf_extractor.validate_extraction(extracted_data):
                    # Add email metadata
                    extracted_data['id'] = f"EMAIL-{email_id}"
                    extracted_data['email_from'] = email_data['from']
                    extracted_data['email_subject'] = email_data['subject']
                    
                    orders_data.append(extracted_data)
                    logger.info(f"Successfully extracted data from {attachment['filename']}")
                else:
                    logger.warning(f"Failed to extract valid data from {attachment['filename']}")
            
            # Mark email as processed
            email_handler.mark_as_read(email_id)
            processed_count += 1
            
            # Progress indicator
            if processed_count % 10 == 0:
                logger.info(f"Processed {processed_count}/{len(email_ids)} emails")
        
        logger.info(f"Completed processing {processed_count} emails")
        logger.info(f"Extracted {len(orders_data)} orders with valid data")
        
    except Exception as e:
        logger.error(f"Error during email processing: {str(e)}", exc_info=True)
    
    finally:
        email_handler.disconnect()
    
    return orders_data


def run_demo_mode(config, logger):
    """
    Run in demo mode with sample data (no email connection).
    
    Args:
        config: Application configuration
        logger: Logger instance
        
    Returns:
        List of demo order data
    """
    logger.info("Running in DEMO mode with sample data...")
    
    exporter = ExcelExporter(config)
    demo_orders = exporter.create_demo_data()
    
    return demo_orders


def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(
        description='Email Order Scraper - Extract order data from emails and PDFs'
    )
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run in demo mode with sample data (no email connection)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=None,
        help='Number of days to search back (overrides config)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output Excel filename (overrides config)'
    )
    
    args = parser.parse_args()
    
    # Initialize configuration
    config_instance = config
    
    # Override config if arguments provided
    if args.days:
        config_instance.search_days = args.days
    
    # Setup logging
    logger = setup_logging(config_instance)
    logger.info("=" * 60)
    logger.info("Email Order Scraper Started")
    logger.info("=" * 60)
    logger.info(f"Configuration: {config_instance}")
    
    try:
        # Process based on mode
        if args.demo:
            orders_data = run_demo_mode(config_instance, logger)
        else:
            # Validate configuration for live mode
            is_valid, errors = config_instance.validate()
            if not is_valid:
                logger.error("Configuration validation failed:")
                for error in errors:
                    logger.error(f"  - {error}")
                logger.error("\nPlease create a .env file with your email credentials.")
                logger.error("Copy .env.example to .env and update the values.")
                sys.exit(1)
            
            orders_data = process_emails(config_instance, logger)
        
        # Export results
        if orders_data:
            exporter = ExcelExporter(config_instance)
            output_file = args.output if args.output else config_instance.output_excel_file
            
            result_path = exporter.export_to_excel(orders_data, output_file)
            
            if result_path:
                logger.info("=" * 60)
                logger.info("PROCESSING COMPLETE")
                logger.info("=" * 60)
                logger.info(f"Orders processed: {len(orders_data)}")
                logger.info(f"Total line items: {sum(len(o.get('line_items', [])) for o in orders_data)}")
                logger.info(f"Excel file: {result_path}")
                logger.info(f"CSV files: {config_instance.csv_export_dir}")
                logger.info("=" * 60)
            else:
                logger.error("Failed to export data")
                sys.exit(1)
        else:
            logger.info("No order data to export")
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
