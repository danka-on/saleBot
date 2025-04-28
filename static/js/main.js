// API Connection Status
function updateConnectionStatus() {
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            document.getElementById('gmail-status').className = 
                'status-indicator ' + (data.gmail_connected ? 'connected' : 'disconnected');
            document.getElementById('sheets-status').className = 
                'status-indicator ' + (data.sheets_connected ? 'connected' : 'disconnected');
        });
}

// Connect APIs
document.getElementById('connect-gmail').addEventListener('click', () => {
    fetch('/api/connect/gmail', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateConnectionStatus();
            } else {
                alert('Failed to connect Gmail API');
            }
        });
});

document.getElementById('connect-sheets').addEventListener('click', () => {
    fetch('/api/connect/sheets', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateConnectionStatus();
            } else {
                alert('Failed to connect Sheets API');
            }
        });
});

// Email Check Interval
let checkInterval = parseInt(document.getElementById('check-interval').value);
let lastCheckTime = 'Never';

document.getElementById('check-interval').addEventListener('change', (e) => {
    checkInterval = parseInt(e.target.value);
});

// Manual Email Check
document.getElementById('check-now').addEventListener('click', () => {
    const searchWindow = document.getElementById('search-window').value;
    fetch('/api/check-emails', { 
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            force_full_search: false,
            search_window_days: parseInt(searchWindow)
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('order-count').textContent = data.order_count;
            document.getElementById('last-check-time').textContent = new Date().toLocaleString();
            
            // Show results
            const resultsDiv = document.getElementById('email-check-results');
            resultsDiv.style.display = 'block';
            document.getElementById('new-orders-count').textContent = data.order_count;
            
            // Update status
            updateStatus();
        } else {
            alert('Error checking emails: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        alert('Error checking emails: ' + error);
    });
});

// Force full search
document.getElementById('force-check').addEventListener('click', () => {
    const searchWindow = document.getElementById('search-window').value;
    fetch('/api/check-emails', { 
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            force_full_search: true,
            search_window_days: parseInt(searchWindow)
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('order-count').textContent = data.order_count;
            document.getElementById('last-check-time').textContent = new Date().toLocaleString();
            
            // Show results
            const resultsDiv = document.getElementById('email-check-results');
            resultsDiv.style.display = 'block';
            document.getElementById('new-orders-count').textContent = 
                data.order_count - parseInt(document.getElementById('order-count').textContent);
            
            // Update status
            updateStatus();
        } else {
            alert('Error checking emails: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        alert('Error checking emails: ' + error);
    });
});

// View Orders
document.getElementById('view-orders').addEventListener('click', () => {
    window.location.href = '/orders';
});

// View Sheets
document.getElementById('view-sheets').addEventListener('click', () => {
    window.location.href = '/sheets';
});

// Send Orders Report
document.getElementById('send-orders').addEventListener('click', () => {
    const recipientEmail = document.getElementById('recipient-email').value;
    if (!recipientEmail) {
        alert('Please enter a recipient email address');
        return;
    }

    fetch('/api/send-orders-report', { 
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            recipient_email: recipientEmail
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Orders report sent successfully to ' + recipientEmail);
        } else {
            alert('Error sending orders report: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        alert('Error sending orders report: ' + error);
    });
});

// Initial status check
updateConnectionStatus(); 