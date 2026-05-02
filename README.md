# Email Order Scraper

A Python application that automatically reads emails, identifies order-related messages with PDF attachments (bills, invoices, purchase orders), extracts content from various PDF formats, and exports the data to organized Excel spreadsheets.

## Features

- **Email Integration**: Connects to IMAP email servers (Gmail, Outlook, etc.)
- **Smart Filtering**: Automatically identifies order-related emails using keywords
- **PDF Processing**: Extracts data from PDF bills/invoices in various formats
- **OCR Support**: Optional OCR for scanned PDF documents
- **Flexible Extraction**: Handles different bill formats from multiple vendors
- **Excel Export**: Creates structured spreadsheets with multiple sheets:
  - Order Summary
  - Line Items
  - Processing Summary
- **CSV Backup**: Exports CSV files for easy data integration
- **Logging**: Comprehensive logging for debugging and auditing

## Project Structure

```
email-scraper/
├── src/
│   ├── main.py           # Main application entry point
│   ├── config.py         # Configuration management
│   ├── email_handler.py  # Email connection and processing
│   ├── pdf_extractor.py  # PDF content extraction
│   └── excel_exporter.py # Excel/CSV export functionality
├── requirements.txt      # Python dependencies
├── .env.example         # Environment variables template
├── README.md            # This file
├── logs/                # Application logs (auto-created)
├── attachments/         # Downloaded PDF attachments (auto-created)
└── csv_export/          # CSV backup files (auto-created)
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- (Optional) Tesseract OCR for scanned PDFs

### Setup Steps

1. **Clone or navigate to the project directory:**
   ```bash
   cd /workspace
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your email credentials:
   ```
   EMAIL_HOST=imap.gmail.com
   EMAIL_PORT=993
   EMAIL_USERNAME=your_email@gmail.com
   EMAIL_PASSWORD=your_app_password
   OUTPUT_EXCEL_FILE=orders_summary.xlsx
   ```

### For Gmail Users

If using Gmail, you need to:
1. Enable 2-Factor Authentication
2. Generate an App Password at: https://myaccount.google.com/apppasswords
3. Use the App Password in your `.env` file

### Optional: OCR Setup

For scanned PDFs, install Tesseract OCR:

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
Download from: https://github.com/tesseract-ocr/tesseract/releases

Then update `.env`:
```
OCR_ENABLED=true
TESSERACT_CMD=/usr/bin/tesseract  # Adjust path for your system
```

## Usage

### Run in Demo Mode (Recommended for Testing)

Test the application without connecting to email:

```bash
python src/main.py --demo
```

This will create a sample Excel file with demo data.

### Run with Real Emails

```bash
python src/main.py
```

### Command-Line Options

```bash
# Basic usage
python src/main.py

# Custom output file
python src/main.py --output custom_orders.xlsx

# Enable debug logging
python src/main.py --debug

# Demo mode (no email connection)
python src/main.py --demo

# Combine options
python src/main.py --demo --debug --output test_output.xlsx
```

## Configuration

Edit the `.env` file to customize:

### Email Settings
- `EMAIL_HOST`: IMAP server (e.g., imap.gmail.com)
- `EMAIL_PORT`: IMAP port (usually 993 for SSL)
- `EMAIL_USERNAME`: Your email address
- `EMAIL_PASSWORD`: Your email password or app password
- `EMAIL_FOLDER`: Folder to check (default: INBOX)
- `UNSEEN_ONLY`: Only process unread emails (true/false)

### Output Settings
- `OUTPUT_EXCEL_FILE`: Name of output Excel file
- `PROCESSED_FOLDER`: Folder to move processed emails
- `ATTACHMENTS_FOLDER`: Where to save PDF attachments

### Processing Settings
- `OCR_ENABLED`: Enable OCR for scanned PDFs (true/false)
- `TESSERACT_CMD`: Path to Tesseract executable

## How It Works

1. **Connect**: Establishes secure IMAP connection to your email
2. **Search**: Finds emails matching order-related criteria
3. **Filter**: Identifies emails with keywords like "order", "invoice", "bill"
4. **Download**: Saves PDF attachments to local folder
5. **Extract**: Parses PDF content using multiple strategies:
   - Direct text extraction
   - Table detection and parsing
   - Pattern matching for key fields
   - OCR (if enabled)
6. **Organize**: Structures data into standardized format
7. **Export**: Creates Excel file with organized data

## Output Format

The generated Excel file contains:

### Sheet 1: Order Summary
- Vendor name
- Order/Invoice number
- Order date
- Total amount
- Currency
- Number of items
- Email sender
- Email subject
- Processing timestamp

### Sheet 2: Line Items
- Order number (linked)
- Vendor
- Item description
- Quantity
- Unit price
- Total price

### Sheet 3: Processing Summary
- Total emails processed
- Order-related emails count
- PDFs processed
- Errors encountered
- Processing timestamps

## Handling Different PDF Formats

The application uses multiple strategies to handle various bill formats:

1. **Table Detection**: Automatically finds and parses tables
2. **Pattern Matching**: Uses regex for common field patterns
3. **Keyword Search**: Locates fields by labels (Order #, Total, etc.)
4. **Fallback Parsing**: Text-based extraction when tables aren't detected

## Troubleshooting

### Connection Issues
- Verify email credentials in `.env`
- Check if IMAP is enabled for your email account
- For Gmail, ensure you're using an App Password, not your regular password

### No Orders Found
- Check email filtering criteria in `config.py`
- Ensure emails contain keywords like "order", "invoice", "bill"
- Try processing unread emails only or all emails

### PDF Extraction Issues
- Some PDFs may be image-only (scanned) - enable OCR
- Complex layouts may require custom extraction rules
- Check logs in `logs/` folder for detailed error messages

### Missing Dependencies
```bash
pip install -r requirements.txt --upgrade
```

## Logs

Application logs are saved in the `logs/` directory with timestamps. Check these for:
- Processing errors
- Email connection issues
- PDF extraction problems
- Performance metrics

## Security Notes

- Never commit your `.env` file to version control
- Use app-specific passwords when possible
- The application only reads emails, doesn't modify them (unless configured)
- Attachments are saved locally for processing

## Extending the Application

To add support for specific vendor formats:

1. Open `src/pdf_extractor.py`
2. Add custom extraction methods in the `PDFExtractor` class
3. Update pattern matching in field extraction methods
4. Test with sample PDFs from that vendor

## License

This project is provided as-is for business use.

## Support

For issues or questions:
1. Check the logs in `logs/` directory
2. Review configuration in `.env`
3. Run with `--debug` flag for detailed output
4. Ensure all dependencies are installed correctly