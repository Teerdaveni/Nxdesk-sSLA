# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from timer.models import Ticket
# from .tasks import send_whatsapp_text_task

# def clean_number(mobile):
#     if not mobile:
#         return None
#     return str(mobile).replace("+", "").replace(" ", "").replace("-", "")

# @receiver(post_save, sender=Ticket)
# def ticket_notifications(sender, instance, created, **kwargs):

#     assignee = instance.assignee
#     mobile = clean_number(getattr(assignee, "mobile", None))

#     if not mobile:
#         return

#     # 1️⃣ Ticket Created
#     if created:
#         msg = f"🎫 New Ticket Assigned:\nID: {instance.ticket_id}\n{instance.summary}"
#         send_whatsapp_text_task.delay(mobile, msg, ticket_id=str(instance.ticket_id))
#         return

#     # Fetch old data
#     try:
#         old = Ticket.objects.get(pk=instance.ticket_id)
#     except Ticket.DoesNotExist:
#         old = None

#     # 2️⃣ Assignment changed
#     if old and old.assignee != instance.assignee:
#         msg = f"👤 You are now assigned to Ticket {instance.ticket_id}"
#         send_whatsapp_text_task.delay(mobile, msg, ticket_id=str(instance.ticket_id))

#     # 3️⃣ Status changed
#     if old and old.status != instance.status:
#         msg = f"🔄 Ticket {instance.ticket_id} status changed to: {instance.status}"
#         send_whatsapp_text_task.delay(mobile, msg, ticket_id=str(instance.ticket_id))

#     # 4️⃣ Resolved
#     if instance.status == "Resolved" and (not old or old.status != "Resolved"):
#         msg = f"✅ Ticket {instance.ticket_id} is resolved."
#         send_whatsapp_text_task.delay(mobile, msg, ticket_id=str(instance.ticket_id))
