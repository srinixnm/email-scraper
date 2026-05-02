# Quick Start Guide

## ✅ Installation Complete!

Your email order scraper is ready to use. Here's what you have:

### 📁 Project Files
```
email-scraper/
├── src/                    # Source code
│   ├── main.py            # Run this file
│   ├── config.py
│   ├── email_handler.py
│   ├── pdf_extractor.py
│   └── excel_exporter.py
├── requirements.txt       # Dependencies (installed ✓)
├── .env.example          # Configuration template
├── README.md             # Full documentation
├── logs/                 # Log files
├── attachments/          # Downloaded PDFs
└── csv_export/           # CSV backups
```

## 🚀 Quick Commands

### Test It Now (Demo Mode)
```bash
cd /workspace/email-scraper
python src/main.py --demo
```

**Output:**
- ✅ `orders_summary.xlsx` - Excel file with sample orders
- ✅ `csv_export/orders_summary.csv` - Order summary
- ✅ `csv_export/line_items.csv` - Line item details
- ✅ `logs/scraper_*.log` - Processing log

### Use With Real Emails

1. **Create configuration file:**
```bash
cp .env.example .env
nano .env  # Edit with your email credentials
```

2. **Edit `.env` with your email:**
```env
EMAIL_HOST=imap.gmail.com
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
```

3. **Run the scraper:**
```bash
python src/main.py
```

## 📊 Sample Output

The demo created:
- **2 sample orders** from different vendors
- **7 line items** total
- **Excel file** with 3 sheets (Summary, Line Items, Statistics)
- **CSV files** for easy integration

## 🔧 Common Tasks

### Process last 30 days:
```bash
python src/main.py --days 30
```

### Custom output filename:
```bash
python src/main.py --output january_orders.xlsx
```

### Enable OCR for scanned PDFs:
Edit `.env`:
```env
USE_OCR=true
```

## 📧 Email Setup (Gmail Example)

1. Go to Google Account Settings
2. Enable 2-Factor Authentication
3. Create App Password: https://myaccount.google.com/apppasswords
4. Use the 16-character app password in `.env`

## ❓ Troubleshooting

**No emails found?**
- Check keywords in `.env`
- Verify IMAP folder name
- Increase SEARCH_DAYS

**PDF extraction failing?**
- Check logs in `logs/` folder
- Try enabling OCR for scanned PDFs
- Some formats may need custom patterns

**Connection errors?**
- Verify email credentials
- Check firewall settings
- For Gmail: Use App Password, not regular password

## 📖 Next Steps

1. ✅ Run demo mode to see it working
2. 📧 Set up your email in `.env`
3. 🔄 Run with real emails
4. 📊 Review the Excel output
5. ⚙️ Customize keywords and settings as needed

---

**Need help?** Check `README.md` for full documentation or review the logs in `logs/` folder.
