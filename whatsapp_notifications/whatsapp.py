# import requests
# from django.conf import settings

# WA_PHONE_NUMBER_ID = settings.WA_PHONE_NUMBER_ID
# WA_ACCESS_TOKEN = settings.WA_ACCESS_TOKEN
# WA_API_VERSION = settings.WA_API_VERSION

# BASE_URL = f"https://graph.facebook.com/{WA_API_VERSION}/{WA_PHONE_NUMBER_ID}/messages"

# HEADERS = {
#     "Authorization": f"Bearer {WA_ACCESS_TOKEN}",
#     "Content-Type": "application/json",
# }

# def post_to_whatsapp(payload):
#     resp = requests.post(BASE_URL, headers=HEADERS, json=payload)
#     try:
#         return resp.status_code, resp.json()
#     except ValueError:
#         return resp.status_code, {"raw": resp.text}

# def send_text(to, message):
#     payload = {
#         "messaging_product": "whatsapp",
#         "to": to,
#         "type": "text",
#         "text": {"body": message},
#     }
#     return post_to_whatsapp(payload)

import requests
from django.conf import settings

# Load from settings.py (values from .env)
WA_PHONE_NUMBER_ID = settings.WA_PHONE_NUMBER_ID
WA_ACCESS_TOKEN = settings.WA_ACCESS_TOKEN
WA_API_VERSION = settings.WA_API_VERSION

# API Endpoint for sending WhatsApp messages
BASE_URL = f"https://graph.facebook.com/{WA_API_VERSION}/{WA_PHONE_NUMBER_ID}/messages"

HEADERS = {
    "Authorization": f"Bearer {WA_ACCESS_TOKEN}",
    "Content-Type": "application/json",
}

def post_to_whatsapp(payload):
    """
    Sends the payload to WhatsApp Cloud API and returns status + response
    """
    resp = requests.post(BASE_URL, headers=HEADERS, json=payload)
    try:
        return resp.status_code, resp.json()
    except ValueError:
        return resp.status_code, {"raw": resp.text}

def send_text(to, message):
    """
    Send a simple text WhatsApp message.
    """
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message},
    }
    return post_to_whatsapp(payload)
