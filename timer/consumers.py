

# from datetime import datetime, time, timedelta
# from django.utils import timezone
# import pytz
# from asgiref.sync import sync_to_async

# @sync_to_async
# def get_working_hours_from_db(ticket_id):
#     """Fetch working hours from database for the given ticket."""
#     try:
#         from django.apps import apps
#         Ticket = apps.get_model('timer', 'Ticket')
#         SLATimer = apps.get_model('timer', 'SLATimer')
        
#         ticket = Ticket.objects.select_related('sla_timers__working_hours').get(ticket_id=ticket_id)
#         sla_timer = ticket.sla_timers
        
#         # Get working hours from SLA timer (same logic as models.py start_sla)
#         working_hours = sla_timer.working_hours if sla_timer else None
        
#         if not working_hours:
#             ticket_org = getattr(ticket, 'ticket_organization', None)
#             if ticket_org:
#                 working_hours = getattr(ticket_org, 'working_hours', None)
        
#         if not working_hours:
#             assignee = getattr(ticket, 'assignee', None)
#             if assignee:
#                 assignee_org = getattr(assignee, 'organisation', None)
#                 if assignee_org:
#                     working_hours = getattr(assignee_org, 'working_hours', None)
        
#         if working_hours:
#             return {
#                 'start_time': working_hours.start_hour,
#                 'end_time': working_hours.end_hour,
#                 'timezone': 'Asia/Kolkata'
#             }
#     except Exception as e:
#         print(f"[ERROR] Error fetching working hours: {e}")
#         import traceback
#         traceback.print_exc()
    
#     # Default fallback - should match the database now
#     return {
#         'start_time': time(9, 30),
#         'end_time': time(18, 30),
#         'timezone': 'Asia/Kolkata'
#     }

# @sync_to_async
# def _compute_within_hours_sync(ticket_id):
#     """Synchronous helper to determine if now is within working hours, considering working days and holidays."""
#     from django.apps import apps
#     from django.utils import timezone as dj_tz
#     from timer.models import Holiday  # local model for holidays

#     try:
#         Ticket = apps.get_model('timer', 'Ticket')
#         # Only include concrete relational fields in select_related; 'organisation' is a property on User
#         ticket = Ticket.objects.select_related(
#             'sla_timers__working_hours',
#             'ticket_organization__working_hours',
#             'assignee'
#         ).get(ticket_id=ticket_id)
#         sla_timer = getattr(ticket, 'sla_timers', None)
#         wh = getattr(sla_timer, 'working_hours', None)
#         if not wh:
#             org = getattr(ticket, 'ticket_organization', None)
#             if org:
#                 wh = getattr(org, 'working_hours', None)
#         if not wh:
#             assignee = getattr(ticket, 'assignee', None)
#             if assignee:
#                 assignee_org = getattr(assignee, 'organisation', None)
#                 if assignee_org:
#                     wh = getattr(assignee_org, 'working_hours', None)

#         if not wh:
#             # No working hours configured; treat as always within hours for enforcement safety
#             return True

#         tz = pytz.timezone('Asia/Kolkata')
#         now_local = dj_tz.now().astimezone(tz)

#         # Parse working days (list or JSON string)
#         working_days_raw = getattr(wh, 'working_days', None)
#         working_days = []
#         if isinstance(working_days_raw, str):
#             import json
#             try:
#                 parsed = json.loads(working_days_raw)
#                 if isinstance(parsed, list):
#                     working_days = [int(d) for d in parsed]
#             except Exception:
#                 working_days = [int(d.strip()) for d in working_days_raw.split(',') if d.strip().isdigit()]
#         elif isinstance(working_days_raw, (list, tuple)):
#             try:
#                 working_days = [int(d) for d in working_days_raw]
#             except Exception:
#                 working_days = []
#         if not working_days:
#             working_days = [0,1,2,3,4]

#         # Day/holiday check
#         if now_local.weekday() not in working_days:
#             return False
#         if Holiday.objects.filter(working_hours=wh, date=now_local.date()).exists():
#             return False

#         # Time of day check
#         return wh.start_hour <= now_local.time() <= wh.end_hour
#     except Exception as e:
#         print(f"[ERROR] _compute_within_hours_sync failed: {e}")
#         return False

# async def is_within_working_hours(ticket_id):
#     """Return True if now is within working hours, considering working days and holidays."""
#     return await _compute_within_hours_sync(ticket_id)

