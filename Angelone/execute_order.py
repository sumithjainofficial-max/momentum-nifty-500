import os
import sys
import pyotp
from SmartApi import SmartConnect

def place_cdsl_order():
    env_file = r"E:\SUMITH'S PROJECT\GOOGLE CLOUD\MOMENTUM NIFFTY 500\Angelone\CREDENTIALS.env"
    creds = {}
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                creds[k.strip()] = v.strip().strip('"').strip("'")

    api_key = creds.get('ANGEL_API_KEY')
    client_id = creds.get('ANGEL_CLIENT_CODE') or creds.get('ANGEL_CLIENT_ID')
    pin = creds.get('ANGEL_PIN')
    totp_secret = creds.get('ANGEL_TOTP_SECRET') or creds.get('ANGEL_TOTP_KEY')

    print(f"[*] Initializing SmartConnect for Client ID: {client_id}...")
    smart_api = SmartConnect(api_key=api_key)

    totp = pyotp.TOTP(totp_secret).now()
    data = smart_api.generateSession(client_id, pin, totp)

    if not data or not data.get('status'):
        print(f"[!] Login failed: {data}")
        return False

    print(f"[✓] Angel One session authenticated successfully!")

    # Check Margin / Funds
    try:
        rms = smart_api.rmsLimit()
        if rms and rms.get('status'):
            net_avail = float(rms['data'].get('net', 0))
            print(f"[i] Available Cash Margin in Demat: INR {net_avail:,.2f}")
    except Exception as e:
        print(f"[!] Warning reading RMS: {e}")

    # Order parameters for CDSL
    order_params = {
        "variety": "NORMAL",
        "tradingsymbol": "CDSL-EQ",
        "symboltoken": "21174",
        "transactiontype": "BUY",
        "exchange": "NSE",
        "ordertype": "LIMIT",
        "producttype": "DELIVERY",
        "duration": "DAY",
        "price": "1348.00",
        "squareoff": "0",
        "stoploss": "0",
        "quantity": "37"
    }

    print(f"[*] Placing LIVE Delivery BUY Order on NSE...")
    print(f"    Symbol: CDSL-EQ (Token: 21174)")
    print(f"    Quantity: 37 Shares")
    print(f"    Price: INR 1,348.00")
    print(f"    Total Value: INR {37 * 1348.00:,.2f}")

    order_resp = smart_api.placeOrder(order_params)
    print(f"[*] Order Response: {order_resp}")

    if order_resp and isinstance(order_resp, dict) and order_resp.get('status'):
        order_id = order_resp.get('data', {}).get('orderid', 'CONFIRMED')
        print(f"[✓] SUCCESS! Order placed successfully. Order ID: {order_id}")
        return True, order_id
    elif isinstance(order_resp, str):
        print(f"[✓] SUCCESS! Order placed successfully. Order ID: {order_resp}")
        return True, order_resp
    else:
        print(f"[!] Order placement returned: {order_resp}")
        return False, order_resp

if __name__ == '__main__':
    place_cdsl_order()
