from datetime import datetime
import schedule
import time
from email.mime.text import MIMEText
import base64
import os

class HealthMonitor:
    def __init__(self, gmail_service, sheets_service):
        self.gmail_service = gmail_service
        self.sheets_service = sheets_service
        self.last_health_check = None
        self.recipient_email = None

    def set_recipient_email(self, email):
        """Set email address for health reports"""
        self.recipient_email = email

    def check_gmail_connection(self):
        """Test Gmail API connection"""
        try:
            # Try to list labels as a simple test
            self.gmail_service.users().labels().list(userId='me').execute()
            return True
        except Exception as e:
            print(f"Gmail connection error: {e}")
            return False

    def check_sheets_connection(self):
        """Test Sheets API connection"""
        try:
            # Try to get spreadsheet metadata as a simple test
            self.sheets_service.spreadsheets().get(
                spreadsheetId=os.getenv('INVENTORY_SHEET_ID')
            ).execute()
            return True
        except Exception as e:
            print(f"Sheets connection error: {e}")
            return False

    def test_sheets_write(self):
        """Test writing to sheets"""
        try:
            test_sheet_id = os.getenv('TEST_SHEET_ID')
            test_value = [[f"Health check: {datetime.now()}"]]
            
            self.sheets_service.spreadsheets().values().append(
                spreadsheetId=test_sheet_id,
                range='HealthChecks!A:A',
                valueInputOption='USER_ENTERED',
                body={'values': test_value}
            ).execute()
            
            return True
        except Exception as e:
            print(f"Sheets write test error: {e}")
            return False

    def send_test_email(self):
        """Test sending email"""
        try:
            message = MIMEText(f"Health check test email: {datetime.now()}")
            message['to'] = self.recipient_email
            message['subject'] = "Health Check Test"
            
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')
            
            self.gmail_service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            return True
        except Exception as e:
            print(f"Email test error: {e}")
            return False

    def run_health_check(self):
        """Run all health checks and send report"""
        if not self.recipient_email:
            print("No recipient email set for health reports")
            return False
            
        results = {
            'gmail_connection': self.check_gmail_connection(),
            'sheets_connection': self.check_sheets_connection(),
            'sheets_write': self.test_sheets_write(),
            'email_send': self.send_test_email()
        }
        
        # Create health report
        report_body = "System Health Report\n\n"
        report_body += f"Time: {datetime.now()}\n\n"
        
        for test, result in results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            report_body += f"{test}: {status}\n"
        
        # Send report
        try:
            message = MIMEText(report_body)
            message['to'] = self.recipient_email
            message['subject'] = f"Health Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')
            
            self.gmail_service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            self.last_health_check = datetime.now()
            return True
            
        except Exception as e:
            print(f"Error sending health report: {e}")
            return False

    def schedule_health_checks(self, interval_hours=12):
        """Schedule periodic health checks"""
        schedule.every(interval_hours).hours.do(self.run_health_check)
        
        while True:
            schedule.run_pending()
            time.sleep(60) 