# async def get_next_start_time(ticket_id):
#     """Get the next start time based on working hours from database."""
#     wh = await get_working_hours_from_db(ticket_id)
#     tz = pytz.timezone(wh['timezone'])
#     now = timezone.now().astimezone(tz)
#     start_work = wh['start_time']
#     end_work = wh['end_time']

#     print(f"[DEBUG] Current time: {now.time()}, Working hours: {start_work} - {end_work}")

#     if now.time() < start_work:
#         # Before working hours — start today at start_time
#         next_start = datetime.combine(now.date(), start_work)
#     elif now.time() > end_work:
#         # After working hours — start tomorrow at start_time
#         next_start = datetime.combine(now.date() + timedelta(days=1), start_work)
#     else:
#         # Within working hours - start immediately
#         next_start = now

#     return tz.localize(next_start) if next_start.tzinfo is None else next_start

# import json
# import asyncio
# from channels.generic.websocket import AsyncWebsocketConsumer
# from asgiref.sync import sync_to_async
# from django.apps import apps
# from django.utils import timezone

# # ✅ Store running timers globally (one per ticket)
# active_timers = {}


# class TimerConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         try:
#             self.ticket_id = self.scope['url_route']['kwargs']['ticket_id']
#             self.group_name = f"timer_{self.ticket_id}"

#             # ✅ Add to channel group
#             await self.channel_layer.group_add(self.group_name, self.channel_name)
#             await self.accept()

#             # ✅ Send initial snapshot
#             await self.send_initial_timer()

#             if self.ticket_id not in active_timers:
#                 # Try to activate scheduled SLA immediately if current hours allow
#                 try:
#                     ticket = await self.get_ticket()
#                     sla_timer = await self.get_sla_timer(ticket)
#                     if sla_timer:
#                         activated = await sync_to_async(sla_timer.maybe_activate_now)()
#                         if activated:
#                             print(f"[TIMER START] SLA activated now for {self.ticket_id}; starting loop.")
#                             active_timers[self.ticket_id] = asyncio.create_task(self.timer_loop())
#                             return
#                 except Exception as e:
#                     print(f"[WARN] maybe_activate_now failed: {e}")

#                 next_start_time = await get_next_start_time(self.ticket_id)
#                 now = timezone.now()

#                 if now < next_start_time:
#                     delay = (next_start_time - now).total_seconds()
#                     print(f"[TIMER WAIT] Waiting {delay/3600:.2f} hours to start timer for Ticket {self.ticket_id} at {next_start_time}")
#                     # Schedule it for later
#                     active_timers[self.ticket_id] = asyncio.create_task(self.delayed_timer_start(delay))
#                 else:
#                     print(f"[TIMER START] Starting loop immediately for Ticket {self.ticket_id}")
#                     active_timers[self.ticket_id] = asyncio.create_task(self.timer_loop())


#             else:
#                 print(f"[TIMER EXISTS] Timer already running for Ticket {self.ticket_id}. Joining existing timer.")

#         except Exception as e:
#             print("WebSocket connect error:", e)
#             await self.close()

#     async def disconnect(self, close_code):
#         try:
#             await self.channel_layer.group_discard(self.group_name, self.channel_name)

#             # ✅ If no users left in the group, stop the timer
#             group_size = len(self.channel_layer.groups.get(self.group_name, set()))
#             if group_size == 0 and self.ticket_id in active_timers:
#                 print(f"[TIMER STOP] No clients left, stopping timer for {self.ticket_id}")
#                 active_timers[self.ticket_id].cancel()
#                 del active_timers[self.ticket_id]

#         except Exception as e:
#             print("WebSocket disconnect error:", e)

#     async def receive(self, text_data):
#         try:
#             data = json.loads(text_data)
#             if data.get("action") == "update_status":
#                 await self.update_status(data)
#         except Exception as e:
#             print("WebSocket receive error:", e)

#     # ------------------------------
#     # Database Accessors
#     # ------------------------------
#     @sync_to_async
#     def get_ticket(self):
#         Ticket = apps.get_model('timer', 'Ticket')
#         return Ticket.objects.get(ticket_id=self.ticket_id)

#     @sync_to_async
#     def get_sla_timer(self, ticket):
#         SLATimer = apps.get_model('timer', 'SLATimer')
#         try:
#             return ticket.sla_timers  # Adjust if your related_name differs
#         except SLATimer.DoesNotExist:
#             return None

#     def _check_within_working_hours(self, ticket):
#         """Check if current time is within working hours. Returns dict with status and error message."""
#         from timer.models import Holiday
#         from django.utils import timezone as dj_tz
#         import pytz
        
