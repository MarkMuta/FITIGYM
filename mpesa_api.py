import requests
import base64
import datetime
import os

# Try different import approaches for dotenv
try:
    from dotenv import load_dotenv
except ImportError:
    # If python-dotenv is not available, create a simple implementation
    def load_dotenv():
        with open('.env', 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
        print("Using custom dotenv loader")

# Load environment variables from .env file
load_dotenv()

# --- M-Pesa API Credentials ---
CONSUMER_KEY = os.getenv('CONSUMER_KEY')
CONSUMER_SECRET = os.getenv('CONSUMER_SECRET')
SHORTCODE = os.getenv('SHORTCODE')
PASSKEY = os.getenv('PASSKEY')
CALLBACK_URL = os.getenv('CALLBACK_URL')

def get_access_token():
    AUTH_URL = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
    try:
        response = requests.get(AUTH_URL, auth=(CONSUMER_KEY, CONSUMER_SECRET))
        response.raise_for_status()
        return response.json()['access_token']
    except requests.exceptions.RequestException as e:
        print(f"Error getting access token: {e}")
        return None

def generate_password(timestamp):
    data_to_encode = SHORTCODE + PASSKEY + timestamp
    return base64.b64encode(data_to_encode.encode()).decode('utf-8')

def initiate_stk_push(phone_number, amount, account_reference, transaction_desc):
    STK_PUSH_URL = 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    password = generate_password(timestamp)
    access_token = get_access_token()

    if not access_token:
        return {"success": False, "message": "Failed to get M-Pesa access token"}

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    payload = {
        'BusinessShortCode': SHORTCODE,
        'Password': password,
        'Timestamp': timestamp,
        'TransactionType': 'CustomerPayBillOnline',
        'Amount': amount,
        'PartyA': phone_number,
        'PartyB': SHORTCODE,
        'PhoneNumber': phone_number,
        'CallBackURL': CALLBACK_URL,
        'AccountReference': account_reference,
        'TransactionDesc': transaction_desc
    }

    try:
        response = requests.post(STK_PUSH_URL, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error initiating STK Push: {e}")
        return {"success": False, "message": str(e)}
