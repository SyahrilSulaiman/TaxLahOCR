#!/usr/bin/env python3
"""Test script to verify improved receipt extraction"""

import re

# Sample raw OCR text from your receipt
raw_text = """Khun Mae Thai Muslim Seri Kembangan
» Jalan Bpp 5/3, Pusat Bandar Putra Permai, Ser!
Kembangan, Selangor, 43300

TRY

( 1450014-P )

kami

https //khunmaethaimustim com/ser- kembangan/

* Self Pickup
* Table Reservation + Pre Order

Waktu Operasi

Setiap hari:

0 12.00 pm - 11.30 pm

Order: MEJA 05
Employee: Cashie

"s

RM14.90 |

RM28.90

AM02 > COLD Ice Water RM2.00
2 x RM1.00

ATO3 > Ala Carte - Telur Mata RM1.50
1 x RM1.50

AM04 > Teh O - Ais RM3.00
1x RM3.00

AM70 Kopi - Ais RM3.50
1x RM3.50

NS02 > Nasi Set - Sup Berempah Daging RM14.90
1x RM14.90

NP Nasi putih RM2.50
1x RM2.50

NW02 > Mee Wantan Kicap + Dumpling RM10.00
1 x RM10.00

ATO1 > Ala Carte - Telur Dadar Single _ RM2.50
1 x RM2.50 | |

Colek RM11.00
I x RM11.00

AM04 > Teh Q - Ais RM3.00
| x RM3.00

Pg Sp aaNet noon aes aaa-
Sa ota RM97.70
pa

QR RM97.70

Jika BAIK, Sila Beritahu Kawan,
Jika TIDAK, Sila Beritahu KAMI...

TERIMA KASIH, NANTI JUMPA LAGI.

5/12/25 9:28 PTG #8-37833

"""

def normalize_quantity_text(text):
    """Normalize OCR errors in quantity text (I, |, l -> 1)"""
    # Fix starting character OCR errors
    text = re.sub(r'^[Il|]\s*x', '1 x', text)
    text = re.sub(r'^[Il|]x', '1x', text)
    # Remove trailing OCR artifacts like "| |" or "| | |"
    text = re.sub(r'\s*[\|l]{1,3}\s*[\|l]{0,3}\s*$', '', text)
    # Remove trailing underscores and pipes
    text = re.sub(r'[\s_|]+$', '', text)
    return text.strip()

def is_non_item_line(line):
    """Check if line is definitely not an item"""
    line_lower = line.lower()
    
    non_item_keywords = [
        'order:', 'employee:', 'cashier:', 'table:', 'meja:',
        'waktu operasi', 'setiap hari', 'self pickup', 'pre order',
        'terima kasih', 'jika baik', 'http', 'www',
        'total', 'subtotal', 'cash', 'change', 'balance',
        'thank you', 'powered by', 'tel:', 'phone:',
        'jumpa lagi', 'beritahu',
    ]
    
    for keyword in non_item_keywords:
        if keyword in line_lower:
            return True
    
    if re.match(r'^\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}', line):
        return True
    
    return False

def clean_item_name(name):
    """Clean up item name"""
    name = re.sub(r'^[A-Z]{2,4}\d{1,3}\s*[>:]\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^[A-Z]{2,4}\d{0,3}\s+', '', name)
    name = name.strip(' -_>:|')
    name = re.sub(r'\s+', ' ', name)
    return name

def is_valid_item_name(name):
    """Check if item name is valid"""
    if not name or len(name) < 2:
        return False
    
    clean = clean_item_name(name)
    
    invalid_patterns = [
        r'^[0-9\s]+x?$',
        r'^[|I!l]\s*x$',
        r'^[^\w\s]+$',
        r'^(sa|ota|qr|pg|sp)$',
        r'^\d+\.\d+$',
        r'^RM\d',
    ]
    
    for pattern in invalid_patterns:
        if re.match(pattern, clean, re.IGNORECASE):
            return False
    
    if not re.search(r'[a-zA-Z]', clean):
        return False
    
    return True