#         tz = pytz.timezone('Asia/Kolkata')
#         now = dj_tz.now().astimezone(tz)
        
#         # Get working hours
#         working_hours = None
#         if hasattr(ticket, 'ticket_organization') and ticket.ticket_organization:
#             working_hours = getattr(ticket.ticket_organization, 'working_hours', None)
#         if not working_hours and hasattr(ticket, 'assignee') and ticket.assignee:
#             assignee_org = getattr(ticket.assignee, 'organisation', None)
#             if assignee_org:
#                 working_hours = getattr(assignee_org, 'working_hours', None)
        
#         if not working_hours:
#             # No working hours configured, allow changes
#             return {'within_hours': True, 'reason': 'no_config', 'error_message': ''}
        
#         # Check if today is a holiday
#         is_holiday = Holiday.objects.filter(working_hours=working_hours, date=now.date()).exists()
#         if is_holiday:
#             holiday = Holiday.objects.get(working_hours=working_hours, date=now.date())
#             return {
#                 'within_hours': False,
#                 'reason': 'holiday',
#                 'error_message': f"Status changes are not allowed during holidays. Today is {holiday.name}."
#             }
        
#         # Parse working days
#         working_days_raw = getattr(working_hours, 'working_days', None)
#         working_days = []
#         if isinstance(working_days_raw, str):
#             import json
#             try:
#                 parsed = json.loads(working_days_raw)
#                 if isinstance(parsed, list):
#                     working_days = [int(d) for d in parsed]
#             except Exception:
#                 working_days = [int(d.strip()) for d in working_days_raw.split(',') if d.strip().isdigit()]
#         elif isinstance(working_days_raw, (list, tuple)):
#             try:
#                 working_days = [int(d) for d in working_days_raw]
#             except Exception:
#                 working_days = []
#         if not working_days:
#             working_days = [0,1,2,3,4]
        
#         # Check if it's a working day
#         if now.weekday() not in working_days:
#             day_name = now.strftime('%A')
#             return {
#                 'within_hours': False,
#                 'reason': 'non_working_day',
#                 'error_message': f"Status changes are not allowed on non-working days. Today is {day_name}."
#             }
        
#         # Check time range
#         within_time = working_hours.start_hour <= now.time() <= working_hours.end_hour
#         if not within_time:
#             return {
#                 'within_hours': False,
#                 'reason': 'outside_hours',
#                 'error_message': f"Status changes are not allowed outside working hours ({working_hours.start_hour.strftime('%H:%M')} - {working_hours.end_hour.strftime('%H:%M')}). Current time: {now.time().strftime('%H:%M')}"
#             }
        
#         return {'within_hours': True, 'reason': 'ok', 'error_message': ''}

#     # ------------------------------
#     # Initial Timer Data
#     # ------------------------------
#     async def send_initial_timer(self):
#         try:
#             ticket = await self.get_ticket()
#             sla_timer = await self.get_sla_timer(ticket)

#             # Calculate remaining time using sync_to_async to avoid ORM in async context
#             remaining_time = await sync_to_async(sla_timer.calculate_remaining_time)()

#             await self.send(text_data=json.dumps({
#                 "action": "timer_init",
#                 "ticket_id": ticket.ticket_id,
#                 "status": ticket.status,
#                 "sla_status": sla_timer.sla_status,
#                 "remaining_time": str(remaining_time),
#                 "due_date": str(sla_timer.sla_due_date),
#                 "start_time": str(sla_timer.start_time),  # ✅ Added for scheduled tickets
#             }))
#         except Exception as e:
#             print("send_initial_timer error:", e)

#     # ------------------------------
#     # Main Timer Loop (1 per ticket)
#     # ------------------------------
#     async def timer_loop(self):
#         """
#         Optimized timer loop with smart updates:
#         - Fast updates (10s) when time is critical (< 1 hour remaining or Active status)
#         - Slow updates (60s) for non-critical tickets (Paused/Scheduled or > 1 hour)
#         - Reduces database load by 6x for most tickets
#         """
#         try:
#             last_sla_status = None
#             last_ticket_status = None
            
#             while True:
#                 ticket = await self.get_ticket()
#                 sla_timer = await self.get_sla_timer(ticket)

