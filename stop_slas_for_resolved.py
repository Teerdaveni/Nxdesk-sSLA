import os
import django
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Ticketing_tool.settings')
django.setup()

from timer.models import Ticket, SLATimer, WorkingHours, Holiday
from django.utils import timezone
import pytz

# Check ticket S00000007
ticket_id = "S00000007"
ticket = Ticket.objects.get(ticket_id=ticket_id)
sla_timer = SLATimer.objects.get(ticket=ticket)

print(f"=== TICKET CREATION & SLA TIMELINE ===\n")

# Ticket creation
tz = pytz.timezone('Asia/Kolkata')
created_at = ticket.created_at.astimezone(tz)
print(f"1. Ticket Created: {created_at}")
print(f"   - Day: {created_at.strftime('%A, %B %d, %Y')}")
print(f"   - Time: {created_at.strftime('%H:%M:%S')}")
print()

# Priority details
print(f"2. Priority: {ticket.priority.urgency_name}")
print(f"   - Response Target: {ticket.priority.response_target_time} ({ticket.priority.response_target_time.total_seconds()/3600} hours)")
print()

# SLA Timer details
sla_start = sla_timer.start_time.astimezone(tz)
print(f"3. SLA Timer Started: {sla_start}")
print(f"   - Day: {sla_start.strftime('%A, %B %d, %Y')}")
print(f"   - Time: {sla_start.strftime('%H:%M:%S')}")
print()

# Check if SLA was started outside working hours
time_diff = sla_start - created_at
print(f"4. Time between creation and SLA start: {time_diff}")
if time_diff > timedelta(minutes=1):
    print(f"   ⚠️ SLA was delayed - ticket created outside working hours")
print()

# SLA Due Date
if sla_timer.sla_due_date:
    sla_due = sla_timer.sla_due_date.astimezone(tz)
    print(f"5. SLA Due Date: {sla_due}")
    print(f"   - Day: {sla_due.strftime('%A, %B %d, %Y')}")
    print(f"   - Time: {sla_due.strftime('%H:%M:%S')}")
    
    # Calculate calendar time from start to due
    calendar_time = sla_due - sla_start
    print(f"   - Calendar time from start to due: {calendar_time}")
    print(f"   - Calendar days: {calendar_time.days} days, {calendar_time.seconds//3600} hours")
print()

# Working Hours configuration
working_hours = sla_timer.working_hours
if working_hours:
    print(f"6. Working Hours Config: {working_hours.name}")
    print(f"   - Hours: {working_hours.start_hour} - {working_hours.end_hour}")
    print(f"   - Working days: {working_hours.working_days}")
else:
    print(f"6. Working Hours: None (using default Mon-Fri 9:30-18:30)")
print()

# Check holidays between start and due
print(f"7. Holidays between {sla_start.date()} and {sla_due.date()}:")
holidays = Holiday.objects.filter(
    date__gte=sla_start.date(),
    date__lte=sla_due.date()
).order_by('date')
if holidays.exists():
    for holiday in holidays:
        print(f"   - {holiday.date} ({holiday.date.strftime('%A')}): {holiday.name}")
else:
    print(f"   - No holidays")
print()

# Current status
print(f"8. Current Status:")
print(f"   - SLA Status: {sla_timer.sla_status}")
print(f"   - Paused at: {sla_timer.paused_time.astimezone(tz) if sla_timer.paused_time else 'Not paused'}")
print(f"   - Remaining at pause: {sla_timer.remaining_at_pause}")
print(f"   - Total paused time: {sla_timer.total_paused_time}")
print()

# Calculate what SHOULD have happened
print(f"=== EXPECTED CALCULATION ===")
print(f"Starting from: {created_at}")
print(f"Target: {ticket.priority.response_target_time} ({ticket.priority.response_target_time.total_seconds()/3600} hours)")

# Simulate working hours calculation
if working_hours:
    daily_hours = (working_hours.end_hour.hour - working_hours.start_hour.hour) + \
                  (working_hours.end_hour.minute - working_hours.start_hour.minute) / 60
    print(f"Daily working hours: {daily_hours} hours")
    
    target_hours = ticket.priority.response_target_time.total_seconds() / 3600
    working_days_needed = target_hours / daily_hours
    print(f"Working days needed: {working_days_needed:.2f} days")
    
    # If 2 hours target and 8.58 hours per day, should be same day
    if target_hours <= daily_hours:
        print(f"✅ Should complete within same working day")
        print(f"Expected due: Same day as creation + {target_hours} working hours")
    else:
        print(f"❌ Requires multiple working days")
print()

# Check for calculation errors
print(f"=== ANALYSIS ===")
expected_remaining = ticket.priority.response_target_time
actual_remaining = sla_timer.remaining_at_pause

if actual_remaining and expected_remaining:
    diff = actual_remaining - expected_remaining
    print(f"Expected remaining: {expected_remaining}")
    print(f"Actual remaining: {actual_remaining}")
    print(f"Difference: {diff} ({diff.total_seconds()/3600:.2f} hours)")
    
    if abs(diff.total_seconds()) > 300:  # More than 5 minutes difference
        print(f"⚠️ SIGNIFICANT DISCREPANCY DETECTED!")
        print(f"   The SLA timer has {actual_remaining} remaining instead of expected {expected_remaining}")
