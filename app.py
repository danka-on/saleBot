from flask import Flask, render_template, jsonify, request, send_file
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
import pickle
import datetime
from dotenv import load_dotenv
import threading
from inventory_manager import InventoryManager
from email_monitor import EmailMonitor
from health_monitor import HealthMonitor

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Google API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/spreadsheets'
]

class APIConnection:
    def __init__(self):
        self.gmail_service = None
        self.sheets_service = None
        self.credentials = None
        self.inventory_manager = None
        self.email_monitor = None
        self.health_monitor = None
        self._http = None

    def _create_authorized_http(self, creds):
        import httplib2
        import ssl
        import certifi
        from google_auth_httplib2 import AuthorizedHttp
        
        # Create a custom SSL context
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Create base HTTP object with custom SSL context
        http = httplib2.Http(
            timeout=30,
            disable_ssl_certificate_validation=True,
            ca_certs=certifi.where()
        )
        
        # Create authorized HTTP client
        return AuthorizedHttp(creds, http=http)

    def get_credentials(self):
        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        
        self.credentials = creds
        return creds

    def connect_gmail(self):
        try:
            creds = self.get_credentials()
            if not self._http:
                self._http = self._create_authorized_http(creds)
            
            # Build service with authorized HTTP client
            self.gmail_service = build('gmail', 'v1', http=self._http)
            
            if not self.email_monitor:
                self.email_monitor = EmailMonitor(self.gmail_service)
            return True
        except Exception as e:
            print(f"Gmail connection error: {e}")
            return False

    def connect_sheets(self):
        try:
            creds = self.get_credentials()
            if not self._http:
                self._http = self._create_authorized_http(creds)
            
            # Build service with authorized HTTP client
            self.sheets_service = build('sheets', 'v4', http=self._http)
            
            if not self.inventory_manager:
                self.inventory_manager = InventoryManager(self.sheets_service)
            return True
        except Exception as e:
            print(f"Sheets connection error: {e}")
            return False

    def setup_health_monitor(self):
        if self.gmail_service and self.sheets_service and not self.health_monitor:
            self.health_monitor = HealthMonitor(self.gmail_service, self.sheets_service)
            self.health_monitor.set_recipient_email(os.getenv('REPORT_RECIPIENT_EMAIL'))
            # Start health check thread
            health_thread = threading.Thread(
                target=self.health_monitor.schedule_health_checks,
                args=(int(os.getenv('HEALTH_CHECK_INTERVAL_HOURS', 12)),)
            )
            health_thread.daemon = True
            health_thread.start()

    def clear_credentials(self):
        """Clear all existing credentials and services"""
        self.gmail_service = None
        self.sheets_service = None
        self.credentials = None
        self.inventory_manager = None
        self.email_monitor = None
        self.health_monitor = None
        # Remove the token file if it exists
        if os.path.exists('token.pickle'):
            os.remove('token.pickle')
        return True

api_connection = APIConnection()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/connect/gmail', methods=['POST'])
def connect_gmail():
    success = api_connection.connect_gmail()
    if success and api_connection.sheets_service:
        api_connection.setup_health_monitor()
    return jsonify({'success': success})

@app.route('/api/connect/sheets', methods=['POST'])
def connect_sheets():
    success = api_connection.connect_sheets()
    if success and api_connection.gmail_service:
        api_connection.setup_health_monitor()
    return jsonify({'success': success})

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        'gmail_connected': api_connection.gmail_service is not None,
        'sheets_connected': api_connection.sheets_service is not None
    })

