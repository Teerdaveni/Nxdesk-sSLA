# utils/sla_utils.py
from datetime import datetime, timedelta

def is_holiday(date, working_hours):
    # Check holidays globally by date, not scoped to specific working_hours
    from timer.models import Holiday
    return Holiday.objects.filter(date=date.date()).exists()


# def next_working_time(current_time, working_hours):
#     """Move current_time to the next valid working time considering weekends and holidays."""

#     # 🧩 Convert working_days into a list of ints
#     working_days_str = getattr(working_hours, "working_days", "")
#     # Example: "0,1,2,3,4" → [0, 1, 2, 3, 4]
#     working_days = [int(day.strip()) for day in working_days_str.split(",") if day.strip().isdigit()]

#     # Safety check
#     if not working_days:
#         # Default to Monday–Friday
#         working_days = [0, 1, 2, 3, 4]

#     from timer.utils import is_holiday  # import if not already inside

#     while current_time.weekday() not in working_days or is_holiday(current_time, working_hours):
#         current_time += timedelta(days=1)
#         current_time = current_time.replace(
#             hour=working_hours.start_hour.hour,
#             minute=working_hours.start_hour.minute,
#             second=0,
#             microsecond=0,
#         )
#     return current_time

# # DAY_MAP = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
# # working_days = [DAY_MAP[d.strip().title()] for d in working_days_str.split(",") if d.strip() in DAY_MAP

# def calculate_sla_due(ticket):
#     """
#     Calculate the SLA due date considering organization's working hours and holidays.
#     """
#     # ✅ Step 1: Get working hours from the organization
#     working_hours = getattr(ticket.ticket_organization, "working_hours", None)
#     if not working_hours:
#         raise ValueError("Organization must have working_hours assigned.")

#     # ✅ Step 2: Get the starting time (when SLA starts)
#     current_time = next_working_time(ticket.start_time, working_hours)
#     hours_left = ticket.sla_hours

#     # ✅ Step 3: Add paused time if any (optional enhancement)
#     if ticket.total_paused_time:
#         hours_left += ticket.total_paused_time.total_seconds() / 3600

#     # ✅ Step 4: Loop until all SLA hours are consumed
#     while hours_left > 0:
#         # Calculate the end of the current working day
#         day_end = current_time.replace(
#             hour=working_hours.end_hour.hour,
#             minute=working_hours.end_hour.minute,
#             second=0, microsecond=0
#         )

#         remaining_today = (day_end - current_time).total_seconds() / 3600

#         # If SLA can be completed today
#         if remaining_today >= hours_left:
#             current_time += timedelta(hours=hours_left)
#             hours_left = 0
#         else:
#             # Consume remaining hours today, move to next working day
#             hours_left -= remaining_today
#             current_time += timedelta(days=1)
#             current_time = current_time.replace(
#                 hour=working_hours.start_hour.hour,
#                 minute=working_hours.start_hour.minute,
#                 second=0, microsecond=0
#             )
#             # Skip weekends/holidays if necessary
#             current_time = next_working_time(current_time, working_hours)

#     return current_time

# utils/sla_utils.py
from datetime import datetime, timedelta


def is_holiday(date, working_hours):
    return working_hours.holidays.filter(date=date.date()).exists()


# ✅ ADD THIS HELPER FUNCTION HERE
def is_within_working_hours(current_time, working_hours):
    """Check if the given time is within working hours."""
    working_days_raw = getattr(working_hours, "working_days", None)
    working_days = []
    if isinstance(working_days_raw, str):
        working_days = [int(day.strip()) for day in working_days_raw.split(",") if day.strip().isdigit()]
    elif isinstance(working_days_raw, (list, tuple)):
        try:
            working_days = [int(d) for d in working_days_raw]
        except Exception:
            working_days = []
    if not working_days:
        working_days = [0, 1, 2, 3, 4]  # Default Mon–Fri

    # Check if it's a working day
    if current_time.weekday() not in working_days:
        return False

    # Check if it's a holiday
    if is_holiday(current_time, working_hours):
        return False

    start = working_hours.start_hour
    end = working_hours.end_hour

    # Check if the time is within working hours
    return start <= current_time.time() <= end


