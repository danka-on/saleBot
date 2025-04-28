# Inventory Management System

A comprehensive inventory management system with barcode generation, email monitoring, and Google Sheets integration.

## Features

- Barcode generation for inventory items
- Location-based inventory tracking
- eBay and Amazon sales email monitoring
- Google Sheets integration for inventory and sales tracking
- Automated health monitoring
- Email reporting system

## Prerequisites

- Python 3.8+
- Google Cloud Platform account with Gmail and Sheets API enabled
- Google API credentials (OAuth 2.0 Client ID)
- Google Sheets set up for inventory and sales tracking

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your configuration:
   ```bash
   cp .env.example .env
   ```

## Google Sheets Setup

1. Create three Google Sheets:
   - Inventory Sheet with columns:
     - Date
     - SKU
     - Name
     - Location
     - Quantity
   - Sales Sheet with columns:
     - Date
     - Buyer Name
     - Item Name
     - SKU
     - Tracking Number
     - Found in Inventory
   - Test Sheet for health checks

2. Share the sheets with your service account email

## Configuration

Edit the `.env` file with your settings:

- `GOOGLE_CLIENT_ID`: Your Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Your Google OAuth client secret
- `INVENTORY_SHEET_ID`: ID of your inventory Google Sheet
- `SALES_SHEET_ID`: ID of your sales Google Sheet
- `TEST_SHEET_ID`: ID of your test Google Sheet
- `REPORT_RECIPIENT_EMAIL`: Email address for reports
- `HEALTH_CHECK_INTERVAL_HOURS`: Interval for health checks

## Usage

1. Start the application:
   ```bash
   python app.py
   ```

2. Open the web interface at `http://localhost:5000`

3. Connect your Gmail and Google Sheets accounts using the interface

4. Use the interface to:
   - Generate barcodes for inventory items
   - Monitor sales emails
   - View and manage inventory
   - Check system health status
   - Generate reports

## Barcode System

The system generates unique barcodes for:
- Packing table locations
- Garage shelf locations
- Office shelf locations

Each barcode includes:
- SKU
- Location code
- Human-readable text

## Email Monitoring

The system monitors:
- eBay sales notifications
- Amazon sales notifications
- Automatically processes order information
- Sends daily order reports

## Health Monitoring

Automated checks for:
- Gmail API connection
- Sheets API connection
- Read/write operations
- Email functionality

Health reports are sent every 12 hours (configurable)

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details 