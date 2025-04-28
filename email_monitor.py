import base64
import email
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import os
import re

class EmailMonitor:
    def __init__(self, gmail_service):
        self.gmail_service = gmail_service
        self.last_check_time = None
        self.current_orders = []
        self.search_window_days = 7  # Default to 7 days if no previous check

    def _parse_ebay_email(self, message_body, message_headers):
        """Parse eBay sale email content"""
        try:
            print("\nParsing eBay email...")
            
            # Get the subject line
            subject = next((h['value'] for h in message_headers if h['name'].lower() == 'subject'), '')
            print(f"Email subject: {subject}")
            
            # Initialize result dictionary
            order_info = {
                'platform': 'eBay',
                'item_name': None,
                'buyer_name': None,
                'date_sold': None,
                'total_price': None,
                'shipping_price': None,
                'image_url': None
            }
            
            # Check if this is a sale notification by looking at the subject
            if subject.startswith("You made the sale for "):
                order_info['item_name'] = subject[21:].strip()
                print(f"Found item name from subject: {order_info['item_name']}")
            
            # Extract buyer name - try multiple patterns
            buyer_patterns = [
                r"Buyer:\s*(.*?)(?:\n|$)",
                r"Buyer\s*ID:\s*(.*?)(?:\n|$)",
                r"Purchased\s*by:\s*(.*?)(?:\n|$)",
                r"Buyer:\s*([^\n]+)",
                r"Buyer\s*ID:\s*([^\n]+)",
                r"Purchased\s*by:\s*([^\n]+)"
            ]
            
            for pattern in buyer_patterns:
                match = re.search(pattern, message_body, re.IGNORECASE | re.MULTILINE)
                if match:
                    order_info['buyer_name'] = match.group(1).strip()
                    print(f"Found buyer: {order_info['buyer_name']}")
                    break
            
            # Extract date sold
            date_patterns = [
                r"Sold\s*on:\s*(.*?)(?:\n|$)",
                r"Date\s*sold:\s*(.*?)(?:\n|$)",
                r"Sale\s*date:\s*(.*?)(?:\n|$)",
                r"Sold\s*on:\s*([^\n]+)",
                r"Date\s*sold:\s*([^\n]+)",
                r"Sale\s*date:\s*([^\n]+)"
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, message_body, re.IGNORECASE | re.MULTILINE)
                if match:
                    order_info['date_sold'] = match.group(1).strip()
                    print(f"Found sale date: {order_info['date_sold']}")
                    break
            
            # Extract total price
            total_price_patterns = [
                r"Total\s*price:\s*\$?(\d+\.\d{2})",
                r"Total\s*amount:\s*\$?(\d+\.\d{2})",
                r"Amount\s*paid:\s*\$?(\d+\.\d{2})",
                r"Total\s*price:\s*\$?([\d,]+\.\d{2})",
                r"Total\s*amount:\s*\$?([\d,]+\.\d{2})",
                r"Amount\s*paid:\s*\$?([\d,]+\.\d{2})"
            ]
            
            for pattern in total_price_patterns:
                match = re.search(pattern, message_body, re.IGNORECASE | re.MULTILINE)
                if match:
                    price_str = match.group(1).replace(',', '')
                    order_info['total_price'] = float(price_str)
                    print(f"Found total price: ${order_info['total_price']}")
                    break
            
            # Extract shipping price
            shipping_patterns = [
                r"Shipping\s*price:\s*\$?(\d+\.\d{2})",
                r"Shipping\s*cost:\s*\$?(\d+\.\d{2})",
                r"Shipping\s*amount:\s*\$?(\d+\.\d{2})",
                r"Shipping\s*price:\s*\$?([\d,]+\.\d{2})",
                r"Shipping\s*cost:\s*\$?([\d,]+\.\d{2})",
                r"Shipping\s*amount:\s*\$?([\d,]+\.\d{2})"
            ]
            
            for pattern in shipping_patterns:
                match = re.search(pattern, message_body, re.IGNORECASE | re.MULTILINE)
                if match:
                    price_str = match.group(1).replace(',', '')
                    order_info['shipping_price'] = float(price_str)
                    print(f"Found shipping price: ${order_info['shipping_price']}")
                    break
            
            # Extract image URL
            image_patterns = [
                r'<img[^>]+src="([^"]+)"',
                r'image\s*URL:\s*(https?://[^\s]+)',
                r'Image\s*link:\s*(https?://[^\s]+)',
                r'src="(https?://[^"]+\.(?:jpg|jpeg|png|gif))"',
                r'<img[^>]+src="(https?://[^"]+)"'
            ]
            
            for pattern in image_patterns:
                match = re.search(pattern, message_body, re.IGNORECASE | re.MULTILINE)
                if match:
                    order_info['image_url'] = match.group(1).strip()
                    print(f"Found image URL: {order_info['image_url']}")
                    break
            
            # Verify we found at least some information
            if any(order_info.values()):
                print("Successfully parsed eBay order")
                return order_info
            else:
                print("No order information found in email")
                return None
                
        except Exception as e:
            print(f"Error parsing eBay email: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None

    def _parse_amazon_email(self, message_body):
        """Parse Amazon sale email content"""
        # Updated patterns to match more email formats
        order_patterns = [
            r"Order\s*#:\s*(.*?)(?:\n|$)",
            r"Order\s*Number:\s*(.*?)(?:\n|$)",
            r"Amazon\s*Order\s*ID:\s*(.*?)(?:\n|$)"
        ]
        item_patterns = [
            r"Item:\s*(.*?)(?:\n|$)",
            r"Product:\s*(.*?)(?:\n|$)",
            r"Title:\s*(.*?)(?:\n|$)"
        ]
        sku_patterns = [
            r"SKU:\s*(.*?)(?:\n|$)",
            r"ASIN:\s*(.*?)(?:\n|$)",
            r"Item\s*Number:\s*(.*?)(?:\n|$)"
        ]
        price_patterns = [
            r"Total\s*price:\s*\$?(\d+\.\d{2})",
            r"Total\s*amount:\s*\$?(\d+\.\d{2})",
            r"Amount\s*paid:\s*\$?(\d+\.\d{2})",
            r"Total\s*price:\s*\$?([\d,]+\.\d{2})",
            r"Total\s*amount:\s*\$?([\d,]+\.\d{2})",
            r"Amount\s*paid:\s*\$?([\d,]+\.\d{2})"
        ]
        
        # Try each pattern
        order_id = None
        item_name = None
        sku = None
        total_price = None
        
        for pattern in order_patterns:
            match = re.search(pattern, message_body, re.IGNORECASE)
            if match:
                order_id = match.group(1).strip()
                break
                
        for pattern in item_patterns:
            match = re.search(pattern, message_body, re.IGNORECASE)
            if match:
                item_name = match.group(1).strip()
                break
                
        for pattern in sku_patterns:
            match = re.search(pattern, message_body, re.IGNORECASE)
            if match:
                sku = match.group(1).strip()
                break
                
        for pattern in price_patterns:
            match = re.search(pattern, message_body, re.IGNORECASE)
            if match:
                price_str = match.group(1).replace(',', '')
                total_price = float(price_str)
                break
        
        if order_id or item_name or sku:
            print(f"Parsed Amazon order: Order={order_id}, Item={item_name}, SKU={sku}, Price={total_price}")
            return {
                'platform': 'Amazon',
                'item_name': item_name,
                'order_id': order_id,
                'sku': sku,
                'total_price': total_price
            }
        return None

    def _extract_email_body(self, msg_payload):
        """Extract email body content, handling different formats including forwarded emails"""
        try:
            body = ""
            
            # First try to get the full message
            if 'parts' in msg_payload:
                for part in msg_payload['parts']:
                    # Check content type
                    content_type = part.get('mimeType', '').lower()
                    print(f"Found part with content type: {content_type}")
                    
                    if content_type == 'text/plain':
                        try:
                            part_body = base64.urlsafe_b64decode(
                                part['body']['data']
                            ).decode('utf-8')
                            print("Successfully decoded text/plain part")
                            
                            # Check for forwarded content indicators
                            if any(indicator in part_body.lower() for indicator in [
                                'forwarded message',
                                'begin forwarded message',
                                'original message',
                                '--- forwarded message ---'
                            ]):
                                print("Found forwarded email content")
                                # Try to extract the original message
                                lines = part_body.split('\n')
                                original_content_started = False
                                for line in lines:
                                    if any(indicator in line.lower() for indicator in [
                                        'forwarded message',
                                        'original message',
                                        '--- forwarded message ---'
                                    ]):
                                        original_content_started = True
                                        continue
                                    if original_content_started:
                                        body += line + '\n'
                            else:
                                body = part_body
                            
                            if body:
                                print("Successfully extracted email body")
                                return body
                        except Exception as e:
                            print(f"Error decoding text/plain part: {str(e)}")
                            continue
                    
                    elif content_type == 'text/html':
                        try:
                            html_body = base64.urlsafe_b64decode(
                                part['body']['data']
                            ).decode('utf-8')
                            print("Found HTML content, attempting to extract text")
                            
                            # Basic HTML to text conversion
                            text_body = re.sub(r'<[^>]+>', '', html_body)
                            text_body = re.sub(r'\s+', ' ', text_body).strip()
                            
                            if text_body:
                                print("Successfully extracted text from HTML")
                                return text_body
                        except Exception as e:
                            print(f"Error processing HTML part: {str(e)}")
                            continue
            
            # If no parts or failed to decode, try the main body
            if not body and 'body' in msg_payload and 'data' in msg_payload['body']:
                try:
                    body = base64.urlsafe_b64decode(
                        msg_payload['body']['data']
                    ).decode('utf-8')
                    print("Successfully decoded email body from main payload")
                except Exception as e:
                    print(f"Error decoding main body: {str(e)}")
            
            return body
            
        except Exception as e:
            print(f"Error extracting email body: {str(e)}")
            return ""

    def check_emails(self, force_full_search=False):
        """Check for new sales emails
        
        Args:
            force_full_search (bool): If True, search the full window regardless of last check time
        """
        try:
            print("\n=== Starting Email Check ===")
            print(f"Current time: {datetime.now()}")
            
            # Calculate search window
            if force_full_search or self.last_check_time is None:
                search_after = datetime.now() - timedelta(days=self.search_window_days)
                print(f"Performing full search of last {self.search_window_days} days")
            else:
                search_after = self.last_check_time
                print(f"Searching since last check: {self.last_check_time}")
            
            search_after_str = search_after.strftime('%Y/%m/%d')
            print(f"Search date range: {search_after_str} to {datetime.now().strftime('%Y/%m/%d')}")
            
            # Search for emails from eBay and Amazon - check all emails, not just unread
            query = f'from:ebay@ebay.com OR from:amazon.com after:{search_after_str}'
            print(f"Gmail query: {query}")
            
            print("Making API call to Gmail...")
            results = self.gmail_service.users().messages().list(
                userId='me',
                q=query,
                maxResults=50  # Increase max results to ensure we get all emails
            ).execute()
            
            messages = results.get('messages', [])
            print(f"API Response: Found {len(messages)} messages to process")
            
            if not messages:
                print("No messages found matching the criteria")
                return []
            
            new_orders = []
            print("\nProcessing individual messages:")
            
            for i, message in enumerate(messages, 1):
                print(f"\nProcessing message {i}/{len(messages)}")
                print(f"Message ID: {message['id']}")
                
                msg = self.gmail_service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='full'
                ).execute()
                
                # Get email body
                if 'payload' in msg:
                    print("Message payload found")
                    headers = msg['payload'].get('headers', [])
                    
                    # Log all headers for debugging
                    print("\nEmail headers:")
                    for header in headers:
                        print(f"{header['name']}: {header['value']}")
                    
                    # Get the original sender from headers
                    original_sender = None
                    for header in headers:
                        if header['name'].lower() == 'from':
                            original_sender = header['value'].lower()
                            break
                    
                    if original_sender:
                        print(f"\nOriginal sender: {original_sender}")
                        
                        # Use the new email body extraction method
                        body = self._extract_email_body(msg['payload'])
                        
                        if body:
                            print("Attempting to parse email...")
                            # Check for eBay senders
                            if 'ebay@ebay.com' in original_sender:
                                print("Detected eBay email")
                                order_info = self._parse_ebay_email(body, headers)
                            elif 'amazon.com' in original_sender:
                                print("Detected Amazon email")
                                order_info = self._parse_amazon_email(body)
                            else:
                                print("Email not from ebay@ebay.com or Amazon, skipping")
                                continue
                            
                            if order_info:
                                print(f"Successfully parsed order: {order_info}")
                                new_orders.append(order_info)
                            else:
                                print("Failed to parse order information")
                        else:
                            print("No email body found to parse")
                    else:
                        print("No 'From' header found in email")
                else:
                    print("No payload found in message")
            
            print(f"\n=== Email Check Complete ===")
            print(f"Total new orders found: {len(new_orders)}")
            self.current_orders.extend(new_orders)
            self.last_check_time = datetime.now()
            
            return new_orders
            
        except Exception as e:
            print(f"\n=== Error in Email Check ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            import traceback
            print("Full traceback:")
            print(traceback.format_exc())
            return []

    def send_orders_report(self, recipient_email):
        """Send email report of current orders"""
        try:
            if not self.current_orders:
                return True  # Nothing to report
                
            # Create email content
            email_body = "Current Orders Report\n\n"
            for order in self.current_orders:
                email_body += f"Platform: {order['platform']}\n"
                email_body += f"Item: {order['item_name']}\n"
                email_body += f"SKU: {order['sku']}\n"
                if 'buyer_name' in order:
                    email_body += f"Buyer: {order['buyer_name']}\n"
                if 'order_id' in order:
                    email_body += f"Order ID: {order['order_id']}\n"
                email_body += "\n"
            
            message = MIMEText(email_body)
            message['to'] = recipient_email
            message['subject'] = f"Orders Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')
            
            self.gmail_service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            return True
            
        except Exception as e:
            print(f"Error sending orders report: {e}")
            return False

    def clear_current_orders(self):
        """Clear the current orders list"""
        self.current_orders = [] 