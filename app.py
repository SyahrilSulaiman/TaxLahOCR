from flask import Flask, request, jsonify
from flask_cors import CORS
import pytesseract
from PIL import Image
import re
import io
import base64
from datetime import datetime
import os
import subprocess
import tempfile

app = Flask(__name__)
CORS(app)

class MalaysianReceiptExtractor:
    """Extract data from Malaysian receipts"""
    
    def __init__(self):
        # Common Malaysian merchant patterns
        self.merchant_keywords = [
            'sdn bhd', 'sdn. bhd.', 'sendirian berhad',
            'berhad', 'enterprise', 'restaurant', 'cafe',
            'kedai', 'restoran', 'kopitiam'
        ]
        
    def preprocess_image(self, image):
        """Preprocess image for better OCR results"""
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # Enhance contrast
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2)
        
        return image
    
    def convert_heic_to_image(self, file_path):
        """Convert HEIC/HEIF format to PIL Image (for iPhone photos)"""
        try:
            # Try using pillow-heif if available
            from pillow_heif import register_heif_opener
            register_heif_opener()
            return Image.open(file_path)
        except ImportError:
            # Fallback: try using ImageMagick convert command if available
            try:
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    tmp_path = tmp.name
                subprocess.run(['convert', file_path, tmp_path], check=True, capture_output=True)
                img = Image.open(tmp_path)
                os.unlink(tmp_path)
                return img
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Last resort: try to open directly
                return Image.open(file_path)
    
    def extract_text_from_image(self, image):
        """Extract text using Tesseract OCR"""
        # Preprocess image
        processed_image = self.preprocess_image(image)
        
        # Perform OCR
        text = pytesseract.image_to_string(processed_image, lang='eng+msa')
        return text
    
    def extract_merchant_name(self, text):
        """Extract merchant/business name"""
        lines = text.split('\n')
        
        # First, try to find the actual merchant name (not registration number)
        potential_names = []
        
        for i, line in enumerate(lines[:15]):  # Check first 15 lines
            line_clean = line.strip()
            
            if not line_clean or len(line_clean) < 3:
                continue
            
            # Skip if it's just a registration number in parentheses
            if re.match(r'^\s*\([0-9A-Z-]+\)\s*$', line_clean):
                continue
            
            # Skip URLs, emails, addresses details
            if any(skip in line_clean.lower() for skip in ['http', 'www', '@', 'tel:', 'phone:']):
                continue
            
            # Skip operational info
            if any(skip in line_clean.lower() for skip in ['waktu operasi', 'setiap hari', 'order:', 'employee:']):
                continue
            
            # Check for company registration patterns
            if any(keyword in line_clean.lower() for keyword in self.merchant_keywords):
                potential_names.append((i, line_clean, 10))
                continue
            
            # Look for lines with capital letters (typical for business names)
            if line_clean[0].isupper() and len(line_clean.split()) > 1:
                if not re.match(r'^[A-Z\s]+$', line_clean):
                    potential_names.append((i, line_clean, 5))
                elif 'restaurant' in line_clean.lower() or 'restoran' in line_clean.lower():
                    potential_names.append((i, line_clean, 8))
        
        if potential_names:
            potential_names.sort(key=lambda x: (-x[2], x[0]))
            return potential_names[0][1]
        
        for line in lines[:10]:
            line_clean = line.strip()
            if len(line_clean) > 5 and not re.match(r'^\([0-9A-Z-]+\)$', line_clean):
                return line_clean
        
        return "Unknown Merchant"
    
    def extract_registration_number(self, text):
        """Extract Malaysian business registration number"""
        patterns = [
            r'\b\d{12}\b',
            r'\b\d{7}-[A-Z]\b',
            r'(?:SSM|REG|NO)[:\s]*([0-9A-Z-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        
        return None
    
    def extract_address(self, text):
        """Extract business address"""
        lines = text.split('\n')
        address_lines = []
        
        for i, line in enumerate(lines):
            if re.search(r'\b\d{5}\b', line):
                start = max(0, i-2)
                end = min(len(lines), i+2)
                address_lines = [l.strip() for l in lines[start:end] if l.strip()]
                break
        
        return ', '.join(address_lines) if address_lines else None
    
    def extract_phone(self, text):
        """Extract phone number"""
        patterns = [
            r'\b0\d{1,2}[-\s]?\d{7,8}\b',
            r'\b01\d[-\s]?\d{7,8}\b',
            r'\+?60\d{1,2}[-\s]?\d{7,8}\b',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        
        return None
    
    def extract_date_time(self, text):
        """Extract date and time"""
        date_patterns = [
            r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
            r'\b(\d{1,2}\s+(?:Jan|Feb|Mac|Apr|Mei|Jun|Jul|Ogo|Sep|Okt|Nov|Dis)[a-z]*\s+\d{2,4})\b',
            r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})\b',
        ]
        
        time_patterns = [
            r'\b(\d{1,2}:\d{2}(?::\d{2})?)\s*(?:AM|PM|PTG|PG)?\b',
            r'\b(\d{1,2}:\d{2}(?::\d{2})?)\b',
        ]
        
        date = None
        time = None
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date = match.group(1)
                break
        
        for pattern in time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                time = match.group(0)
                break
        
        return date, time
    
    def extract_receipt_number(self, text):
        """Extract receipt/invoice number"""
        patterns = [
            r'#\s*(\d+-\d+)',
            r'#\s*([0-9]+-[0-9]+)',
            r'(?:RECEIPT|INVOICE|BILL|NO)[:\s#]+([A-Z0-9-]+)',
            r'\b(?:REC|INV|BIL)\s*[:#]?\s*([A-Z0-9-]+)',
            r'(?:Resit|Invois)[:\s#]+([A-Z0-9-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                receipt_num = match.group(1).strip()
                if len(receipt_num) >= 3:
                    if not re.match(r'^\d{1,2}[/-]\d', receipt_num):
                        if not (receipt_num.replace('-', '').isdigit() and len(receipt_num.replace('-', '')) > 7):
                            if not (receipt_num.isdigit() and len(receipt_num) == 5):
                                return receipt_num
        
        return None
    
    def _normalize_quantity_text(self, text):
        """Normalize OCR errors in quantity text (I, |, l -> 1)"""
        text = re.sub(r'^[Il|]\s*x', '1 x', text)
        text = re.sub(r'^[Il|]x', '1x', text)
        text = re.sub(r'\s*[\|l]{1,3}\s*[\|l]{0,3}\s*$', '', text)
        text = re.sub(r'[\s_|]+$', '', text)
        return text.strip()
    
    def _find_quantity_line(self, lines, start_idx, max_look_ahead=3):
        """Look ahead to find the quantity line, skipping blank/garbage lines"""
        for offset in range(1, max_look_ahead + 1):
            if start_idx + offset >= len(lines):
                break
            
            next_line = self._normalize_quantity_text(lines[start_idx + offset].strip())
            
            # Skip empty lines and garbage lines
            if not next_line or len(next_line) < 3:
                continue
            if re.match(r'^[\s\-_=<>|]+$', next_line):
                continue
            
            # Check if this is a quantity line
            qty_match = re.match(r'^(\d+)\s*x\s+RM\s*(\d+[.,]\d{2})', next_line, re.IGNORECASE)
            if qty_match:
                return qty_match, offset
        
        return None, 0
    
    def extract_items(self, text):
        """Extract line items from receipt - handles multiple formats"""
        lines = text.split('\n')
        items = []
        i = 0
        
        seen_items = {}
        
        while i < len(lines):
            line = lines[i].strip()
            
            if not line or len(line) < 3:
                i += 1
                continue
            
            if self._is_non_item_line(line):
                i += 1
                continue
            
            # ============================================================
            # FORMAT A: Item name and price on SAME line
            # Example: "AM04 > Teh O - Ais RM3.00"
            # Followed by: "1x RM3.00" (may have blank lines in between)
            # ============================================================
            
            # PATTERN A1: Full format with code, separator, name, and price on same line
            full_pattern_same_line = re.match(
                r'^([A-Z]{2,4}\d{1,3})\s*[>:]\s*(.+?)\s*[_\s]*RM\s*(\d+\.\d{2})\s*[\|]*$',
                line, re.IGNORECASE
            )
            
            if full_pattern_same_line:
                item_code = full_pattern_same_line.group(1)
                item_name = full_pattern_same_line.group(2).strip()
                total_price = float(full_pattern_same_line.group(3))
                
                qty_match, offset = self._find_quantity_line(lines, i)
                
                if qty_match:
                    quantity = int(qty_match.group(1))
                    unit_price = float(qty_match.group(2).replace(',', '.'))
                    
                    expected_total = unit_price * quantity
                    if abs(expected_total - total_price) < 0.05:
                        item_key = f"{i}_{item_name}_{unit_price}_{total_price}"
                        if item_key not in seen_items:
                            items.append({
                                'name': self._clean_item_name(item_name),
                                'quantity': quantity,
                                'unit_price': unit_price,
                                'total_price': total_price
                            })
                            seen_items[item_key] = True
                        i += offset + 1
                        continue
            
            # PATTERN A2: Code without > separator, price on same line
            code_no_sep_same_line = re.match(
                r'^([A-Z]{2,4}\d{1,3})\s+(.+?)\s+RM\s*(\d+\.\d{2})\s*[\|]*$',
                line, re.IGNORECASE
            )
            
            if code_no_sep_same_line:
                item_code = code_no_sep_same_line.group(1)
                item_name = code_no_sep_same_line.group(2).strip()
                total_price = float(code_no_sep_same_line.group(3))
                
                qty_match, offset = self._find_quantity_line(lines, i)
                
                if qty_match:
                    quantity = int(qty_match.group(1))
                    unit_price = float(qty_match.group(2).replace(',', '.'))
                    
                    expected_total = unit_price * quantity
                    if abs(expected_total - total_price) < 0.05:
                        item_key = f"{i}_{item_name}_{unit_price}_{total_price}"
                        if item_key not in seen_items:
                            items.append({
                                'name': self._clean_item_name(item_name),
                                'quantity': quantity,
                                'unit_price': unit_price,
                                'total_price': total_price
                            })
                            seen_items[item_key] = True
                        i += offset + 1
                        continue
            
            # PATTERN A3: Short code pattern, price on same line
            short_code_same_line = re.match(
                r'^([A-Z]{2})\s+(.+?)\s+RM\s*(\d+\.\d{2})\s*[\[\|]*',
                line, re.IGNORECASE
            )
            
            if short_code_same_line:
                item_code = short_code_same_line.group(1)
                item_name = short_code_same_line.group(2).strip()
                total_price = float(short_code_same_line.group(3))
                
                qty_match, offset = self._find_quantity_line(lines, i)
                
                if qty_match:
                    quantity = int(qty_match.group(1))
                    unit_price = float(qty_match.group(2).replace(',', '.'))
                    
                    expected_total = unit_price * quantity
                    if abs(expected_total - total_price) < 0.05:
                        item_key = f"{i}_{item_name}_{unit_price}_{total_price}"
                        if item_key not in seen_items:
                            items.append({
                                'name': self._clean_item_name(item_name),
                                'quantity': quantity,
                                'unit_price': unit_price,
                                'total_price': total_price
                            })
                            seen_items[item_key] = True
                        i += offset + 1
                        continue
            
            # PATTERN A4: Simple item name with price (no code)
            simple_same_line = re.match(
                r'^([A-Za-z][A-Za-z0-9\s\-\+]+?)\s+RM\s*(\d+\.\d{2})\s*[\[\|f=]*$',
                line, re.IGNORECASE
            )
            
            if simple_same_line:
                item_name = simple_same_line.group(1).strip()
                total_price = float(simple_same_line.group(2))
                
                if self._is_valid_item_name(item_name) and not self._is_summary_line(item_name):
                    qty_match, offset = self._find_quantity_line(lines, i)
                    
                    if qty_match:
                        quantity = int(qty_match.group(1))
                        unit_price = float(qty_match.group(2).replace(',', '.'))
                        
                        expected_total = unit_price * quantity
                        if abs(expected_total - total_price) < 0.05:
                            item_key = f"{i}_{item_name}_{unit_price}_{total_price}"
                            if item_key not in seen_items:
                                items.append({
                                    'name': self._clean_item_name(item_name),
                                    'quantity': quantity,
                                    'unit_price': unit_price,
                                    'total_price': total_price
                                })
                                seen_items[item_key] = True
                            i += offset + 1
                            continue
            
            # ============================================================
            # FORMAT B: Item name on one line, quantity on next line (NO price on item line)
            # Example: "NS02 > Nasi Set - Sup Berempah Daging"
            # Followed by: "1x RM14.90"
            # ============================================================
            
            # PATTERN B1: Code with separator, NO price on item line
            item_only_pattern = re.match(
                r'^([A-Z]{2,4}\d{1,3})\s*[>:]\s*(.+?)$',
                line, re.IGNORECASE
            )
            
            if item_only_pattern:
                item_code = item_only_pattern.group(1)
                item_name = item_only_pattern.group(2).strip()
                
                # Make sure item_name doesn't contain RM (price)
                if 'RM' not in item_name.upper() and self._is_valid_item_name(item_name):
                    qty_match, offset = self._find_quantity_line(lines, i)
                    
                    if qty_match:
                        quantity = int(qty_match.group(1))
                        unit_price = float(qty_match.group(2).replace(',', '.'))
                        total_price = round(unit_price * quantity, 2)
                        
                        item_key = f"{i}_{item_name}_{unit_price}_{total_price}"
                        if item_key not in seen_items:
                            items.append({
                                'name': self._clean_item_name(item_name),
                                'quantity': quantity,
                                'unit_price': unit_price,
                                'total_price': total_price
                            })
                            seen_items[item_key] = True
                        i += offset + 1
                        continue
            
            # PATTERN B2: Code without separator, NO price on item line
            item_only_no_sep = re.match(
                r'^([A-Z]{2,4}\d{1,3})\s+(.+?)$',
                line, re.IGNORECASE
            )
            
            if item_only_no_sep:
                item_code = item_only_no_sep.group(1)
                item_name = item_only_no_sep.group(2).strip()
                
                if 'RM' not in item_name.upper() and self._is_valid_item_name(item_name):
                    qty_match, offset = self._find_quantity_line(lines, i)
                    
                    if qty_match:
                        quantity = int(qty_match.group(1))
                        unit_price = float(qty_match.group(2).replace(',', '.'))
                        total_price = round(unit_price * quantity, 2)
                        
                        item_key = f"{i}_{item_name}_{unit_price}_{total_price}"
                        if item_key not in seen_items:
                            items.append({
                                'name': self._clean_item_name(item_name),
                                'quantity': quantity,
                                'unit_price': unit_price,
                                'total_price': total_price
                            })
                            seen_items[item_key] = True
                        i += offset + 1
                        continue
            
            # ============================================================
            # FORMAT C: Inline quantity at start of line
            # Example: "2 x Nasi Lemak RM17.00"
            # ============================================================
            
            inline_pattern = re.match(
                r'^(\d+)\s*x\s+([A-Z]{2,4}\d{1,3}\s*[>:]\s*)?(.+?)\s+RM\s*(\d+\.\d{2})$',
                line, re.IGNORECASE
            )
            
            if inline_pattern:
                quantity = int(inline_pattern.group(1))
                item_name = inline_pattern.group(3).strip()
                total_price = float(inline_pattern.group(4))
                
                if self._is_valid_item_name(item_name):
                    unit_price = round(total_price / quantity, 2)
                    item_key = f"{i}_{item_name}_{unit_price}_{total_price}"
                    if item_key not in seen_items:
                        items.append({
                            'name': self._clean_item_name(item_name),
                            'quantity': quantity,
                            'unit_price': unit_price,
                            'total_price': total_price
                        })
                        seen_items[item_key] = True
                i += 1
                continue
            
            i += 1
        
        # Validation
        validated_items = []
        for item in items:
            if item['unit_price'] > 200.0:
                continue
            if not self._is_valid_item_name(item['name']):
                continue
            validated_items.append(item)
        
        return validated_items
    
    def _is_valid_item_name(self, name):
        """Check if item name is valid"""
        if not name or len(name) < 2:
            return False
        
        clean = self._clean_item_name(name)
        
        invalid_patterns = [
            r'^[0-9\s]+x?$',
            r'^[|I!l]\s*x$',
            r'^[^\w\s]+$',
            r'^(sa|ota|qr|pg|sp|bh|pos)$',
            r'^\d+\.\d+$',
            r'^RM\d',
            r'^dine\s*in$',
        ]
        
        for pattern in invalid_patterns:
            if re.match(pattern, clean, re.IGNORECASE):
                return False
        
        if not re.search(r'[a-zA-Z]', clean):
            return False
        
        return True
    
    def _is_non_item_line(self, line):
        """Check if line is definitely not an item"""
        line_lower = line.lower()
        
        non_item_keywords = [
            'order:', 'employee:', 'cashier:', 'table:', 'meja:',
            'waktu operasi', 'setiap hari', 'self pickup', 'pre order',
            'terima kasih', 'jika baik', 'http', 'www',
            'total', 'subtotal', 'cash', 'change', 'balance',
            'thank you', 'powered by', 'tel:', 'phone:',
            'jumpa lagi', 'beritahu', 'pos:', 'dine in',
            'tempahan', 'melalui', 'laman web',
        ]
        
        for keyword in non_item_keywords:
            if keyword in line_lower:
                return True
        
        if re.match(r'^\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}', line):
            return True
        
        # Skip lines that are just dashes or symbols
        if re.match(r'^[\s\-_=<>|]+$', line):
            return True
        
        return False
    
    def _clean_item_name(self, name):
        """Clean up item name"""
        name = re.sub(r'^[A-Z]{2,4}\d{1,3}\s*[>:]\s*', '', name, flags=re.IGNORECASE)
        name = re.sub(r'^[A-Z]{2,4}\d{0,3}\s+', '', name)
        name = name.strip(' -_>:|')
        name = re.sub(r'\s+', ' ', name)
        # Remove trailing OCR artifacts
        name = re.sub(r'\s*[\[\|f=]+\s*$', '', name)
        return name
    
    def _is_summary_line(self, text):
        """Check if line is a summary/total line"""
        text_lower = text.lower()
        summary_keywords = [
            'total', 'subtotal', 'sub total', 'tax', 'sst', 'gst',
            'service', 'charge', 'change', 'balance', 'cash', 'card',
            'payment', 'paid', 'amount', 'grand total', 'net total',
            'rounding', 'discount'
        ]
        return any(keyword in text_lower for keyword in summary_keywords)
    
    def extract_totals(self, text):
        """Extract subtotal, tax, service charge, and total"""
        amounts = {
            'subtotal': None,
            'service_charge': None,
            'service_charge_rate': None,
            'sst': None,
            'sst_rate': None,
            'rounding': None,
            'total': None,
            'cash': None,
            'change': None
        }
        
        lines = text.split('\n')
        all_amounts = []
        
        for line in lines:
            line_lower = line.lower()
            
            amount_matches = re.finditer(r'rm\s*(\d+\.\d{2})', line, re.IGNORECASE)
            for match in amount_matches:
                amount = float(match.group(1))
                all_amounts.append((amount, line_lower, line))
        
        for amount, line_lower, line in all_amounts:
            if any(keyword in line_lower for keyword in ['subtotal', 'sub total', 'sub-total']):
                amounts['subtotal'] = amount
                continue
            
            if 'service' in line_lower and 'charge' in line_lower:
                amounts['service_charge'] = amount
                rate_match = re.search(r'(\d+(?:\.\d+)?)\s*%', line)
                if rate_match:
                    amounts['service_charge_rate'] = float(rate_match.group(1))
                continue
            
            if any(keyword in line_lower for keyword in ['sst', 'tax', 'gst', 'cukai']):
                amounts['sst'] = amount
                rate_match = re.search(r'(\d+(?:\.\d+)?)\s*%', line)
                if rate_match:
                    amounts['sst_rate'] = float(rate_match.group(1))
                continue
            
            if 'rounding' in line_lower or 'round' in line_lower:
                amounts['rounding'] = amount
                continue
            
            if any(keyword in line_lower for keyword in [
                'total', 'jumlah', 'grand total', 'net total', 'amount payable',
                'total amount', 'amount due', 'sa ota'
            ]):
                if 'sub' not in line_lower:
                    if amounts['total'] is None or amount > amounts['total']:
                        amounts['total'] = amount
                continue
            
            if 'qr' in line_lower and amount > 10:
                if amounts['total'] is None or amount >= amounts['total']:
                    amounts['total'] = amount
                continue
            
            if any(keyword in line_lower for keyword in ['cash', 'tunai', 'paid', 'bayar']):
                if 'cashier' not in line_lower and 'kasir' not in line_lower:
                    amounts['cash'] = amount
                continue
            
            if any(keyword in line_lower for keyword in ['change', 'balance', 'baki']):
                amounts['change'] = amount
                continue
        
        if amounts['total'] is None and all_amounts:
            last_section_start = int(len(lines) * 0.8)
            last_section_amounts = [
                amt for amt, _, original_line in all_amounts 
                if any(original_line in l for l in lines[last_section_start:])
            ]
            
            if last_section_amounts:
                potential_total = max(last_section_amounts)
                if potential_total > 1.0:
                    amounts['total'] = potential_total
        
        return amounts
    
    def extract_payment_method(self, text):
        """Extract payment method"""
        text_lower = text.lower()
        
        if 'qr' in text_lower:
            return 'QR Payment'
        elif 'cash' in text_lower:
            return 'Cash'
        elif any(keyword in text_lower for keyword in ['card', 'credit', 'debit', 'visa', 'mastercard']):
            return 'Card'
        elif 'tng' in text_lower or 'touch n go' in text_lower or 'touchngo' in text_lower:
            return 'Touch n Go'
        elif 'grabpay' in text_lower:
            return 'GrabPay'
        elif 'boost' in text_lower:
            return 'Boost'
        elif 'shopee' in text_lower:
            return 'ShopeePay'
        elif 'online' in text_lower or 'transfer' in text_lower:
            return 'Online Transfer'
        
        return 'Unknown'
    
    def extract_data(self, image):
        """Main extraction method"""
        text = self.extract_text_from_image(image)
        
        merchant_name = self.extract_merchant_name(text)
        registration_number = self.extract_registration_number(text)
        address = self.extract_address(text)
        phone = self.extract_phone(text)
        date, time = self.extract_date_time(text)
        receipt_number = self.extract_receipt_number(text)
        items = self.extract_items(text)
        amounts = self.extract_totals(text)
        payment_method = self.extract_payment_method(text)
        
        if items:
            calculated_subtotal = sum(item['total_price'] for item in items)
            
            if amounts['total'] and calculated_subtotal > amounts['total'] * 2:
                pass
            elif amounts['subtotal'] is None:
                amounts['subtotal'] = round(calculated_subtotal, 2)
            elif abs(calculated_subtotal - amounts['subtotal']) < 1.0:
                amounts['subtotal'] = round(calculated_subtotal, 2)
        
        if amounts['total'] is None and amounts['subtotal'] is not None:
            amounts['total'] = amounts['subtotal']
            if amounts['service_charge']:
                amounts['total'] += amounts['service_charge']
            if amounts['sst']:
                amounts['total'] += amounts['sst']
            if amounts['rounding']:
                amounts['total'] += amounts['rounding']
            amounts['total'] = round(amounts['total'], 2)
        
        if items and amounts['total']:
            items_total = sum(item['total_price'] for item in items)
            
            if items_total > amounts['total'] * 1.5:
                validated_items = []
                for item in items:
                    if item['unit_price'] <= amounts['total']:
                        validated_items.append(item)
                items = validated_items
                
                if items:
                    amounts['subtotal'] = round(sum(item['total_price'] for item in items), 2)
        
        return {
            'merchant': {
                'name': merchant_name,
                'registration_number': registration_number,
                'address': address,
                'phone': phone
            },
            'receipt': {
                'number': receipt_number,
                'date': date,
                'time': time
            },
            'items': items,
            'amounts': amounts,
            'payment_method': payment_method,
            'raw_text': text
        }


# Initialize extractor
extractor = MalaysianReceiptExtractor()


@app.route('/')
def index():
    """API information"""
    return jsonify({
        'name': 'Malaysian Receipt Data Extraction API',
        'version': '1.2',
        'endpoints': {
            '/extract': 'POST - Extract data from receipt image',
            '/health': 'GET - Check API health'
        }
    })


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})


@app.route('/extract', methods=['POST'])
def extract_receipt():
    """Extract data from receipt image"""
    try:
        if 'image' not in request.files and 'image_base64' not in request.json:
            return jsonify({'error': 'No image provided'}), 400
        
        if 'image' in request.files:
            file = request.files['image']
            
            filename = file.filename.lower() if file.filename else ''
            if filename.endswith(('.heic', '.heif')):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.heic') as tmp:
                    file.save(tmp.name)
                    tmp_path = tmp.name
                
                try:
                    image = extractor.convert_heic_to_image(tmp_path)
                finally:
                    os.unlink(tmp_path)
            else:
                image = Image.open(file.stream)
        else:
            image_data = request.json['image_base64']
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
        
        result = extractor.extract_data(image)
        
        return jsonify({
            'success': True,
            'data': result
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)