#                 # Stop timer loop if SLA is stopped (resolved/closed)
#                 if sla_timer.sla_status == 'Stopped':
#                     print(f"[TIMER LOOP] Ticket: {ticket.ticket_id} | SLA stopped. Sending final update and exiting loop.")
#                     remaining_time = await sync_to_async(sla_timer.calculate_remaining_time)()
#                     await self.channel_layer.group_send(
#                         self.group_name,
#                         {
#                             "type": "timer_message",
#                             "action": "timer_stopped",
#                             "ticket_id": ticket.ticket_id,
#                             "status": ticket.status,
#                             "sla_status": sla_timer.sla_status,
#                             "remaining_time": str(remaining_time),
#                             "due_date": str(sla_timer.sla_due_date),
#                             "start_time": str(sla_timer.start_time),
#                         }
#                     )
#                     break  # Exit the timer loop

#                 # Auto pause/resume based on working hours
#                 # Holiday-aware within-hours check
#                 within_hours = await is_within_working_hours(self.ticket_id)
#                 if not within_hours and sla_timer.sla_status == 'Active':
#                     # Auto-schedule to next working day (not just pause)
#                     await sync_to_async(sla_timer.pause_sla)(auto_schedule=True)
#                     await self.channel_layer.group_send(
#                         self.group_name,
#                         {
#                             "type": "timer_message",
#                             "action": "timer_auto_scheduled",
#                             "ticket_id": ticket.ticket_id,
#                             "status": ticket.status,
#                             "sla_status": sla_timer.sla_status,
#                             "remaining_time": str(await sync_to_async(sla_timer.calculate_remaining_time)()),
#                             "due_date": str(sla_timer.sla_due_date),
#                             "start_time": str(sla_timer.start_time),
#                         }
#                     )
#                     last_sla_status = sla_timer.sla_status  # Update tracker
#                 elif within_hours and sla_timer.sla_status == 'Scheduled':
#                     # Activate scheduled SLA when working hours begin
#                     await sync_to_async(sla_timer.activate_scheduled_sla)()
#                     await self.channel_layer.group_send(
#                         self.group_name,
#                         {
#                             "type": "timer_message",
#                             "action": "timer_activated",
#                             "ticket_id": ticket.ticket_id,
#                             "status": ticket.status,
#                             "sla_status": sla_timer.sla_status,
#                             "remaining_time": str(await sync_to_async(sla_timer.calculate_remaining_time)()),
#                             "due_date": str(sla_timer.sla_due_date),
#                             "start_time": str(sla_timer.start_time),
#                         }
#                     )
#                     last_sla_status = sla_timer.sla_status  # Update tracker
#                 elif within_hours and sla_timer.sla_status == 'Paused':
#                     # Only auto-resume if ticket isn't in a user-waiting state
#                     if str(ticket.status).lower() not in ["waiting for user response"]:
#                         await sync_to_async(sla_timer.resume_sla)()
#                         await self.channel_layer.group_send(
#                             self.group_name,
#                             {
#                                 "type": "timer_message",
#                                 "action": "timer_auto_resumed",
#                                 "ticket_id": ticket.ticket_id,
#                                 "status": ticket.status,
#                                 "sla_status": sla_timer.sla_status,
#                                 "remaining_time": str(await sync_to_async(sla_timer.calculate_remaining_time)()),
#                                 "due_date": str(sla_timer.sla_due_date),
#                                 "start_time": str(sla_timer.start_time),
#                             }
#                         )
#                         last_sla_status = sla_timer.sla_status  # Update tracker

#                 # Calculate remaining time in a thread to prevent async ORM access
#                 remaining_time = await sync_to_async(sla_timer.calculate_remaining_time)()
                
#                 # 🚀 SMART UPDATE LOGIC - Only send if something changed or it's critical
#                 status_changed = (sla_timer.sla_status != last_sla_status or 
#                                 ticket.status != last_ticket_status)
                
#                 # Parse remaining time to determine if critical
#                 is_critical = False
#                 try:
#                     # remaining_time format: "HH:MM:SS" or negative
#                     if remaining_time and str(remaining_time).startswith('-'):
#                         is_critical = True  # Already breached
#                     elif remaining_time:
#                         parts = str(remaining_time).split(':')
#                         if len(parts) >= 2:
#                             hours = int(parts[0])
#                             is_critical = hours < 1  # Less than 1 hour remaining
#                 except Exception:
#                     is_critical = True  # On parse error, treat as critical
                
#                 # Send update if status changed OR if it's critical time
#                 if status_changed or is_critical or sla_timer.sla_status == 'Active':
#                     print(
#                         f"[TIMER LOOP] Ticket: {ticket.ticket_id} | "
#                         f"Remaining: {remaining_time} | Status: {sla_timer.sla_status} | "
#                         f"Critical: {is_critical}"
#                     )
                    
