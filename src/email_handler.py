"""
Email handler module for connecting to IMAP servers and retrieving emails.
Filters and downloads attachments from order-related emails.
"""

import email
import imaplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging
import base64
import quopri

from config import Config

logger = logging.getLogger(__name__)


class EmailHandler:
    """Handle IMAP email connections and message retrieval."""
    
    def __init__(self):
        """Initialize email handler with configuration."""
        self.host = Config.EMAIL_HOST
        self.port = Config.EMAIL_PORT
        self.username = Config.EMAIL_USERNAME
        self.password = Config.EMAIL_PASSWORD
        self.folder = Config.EMAIL_FOLDER
        self.unseen_only = Config.UNSEEN_ONLY
        
        self.mail = None
        self.connected = False
    
    def connect(self) -> bool:
        """
        Connect to the IMAP email server.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info(f"Connecting to {self.host}:{self.port}...")
            
            # Create SSL connection
            self.mail = imaplib.IMAP4_SSL(self.host, self.port)
            
            # Login
            self.mail.login(self.username, self.password)
            logger.info("Successfully logged in")
            
            # Select folder
            status, messages = self.mail.select(self.folder)
            if status != 'OK':
                logger.error(f"Could not select folder {self.folder}")
                return False
            
            logger.info(f"Selected folder: {self.folder}")
            self.connected = True
            return True
            
        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP error: {e}")
            return False
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the email server."""
        if self.mail:
            try:
                self.mail.close()
                self.mail.logout()
                logger.info("Disconnected from email server")
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
            finally:
                self.connected = False
    
    def search_emails(self, criteria: str = None) -> List[str]:
        """
        Search for emails matching criteria.
        
        Args:
            criteria: IMAP search criteria (default: UNSEEN if configured)
            
        Returns:
            List of email IDs
        """
        if not self.connected:
            logger.error("Not connected to email server")
            return []
        
        try:
            if criteria is None:
                if self.unseen_only:
                    criteria = '(UNSEEN)'
                else:
                    criteria = 'ALL'
            
            status, data = self.mail.search(None, criteria)
            
            if status != 'OK':
                logger.error("Search failed")
                return []
            
            email_ids = data[0].split()
            logger.info(f"Found {len(email_ids)} emails matching criteria")
            
            return [eid.decode() for eid in email_ids]
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def fetch_email(self, email_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a single email by ID.
        
        Args:
            email_id: The email ID to fetch
            
        Returns:
            Dictionary containing email data or None if failed
        """
        if not self.connected:
            logger.error("Not connected to email server")
            return None
        
        try:
            status, msg_data = self.mail.fetch(email_id, '(RFC822)')
            
            if status != 'OK':
                logger.error(f"Failed to fetch email {email_id}")
                return None
            
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)
            
            # Parse email data
            email_data = {
                'id': email_id,
                'subject': self._decode_subject(email_message),
                'from': email_message.get('From', ''),
                'to': email_message.get('To', ''),
                'date': email_message.get('Date', ''),
                'body': '',
                'attachments': [],
                'is_order_related': False,
            }
            
            # Extract body and attachments
            self._extract_content(email_message, email_data)
            
            # Check if order-related
            email_data['is_order_related'] = self._is_order_email(email_data)
            
            return email_data
            
        except Exception as e:
            logger.error(f"Error fetching email {email_id}: {e}")
            return None
    
    def _decode_subject(self, email_message) -> str:
        """Decode email subject with proper encoding handling."""
        subject = email_message.get('Subject', '')
        
        try:
            # Try decoding header
            decoded_parts = email.header.decode_header(subject)
            decoded_subject = ''
            
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    decoded_subject += part.decode(encoding or 'utf-8', errors='ignore')
                else:
                    decoded_subject += part
            
            return decoded_subject
        except Exception:
            return subject
    
    def _extract_content(self, email_message, email_data: Dict[str, Any]):
        """
        Extract body content and attachments from email message.
        
        Args:
            email_message: The parsed email message
            email_data: Dictionary to store extracted data
        """
        try:
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get('Content-Disposition', ''))
                    
                    # Handle attachments
                    if 'attachment' in content_disposition.lower():
                        attachment = self._process_attachment(part)
                        if attachment:
                            email_data['attachments'].append(attachment)
                    
                    # Handle text body
                    elif content_type == 'text/plain':
                        try:
                            charset = part.get_content_charset() or 'utf-8'
                            payload = part.get_payload(decode=True)
                            if payload:
                                email_data['body'] += payload.decode(charset, errors='ignore') + '\n'
                        except Exception as e:
                            logger.warning(f"Error decoding text part: {e}")
                    
                    elif content_type == 'text/html':
                        # Could add HTML parsing here if needed
                        pass
                        
            else:
                # Simple email (not multipart)
                content_type = email_message.get_content_type()
                
                if content_type == 'text/plain':
                    try:
                        charset = email_message.get_content_charset() or 'utf-8'
                        payload = email_message.get_payload(decode=True)
                        if payload:
                            email_data['body'] = payload.decode(charset, errors='ignore')
                    except Exception as e:
                        logger.warning(f"Error decoding email body: {e}")
                        
        except Exception as e:
            logger.error(f"Error extracting content: {e}")
    
    def _process_attachment(self, part) -> Optional[Dict[str, Any]]:
        """
        Process an email attachment part.
        
        Args:
            part: The email part containing attachment
            
        Returns:
            Dictionary with attachment info or None
        """
        try:
            filename = part.get_filename()
            
            if not filename:
                # Try to get filename from Content-Disposition header
                disposition = part.get('Content-Disposition', '')
                if 'filename=' in disposition:
                    filename = disposition.split('filename=')[1].strip('";')
            
            if not filename:
                return None
            
            # Decode filename if encoded
            try:
                decoded_parts = email.header.decode_header(filename)
                decoded_filename = ''
                for part_bytes, encoding in decoded_parts:
                    if isinstance(part_bytes, bytes):
                        decoded_filename += part_bytes.decode(encoding or 'utf-8', errors='ignore')
                    else:
                        decoded_filename += part_bytes
                filename = decoded_filename
            except Exception:
                pass
            
            # Get file data
            file_data = part.get_payload(decode=True)
            
            if not file_data:
                return None
            
            attachment = {
                'filename': filename,
                'content_type': part.get_content_type(),
                'data': file_data,
                'size': len(file_data),
            }
            
            logger.debug(f"Processed attachment: {filename} ({attachment['size']} bytes)")
            return attachment
            
        except Exception as e:
            logger.error(f"Error processing attachment: {e}")
            return None
    
    def _is_order_email(self, email_data: Dict[str, Any]) -> bool:
        """
        Check if an email is related to orders/bills/invoices.
        
        Args:
            email_data: The parsed email data
            
        Returns:
            True if order-related, False otherwise
        """
        # Check subject
        subject = email_data['subject'].lower()
        body = email_data['body'].lower()
        
        # Check for order-related keywords
        for keyword in Config.ORDER_KEYWORDS:
            if keyword in subject or keyword in body:
                return True
        
        # Check if has PDF attachments
        for attachment in email_data['attachments']:
            if attachment['filename'].lower().endswith('.pdf'):
                return True
        
        return False
    
    def mark_as_read(self, email_id: str):
        """Mark an email as read."""
        if not self.connected:
            return
        
        try:
            self.mail.store(email_id, '+FLAGS', '\\Seen')
            logger.debug(f"Marked email {email_id} as read")
        except Exception as e:
            logger.error(f"Error marking email as read: {e}")
    
    def move_to_folder(self, email_id: str, folder_name: str):
        """
        Move an email to a different folder.
        
        Args:
            email_id: The email ID to move
            folder_name: Destination folder name
        """
        if not self.connected:
            return
        
        try:
            # Copy to new folder
            self.mail.copy(email_id, folder_name)
            
            # Delete from current folder
            self.mail.store(email_id, '+FLAGS', '\\Deleted')
            self.mail.expunge()
            
            logger.info(f"Moved email {email_id} to {folder_name}")
        except Exception as e:
            logger.error(f"Error moving email: {e}")
    
    def download_attachments(self, email_data: Dict[str, Any], 
                            output_dir: Path) -> List[Path]:
        """
        Download attachments from an email to disk.
        
        Args:
            email_data: The email data containing attachments
            output_dir: Directory to save attachments
            
        Returns:
            List of saved file paths
        """
        saved_files = []
        
        for attachment in email_data['attachments']:
            try:
                file_path = output_dir / attachment['filename']
                
                # Handle duplicate filenames
                counter = 1
                while file_path.exists():
                    stem = file_path.stem
                    suffix = file_path.suffix
                    file_path = output_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
                
                # Write file
                with open(file_path, 'wb') as f:
                    f.write(attachment['data'])
                
                saved_files.append(file_path)
                logger.info(f"Saved attachment: {file_path.name}")
                
            except Exception as e:
                logger.error(f"Error saving attachment {attachment['filename']}: {e}")
        
        return saved_files
