# Quick Start Guide

## Installation (5 minutes)

### Step 1: Install Tesseract OCR

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-msa
```

**macOS:**
```bash
brew install tesseract tesseract-lang
```

### Step 2: Install Python Dependencies
```bash
pip install -r requirements.txt
```

## Running the API (1 minute)

```bash
python app.py
```

The API will start at: http://localhost:5000

## Testing (2 minutes)

### Option 1: Web Interface
1. Open `web_client.html` in your browser
2. Upload a receipt image
3. Click "Extract Data"

### Option 2: Python Client
```bash
python test_client.py your_receipt.jpg
```

### Option 3: curl Command
```bash
curl -X POST -F "image=@receipt.jpg" http://localhost:5000/extract
```

## Sample Receipt Format

For best results, your receipt should include:

```
RESTAURANT ABC SDN BHD
123, Jalan Sultan
50000 Kuala Lumpur
Tel: 03-12345678

Receipt No: INV-001
Date: 09/12/2024
Time: 14:30

Nasi Lemak          RM 8.50
Teh Tarik           RM 3.00
                    -------
Subtotal            RM 11.50
Service Charge (10%) RM 1.15
SST (6%)            RM 0.76
                    -------
TOTAL               RM 13.41

Cash                RM 20.00
Change              RM 6.59

Thank you!
```

## Docker Quick Start

```bash
# Build and run
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## Troubleshooting

**Problem:** "Tesseract not found"
**Solution:** Make sure Tesseract is installed and in your PATH

**Problem:** Poor extraction accuracy
**Solution:** Ensure good image quality (clear text, good lighting, no shadows)

**Problem:** CORS errors
**Solution:** API has CORS enabled by default. Check your request headers.

## Next Steps

- Check the full README.md for detailed documentation
- Customize extraction patterns for your specific receipts
- Deploy to production using Docker or Gunicorn
- Integrate with your mobile app or web application

## Support

For issues or questions, refer to README.md or check the code comments in app.py.
