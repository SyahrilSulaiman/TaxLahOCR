# Malaysian Receipt Data Extraction API

A Flask-based API for extracting structured data from Malaysian merchant receipts using OCR (Optical Character Recognition).

## Features

### Extracted Data Points

**Merchant Information:**
- Business name
- Registration number (SSM format)
- Address (with postal code detection)
- Phone number (landline and mobile formats)

**Receipt Information:**
- Receipt/Invoice number
- Date
- Time

**Transaction Details:**
- Line items with prices
- Subtotal
- Service charge (with percentage)
- SST/GST (Sales and Service Tax - with percentage)
- Total amount
- Cash received
- Change given

**Payment Information:**
- Payment method detection (Cash, Card, Touch n Go, GrabPay, Boost, ShopeePay, etc.)

### Malaysian-Specific Features

- SST tax recognition (6% or 8%)
- Service charge detection (typically 10%)
- Malaysian business registration number formats
- Malaysian postal code patterns (5 digits)
- Support for Ringgit Malaysia (RM) currency
- Malaysian phone number formats
- Bilingual OCR support (English and Malay)

## Prerequisites

Before running the application, you need to install:

1. **Python 3.8+**
2. **Tesseract OCR**

### Installing Tesseract OCR

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-msa  # Malay language support
```

**macOS:**
```bash
brew install tesseract
brew install tesseract-lang  # For language packs
```

**Windows:**
Download and install from: https://github.com/UB-Mannheim/tesseract/wiki

## Installation

1. Clone or download the project files

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Running the API

Start the Flask server:
```bash
python app.py
```

The API will be available at `http://localhost:5000`

## API Endpoints

### 1. Health Check
```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-12-09T10:30:00"
}
```

### 2. Extract Receipt Data
```
POST /extract
```

**Method 1: File Upload**
```bash
curl -X POST -F "image=@receipt.jpg" http://localhost:5000/extract
```

**Method 2: Base64 Encoded**
```bash
curl -X POST http://localhost:5000/extract \
  -H "Content-Type: application/json" \
  -d '{
    "image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "merchant": {
      "name": "RESTORAN ABC SDN BHD",
      "registration_number": "202001234567",
      "address": "123, Jalan Sultan, 50000 Kuala Lumpur",
      "phone": "03-12345678"
    },
    "receipt": {
      "number": "INV-2024-001",
      "date": "09/12/2024",
      "time": "14:30:00"
    },
    "items": [
      {
        "name": "Nasi Lemak",
        "price": 8.50
      },
      {
        "name": "Teh Tarik",
        "price": 3.00
      }
    ],
    "amounts": {
      "subtotal": 11.50,
      "service_charge": 1.15,
      "service_charge_rate": 10.0,
      "sst": 0.76,
      "sst_rate": 6.0,
      "total": 13.41,
      "cash": 20.00,
      "change": 6.59
    },
    "payment_method": "Cash",
    "raw_text": "..."
  }
}
```

## Usage Examples

### Python Client

Use the provided test client:
```bash
python test_client.py receipt.jpg
```

### JavaScript/Node.js

```javascript
const FormData = require('form-data');
const fs = require('fs');
const axios = require('axios');

async function extractReceipt(imagePath) {
  const form = new FormData();
  form.append('image', fs.createReadStream(imagePath));
  
  const response = await axios.post('http://localhost:5000/extract', form, {
    headers: form.getHeaders()
  });
  
  return response.data;
}

// Usage
extractReceipt('receipt.jpg')
  .then(result => console.log(JSON.stringify(result, null, 2)))
  .catch(error => console.error(error));
```

### React Native

```javascript
import * as ImagePicker from 'expo-image-picker';

async function uploadReceipt() {
  // Pick image
  let result = await ImagePicker.launchCameraAsync({
    mediaTypes: ImagePicker.MediaTypeOptions.Images,
    quality: 1,
  });

  if (!result.cancelled) {
    // Create form data
    const formData = new FormData();
    formData.append('image', {
      uri: result.uri,
      type: 'image/jpeg',
      name: 'receipt.jpg',
    });

    // Upload
    const response = await fetch('http://your-server:5000/extract', {
      method: 'POST',
      body: formData,
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    const data = await response.json();
    console.log(data);
  }
}
```

## Tips for Best Results

1. **Image Quality:**
   - Use good lighting
   - Avoid shadows and glare
   - Keep the receipt flat
   - Capture the entire receipt
   - Minimum resolution: 1280x720

2. **Receipt Condition:**
   - Ensure text is clear and not faded
   - Avoid wrinkled or torn receipts
   - Clean receipts work better

3. **Camera Position:**
   - Hold camera parallel to receipt
   - Avoid angles
   - Fill the frame with the receipt

## Customization

### Adding New Merchant Patterns

Edit the `merchant_keywords` list in `app.py`:
```python
self.merchant_keywords = [
    'sdn bhd', 'sdn. bhd.', 'sendirian berhad',
    'berhad', 'enterprise', 'restaurant', 'cafe',
    'kedai', 'restoran', 'kopitiam',
    # Add your custom patterns here
]
```

### Adjusting OCR Settings

Modify the OCR configuration in `extract_text_from_image()`:
```python
# Add custom config
custom_config = r'--oem 3 --psm 6'
text = pytesseract.image_to_string(processed_image, lang='eng+msa', config=custom_config)
```

### Adding New Tax Rates

Update the `extract_totals()` method to recognize different tax patterns.

## Deployment

### Production Deployment

For production, use a WSGI server like Gunicorn:

```bash
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Docker Deployment

Create a `Dockerfile`:
```dockerfile
FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-msa \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

Build and run:
```bash
docker build -t receipt-extractor .
docker run -p 5000:5000 receipt-extractor
```

## Troubleshooting

### Common Issues

**1. "Tesseract not found"**
- Make sure Tesseract is installed and in your PATH
- On Windows, add Tesseract installation directory to PATH

**2. Poor OCR accuracy**
- Improve image quality
- Adjust image preprocessing in `preprocess_image()`
- Try different Tesseract configurations

**3. Missing items or amounts**
- Check receipt formatting
- Adjust regex patterns for your receipt format
- Review `raw_text` in response to debug

**4. CORS errors in web applications**
- The API already includes CORS support via flask-cors
- Adjust CORS settings if needed in `app.py`

## Performance Considerations

- OCR processing can take 1-5 seconds depending on image size
- Consider implementing a queue system for high-volume scenarios
- Cache frequently accessed receipts
- Resize large images before processing

## Security Considerations

- Implement authentication for production use
- Add rate limiting to prevent abuse
- Validate and sanitize all inputs
- Consider encrypting stored receipt data
- Implement proper error handling without exposing sensitive info

## License

This project is provided as-is for educational and commercial use.

## Support

For issues or questions, please refer to the documentation or contact your development team.

## Changelog

### Version 1.0
- Initial release
- Support for Malaysian receipt formats
- SST and service charge detection
- Multi-payment method support
- Bilingual OCR (English/Malay)