#                     await self.channel_layer.group_send(
#                         self.group_name,
#                         {
#                             "type": "timer_message",
#                             "action": "timer_update",
#                             "ticket_id": ticket.ticket_id,
#                             "status": ticket.status,
#                             "sla_status": sla_timer.sla_status,
#                             "remaining_time": str(remaining_time),
#                             "due_date": str(sla_timer.sla_due_date),
#                             "start_time": str(sla_timer.start_time),
#                         }
#                     )
                    
#                     # Update trackers
#                     last_sla_status = sla_timer.sla_status
#                     last_ticket_status = ticket.status

#                 # 🚀 DYNAMIC SLEEP INTERVAL - Adjust based on criticality
#                 if sla_timer.sla_status == 'Active' and is_critical:
#                     await asyncio.sleep(10)  # Fast updates for critical active tickets
#                 elif sla_timer.sla_status == 'Active':
#                     await asyncio.sleep(30)  # Medium updates for active tickets
#                 else:
#                     await asyncio.sleep(60)  # Slow updates for paused/scheduled tickets
#         except asyncio.CancelledError:
#             print(f"[TIMER LOOP STOPPED] Ticket {self.ticket_id}")
#         except Exception as e:
#             print("timer_loop error:", e)

#     # ------------------------------
#     # Ticket Status Updates
#     # ------------------------------
#     async def update_status(self, data):
#         new_status = data.get("status")
#         if not new_status:
#             return

#         try:
#             ticket = await self.get_ticket()
#             sla_timer = await self.get_sla_timer(ticket)

#             # ❌ BLOCK STATUS CHANGES OUTSIDE WORKING HOURS
#             within_hours_result = await sync_to_async(self._check_within_working_hours)(ticket)
#             if not within_hours_result['within_hours']:
#                 error_msg = within_hours_result['error_message']
#                 await self.send(text_data=json.dumps({
#                     "action": "status_change_blocked",
#                     "ticket_id": ticket.ticket_id,
#                     "error": error_msg,
#                     "current_status": ticket.status,
#                     "reason": within_hours_result['reason']
#                 }))
#                 print(f"[WORKING HOURS BLOCK] Status change blocked for ticket {ticket.ticket_id}: {within_hours_result['reason']}")
#                 return

#             ticket.status = new_status
#             await sync_to_async(ticket.save)()

#             action_type = "status_update"
#             if sla_timer:
#                 if new_status.lower() == "waiting for user response":
#                     await sync_to_async(sla_timer.pause_sla)()
#                     action_type = "timer_paused"
#                 elif new_status.lower() in ["working in progress", "in progress"]:
#                     # Block starting if SLA is scheduled for future
#                     should_block = False
#                     if sla_timer.sla_status == "Scheduled" and sla_timer.start_time:
#                         from django.utils import timezone as dj_tz
#                         if dj_tz.now() < sla_timer.start_time:
#                             should_block = True
#                     if should_block:
#                         action_type = "timer_blocked"
#                     else:
#                         await sync_to_async(sla_timer.resume_sla)()
#                         action_type = "timer_resumed"
#                 elif new_status.lower() in ["resolved", "closed"]:
#                     await sync_to_async(sla_timer.stop_sla)()
#                     action_type = "timer_stopped"

#             await self.channel_layer.group_send(
#                 self.group_name,
#                 {
#                     "type": "timer_message",
#                     "action": action_type,
#                     "ticket_id": ticket.ticket_id,
#                     "status": ticket.status,
#                     "sla_status": sla_timer.sla_status if sla_timer else None,
#                     "remaining_time": str(await sync_to_async(sla_timer.calculate_remaining_time)()) if sla_timer else None,
#                     "due_date": str(sla_timer.sla_due_date) if sla_timer else None,
#                     "start_time": str(sla_timer.start_time) if sla_timer else None
#                 }
#             )

#         except Exception as e:
#             print("update_status error:", e)

#     # ------------------------------
#     # Broadcast Handler
#     # ------------------------------
#     async def timer_message(self, event):
#         try:
#             await self.send(text_data=json.dumps(event))
#         except Exception as e:
#             print("timer_message send error:", e)

