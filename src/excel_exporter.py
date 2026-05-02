"""
Excel export module for converting extracted order data to spreadsheet format.
Creates structured Excel files with multiple sheets for different data types.
"""

import pandas as pd
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ExcelExporter:
    """Export extracted order data to Excel spreadsheets."""
    
    def __init__(self, output_path: str):
        """
        Initialize Excel exporter.
        
        Args:
            output_path: Path to the output Excel file
        """
        self.output_path = Path(output_path)
        self.all_orders = []
        self.all_items = []
        self.processing_summary = {
            'total_emails': 0,
            'order_emails': 0,
            'pdfs_processed': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None,
        }
    
    def add_order(self, order_data: Dict[str, Any], email_info: Dict[str, Any] = None):
        """
        Add an order to the export queue.
        
        Args:
            order_data: Extracted order data from PDF
            email_info: Optional email metadata
        """
        # Create summary record
        order_record = {
            'vendor': order_data.get('vendor', 'Unknown'),
            'order_number': order_data.get('order_number', 'N/A'),
            'order_date': order_data.get('order_date', 'N/A'),
            'total_amount': order_data.get('total_amount', 'N/A'),
            'currency': order_data.get('currency', 'USD'),
            'file_name': order_data.get('file_name', ''),
            'items_count': len(order_data.get('items', [])),
            'customer_info': order_data.get('customer_info', '')[:100] if order_data.get('customer_info') else '',
            'shipping_address': order_data.get('shipping_address', '')[:100] if order_data.get('shipping_address') else '',
            'processed_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        # Add email info if available
        if email_info:
            order_record['email_from'] = email_info.get('from', '')
            order_record['email_subject'] = email_info.get('subject', '')
            order_record['email_date'] = email_info.get('date', '')
        
        self.all_orders.append(order_record)
        
        # Add items separately
        items = order_data.get('items', [])
        for item in items:
            item_record = {
                'order_number': order_record['order_number'],
                'vendor': order_record['vendor'],
                'description': item.get('description', ''),
                'quantity': item.get('quantity', ''),
                'unit_price': item.get('unit_price', ''),
                'total_price': item.get('total_price', ''),
                'file_name': order_record['file_name'],
            }
            self.all_items.append(item_record)
        
        logger.debug(f"Added order: {order_record['order_number']} ({len(items)} items)")
    
    def increment_summary(self, field: str, count: int = 1):
        """Increment a summary counter."""
        if field in self.processing_summary:
            self.processing_summary[field] += count
    
    def set_processing_times(self, start_time: datetime, end_time: datetime):
        """Set processing start and end times."""
        self.processing_summary['start_time'] = start_time.strftime('%Y-%m-%d %H:%M:%S')
        self.processing_summary['end_time'] = end_time.strftime('%Y-%m-%d %H:%M:%S')
    
    def export(self) -> bool:
        """
        Export all collected data to Excel file.
        
        Returns:
            True if export successful, False otherwise
        """
        try:
            logger.info(f"Exporting {len(self.all_orders)} orders to {self.output_path}")
            
            # Create Excel writer with multiple sheets
            with pd.ExcelWriter(self.output_path, engine='openpyxl') as writer:
                
                # Sheet 1: Order Summary
                if self.all_orders:
                    df_orders = pd.DataFrame(self.all_orders)
                    
                    # Reorder columns for better readability
                    column_order = [
                        'vendor', 'order_number', 'order_date', 'total_amount', 
                        'currency', 'items_count', 'email_from', 'email_subject',
                        'email_date', 'processed_date', 'file_name',
                        'customer_info', 'shipping_address'
                    ]
                    
                    # Only include columns that exist
                    existing_columns = [col for col in column_order if col in df_orders.columns]
                    df_orders = df_orders[existing_columns]
                    
                    df_orders.to_excel(writer, sheet_name='Order Summary', index=False)
                    
                    # Auto-adjust column widths
                    self._adjust_column_width(writer, df_orders, 'Order Summary')
                
                # Sheet 2: Line Items
                if self.all_items:
                    df_items = pd.DataFrame(self.all_items)
                    
                    column_order = [
                        'order_number', 'vendor', 'description', 'quantity',
                        'unit_price', 'total_price', 'file_name'
                    ]
                    
                    existing_columns = [col for col in column_order if col in df_items.columns]
                    df_items = df_items[existing_columns]
                    
                    df_items.to_excel(writer, sheet_name='Line Items', index=False)
                    self._adjust_column_width(writer, df_items, 'Line Items')
                
                # Sheet 3: Processing Summary
                summary_df = pd.DataFrame([
                    {'Metric': 'Total Emails Processed', 'Value': self.processing_summary['total_emails']},
                    {'Metric': 'Order-Related Emails', 'Value': self.processing_summary['order_emails']},
                    {'Metric': 'PDFs Processed', 'Value': self.processing_summary['pdfs_processed']},
                    {'Metric': 'Errors Encountered', 'Value': self.processing_summary['errors']},
                    {'Metric': 'Start Time', 'Value': self.processing_summary['start_time'] or 'N/A'},
                    {'Metric': 'End Time', 'Value': self.processing_summary['end_time'] or 'N/A'},
                    {'Metric': 'Total Orders Extracted', 'Value': len(self.all_orders)},
                    {'Metric': 'Total Line Items', 'Value': len(self.all_items)},
                ])
                
                summary_df.to_excel(writer, sheet_name='Processing Summary', index=False)
                
                # Sheet 4: Raw Data (if needed for debugging)
                # Could add full text content here if needed
            
            logger.info(f"Successfully exported to {self.output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            return False
    
    def _adjust_column_width(self, writer, df, sheet_name):
        """
        Adjust column widths based on content.
        
        Args:
            writer: Excel writer object
            df: DataFrame written to sheet
            sheet_name: Name of the sheet
        """
        try:
            worksheet = writer.sheets[sheet_name]
            
            for idx, col in enumerate(df.columns):
                # Get maximum length of column content
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(str(col))
                )
                
                # Add some padding
                adjusted_width = min(max_length + 2, 50)
                
                # Set column width
                worksheet.column_dimensions[chr(65 + idx)].width = adjusted_width
                
        except Exception as e:
            logger.warning(f"Could not adjust column widths: {e}")
    
    def export_to_csv(self, output_dir: Path) -> List[Path]:
        """
        Export data to separate CSV files.
        
        Args:
            output_dir: Directory to save CSV files
            
        Returns:
            List of created file paths
        """
        saved_files = []
        
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Export orders
            if self.all_orders:
                orders_path = output_dir / 'orders_summary.csv'
                df_orders = pd.DataFrame(self.all_orders)
                df_orders.to_csv(orders_path, index=False)
                saved_files.append(orders_path)
                logger.info(f"Saved orders to {orders_path}")
            
            # Export items
            if self.all_items:
                items_path = output_dir / 'line_items.csv'
                df_items = pd.DataFrame(self.all_items)
                df_items.to_csv(items_path, index=False)
                saved_files.append(items_path)
                logger.info(f"Saved items to {items_path}")
            
            return saved_files
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return []
