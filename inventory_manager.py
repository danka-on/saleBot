import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime

class InventoryManager:
    def __init__(self, sheets_service):
        self.sheets_service = sheets_service
        self.inventory_sheet_id = os.getenv('INVENTORY_SHEET_ID')
        self.sales_sheet_id = os.getenv('SALES_SHEET_ID')
        
    def generate_barcode(self, sku, location_code):
        """Generate a barcode with location information"""
        # Create barcode
        code128 = barcode.get('code128', f"{sku}-{location_code}", writer=ImageWriter())
        
        # Save barcode to file
        filename = code128.save(f'barcodes/{sku}_{location_code}')
        
        # Open the image to add location text
        img = Image.open(filename)
        draw = ImageDraw.Draw(img)
        
        # Add location text
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
            
        draw.text((10, img.height - 30), f"Location: {location_code}", fill='black', font=font)
        
        # Save modified image
        img.save(filename)
        return filename

    def add_inventory_item(self, sku, name, location_code, quantity):
        """Add new item to inventory"""
        try:
            values = [[datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                      sku, name, location_code, quantity]]
            
            body = {
                'values': values
            }
            
            result = self.sheets_service.spreadsheets().values().append(
                spreadsheetId=self.inventory_sheet_id,
                range='Inventory!A:E',
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            return True
        except Exception as e:
            print(f"Error adding inventory item: {e}")
            return False

    def update_inventory_quantity(self, sku, quantity_change):
        """Update inventory quantity"""
        try:
            # Get current inventory
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.inventory_sheet_id,
                range='Inventory!A:E'
            ).execute()
            
            rows = result.get('values', [])
            for i, row in enumerate(rows):
                if row[1] == sku:  # SKU is in column B
                    current_quantity = int(row[4])  # Quantity is in column E
                    new_quantity = current_quantity + quantity_change
                    
                    if new_quantity < 0:
                        return False, "Insufficient inventory"
                    
                    # Update quantity
                    body = {
                        'values': [[new_quantity]]
                    }
                    
                    self.sheets_service.spreadsheets().values().update(
                        spreadsheetId=self.inventory_sheet_id,
                        range=f'Inventory!E{i+1}',
                        valueInputOption='USER_ENTERED',
                        body=body
                    ).execute()
                    
                    return True, f"Updated quantity to {new_quantity}"
            
            return False, "SKU not found"
        except Exception as e:
            print(f"Error updating inventory: {e}")
            return False, str(e)

    def log_sale(self, date, buyer_name, item_name, sku, tracking_number, found_in_inventory=True):
        """Log a sale in the sales database"""
        try:
            values = [[date.strftime('%Y-%m-%d %H:%M:%S'), 
                      buyer_name, item_name, sku, tracking_number, 
                      'Yes' if found_in_inventory else 'No']]
            
            body = {
                'values': values
            }
            
            result = self.sheets_service.spreadsheets().values().append(
                spreadsheetId=self.sales_sheet_id,
                range='Sales!A:F',
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            return True
        except Exception as e:
            print(f"Error logging sale: {e}")
            return False

    def get_inventory_location(self, sku):
        """Get location of an item by SKU"""
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.inventory_sheet_id,
                range='Inventory!A:E'
            ).execute()
            
            rows = result.get('values', [])
            for row in rows:
                if row[1] == sku:  # SKU is in column B
                    return row[3]  # Location is in column D
            
            return None
        except Exception as e:
            print(f"Error getting inventory location: {e}")
            return None 