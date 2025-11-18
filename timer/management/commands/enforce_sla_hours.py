"""
Management command to dynamically enforce working hours on SLAs.

- Auto-pause Active timers when outside working hours
- Auto-resume Paused timers when within working hours (except when ticket is waiting for user)
- Optionally activate Scheduled timers now if hours allow

Run:
  python manage.py enforce_sla_hours
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
import pytz

from timer.models import SLATimer, Holiday


class Command(BaseCommand):
    help = "Enforce SLA working hours: auto-pause/resume/activate based on current time"

    def handle(self, *args, **options):
        count_paused = 0
        count_resumed = 0
        count_activated = 0

        now_utc = timezone.now()

        for sla in SLATimer.objects.select_related('ticket').all():
            ticket = sla.ticket
            if not ticket:
                continue

            # Resolve working hours via same hierarchy used elsewhere
            wh = getattr(sla, 'working_hours', None)
            if not wh:
                ticket_org = getattr(ticket, 'ticket_organization', None)
                if ticket_org:
                    wh = getattr(ticket_org, 'working_hours', None)
            if not wh:
                assignee = getattr(ticket, 'assignee', None)
                if assignee:
                    assignee_org = getattr(assignee, 'organisation', None)
                    if assignee_org:
                        wh = getattr(assignee_org, 'working_hours', None)

            # Default: if no working hours configured, skip enforcement
            if not wh:
                continue

            tz = pytz.timezone('Asia/Kolkata')
            now_local = now_utc.astimezone(tz)

            # Compute working days list
            working_days = []
            wd_raw = getattr(wh, 'working_days', None)
            if isinstance(wd_raw, str):
                import json
                try:
                    parsed = json.loads(wd_raw)
                    if isinstance(parsed, list):
                        working_days = [int(d) for d in parsed]
                except Exception:
                    working_days = [int(d.strip()) for d in wd_raw.split(',') if d.strip().isdigit()]
            elif isinstance(wd_raw, (list, tuple)):
                try:
                    working_days = [int(d) for d in wd_raw]
                except Exception:
                    working_days = []
            if not working_days:
                working_days = [0,1,2,3,4]

            # Determine if now is within working hours considering days/holidays
            is_working_day = now_local.weekday() in working_days
            is_holiday = Holiday.objects.filter(working_hours=wh, date=now_local.date()).exists()
            within_time = wh.start_hour <= now_local.time() <= wh.end_hour
            within_hours = is_working_day and not is_holiday and within_time

            # Active -> Schedule to next working day if outside hours
            if sla.sla_status == 'Active' and not within_hours:
                sla.pause_sla(auto_schedule=True)
                count_paused += 1
                continue

            # Paused or Scheduled -> Resume/Activate if within hours and not waiting state
            if sla.sla_status in ['Paused', 'Scheduled'] and within_hours:
                if str(ticket.status).lower() in ['waiting for user response']:
                    continue
                    
                # Try to activate scheduled tickets if enough time remains
                if sla.sla_status == 'Scheduled':
                    try:
                        if sla.maybe_activate_now():
                            count_activated += 1
                            continue
                    except Exception:
                        pass
                
                # Resume paused tickets
                if sla.sla_status == 'Paused':
                    sla.resume_sla()
                    count_resumed += 1
                    continue

        self.stdout.write(self.style.SUCCESS(
            f"Enforcement complete: paused={count_paused}, resumed={count_resumed}, activated={count_activated}"
        ))
