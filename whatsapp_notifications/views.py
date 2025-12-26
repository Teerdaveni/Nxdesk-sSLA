# from django.shortcuts import render

# # Create your views here.
# import json
# from django.http import JsonResponse, HttpResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.conf import settings
# from .models import WhatsAppMessageLog
# from timer.models import Ticket, TicketComment

# VERIFY_TOKEN = settings.WA_VERIFY_TOKEN

# @csrf_exempt
# def whatsapp_webhook(request):
#     if request.method == "GET":
#         if request.GET.get("hub.verify_token") == VERIFY_TOKEN:
#             return HttpResponse(request.GET.get("hub.challenge"))
#         return HttpResponse("Invalid verify token", status=403)

#     if request.method == "POST":
#         data = json.loads(request.body.decode("utf-8"))

#         for entry in data.get("entry", []):
#             for change in entry.get("changes", []):
#                 value = change.get("value", {})
#                 messages = value.get("messages", [])

#                 for msg in messages:
#                     frm = msg.get("from")
#                     text = msg.get("text", {}).get("body")

#                     WhatsAppMessageLog.objects.create(
#                         to=frm,
#                         direction="in",
#                         payload=msg
#                     )

#                     # link to latest assigned ticket
#                     ticket = Ticket.objects.filter(assignee__mobile=frm).order_by("-created_at").first()
#                     if ticket:
#                         TicketComment.objects.create(
#                             ticket=ticket,
#                             comment=f"WhatsApp: {text}",
#                             created_by=ticket.assignee,
#                             is_internal=False
#                         )

#         return JsonResponse({"status": "received"})
from django.shortcuts import render
import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import WhatsAppMessageLog
from timer.models import Ticket, TicketComment

VERIFY_TOKEN = settings.WA_VERIFY_TOKEN

@csrf_exempt
def whatsapp_webhook(request):

    # ✔ STEP 1: META WEBHOOK VERIFICATION
    if request.method == "GET":
        verify = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if verify == VERIFY_TOKEN:
            return HttpResponse(challenge)
        return HttpResponse("Invalid verify token", status=403)

    # ✔ STEP 2: HANDLE INCOMING WHATSAPP MESSAGES
    if request.method == "POST":

        try:
            raw = request.body.decode("utf-8")
            data = json.loads(raw) if raw else {}
        except Exception:
            data = {}

        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])

                for msg in messages:
                    frm = msg.get("from")
                    text = msg.get("text", {}).get("body", "")

                    WhatsAppMessageLog.objects.create(
                        to=frm,
                        direction="in",
                        payload=msg
                    )

                    # attach message to ticket based on assigneeMobile
                    ticket = Ticket.objects.filter(assignee__mobile=frm).order_by("-created_at").first()
                    if ticket:
                        TicketComment.objects.create(
                            ticket=ticket,
                            comment=f"WhatsApp: {text}",
                            created_by=ticket.assignee,
                            is_internal=False
                        )

        return JsonResponse({"status": "received"})