#     async def delayed_timer_start(self, delay):
#         try:
#             await asyncio.sleep(delay)
#             # Ensure the DB state updates: activate scheduled SLA
#             ticket = await self.get_ticket()
#             sla_timer = await self.get_sla_timer(ticket)
#             if sla_timer:
#                 await sync_to_async(sla_timer.activate_scheduled_sla)()
#             print(f"[TIMER DELAY COMPLETE] Starting loop for Ticket {self.ticket_id}")
#             active_timers[self.ticket_id] = asyncio.create_task(self.timer_loop())
#         except asyncio.CancelledError:
#             print(f"[TIMER DELAY CANCELLED] Ticket {self.ticket_id}")





from datetime import datetime, time, timedelta
from django.utils import timezone
import pytz
from asgiref.sync import sync_to_async

@sync_to_async
def get_working_hours_from_db(ticket_id):
    """Fetch working hours from database for the given ticket."""
    try:
        from django.apps import apps
        Ticket = apps.get_model('timer', 'Ticket')
        SLATimer = apps.get_model('timer', 'SLATimer')
        
        ticket = Ticket.objects.select_related('sla_timers__working_hours').get(ticket_id=ticket_id)
        sla_timer = ticket.sla_timers
        
        # Get working hours from SLA timer (same logic as models.py start_sla)
        working_hours = sla_timer.working_hours if sla_timer else None
        
        if not working_hours:
            ticket_org = getattr(ticket, 'ticket_organization', None)
            if ticket_org:
                working_hours = getattr(ticket_org, 'working_hours', None)
        
        if not working_hours:
            assignee = getattr(ticket, 'assignee', None)
            if assignee:
                assignee_org = getattr(assignee, 'organisation', None)
                if assignee_org:
                    working_hours = getattr(assignee_org, 'working_hours', None)
        
        if working_hours:
            return {
                'start_time': working_hours.start_hour,
                'end_time': working_hours.end_hour,
                'timezone': 'Asia/Kolkata'
            }
    except Exception as e:
        print(f"[ERROR] Error fetching working hours: {e}")
        import traceback
        traceback.print_exc()
    
    # Default fallback - should match the database now
    return {
        'start_time': time(9, 30),
        'end_time': time(18, 30),
        'timezone': 'Asia/Kolkata'
    }

async def is_within_working_hours(ticket_id):
    """Return True if now is within working hours."""
    wh = await get_working_hours_from_db(ticket_id)
    tz = pytz.timezone(wh['timezone'])
    now = timezone.now().astimezone(tz)
    return wh['start_time'] <= now.time() <= wh['end_time']

async def get_next_start_time(ticket_id):
    """Get the next start time based on working hours from database."""
    wh = await get_working_hours_from_db(ticket_id)
    tz = pytz.timezone(wh['timezone'])
    now = timezone.now().astimezone(tz)
    start_work = wh['start_time']
    end_work = wh['end_time']

    print(f"[DEBUG] Current time: {now.time()}, Working hours: {start_work} - {end_work}")

    if now.time() < start_work:
        # Before working hours — start today at start_time
        next_start = datetime.combine(now.date(), start_work)
    elif now.time() > end_work:
        # After working hours — start tomorrow at start_time
        next_start = datetime.combine(now.date() + timedelta(days=1), start_work)
    else:
        # Within working hours - start immediately
        next_start = now

    return tz.localize(next_start) if next_start.tzinfo is None else next_start

import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.apps import apps
from django.utils import timezone

# ✅ Store running timers globally (one per ticket)
active_timers = {}


class TimerConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.ticket_id = self.scope['url_route']['kwargs']['ticket_id']
            self.group_name = f"timer_{self.ticket_id}"

            # ✅ Add to channel group
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

            # ✅ Send initial snapshot
            await self.send_initial_timer()

            # ✅ Start timer only if not already running
            # if self.ticket_id not in active_timers:
            #     print(f"[TIMER START] Starting loop for Ticket {self.ticket_id}")
            #     active_timers[self.ticket_id] = asyncio.create_task(self.timer_loop())
            if self.ticket_id not in active_timers:
                # Try to activate scheduled SLA immediately if current hours allow
                try:
                    ticket = await self.get_ticket()
                    sla_timer = await self.get_sla_timer(ticket)
                    if sla_timer:
                        activated = await sync_to_async(sla_timer.maybe_activate_now)()
                        if activated:
                            print(f"[TIMER START] SLA activated now for {self.ticket_id}; starting loop.")
                            active_timers[self.ticket_id] = asyncio.create_task(self.timer_loop())
                            return
                except Exception as e:
                    print(f"[WARN] maybe_activate_now failed: {e}")

                next_start_time = await get_next_start_time(self.ticket_id)
                now = timezone.now()

                if now < next_start_time:
                    delay = (next_start_time - now).total_seconds()
                    print(f"[TIMER WAIT] Waiting {delay/3600:.2f} hours to start timer for Ticket {self.ticket_id} at {next_start_time}")
                    # Schedule it for later
                    active_timers[self.ticket_id] = asyncio.create_task(self.delayed_timer_start(delay))
                else:
                    print(f"[TIMER START] Starting loop immediately for Ticket {self.ticket_id}")
                    active_timers[self.ticket_id] = asyncio.create_task(self.timer_loop())


            else:
                print(f"[TIMER EXISTS] Timer already running for Ticket {self.ticket_id}. Joining existing timer.")

        except Exception as e:
            print("WebSocket connect error:", e)
            await self.close()

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

            # ✅ If no users left in the group, stop the timer
            group_size = len(self.channel_layer.groups.get(self.group_name, set()))
            if group_size == 0 and self.ticket_id in active_timers:
                print(f"[TIMER STOP] No clients left, stopping timer for {self.ticket_id}")
                active_timers[self.ticket_id].cancel()
                del active_timers[self.ticket_id]

        except Exception as e:
            print("WebSocket disconnect error:", e)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            if data.get("action") == "update_status":
                await self.update_status(data)
        except Exception as e:
            print("WebSocket receive error:", e)

    # ------------------------------
    # Database Accessors
    # ------------------------------
    @sync_to_async
    def get_ticket(self):
        Ticket = apps.get_model('timer', 'Ticket')
        return Ticket.objects.get(ticket_id=self.ticket_id)

    @sync_to_async
    def get_sla_timer(self, ticket):
        SLATimer = apps.get_model('timer', 'SLATimer')
        try:
            return ticket.sla_timers  # Adjust if your related_name differs
        except SLATimer.DoesNotExist:
            return None

    # ------------------------------
    # Initial Timer Data
    # ------------------------------
    async def send_initial_timer(self):
        try:
            ticket = await self.get_ticket()
            sla_timer = await self.get_sla_timer(ticket)

            # Refresh objects from DB to avoid stale reads / race conditions
            try:
                await sync_to_async(ticket.refresh_from_db)()
            except Exception:
                pass
            if sla_timer:
                try:
                    await sync_to_async(sla_timer.refresh_from_db)()
                except Exception:
                    pass

            # Calculate remaining time using sync_to_async to avoid ORM in async context
            remaining_time = await sync_to_async(sla_timer.calculate_remaining_time)() if sla_timer else None

            await self.send(text_data=json.dumps({
                "action": "timer_init",
                "ticket_id": ticket.ticket_id,
                "status": ticket.status,
                "sla_status": sla_timer.sla_status,
                "remaining_time": str(remaining_time),
                "due_date": str(sla_timer.sla_due_date),
                "start_time": str(sla_timer.start_time),  # ✅ Added for scheduled tickets
            }))
        except Exception as e:
            print("send_initial_timer error:", e)

    # ------------------------------
    # Main Timer Loop (1 per ticket)
    # ------------------------------
    async def timer_loop(self):
        try:
            while True:
                ticket = await self.get_ticket()
                sla_timer = await self.get_sla_timer(ticket)
                # Refresh from DB to ensure we compute remaining_time from the latest state
                try:
                    await sync_to_async(ticket.refresh_from_db)()
                except Exception:
                    pass
                if sla_timer:
                    try:
                        await sync_to_async(sla_timer.refresh_from_db)()
                    except Exception:
                        pass
                # Auto pause/resume based on working hours AND holidays
                from timer.models import is_within_working_hours
                tz = pytz.timezone('Asia/Kolkata')
                now_local = timezone.now().astimezone(tz)
                
                # Get working hours for this ticket
                working_hours_obj = await sync_to_async(lambda: sla_timer.working_hours)()
                
                # Use the proper is_within_working_hours function that checks time, days, AND holidays
                within_hours = await sync_to_async(is_within_working_hours)(now_local, working_hours_obj)
                if not within_hours and sla_timer.sla_status == 'Active':
                    # Auto-schedule to next working day (not just pause)
                    await sync_to_async(sla_timer.pause_sla)(auto_schedule=True)
                    await self.channel_layer.group_send(
                        self.group_name,
                        {
                            "type": "timer_message",
                            "action": "timer_auto_scheduled",
                            "ticket_id": ticket.ticket_id,
                            "status": ticket.status,
                            "sla_status": sla_timer.sla_status,
                            "remaining_time": str(await sync_to_async(sla_timer.calculate_remaining_time)()),
                            "due_date": str(sla_timer.sla_due_date),
                            "start_time": str(sla_timer.start_time),
                        }
                    )
                elif within_hours and sla_timer.sla_status in ['Paused', 'Scheduled']:
                    # Only auto-resume if ticket isn't in a user-waiting state
                    if str(ticket.status).lower() not in ["waiting for user response"]:
                        await sync_to_async(sla_timer.resume_sla)()
                        await self.channel_layer.group_send(
                            self.group_name,
                            {
                                "type": "timer_message",
                                "action": "timer_auto_resumed",
                                "ticket_id": ticket.ticket_id,
                                "status": ticket.status,
                                "sla_status": sla_timer.sla_status,
                                "remaining_time": str(await sync_to_async(sla_timer.calculate_remaining_time)()),
                                "due_date": str(sla_timer.sla_due_date),
                                "start_time": str(sla_timer.start_time),
                            }
                        )

                # Calculate remaining time in a thread to prevent async ORM access
                remaining_time = await sync_to_async(sla_timer.calculate_remaining_time)()
                print(
                    f"[TIMER LOOP] Ticket: {ticket.ticket_id} | "
                    f"Remaining: {remaining_time} | Status: {sla_timer.sla_status}"
                )

                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "timer_message",
                        "action": "timer_update",
                        "ticket_id": ticket.ticket_id,
                        "status": ticket.status,
                        "sla_status": sla_timer.sla_status,
                        "remaining_time": str(remaining_time),
                        "due_date": str(sla_timer.sla_due_date),
                        "start_time": str(sla_timer.start_time),  # ✅ Added for scheduled tickets
                    }
                )

                # Reduce update frequency to improve performance (10 minutes)
                await asyncio.sleep(600)
        except asyncio.CancelledError:
            print(f"[TIMER LOOP STOPPED] Ticket {self.ticket_id}")
        except Exception as e:
            print("timer_loop error:", e)

    # ------------------------------
    # Ticket Status Updates
    # ------------------------------
    async def update_status(self, data):
        new_status = data.get("status")
        if not new_status:
            return

        try:
            ticket = await self.get_ticket()
            sla_timer = await self.get_sla_timer(ticket)

            ticket.status = new_status
            await sync_to_async(ticket.save)()

            action_type = "status_update"
            if sla_timer:
                if new_status.lower() == "waiting for user response":
                    await sync_to_async(sla_timer.pause_sla)()
                    action_type = "timer_paused"
                elif new_status.lower() in ["working in progress", "in progress"]:
                    # Block starting if SLA is scheduled for future
                    should_block = False
                    if sla_timer.sla_status == "Scheduled" and sla_timer.start_time:
                        from django.utils import timezone as dj_tz
                        if dj_tz.now() < sla_timer.start_time:
                            should_block = True
                    if should_block:
                        action_type = "timer_blocked"
                    else:
                        await sync_to_async(sla_timer.resume_sla)()
                        action_type = "timer_resumed"
                elif new_status.lower() in ["resolved", "closed"]:
                    await sync_to_async(sla_timer.stop_sla)()
                    action_type = "timer_stopped"

            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "timer_message",
                    "action": action_type,
                    "ticket_id": ticket.ticket_id,
                    "status": ticket.status,
                    "sla_status": sla_timer.sla_status if sla_timer else None,
                    "remaining_time": str(await sync_to_async(sla_timer.calculate_remaining_time)()) if sla_timer else None,
                    "due_date": str(sla_timer.sla_due_date) if sla_timer else None,
                    "start_time": str(sla_timer.start_time) if sla_timer else None
                }
            )

        except Exception as e:
            print("update_status error:", e)

    # ------------------------------
    # Broadcast Handler
    # ------------------------------
    async def timer_message(self, event):
        try:
            await self.send(text_data=json.dumps(event))
        except Exception as e:
            print("timer_message send error:", e)

    async def delayed_timer_start(self, delay):
        try:
            await asyncio.sleep(delay)
            # Ensure the DB state updates: activate scheduled SLA
            ticket = await self.get_ticket()
            sla_timer = await self.get_sla_timer(ticket)
            if sla_timer:
                await sync_to_async(sla_timer.activate_scheduled_sla)()
            print(f"[TIMER DELAY COMPLETE] Starting loop for Ticket {self.ticket_id}")
            active_timers[self.ticket_id] = asyncio.create_task(self.timer_loop())
        except asyncio.CancelledError:
            print(f"[TIMER DELAY CANCELLED] Ticket {self.ticket_id}")

