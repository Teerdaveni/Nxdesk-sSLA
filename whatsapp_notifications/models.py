from django.db import models

# Create your models here.
from django.db import models

class WhatsAppMessageLog(models.Model):
    to = models.CharField(max_length=32)
    direction = models.CharField(max_length=8, choices=(("out","out"),("in","in")))
    payload = models.JSONField(null=True, blank=True)
    response = models.JSONField(null=True, blank=True)
    ticket = models.ForeignKey("timer.Ticket", on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.direction} to {self.to} at {self.created_at}"
