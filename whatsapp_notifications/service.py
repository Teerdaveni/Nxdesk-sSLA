from whatsapp_notifications.whatsapp import send_text

def notify_user(mobile, message):
    """
    Sends a WhatsApp message ONLY if mobile number exists.
    """
    if not mobile:
        return {"error": "User has no mobile number"}

    # WhatsApp requires full country code (example: +91XXXXXXXXXX)
    mobile = mobile.strip()

    return send_text(mobile, message)
