"""
Email handler module for connecting to IMAP servers and processing emails.
"""

import email
import imaplib
import logging
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class EmailHandler:
    """Handle email connections and message retrieval."""
    
    def __init__(self, config):
        self.config = config
        self.connection = None
        
    def connect(self) -> bool:
        """Connect to the IMAP server."""
        try:
            logger.info(f"Connecting to {self.config.email_host}:{self.config.email_port}")
            self.connection = imaplib.IMAP4_SSL(self.config.email_host, self.config.email_port)
            
            # Login
            self.connection.login(self.config.email_username, self.config.email_password)
            logger.info("Successfully logged in")
            
            # Select mailbox
            self.connection.select(self.config.imap_folder)
            logger.info(f"Selected mailbox: {self.config.imap_folder}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect: {str(e)}")
            return False
    
    def disconnect(self):
        """Disconnect from the IMAP server."""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
                logger.info("Disconnected from server")
            except Exception as e:
                logger.error(f"Error during disconnect: {str(e)}")
    
    def search_emails(self, days: int = None) -> List[int]:
        """
        Search for emails within the specified number of days.
        
        Args:
            days: Number of days to search back (default from config)
            
        Returns:
            List of email IDs
        """
        if days is None:
            days = self.config.search_days
            
        try:
            # Calculate date threshold
            since_date = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
            
            # Search criteria
            search_criteria = f'(SINCE "{since_date}")'
            
            # Add keyword search if configured
            if self.config.keywords:
                keyword_query = ' OR '.join([f'(BODY "{kw}")' for kw in self.config.keywords])
                search_criteria = f'{search_criteria} ({keyword_query})'
            
            logger.info(f"Searching emails with criteria: {search_criteria}")
            
            status, messages = self.connection.search(None, search_criteria)
            
            if status == 'OK':
                email_ids = [int(msg_id) for msg_id in messages[0].split()]
                logger.info(f"Found {len(email_ids)} emails")
                return email_ids
            else:
                logger.warning("Search returned no results")
                return []
                
        except Exception as e:
            logger.error(f"Error searching emails: {str(e)}")
            return []
    
    def fetch_email(self, email_id: int) -> Optional[Dict]:
        """
        Fetch a single email by ID.
        
        Args:
            email_id: The email ID to fetch
            
        Returns:
            Dictionary with email data or None if failed
        """
        try:
            status, msg_data = self.connection.fetch(str(email_id), '(RFC822)')
            
            if status != 'OK':
                logger.warning(f"Failed to fetch email {email_id}")
                return None
            
            # Parse email
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)
            
            # Extract email data
            email_data = {
                'id': email_id,
                'subject': self._decode_header(email_message.get('Subject', '')),
                'from': self._decode_header(email_message.get('From', '')),
                'to': self._decode_header(email_message.get('To', '')),
                'date': email_message.get('Date', ''),
                'body': '',
                'attachments': []
            }
            
            # Process email parts
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get_content_disposition())
                
                # Get text body
                if content_type == 'text/plain' and 'attachment' not in content_disposition:
                    try:
                        charset = part.get_content_charset() or 'utf-8'
                        email_data['body'] = part.get_payload(decode=True).decode(charset, errors='ignore')
                    except Exception as e:
                        logger.warning(f"Error decoding text part: {str(e)}")
                
                # Get attachments
                elif 'attachment' in content_disposition:
                    attachment = self._process_attachment(part)
                    if attachment:
                        email_data['attachments'].append(attachment)
            
            logger.debug(f"Fetched email {email_id}: {email_data['subject']}")
            return email_data
            
        except Exception as e:
            logger.error(f"Error fetching email {email_id}: {str(e)}")
            return None
    
    def _decode_header(self, header: str) -> str:
        """Decode email header with proper encoding handling."""
        if not header:
            return ''
        
        decoded_parts = email.header.decode_header(header)
        decoded_string = ''
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    decoded_string += part.decode(encoding or 'utf-8', errors='ignore')
                except:
                    decoded_string += part.decode('latin-1', errors='ignore')
            else:
                decoded_string += part
        
        return decoded_string.strip()
    
    def _process_attachment(self, part) -> Optional[Dict]:
        """
        Process an email attachment.
        
        Args:
            part: The email part containing the attachment
            
        Returns:
            Dictionary with attachment data or None if failed
        """
        try:
            filename = part.get_filename()
            
            if not filename:
                return None
            
            filename = self._decode_header(filename)
            
            # Save attachment to disk
            attachment_path = self.config.attachments_dir / filename
            
            with open(attachment_path, 'wb') as f:
                f.write(part.get_payload(decode=True))
            
            logger.debug(f"Saved attachment: {filename}")
            
            return {
                'filename': filename,
                'path': str(attachment_path),
                'content_type': part.get_content_type(),
                'size': len(part.get_payload(decode=True))
            }
            
        except Exception as e:
            logger.error(f"Error processing attachment: {str(e)}")
            return None
    
    def mark_as_read(self, email_id: int):
        """Mark an email as read."""
        try:
            self.connection.store(str(email_id), '+FLAGS', '\\Seen')
            logger.debug(f"Marked email {email_id} as read")
        except Exception as e:
            logger.error(f"Error marking email as read: {str(e)}")
    
    def move_to_folder(self, email_id: int, folder_name: str):
        """Move an email to a different folder."""
        try:
            self.connection.copy(str(email_id), folder_name)
            self.connection.store(str(email_id), '+FLAGS', '\\Deleted')
            self.connection.expunge()
            logger.info(f"Moved email {email_id} to {folder_name}")
        except Exception as e:
            logger.error(f"Error moving email: {str(e)}")