def extract_items_improved(text):
    """Extract line items with improved patterns"""
    lines = text.split('\n')
    items = []
    i = 0
    seen_items = {}
    
    while i < len(lines):
        line = lines[i].strip()
        
        if not line or len(line) < 3:
            i += 1
            continue
        
        if is_non_item_line(line):
            i += 1
            continue
        
        # PATTERN 1: Full format with code and > separator
        full_pattern = re.match(
            r'^([A-Z]{2,4}\d{1,3})\s*[>:]\s*(.+?)\s+RM\s*(\d+\.\d{2})$',
            line, re.IGNORECASE
        )
        
        if full_pattern and i + 1 < len(lines):
            item_code = full_pattern.group(1)
            item_name = full_pattern.group(2).strip()
            total_price = float(full_pattern.group(3))
            
            next_line = normalize_quantity_text(lines[i + 1].strip())
            qty_match = re.match(r'^(\d+)\s*x\s+RM\s*(\d+\.\d{2})$', next_line, re.IGNORECASE)
            
            if qty_match:
                quantity = int(qty_match.group(1))
                unit_price = float(qty_match.group(2))
                
                expected_total = unit_price * quantity
                if abs(expected_total - total_price) < 0.05:
                    item_key = f"{item_name}_{unit_price}_{total_price}"
                    if item_key not in seen_items:
                        items.append({
                            'name': clean_item_name(item_name),
                            'quantity': quantity,
                            'unit_price': unit_price,
                            'total_price': total_price
                        })
                        seen_items[item_key] = True
                    i += 2
                    continue
        
        # PATTERN 2: Code without > separator
        code_no_sep_pattern = re.match(
            r'^([A-Z]{2,4}\d{1,3})\s+(.+?)\s+RM\s*(\d+\.\d{2})$',
            line, re.IGNORECASE
        )
        
        if code_no_sep_pattern and i + 1 < len(lines):
            item_code = code_no_sep_pattern.group(1)
            item_name = code_no_sep_pattern.group(2).strip()
            total_price = float(code_no_sep_pattern.group(3))
            
            next_line = normalize_quantity_text(lines[i + 1].strip())
            qty_match = re.match(r'^(\d+)\s*x\s+RM\s*(\d+\.\d{2})$', next_line, re.IGNORECASE)
            
            if qty_match:
                quantity = int(qty_match.group(1))
                unit_price = float(qty_match.group(2))
                
                expected_total = unit_price * quantity
                if abs(expected_total - total_price) < 0.05:
                    item_key = f"{item_name}_{unit_price}_{total_price}"
                    if item_key not in seen_items:
                        items.append({
                            'name': clean_item_name(item_name),
                            'quantity': quantity,
                            'unit_price': unit_price,
                            'total_price': total_price
                        })
                        seen_items[item_key] = True
                    i += 2
                    continue
        
        # PATTERN 3: Short code pattern (e.g., "NP Nasi putih RM2.50")
        short_code_pattern = re.match(
            r'^([A-Z]{2})\s+(.+?)\s+RM\s*(\d+\.\d{2})$',
            line, re.IGNORECASE
        )
        
        if short_code_pattern and i + 1 < len(lines):
            item_code = short_code_pattern.group(1)
            item_name = short_code_pattern.group(2).strip()
            total_price = float(short_code_pattern.group(3))
            
            next_line = normalize_quantity_text(lines[i + 1].strip())
            qty_match = re.match(r'^(\d+)\s*x\s+RM\s*(\d+\.\d{2})$', next_line, re.IGNORECASE)
            
            if qty_match:
                quantity = int(qty_match.group(1))
                unit_price = float(qty_match.group(2))
                
                expected_total = unit_price * quantity
                if abs(expected_total - total_price) < 0.05:
                    item_key = f"{item_name}_{unit_price}_{total_price}"
                    if item_key not in seen_items:
                        items.append({
                            'name': clean_item_name(item_name),
                            'quantity': quantity,
                            'unit_price': unit_price,
                            'total_price': total_price
                        })
                        seen_items[item_key] = True
                    i += 2
                    continue
        
        # PATTERN 4: Simple item name with price (no code)
        simple_pattern = re.match(
            r'^([A-Za-z][A-Za-z0-9\s\-\+]+?)\s+RM\s*(\d+\.\d{2})$',
            line, re.IGNORECASE
        )
        
        if simple_pattern and i + 1 < len(lines):
            item_name = simple_pattern.group(1).strip()
            total_price = float(simple_pattern.group(2))
            
            if is_valid_item_name(item_name):
                next_line = normalize_quantity_text(lines[i + 1].strip())
                qty_match = re.match(r'^(\d+)\s*x\s+RM\s*(\d+\.\d{2})$', next_line, re.IGNORECASE)
                
                if qty_match:
                    quantity = int(qty_match.group(1))
                    unit_price = float(qty_match.group(2))
                    
                    expected_total = unit_price * quantity
                    if abs(expected_total - total_price) < 0.05:
                        item_key = f"{item_name}_{unit_price}_{total_price}"
                        if item_key not in seen_items:
                            items.append({
                                'name': clean_item_name(item_name),
                                'quantity': quantity,
                                'unit_price': unit_price,
                                'total_price': total_price
                            })
                            seen_items[item_key] = True
                        i += 2
                        continue
        
        i += 1
    
    return items