@app.route('/api/check-emails', methods=['POST'])
def check_emails():
    try:
        data = request.get_json()
        force_full_search = data.get('force_full_search', False)
        search_window_days = data.get('search_window_days', 7)
        
        if not api_connection.email_monitor:
            return jsonify({'success': False, 'error': 'Email monitor not initialized'})
            
        # Update search window if provided
        if search_window_days:
            api_connection.email_monitor.search_window_days = search_window_days
            
        # Check emails
        new_orders = api_connection.email_monitor.check_emails(force_full_search=force_full_search)
        
        return jsonify({
            'success': True,
            'order_count': len(api_connection.email_monitor.current_orders),
            'new_orders': len(new_orders)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/send-orders-report', methods=['POST'])
def send_orders_report():
    if not api_connection.email_monitor:
        return jsonify({'success': False, 'error': 'Email monitor not initialized'})
    
    data = request.get_json()
    recipient_email = data.get('recipient_email')
    
    if not recipient_email:
        return jsonify({'success': False, 'error': 'No recipient email provided'})
    
    success = api_connection.email_monitor.send_orders_report(recipient_email)
    return jsonify({'success': success})

@app.route('/api/inventory/add', methods=['POST'])
def add_inventory():
    if not api_connection.inventory_manager:
        return jsonify({'success': False, 'error': 'Inventory manager not initialized'})
    
    data = request.json
    success = api_connection.inventory_manager.add_inventory_item(
        data['sku'],
        data['name'],
        data['location_code'],
        data['quantity']
    )
    return jsonify({'success': success})

@app.route('/api/inventory/update', methods=['POST'])
def update_inventory():
    if not api_connection.inventory_manager:
        return jsonify({'success': False, 'error': 'Inventory manager not initialized'})
    
    data = request.json
    success, message = api_connection.inventory_manager.update_inventory_quantity(
        data['sku'],
        data['quantity_change']
    )
    return jsonify({'success': success, 'message': message})

@app.route('/api/inventory/location/<sku>', methods=['GET'])
def get_location(sku):
    if not api_connection.inventory_manager:
        return jsonify({'success': False, 'error': 'Inventory manager not initialized'})
    
    location = api_connection.inventory_manager.get_inventory_location(sku)
    return jsonify({
        'success': True,
        'location': location
    })

@app.route('/api/barcode/generate', methods=['POST'])
def generate_barcode():
    if not api_connection.inventory_manager:
        return jsonify({'success': False, 'error': 'Inventory manager not initialized'})
    
    data = request.json
    filename = api_connection.inventory_manager.generate_barcode(
        data['sku'],
        data['location_code']
    )
    return send_file(filename, mimetype='image/png')

@app.route('/orders')
def view_orders():
    if not api_connection.email_monitor:
        return render_template('orders.html', orders=[])
    return render_template('orders.html', orders=api_connection.email_monitor.current_orders)

@app.route('/sheets')
def view_sheets():
    if not api_connection.sheets_service:
        return render_template('sheets.html', inventory_data=[], sales_data=[])
    
    try:
        # Get inventory data
        inventory_result = api_connection.sheets_service.spreadsheets().values().get(
            spreadsheetId=os.getenv('INVENTORY_SHEET_ID'),
            range='Inventory!A:E'
        ).execute()
        
        inventory_data = []
        rows = inventory_result.get('values', [])
        for row in rows[1:]:  # Skip header row
            if len(row) >= 5:
                inventory_data.append({
                    'date': row[0],
                    'sku': row[1],
                    'name': row[2],
                    'location': row[3],
                    'quantity': row[4]
                })
        
        # Get sales data
        sales_result = api_connection.sheets_service.spreadsheets().values().get(
            spreadsheetId=os.getenv('SALES_SHEET_ID'),
            range='Sales!A:F'
        ).execute()
        
        sales_data = []
        rows = sales_result.get('values', [])
        for row in rows[1:]:  # Skip header row
            if len(row) >= 6:
                sales_data.append({
                    'date': row[0],
                    'buyer_name': row[1],
                    'item_name': row[2],
                    'sku': row[3],
                    'tracking_number': row[4],
                    'found_in_inventory': row[5]
                })
        
        return render_template('sheets.html', 
                             inventory_data=inventory_data,
                             sales_data=sales_data)
    except Exception as e:
        print(f"Error fetching sheets data: {e}")
        return render_template('sheets.html', inventory_data=[], sales_data=[])

@app.route('/api/refresh-inventory', methods=['POST'])
def refresh_inventory():
    try:
        if not api_connection.sheets_service:
            return jsonify({'success': False, 'error': 'Sheets API not connected'})
            
        # Get fresh inventory data
        result = api_connection.sheets_service.spreadsheets().values().get(
            spreadsheetId=os.getenv('INVENTORY_SHEET_ID'),
            range='Inventory!A:E'
        ).execute()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/refresh-sales', methods=['POST'])
def refresh_sales():
    try:
        if not api_connection.sheets_service:
            return jsonify({'success': False, 'error': 'Sheets API not connected'})
            
        # Get fresh sales data
        result = api_connection.sheets_service.spreadsheets().values().get(
            spreadsheetId=os.getenv('SALES_SHEET_ID'),
            range='Sales!A:F'
        ).execute()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/reconnect', methods=['POST'])
def reconnect():
    success = api_connection.clear_credentials()
    return jsonify({'success': success})

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('barcodes', exist_ok=True)
    
    app.run(debug=True) 