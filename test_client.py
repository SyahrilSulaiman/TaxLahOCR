import requests
import base64
import json

def test_extract_with_file(image_path):
    """Test extraction with image file upload"""
    url = 'http://localhost:6000/extract'
    
    with open(image_path, 'rb') as f:
        files = {'image': f}
        response = requests.post(url, files=files)
    
    return response.json()


def test_extract_with_base64(image_path):
    """Test extraction with base64 encoded image"""
    url = 'http://localhost:6000/extract'
    
    # Read and encode image
    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')
    
    # Send request
    response = requests.post(
        url,
        json={'image_base64': f'data:image/jpeg;base64,{image_data}'}
    )
    
    return response.json()


def print_result(result):
    """Pretty print extraction result"""
    if not result.get('success'):
        print(f"Error: {result.get('error')}")
        return
    
    data = result['data']
    
    print("\n" + "="*60)
    print("RECEIPT EXTRACTION RESULT")
    print("="*60)
    
    # Merchant info
    print("\n📍 MERCHANT INFORMATION:")
    print(f"  Name: {data['merchant']['name']}")
    if data['merchant']['registration_number']:
        print(f"  Registration No: {data['merchant']['registration_number']}")
    if data['merchant']['address']:
        print(f"  Address: {data['merchant']['address']}")
    if data['merchant']['phone']:
        print(f"  Phone: {data['merchant']['phone']}")
    
    # Receipt info
    print("\n📄 RECEIPT INFORMATION:")
    if data['receipt']['number']:
        print(f"  Receipt No: {data['receipt']['number']}")
    if data['receipt']['date']:
        print(f"  Date: {data['receipt']['date']}")
    if data['receipt']['time']:
        print(f"  Time: {data['receipt']['time']}")
    
    # Items
    if data['items']:
        print("\n🛒 ITEMS:")
        for i, item in enumerate(data['items'], 1):
            print(f"  {i}. {item['name']:<40} RM {item['price']:>8.2f}")
    
    # Amounts
    print("\n💰 AMOUNTS:")
    amounts = data['amounts']
    if amounts['subtotal']:
        print(f"  Subtotal: RM {amounts['subtotal']:.2f}")
    if amounts['service_charge']:
        rate_text = f" ({amounts['service_charge_rate']}%)" if amounts['service_charge_rate'] else ""
        print(f"  Service Charge{rate_text}: RM {amounts['service_charge']:.2f}")
    if amounts['sst']:
        rate_text = f" ({amounts['sst_rate']}%)" if amounts['sst_rate'] else ""
        print(f"  SST{rate_text}: RM {amounts['sst']:.2f}")
    if amounts['total']:
        print(f"  {'='*50}")
        print(f"  TOTAL: RM {amounts['total']:.2f}")
    if amounts['cash']:
        print(f"\n  Cash: RM {amounts['cash']:.2f}")
    if amounts['change']:
        print(f"  Change: RM {amounts['change']:.2f}")
    
    # Payment method
    print(f"\n💳 PAYMENT METHOD: {data['payment_method']}")
    
    print("\n" + "="*60 + "\n")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_client.py <image_path>")
        print("\nExample:")
        print("  python test_client.py receipt.jpg")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    print("Testing receipt extraction...")
    print(f"Image: {image_path}")
    
    # Test with file upload
    result = test_extract_with_file(image_path)
    print_result(result)
    
    # Optionally save to JSON
    with open('extraction_result.json', 'w') as f:
        json.dump(result, f, indent=2)
    print("Results saved to extraction_result.json")
