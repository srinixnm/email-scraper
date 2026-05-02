# Email Order Scraper

A Python application that automatically reads emails, extracts PDF order bills/invoices, and exports the data to Excel spreadsheets. Perfect for companies handling high volumes of purchase orders daily.

## Features

- 📧 **Email Integration** - Connects to any IMAP email server (Gmail, Outlook, etc.)
- 🔍 **Smart Filtering** - Automatically detects order-related emails using customizable keywords
- 📄 **PDF Processing** - Extracts data from bills/invoices in various formats
- 🔎 **OCR Support** - Optional OCR for scanned PDFs
- 📊 **Flexible Extraction** - Handles different vendor formats using:
  - Table detection
  - Pattern matching
  - Keyword search
- 📈 **Excel Export** - Multi-sheet spreadsheets with:
  - Order Summary
  - Line Items Detail
  - Processing Statistics
- 💾 **CSV Backup** - Additional CSV exports for easy integration with other systems

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

### Step 1: Clone or Download

```bash
cd email-scraper
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure Email Access

Copy the example environment file and edit it:

```bash
cp .env.example .env
```

Edit `.env` with your email credentials:

```env
# Email Configuration
EMAIL_HOST=imap.gmail.com
EMAIL_PORT=993
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# Email Settings
IMAP_FOLDER=INBOX
SEARCH_DAYS=7
KEYWORDS=order,invoice,bill,purchase,receipt

# Output Settings
OUTPUT_EXCEL_FILE=orders_summary.xlsx
CSV_EXPORT_DIR=csv_export
ATTACHMENTS_DIR=attachments
LOGS_DIR=logs

# OCR Settings (optional)
USE_OCR=false
OCR_LANGUAGE=eng
```

### Email Security Notes

**For Gmail:**
1. Enable 2-Factor Authentication
2. Generate an App Password: https://myaccount.google.com/apppasswords
3. Use the App Password in `.env` (not your regular password)

**For Outlook/Office 365:**
- Use your regular password or app password if MFA is enabled
- IMAP server: `outlook.office365.com`

## Usage

### Demo Mode (Recommended for Testing)

Run without connecting to email to test the application:

```bash
python src/main.py --demo
```

This will:
- Generate sample order data
- Create an Excel file with demo orders
- Export CSV backups
- Show you the expected output format

### Live Mode (Real Emails)

Process actual emails from your inbox:

```bash
python src/main.py
```

### Command Line Options

```bash
# Process last 30 days instead of default 7
python src/main.py --days 30

# Specify custom output filename
python src/main.py --output monthly_orders.xlsx

# Combine options
python src/main.py --demo --days 14 --output test_output.xlsx
```

## Output Files

After running, you'll get:

### Excel File (`orders_summary.xlsx`)
- **Order Summary Sheet**: All orders with vendor, invoice number, date, total
- **Line Items Sheet**: Detailed breakdown of each item in every order
- **Processing Summary**: Statistics and vendor breakdown

### CSV Files (`csv_export/`)
- `orders_summary.csv`: Order-level data
- `line_items.csv`: Individual line items

### Attachments (`attachments/`)
- All downloaded PDF invoices are saved here for reference

### Logs (`logs/`)
- Detailed processing logs for debugging

## How It Works

1. **Connect** to your email server via IMAP
2. **Search** for emails containing order-related keywords
3. **Download** PDF attachments from matching emails
4. **Extract** data using multiple methods:
   - Table structure detection
   - Text pattern matching
   - OCR (if enabled for scanned PDFs)
5. **Validate** extracted data for completeness
6. **Export** to Excel and CSV formats
7. **Mark** processed emails as read

## Handling Different PDF Formats

The application uses intelligent extraction to handle various invoice formats:

- **Structured PDFs**: Extracts tables directly
- **Text-based PDFs**: Uses pattern matching for key fields
- **Scanned PDFs**: OCR extraction (requires Tesseract installation)

### Common Fields Extracted

- Vendor/Supplier name
- Invoice/Order number
- Invoice date
- Total amount
- Currency
- Line items (description, quantity, unit price, amount)

## Troubleshooting

### "Configuration validation failed"
- Ensure `.env` file exists with valid email credentials
- Check that EMAIL_USERNAME and EMAIL_PASSWORD are set

### "Failed to connect to email server"
- Verify IMAP settings for your email provider
- Check firewall/network connectivity
- For Gmail, ensure "Less secure app access" or App Password is configured

### "No data extracted from PDF"
- The PDF might be a scanned image (enable OCR)
- The format might not match expected patterns
- Check logs for detailed extraction errors

### OCR Not Working
Install Tesseract OCR:

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

## Customization

### Add More Keywords

Edit `.env` to include more search terms:

```env
KEYWORDS=order,invoice,bill,purchase,receipt,po,purchase-order
```

### Adjust Search Period

```env
SEARCH_DAYS=30  # Look back 30 days instead of 7
```

### Enable OCR

```env
USE_OCR=true
```

## Security Best Practices

1. **Never commit `.env`** to version control
2. **Use App Passwords** instead of regular passwords
3. **Enable 2FA** on your email account
4. **Review logs** regularly for unusual activity
5. **Limit email access** to a dedicated folder if possible

## License

This project is provided as-is for business use.

## Support

For issues or questions:
1. Check the logs in `logs/` directory
2. Run in demo mode first to verify installation
3. Review troubleshooting section above

---

**Ready to automate your order processing? Start with demo mode and scale up!** 🚀