# ✅ Existing functions stay below this
def next_working_time(current_time, working_hours):
    """Move current_time to the next valid working time considering weekends, holidays, and working hours."""
    # support working_days stored as a list (JSONField) or as a comma-separated string
    working_days_raw = getattr(working_hours, "working_days", None)
    working_days = []
    
    # Parse working_days - handle both string and list formats
    if isinstance(working_days_raw, str):
        # Try JSON parsing first (for strings like "[0, 1, 2, 3, 4]")
        import json
        try:
            parsed = json.loads(working_days_raw)
            if isinstance(parsed, list):
                working_days = [int(d) for d in parsed]
            else:
                working_days = []
        except (json.JSONDecodeError, ValueError):
            # Fall back to comma-separated parsing (for strings like "0,1,2,3,4")
            working_days = [int(day.strip()) for day in working_days_raw.split(",") if day.strip().isdigit()]
    elif isinstance(working_days_raw, (list, tuple)):
        # assume values are integers already
        try:
            working_days = [int(d) for d in working_days_raw]
        except Exception:
            working_days = []
    
    if not working_days:
        working_days = [0, 1, 2, 3, 4]
    
    print(f"[DEBUG next_working_time] Input: {current_time}, Working days: {working_days}, Current weekday: {current_time.weekday()}")

    # ✅ CRITICAL FIX: If current time is past working hours today, move to next day
    if current_time.time() > working_hours.end_hour:
        print(f"[DEBUG] Time {current_time.time()} is past end hour {working_hours.end_hour}, moving to next day")
        current_time += timedelta(days=1)
        current_time = current_time.replace(
            hour=working_hours.start_hour.hour,
            minute=working_hours.start_hour.minute,
            second=0,
            microsecond=0,
        )
    # ✅ If current time is before working hours today, set to start of today
    elif current_time.time() < working_hours.start_hour:
        print(f"[DEBUG] Time {current_time.time()} is before start hour {working_hours.start_hour}, setting to start of today")
        current_time = current_time.replace(
            hour=working_hours.start_hour.hour,
            minute=working_hours.start_hour.minute,
            second=0,
            microsecond=0,
        )

    # Now check weekdays/holidays
    loop_count = 0
    while current_time.weekday() not in working_days or is_holiday(current_time, working_hours):
        loop_count += 1
        if loop_count > 14:  # Prevent infinite loops
            print(f"[ERROR] Infinite loop detected in next_working_time!")
            break
        print(f"[DEBUG] Day {current_time.date()} (weekday {current_time.weekday()}) is not a working day, moving to next day")
        current_time += timedelta(days=1)
        current_time = current_time.replace(
            hour=working_hours.start_hour.hour,
            minute=working_hours.start_hour.minute,
            second=0,
            microsecond=0,
        )
    
    print(f"[DEBUG next_working_time] Result: {current_time}")
    return current_time
def calculate_sla_due(ticket):
    """
    Calculate the SLA due date considering organization's working hours and holidays.
    """
    # ✅ Step 1: Get working hours from the organization
    working_hours = getattr(ticket.ticket_organization, "working_hours", None)
    if not working_hours:
        raise ValueError("Organization must have working_hours assigned.")

    # ✅ Step 2: Get the starting time (when SLA starts)
    current_time = next_working_time(ticket.start_time, working_hours)
    hours_left = ticket.sla_hours

    # ✅ Step 3: Add paused time if any (optional enhancement)
    if ticket.total_paused_time:
        hours_left += ticket.total_paused_time.total_seconds() / 3600

    # ✅ Step 4: Loop until all SLA hours are consumed
    while hours_left > 0:
        # Calculate the end of the current working day
        day_end = current_time.replace(
            hour=working_hours.end_hour.hour,
            minute=working_hours.end_hour.minute,
            second=0, microsecond=0
        )

        remaining_today = (day_end - current_time).total_seconds() / 3600

        # If SLA can be completed today
        if remaining_today >= hours_left:
            current_time += timedelta(hours=hours_left)
            hours_left = 0
        else:
            # Consume remaining hours today, move to next working day
            hours_left -= remaining_today
            current_time += timedelta(days=1)
            current_time = current_time.replace(
                hour=working_hours.start_hour.hour,
                minute=working_hours.start_hour.minute,
                second=0, microsecond=0
            )
            # Skip weekends/holidays if necessary
            if is_within_working_hours(ticket.start_time, working_hours):
                current_time = ticket.start_time
            else:
                current_time = next_working_time(ticket.start_time, working_hours)


    return current_time