import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Ticketing_tool.settings')
django.setup()
from django.utils import timezone
from timer.models import Ticket

import sys

ticket_id = sys.argv[1] if len(sys.argv) > 1 else 'S00000005'
try:
    t = Ticket.objects.get(ticket_id=ticket_id)
    s = t.sla_timers
    print('Ticket.status:', t.status)
    print('SLA.status:', s.sla_status)
    print('start_time (raw):', s.start_time)
    print('start_time (IST):', s.start_time.astimezone(__import__('pytz').timezone('Asia/Kolkata')) if s.start_time else None)
    print('sla_due_date (raw):', s.sla_due_date)
    print('sla_due_date (IST):', s.sla_due_date.astimezone(__import__('pytz').timezone('Asia/Kolkata')) if s.sla_due_date else None)
    print('priority.response_target_time:', getattr(t.priority, 'response_target_time', None))
    print('remaining_at_pause:', s.remaining_at_pause)
    print('total_paused_time:', s.total_paused_time)
    print('calculated remaining (get_remaining_time):', s.get_remaining_time())
    try:
        print('working_hours on SLA:', s.working_hours.id if s.working_hours else None)
    except Exception:
        print('working_hours on SLA: error')
except Exception as e:
    print('Error:', e)