def extract_receipt_number(text):
    """Extract receipt number"""
    patterns = [
        r'#\s*(\d+-\d+)',
        r'#\s*([0-9]+-[0-9]+)',
        r'(?:RECEIPT|INVOICE|BILL|NO)[:\s#]+([A-Z0-9-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return None

def extract_totals(text):
    """Extract totals"""
    amounts = {
        'subtotal': None,
        'total': None,
    }
    
    lines = text.split('\n')
    
    for line in lines:
        line_lower = line.lower()
        
        amount_matches = re.finditer(r'rm\s*(\d+\.\d{2})', line, re.IGNORECASE)
        for match in amount_matches:
            amount = float(match.group(1))
            
            if any(keyword in line_lower for keyword in ['sa ota', 'total', 'jumlah']):
                if 'sub' not in line_lower:
                    if amounts['total'] is None or amount > amounts['total']:
                        amounts['total'] = amount
            
            if 'qr' in line_lower and amount > 10:
                if amounts['total'] is None or amount >= amounts['total']:
                    amounts['total'] = amount
    
    return amounts

def extract_payment_method(text):
    """Extract payment method"""
    text_lower = text.lower()
    
    if 'qr' in text_lower:
        return 'QR Payment'
    elif 'cash' in text_lower:
        return 'Cash'
    
    return 'Unknown'

# Run the test
print("=" * 60)
print("IMPROVED RECEIPT EXTRACTION TEST")
print("=" * 60)

print("\n--- ITEMS EXTRACTION ---")
items = extract_items_improved(raw_text)

expected_items = [
    ("COLD Ice Water", 2, 1.00, 2.00),
    ("Ala Carte - Telur Mata", 1, 1.50, 1.50),
    ("Teh O - Ais", 1, 3.00, 3.00),
    ("Kopi - Ais", 1, 3.50, 3.50),
    ("Nasi Set - Sup Berempah Daging", 1, 14.90, 14.90),
    ("Nasi putih", 1, 2.50, 2.50),
    ("Mee Wantan Kicap + Dumpling", 1, 10.00, 10.00),
    ("Ala Carte - Telur Dadar Single", 1, 2.50, 2.50),
    ("Colek", 1, 11.00, 11.00),
    ("Teh O - Ais", 1, 3.00, 3.00),  # Second order
]

print(f"\nExtracted {len(items)} items:")
for item in items:
    print(f"  - {item['name']}: {item['quantity']} x RM{item['unit_price']:.2f} = RM{item['total_price']:.2f}")

calculated_subtotal = sum(item['total_price'] for item in items)
print(f"\nCalculated subtotal: RM{calculated_subtotal:.2f}")

expected_total = sum(exp[3] for exp in expected_items)
print(f"Expected subtotal: RM{expected_total:.2f}")

print("\n--- RECEIPT NUMBER ---")
receipt_num = extract_receipt_number(raw_text)
print(f"Receipt number: {receipt_num}")
print(f"Expected: 8-37833")

print("\n--- TOTALS ---")
amounts = extract_totals(raw_text)
print(f"Total: RM{amounts['total']}")
print(f"Expected total: RM97.70")

print("\n--- PAYMENT METHOD ---")
payment = extract_payment_method(raw_text)
print(f"Payment method: {payment}")
print(f"Expected: QR Payment")

print("\n" + "=" * 60)
print("COMPARISON WITH ORIGINAL EXTRACTION")
print("=" * 60)

original_items = [
    {"name": "Ala Carte - Telur Mata", "quantity": 1, "total_price": 1.5, "unit_price": 1.5},
    {"name": "Teh O - Ais", "quantity": 1, "total_price": 3.0, "unit_price": 3.0},
    {"name": "Nasi Set - Sup Berempah Daging", "quantity": 1, "total_price": 14.9, "unit_price": 14.9},
    {"name": "Nasi putih", "quantity": 1, "total_price": 2.5, "unit_price": 2.5},
    {"name": "Mee Wantan Kicap + Dumpling", "quantity": 1, "total_price": 10.0, "unit_price": 10.0},
]

print(f"\nOriginal extraction: {len(original_items)} items, subtotal: RM31.90")
print(f"Improved extraction: {len(items)} items, subtotal: RM{calculated_subtotal:.2f}")

print("\n--- MISSING ITEMS IN ORIGINAL ---")
original_names = {item['name'] for item in original_items}
for item in items:
    if item['name'] not in original_names:
        print(f"  + {item['name']}: RM{item['total_price']:.2f}")

print("\n" + "=" * 60)
print("SUMMARY OF IMPROVEMENTS")
print("=" * 60)
print("1. Fixed OCR quantity normalization (I, |, l -> 1)")
print("2. Added pattern for codes without > separator (e.g., 'AM70 Kopi - Ais')")
print("3. Added pattern for short codes (e.g., 'NP Nasi putih')")
print("4. Added pattern for simple items without codes (e.g., 'Colek')")
print("5. Fixed receipt number extraction for '#8-37833' format")
print("6. Fixed total extraction for 'Sa ota' (OCR error) and 'QR' patterns")
print("7. Updated payment method to detect QR payments")