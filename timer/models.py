

import pdb
import uuid
from datetime import datetime, timedelta
import pytz
from django.db import models
# from django.utils.timezone import now
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
import logging
logger = logging.getLogger(__name__)
# User = get_user_model()
from organisation_details.models import Organisation
from solution_groups.models import SolutionGroup
from priority.models import Priority
from login_details.models import User
import random,string
from project_details.models import ProjectsDetails
from .utils import next_working_time
from whatsapp_notifications.service import notify_user




def is_within_working_hours(current_time, working_hours):
    """
    Check if the current_time is within working hours, considering days and holidays.
    """
    if not working_hours:
        # No working hours configured — fall back to default Mon-Fri 09:30-18:30
        # but still respect holidays recorded in the Holiday table.
        from datetime import time as _time
        # If today is a holiday (recorded for any working_hours), treat as non-working
        try:
            if Holiday.objects.filter(date=current_time.date()).exists():
                return False
        except Exception:
            # If Holiday table unavailable for any reason, be permissive
            pass

        # Create a lightweight default working_hours-like object for time checks
        working_hours = type('WHDefault', (), {})()
        working_hours.start_hour = _time(9, 30)
        working_hours.end_hour = _time(18, 30)
        working_hours.working_days = [0, 1, 2, 3, 4]

    ist = pytz.timezone('Asia/Kolkata')
    current_time = current_time.astimezone(ist) if current_time.tzinfo else ist.localize(current_time)
    
    # Check if it's a working day
    weekday = current_time.weekday()  # 0=Monday, 6=Sunday
    
    # Handle working_days as either list or comma-separated string
    working_days = working_hours.working_days
    if isinstance(working_days, str):
        # Parse comma-separated string to list of integers
        working_days = [int(d.strip()) for d in working_days.split(',') if d.strip().isdigit()]
    
    if weekday not in working_days:
        return False
    
    # Check holidays - check by date only (regardless of which working_hours they're linked to)
    if Holiday.objects.filter(date=current_time.date()).exists():
        return False
    
    # Check time range
    start_time = datetime.combine(current_time.date(), working_hours.start_hour)
    end_time = datetime.combine(current_time.date(), working_hours.end_hour)
    start_time = ist.localize(start_time)
    end_time = ist.localize(end_time)
    
    return start_time <= current_time <= end_time

def get_next_start_time_for_wh(working_hours):
        """Return next start datetime in IST for given WorkingHours model instance."""
        import pytz
        from datetime import datetime, timedelta
        from django.utils import timezone

        tz = pytz.timezone("Asia/Kolkata")
        now = timezone.now().astimezone(tz)
        start_work = working_hours.start_hour
        end_work = working_hours.end_hour

        # before today's start
        if now.time() < start_work:
            next_start = datetime.combine(now.date(), start_work)
        # after today's end -> next day start
        elif now.time() > end_work:
            next_start = datetime.combine(now.date() + timedelta(days=1), start_work)
        else:
            next_start = now





class Ticket(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('Working in Progress', 'Working in Progress'),
        ('Waiting for User Response', 'Waiting for User Response'),
        ('Resolved', 'Resolved'),
        ('Closed', 'Closed'),
        ('Breached', 'Breached'),
        ('Canceled', 'Canceled'),
        ('Delegated', 'Delegated')
    ]
   
    IMPACT = [
        ('A', 'High'),
        ('B', 'Medium'),
        ('C', 'Low')
    ]
    SUPPORT = [
        ('a', 'FirstLevel'),
        ('b', 'SecondLevel')
    ]

  
    developer_organization = models.ForeignKey(Organisation, on_delete=models.CASCADE, null=True, blank=True)

    assignee = models.ForeignKey("login_details.User", on_delete=models.CASCADE,null=True, related_name='solution_engineer')
    service_domain = models.ForeignKey('services.IssueCategory', on_delete=models.SET_NULL, null=True, blank=True)
    service_type = models.ForeignKey('services.IssueType', on_delete=models.SET_NULL, null=True, blank=True,related_name='s_product')
    solution_grp = models.ForeignKey(SolutionGroup, on_delete=models.SET_NULL, related_name='s_solution_group', null=True, blank=True)
    reference_tickets = models.ManyToManyField('self',blank=True)
    pre_assignee = models.JSONField(default=list,null= True)  # Stores a list of strings
    impact = models.CharField(
        max_length=50, 
        choices=IMPACT, 
        blank=True, 
        null=True, 
        default=""
    )
    support_team = models.CharField(max_length=50, choices=SUPPORT,blank=True, 
        null=True, 
        default="")
    customer_number = models.CharField(max_length=50, blank=True, null=True,)
    developer_organization = models.ForeignKey(Organisation, on_delete=models.CASCADE, null=True, blank=True,related_name='developer_organization_tickets')
    ticket_organization = models.ForeignKey(Organisation, on_delete=models.CASCADE, null=True, blank=True,related_name='ticket_organization_tickets')
    is_active = models.BooleanField(default=False)
    customer_country = models.CharField(max_length=50, blank=True, null=True)
    ticket_id = models.CharField(
        max_length=32, primary_key=True, unique=True, editable=True
    )
    summary = models.CharField(max_length=250)
    description = models.TextField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='open')
    project = models.ForeignKey(ProjectsDetails, null=True, blank=True, on_delete=models.SET_NULL)
    project_owner_email = models.EmailField(null=True, blank=True)# Optio
 

    priority = models.ForeignKey(Priority, on_delete=models.SET_NULL,related_name="priority",null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    on_behalf_of = models.ForeignKey(
        User, related_name='ticket_on_behalf_of', on_delete=models.SET_NULL, null=True, blank=True
    )
    created_by = models.ForeignKey("login_details.User", related_name='ticket_created_by', on_delete=models.SET_NULL, null=True, blank=True
    )
    modified_by = models.ForeignKey("login_details.User", related_name='ticket_modified_by', on_delete=models.SET_NULL, null=True, blank=True
    )
    VALID_TRANSITIONS = {
        "Open": ["Working in Progress", "Waiting for User Response", "Canceled"],
        "Working in Progress": ["Waiting for User Response", "Resolved", "Breached"],
        "Waiting for User Response": ["Working in Progress", "Canceled"],
        "Resolved": ["Closed"],
        "Breached": ["Closed"],
        "Closed": []
    }

   

    
   

    def save(self, *args, **kwargs):
        ist = pytz.timezone('Asia/Kolkata')
        current_time = timezone.now().astimezone(ist)

        is_new = self._state.adding  # Check if the ticket is new

        # Allow status changes at any time - remove blocking for Scheduled SLA
        # Users should be able to update ticket status regardless of working hours/holidays
        
        super().save(*args, **kwargs)
        # -------------------------------
# WhatsApp Notification: New Ticket
# -------------------------------
        # -------------------------------
# WhatsApp Notification: New Ticket
# -------------------------------
        if is_new and self.assignee and self.assignee.mobile:
            from whatsapp_notifications.service import notify_user

            message = (
                f"🆕 New Ticket Assigned\n"
                f"ID: {self.ticket_id}\n"
                f"Summary: {self.summary}\n"
                f"Status: {self.status}"
            )

            print(">>> Sending WhatsApp message to:", self.assignee.mobile)
            status, response = notify_user(self.assignee.mobile, message)
            print(">>> WhatsApp API Response:", status, response)


        sla_timer, created = SLATimer.objects.get_or_create(ticket=self)

        # Start SLA timer if the status is "open"
        print(f"[DEBUG] Ticket status: '{self.status}', Checking if == 'open'")
        if self.status == "open":
            print("[DEBUG] Starting SLA...")
            sla_timer.start_sla()

        if self.status == "Working in Progress":
            sla_timer.resume_sla()

        elif self.status == "Waiting for User Response":
            sla_timer.pause_sla()

        elif self.status == "Resolved":
            # Ensure SLA is stopped when ticket is resolved so timer does not remain Active
            try:
                sla_timer.stop_sla()
            except Exception as e:
                # Fallback: set end_time and mark stopped
                sla_timer.end_time = current_time
                sla_timer.sla_status = 'Stopped'
                sla_timer.save(update_fields=['end_time', 'sla_status'])

        elif self.status == "Delegated":
            pass
        elif self.status == "Breached":
            sla_timer.end_time = current_time
            sla_timer.breached = True
            sla_timer.save()         
        sla_timer.check_sla_breach()
        super().save(update_fields=['status'])

    

class Attachment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

class WorkingHours(models.Model):
    name = models.CharField(max_length=100, unique=True)  # Office or Client
    start_hour = models.TimeField(default="09:00")
    end_hour = models.TimeField(default="18:00")
    working_days = models.JSONField(default=list)  # [0,1,2,3,4] = Mon-Fri

    def __str__(self):
        return self.name


class Holiday(models.Model):
    working_hours = models.ForeignKey(
        WorkingHours, on_delete=models.CASCADE, related_name="holidays"
    )
    name = models.CharField(max_length=100)
    date = models.DateField()

    def __str__(self):
        return f"{self.name} ({self.date})"
    
from datetime import time, datetime, timedelta
from django.utils import timezone
import pytz 
class SLATimer(models.Model):
    """Model to track SLA start and end times."""
    sla_id = models.AutoField(primary_key=True)
    ticket = models.OneToOneField("timer.Ticket", on_delete=models.CASCADE, related_name="sla_timers")
    # start_time = models.DateTimeField(default=timezone.now().astimezone(pytz.timezone('Asia/Kolkata')))
    start_time = models.DateTimeField(default=timezone.now)
    paused_time = models.DateTimeField(null=True, blank=True)
    resumed_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    total_paused_time = models.DurationField(default=timedelta(0))
    working_hours =  models.ForeignKey(WorkingHours, on_delete=models.SET_NULL, null=True, blank=True)
    sla_hours = models.FloatField(null=True, blank=True)  # Total SLA hours
    sla_due_date = models.DateTimeField(null=True, blank=True)
    breached = models.BooleanField(default=False)
    warning_sent = models.BooleanField(default=False)
    sla_status = models.CharField(max_length=20, choices=[('Active', 'Active'), ('Paused', 'Paused'), ('Stopped', 'Stopped')], default='Active')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey("login_details.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="sla_created")
    modified_by = models.ForeignKey("login_details.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="sla_modified")
    is_active = models.BooleanField(default=True)
    remaining_at_pause = models.DurationField(null=True, blank=True)

    def check_and_pause_if_outside_hours(self):
        """
        Automatically pause SLA if outside working hours and SLA is active.
        """
        if self.sla_status != 'Active':
            return
        
        now = timezone.now()
        if not is_within_working_hours(now, self.working_hours):
            self.pause_sla()
            print(f"[DEBUG] SLA auto-paused due to outside working hours for Ticket ID: {self.ticket.ticket_id}")


    def get_next_start_time(self, working_hours):
        """
        Returns the correct SLA start time based on organisation's working hours.
        Skips weekends and holidays.
        """
        from timer.utils import next_working_time
        
        tz = pytz.timezone("Asia/Kolkata")
        now = timezone.now().astimezone(tz)
        start_work = working_hours.start_hour
        end_work = working_hours.end_hour

        # ✅ CRITICAL FIX: Always use next_working_time to check holidays
        # Don't assume current time is valid just because it's within working hours
        next_start = next_working_time(now, working_hours)
        
        # If next_working_time moved us to a different day, use start of that day
        # Otherwise, use the current time
        if next_start.date() != now.date():
            # Moved to next working day, so return that day's start time
            return next_start
        else:
            # Same day and within working hours, use current time
            if now.time() < start_work:
                # Before working hours → today at start time
                next_start = datetime.combine(now.date(), start_work)
                next_start = tz.localize(next_start) if next_start.tzinfo is None else next_start
            elif now.time() > end_work:
                # This shouldn't happen since next_working_time would have moved to next day
                # But keep as fallback
                next_day = now + timedelta(days=1)
                next_start = datetime.combine(next_day.date(), start_work)
                next_start = tz.localize(next_start) if next_start.tzinfo is None else next_start
                next_start = next_working_time(next_start, working_hours)
            else:
                # Within working hours on a working day → start now
                next_start = now

        return next_start

   

    
    
    def start_sla(self):
        """Start SLA timer based on organization's working hours (IST-based)."""
        from django.utils import timezone
        import pytz
        from datetime import datetime, timedelta, time

        tz = pytz.timezone("Asia/Kolkata")
        # Use ticket creation time as reference, not current time
        # This ensures SLA calculations are based on when ticket was created
        now = self.ticket.created_at.astimezone(tz)

        # Get working hours first
        working_hours = self.working_hours
        if not working_hours:
            ticket_org = getattr(self.ticket, 'ticket_organization', None)
            if ticket_org:
                working_hours = getattr(ticket_org, 'working_hours', None)
        if not working_hours:
            assignee = getattr(self.ticket, 'assignee', None)
            if assignee:
                assignee_org = getattr(assignee, 'organisation', None)
                if assignee_org:
                    working_hours = getattr(assignee_org, 'working_hours', None)
        if not working_hours:
            start_work, end_work = time(9, 30), time(18, 30)
        else:
            start_work, end_work = working_hours.start_hour, working_hours.end_hour

        # Block starting outside working hours - schedule for next day
        if not (start_work <= now.time() <= end_work):
            print(f"[SCHEDULED] Ticket created outside working hours for Ticket {self.ticket.ticket_id}. Now: {now.time()}, Allowed: {start_work}-{end_work}")
            # Schedule for next working day
            next_start = self.get_next_start_time(working_hours)
            self.start_time = next_start
            self.sla_status = 'Scheduled'
            response_time = getattr(self.ticket.priority, "response_target_time", timedelta(hours=8))
            
            # ✅ Store full priority response time in remaining_at_pause
            self.remaining_at_pause = response_time
            
            # Only calculate due date if not already set
            if not self.sla_due_date:
                self.sla_due_date = self.calculate_sla_due_with_working_hours(response_time)
            self.save(update_fields=["start_time", "sla_status", "sla_due_date", "remaining_at_pause"])
            print(f"[TIMER WAIT] SLA scheduled for {next_start}, due {self.sla_due_date}")
            print(f"[TIMER WAIT] Remaining at pause: {self.remaining_at_pause}")
            return

        tz = pytz.timezone("Asia/Kolkata")
        
        # ✅ CRITICAL FIX: Use ticket creation time if SLA has never been started
        # This ensures we calculate from when the ticket was created, not when start_sla() is called
        if not self.start_time or self.sla_status == "Scheduled":
            reference_time = self.ticket.created_at.astimezone(tz)
            print(f"[DEBUG] Using ticket creation time as reference: {reference_time}")
        else:
            reference_time = timezone.now().astimezone(tz)
            print(f"[DEBUG] Using current time as reference: {reference_time}")
        
        now = reference_time
        print(f"[DEBUG] Current IST Time: {now}")

        # 1️⃣ Dynamically get working hours
        # Resolve working hours in a safe order:
        # 1. explicitly set on the SLA timer
        # 2. ticket's configured organisation working hours
        # 3. ticket assignee's organisation working hours
        working_hours = self.working_hours
        if not working_hours:
            ticket_org = getattr(self.ticket, 'ticket_organization', None)
            if ticket_org:
                working_hours = getattr(ticket_org, 'working_hours', None)
        if not working_hours:
            assignee = getattr(self.ticket, 'assignee', None)
            if assignee:
                assignee_org = getattr(assignee, 'organisation', None)
                if assignee_org:
                    working_hours = getattr(assignee_org, 'working_hours', None)

        if not working_hours:
            print("[DEBUG] No working hours configured. Using default 09:30–18:30.")
            start_work, end_work = time(9, 30), time(18, 30)
        else:
            start_work, end_work = working_hours.start_hour, working_hours.end_hour
            print(f"[DEBUG] Found WorkingHours ID: {working_hours.id}, Name: {working_hours.name}")

        print(f"[DEBUG] Working Hours: {start_work} to {end_work}")
        print(f"[DEBUG] Current time is: {now.time()}")

        # 2️⃣ Check if reference time is within working hours (including holiday check)
        if is_within_working_hours(now, working_hours):
            # Calculate remaining time today
            end_time_today = now.replace(hour=end_work.hour, minute=end_work.minute, second=0, microsecond=0)
            remaining_minutes_today = (end_time_today - now).total_seconds() / 60
            
            # Get response time to check if there's enough time today
            response_time = getattr(self.ticket.priority, "response_target_time", timedelta(hours=8))
            response_minutes = response_time.total_seconds() / 60
            
            print(f"[DEBUG] Remaining minutes today: {remaining_minutes_today:.2f}")
            print(f"[DEBUG] Response time needed: {response_minutes:.2f} minutes")
            
            # ✅ If less than 15 minutes remaining today OR not enough time for the full SLA, schedule for next day
            if remaining_minutes_today < 15 or remaining_minutes_today < response_minutes * 0.1:
                print(f"[DEBUG] Insufficient time remaining today ({remaining_minutes_today:.2f} min). Scheduling for next working day.")
                next_start = self.get_next_start_time(working_hours)
                current_now = timezone.now().astimezone(tz)
                
                self.start_time = next_start
                self.sla_status = "Scheduled"
                
                # ✅ Store full priority response time in remaining_at_pause
                self.remaining_at_pause = response_time
                
                # ✅ Calculate due date even for scheduled tickets so frontend knows completion time
                # Only calculate if not already set
                if not self.sla_due_date:
                    self.sla_due_date = self.calculate_sla_due_with_working_hours(response_time)
                
                self.save(update_fields=["start_time", "sla_status", "sla_due_date", "remaining_at_pause"])
                print(f"[TIMER WAIT] SLA will start later at {next_start}")
                print(f"[TIMER WAIT] Due date will be: {self.sla_due_date}")
                print(f"[TIMER WAIT] Remaining at pause: {self.remaining_at_pause}")
                return
            
            # Within working hours with sufficient time → start immediately
            print(f"[DEBUG] Sufficient time remaining today. Starting SLA immediately.")
            self.start_time = reference_time
            self.sla_status = "Active"
            
            # Only calculate due date if not already set
            if not self.sla_due_date:
                self.sla_due_date = self.calculate_sla_due_with_working_hours(response_time)
            self.save(update_fields=["start_time", "sla_status", "sla_due_date"])
            
            print(f"[SLA STARTED] Ticket {self.ticket.ticket_id} | Start: {self.start_time} | Due: {self.sla_due_date}")
        else:
            # Outside working hours → schedule for next working time
            next_start = self.get_next_start_time(working_hours)
            current_now = timezone.now().astimezone(tz)
            time_diff = (next_start - current_now).total_seconds()
            
            if time_diff > 1:
                self.start_time = next_start
                self.sla_status = "Scheduled"
                
                # ✅ Store full priority response time in remaining_at_pause
                response_time = getattr(self.ticket.priority, "response_target_time", timedelta(hours=8))
                print(f"[DEBUG] Response time from priority: {response_time}")
                self.remaining_at_pause = response_time
                print(f"[DEBUG] Set remaining_at_pause to: {self.remaining_at_pause}")
                
                # ✅ Calculate due date for scheduled tickets
                # Only calculate if not already set
                if not self.sla_due_date:
                    self.sla_due_date = self.calculate_sla_due_with_working_hours(response_time)
                    print(f"[DEBUG] Calculated sla_due_date: {self.sla_due_date}")
                
                self.save(update_fields=["start_time", "sla_status", "sla_due_date", "remaining_at_pause"])
                print(f"[TIMER WAIT] SLA will start later at {next_start}")
                print(f"[TIMER WAIT] Due date will be: {self.sla_due_date}")
                print(f"[TIMER WAIT] Remaining at pause: {self.remaining_at_pause}")
                return
            else:
                # Edge case: next_start is now, start immediately
                self.start_time = current_now
                self.sla_status = "Active"
                
                response_time = getattr(self.ticket.priority, "response_target_time", timedelta(hours=8))
                # Only calculate if not already set
                if not self.sla_due_date:
                    self.sla_due_date = self.calculate_sla_due_with_working_hours(response_time)
                
                self.save(update_fields=["start_time", "sla_status", "sla_due_date"])
                
                print(f"[SLA STARTED] Ticket {self.ticket.ticket_id} | Start: {self.start_time} | Due: {self.sla_due_date}")






    def activate_scheduled_sla(self):
        """Activate a previously scheduled SLA (only when schedule time arrives)."""
        # Only activate if currently Scheduled and a start_time exists
        if self.sla_status != "Scheduled" or not self.start_time:
            return

        ist = pytz.timezone('Asia/Kolkata')
        now = timezone.now().astimezone(ist)

        # Define working hours (prefer configured hours)
        wh = self.working_hours
        if not wh:
            ticket_org = getattr(self.ticket, 'ticket_organization', None)
            if ticket_org:
                wh = getattr(ticket_org, 'working_hours', None)
        if not wh:
            assignee = getattr(self.ticket, 'assignee', None)
            if assignee:
                assignee_org = getattr(assignee, 'organisation', None)
                if assignee_org:
                    wh = getattr(assignee_org, 'working_hours', None)

        if wh:
            start_work, end_work = wh.start_hour, wh.end_hour
        else:
            start_work, end_work = time(9, 30), time(18, 30)

        # ✅ If current time is outside working hours, delay activation until next working window
        if now.time() < start_work:
            # Before office hours — wait until today's 9:30 AM
            self.start_time = now.replace(hour=start_work.hour, minute=start_work.minute, second=0, microsecond=0)
            print(f"[TIMER WAIT] Before working hours. SLA will start at {self.start_time}")

            return

        elif now.time() > end_work:
            # After office hours — schedule next day at 9:30 AM
            next_day = now + timedelta(days=1)
            self.start_time = next_day.replace(hour=start_work.hour, minute=start_work.minute, second=0, microsecond=0)
            print(f"[TIMER WAIT] After working hours. SLA will start next day at {self.start_time}")

            return

        # ✅ If within working hours and scheduled time reached, activate SLA immediately
        print(f"[TIMER START] Activating scheduled SLA for ticket {self.ticket.ticket_id} at {now}")

        # Compute SLA due date
        if self.remaining_at_pause:
            response_time = self.remaining_at_pause
        else:
            response_time = getattr(self.ticket.priority, "response_target_time", timedelta(hours=8))
        
        # Only calculate if not already set
        if not self.sla_due_date:
            self.sla_due_date = self.calculate_sla_due_with_working_hours(response_time)

        self.sla_status = "Active"
        self.remaining_at_pause = None
        self.paused_time = None
        self.save(update_fields=["sla_status", "sla_due_date", "remaining_at_pause", "paused_time"])
        print(f"[DEBUG] Scheduled SLA activated for ticket {self.ticket.ticket_id} at {now}, due {self.sla_due_date}")

            



    def pause_sla(self, auto_schedule=False):
        """
        Pause the SLA timer.
        If auto_schedule=True, transitions to Scheduled (for end-of-day) instead of Paused.
        """
        # Don't pause if already Scheduled - it already has correct remaining_at_pause
        if self.sla_status == 'Scheduled':
            print(f"[DEBUG] Ticket {self.ticket.ticket_id} already Scheduled. Skipping pause.")
            return
            
        if self.sla_status == 'Active':
            # Compute remaining first, then mark paused_time to avoid a tiny skew
            remaining = self.calculate_remaining_time()
            self.remaining_at_pause = remaining  # Store remaining time
            self.paused_time = timezone.now()

            if auto_schedule:
                # Transition to Scheduled for next working day instead of Paused
                working_hours = self.working_hours
                if not working_hours:
                    ticket_org = getattr(self.ticket, 'ticket_organization', None)
                    if ticket_org:
                        working_hours = getattr(ticket_org, 'working_hours', None)
                if not working_hours:
                    assignee = getattr(self.ticket, 'assignee', None)
                    if assignee:
                        assignee_org = getattr(assignee, 'organisation', None)
                        if assignee_org:
                            working_hours = getattr(assignee_org, 'working_hours', None)
                next_start = self.get_next_start_time(working_hours)
                self.start_time = next_start
                self.sla_status = 'Scheduled'
                # remaining already computed above; ensure it's stored
                self.save(update_fields=['paused_time', 'remaining_at_pause', 'sla_status', 'start_time'])
                print(f"[AUTO SCHEDULED] SLA scheduled for next working day at {next_start} for Ticket {self.ticket.ticket_id}. Remaining at pause: {self.remaining_at_pause}")
            else:
                # Normal pause (user-initiated)
                self.sla_status = 'Paused'
                self.save(update_fields=['paused_time', 'remaining_at_pause', 'sla_status'])
                print(f"[DEBUG] SLA paused for Ticket ID: {self.ticket.ticket_id}. Remaining Time: {self.remaining_at_pause}")

    

    
    def resume_sla(self):
        # Block resuming outside working hours
        from django.utils import timezone
        import pytz
        from datetime import time

        tz = pytz.timezone("Asia/Kolkata")
        now = timezone.now().astimezone(tz)

        # Get working hours
        working_hours = self.working_hours
        if not working_hours:
            ticket_org = getattr(self.ticket, 'ticket_organization', None)
            if ticket_org:
                working_hours = getattr(ticket_org, 'working_hours', None)
        if not working_hours:
            assignee = getattr(self.ticket, 'assignee', None)
            if assignee:
                assignee_org = getattr(assignee, 'organisation', None)
                if assignee_org:
                    working_hours = getattr(assignee_org, 'working_hours', None)
        if not working_hours:
            start_work, end_work = time(9, 30), time(18, 30)
        else:
            start_work, end_work = working_hours.start_hour, working_hours.end_hour

        if not (start_work <= now.time() <= end_work):
            print(f"[BLOCKED] Attempt to resume SLA outside working hours for Ticket {self.ticket.ticket_id}. Now: {now.time()}, Allowed: {start_work}-{end_work}")
            return
        # Restrict starting if SLA is scheduled for a future time
        if self.sla_status == 'Scheduled' and self.start_time and timezone.now() < self.start_time:
            print(f"[BLOCKED] Attempt to start SLA before scheduled time for Ticket {self.ticket.ticket_id}. Scheduled at {self.start_time}")
            return

        # Allow both Paused and Scheduled to resume
        if self.sla_status not in ['Paused', 'Scheduled']:
            return

        now = timezone.now()

        # Use remaining_at_pause if present, else fallback to full response time
        remaining = self.remaining_at_pause
        if not remaining:
            response_time = None
            if self.ticket and self.ticket.priority:
                response_time = self.ticket.priority.response_target_time
            remaining = response_time

        # Accumulate total paused time for metrics
        if self.paused_time:
            try:
                pause_duration = timezone.now() - self.paused_time
                if isinstance(pause_duration, timedelta):
                    self.total_paused_time = (self.total_paused_time or timedelta(0)) + pause_duration
            except Exception:
                pass

        # Recalculate due date from now using remaining (always recalc on resume)
        self.sla_due_date = self.calculate_due_from(now, remaining)

        # Clear pause markers and activate
        self.paused_time = None
        self.remaining_at_pause = None
        self.sla_status = 'Active'
        self.save(update_fields=['sla_due_date', 'sla_status', 'paused_time', 'remaining_at_pause', 'total_paused_time'])
        print(f"[DEBUG] Resuming SLA for Ticket ID: {self.ticket.ticket_id}. Remaining Time: {remaining}, New Due Date: {self.sla_due_date}")

    def calculate_due_from(self, base_time, response_time=None):
        """Calculate due date starting from base_time, respecting working hours/holidays."""
        if not base_time:
            base_time = timezone.now()
        if not response_time:
            response_time = self.ticket.priority.response_target_time or timedelta(hours=8)

        # Resolve working hours
        working_hours = getattr(self, 'working_hours', None)
        if not working_hours:
            ticket_org = getattr(self.ticket, 'ticket_organization', None)
            if ticket_org:
                working_hours = getattr(ticket_org, 'working_hours', None)
        if not working_hours:
            assignee = getattr(self.ticket, 'assignee', None)
            if assignee:
                assignee_org = getattr(assignee, 'organisation', None)
                if assignee_org:
                    working_hours = getattr(assignee_org, 'working_hours', None)
        if not working_hours:
            return base_time + response_time

        ist = pytz.timezone('Asia/Kolkata')
        current_time = base_time.astimezone(ist)

        remaining_hours = response_time.total_seconds() / 3600
        # Note: do NOT add self.total_paused_time here — that would inflate the remaining time
        # The remaining time passed in (response_time or remaining_at_pause) already accounts for pauses.

        # Snap to next working time
        current_time = next_working_time(current_time, working_hours)

        while remaining_hours > 0:
            day_end = current_time.replace(
                hour=working_hours.end_hour.hour,
                minute=working_hours.end_hour.minute,
                second=0,
                microsecond=0
            )
            hours_left_today = (day_end - current_time).total_seconds() / 3600
            if hours_left_today >= remaining_hours:
                current_time += timedelta(hours=remaining_hours)
                remaining_hours = 0
            else:
                remaining_hours -= max(hours_left_today, 0)
                current_time = day_end + timedelta(hours=1)
                current_time = next_working_time(current_time, working_hours)

        return current_time

    def maybe_activate_now(self):
        """If currently Scheduled but now is within working hours and sufficient time remains, activate immediately."""
        if self.sla_status != 'Scheduled':
            return False

        ist = pytz.timezone('Asia/Kolkata')
        now = timezone.now().astimezone(ist)

        # Determine working hours
        wh = self.working_hours
        if not wh:
            ticket_org = getattr(self.ticket, 'ticket_organization', None)
            if ticket_org:
                wh = getattr(ticket_org, 'working_hours', None)
        if not wh:
            assignee = getattr(self.ticket, 'assignee', None)
            if assignee:
                assignee_org = getattr(assignee, 'organisation', None)
                if assignee_org:
                    wh = getattr(assignee_org, 'working_hours', None)

        if wh:
            start_work, end_work = wh.start_hour, wh.end_hour
        else:
            start_work, end_work = time(9, 30), time(18, 30)

        # Only consider activating if within working hours (including holiday check)
        if not is_within_working_hours(now, wh):
            return False

        # Check if enough time remains today
        end_today = now.replace(hour=end_work.hour, minute=end_work.minute, second=0, microsecond=0)
        remaining_minutes_today = (end_today - now).total_seconds() / 60

        response_time = getattr(self.ticket.priority, 'response_target_time', timedelta(hours=8))
        response_minutes = response_time.total_seconds() / 60

        if remaining_minutes_today < 15 or remaining_minutes_today < response_minutes * 0.1:
            # Still not enough time to start today
            return False

        # Activate immediately using current time as start
        self.start_time = now
        self.sla_status = 'Active'
        
        # Only calculate if not already set
        if not self.sla_due_date:
            self.sla_due_date = self.calculate_sla_due_with_working_hours(response_time)
        
        self.save(update_fields=['start_time', 'sla_status', 'sla_due_date'])
        print(f"[SLA STARTED NOW] Ticket {self.ticket.ticket_id} | Start: {self.start_time} | Due: {self.sla_due_date}")
        return True





    # 4️⃣ Stop SLA
    def stop_sla(self):
        # Store remaining time before stopping
        if self.sla_status == 'Active':
            self.remaining_at_pause = self.calculate_remaining_time()
        
        self.sla_status = 'Stopped'
        self.end_time = timezone.now()
        self.save(update_fields=['sla_status', 'end_time', 'remaining_at_pause'])


   
    
    def calculate_remaining_time(self):
        # If Scheduled, show last paused time if available, else full SLA
        if self.sla_status == 'Scheduled':
            if self.remaining_at_pause:
                return self.remaining_at_pause
            if self.ticket and self.ticket.priority:
                return self.ticket.priority.response_target_time or timedelta(hours=8)
            return timedelta(hours=8)

        if self.sla_status == 'Paused' and self.remaining_at_pause:
            return self.remaining_at_pause

        # If SLA is stopped or breached, show remaining time at the moment it was stopped/breached
        if self.sla_status in ['Stopped', 'Breached']:
            if self.remaining_at_pause:
                return self.remaining_at_pause
            return timedelta(0)

        if not self.sla_due_date:
            return timedelta(0)

        # For Active tickets, calculate working hours remaining (not calendar time)
        if self.sla_status == 'Active':
            return self.calculate_working_hours_between(timezone.now(), self.sla_due_date)

        remaining = self.sla_due_date - timezone.now()
        if remaining.total_seconds() < 0:
            return timedelta(0)
        return remaining
    
    def calculate_working_hours_between(self, start_time, end_time):
        """Calculate actual working hours between start_time and end_time."""
        if not start_time or not end_time or start_time >= end_time:
            return timedelta(0)
        
        # Get working hours config
        working_hours = getattr(self, 'working_hours', None)
        if not working_hours:
            ticket_org = getattr(self.ticket, 'ticket_organization', None)
            if ticket_org:
                working_hours = getattr(ticket_org, 'working_hours', None)
        if not working_hours:
            assignee = getattr(self.ticket, 'assignee', None)
            if assignee:
                assignee_org = getattr(assignee, 'organisation', None)
                if assignee_org:
                    working_hours = getattr(assignee_org, 'working_hours', None)
        
        if not working_hours:
            # No working hours - return calendar time
            return end_time - start_time
        
        import pytz
        from datetime import time as dt_time
        ist = pytz.timezone('Asia/Kolkata')
        current = start_time.astimezone(ist)
        end = end_time.astimezone(ist)
        
        start_hour = working_hours.start_hour
        end_hour = working_hours.end_hour
        working_days = working_hours.working_days
        if isinstance(working_days, str):
            import json
            working_days = json.loads(working_days)
        
        total_minutes = 0
        
        while current < end:
            # Skip non-working days
            if current.weekday() not in working_days:
                current = current.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                continue
            
            # Get working window for current day
            day_start = current.replace(hour=start_hour.hour, minute=start_hour.minute, second=0, microsecond=0)
            day_end = current.replace(hour=end_hour.hour, minute=end_hour.minute, second=0, microsecond=0)
            
            # Clip to working hours
            work_start = max(current, day_start)
            work_end = min(end, day_end)
            
            if work_start < work_end and work_start.time() >= start_hour and work_start.time() <= end_hour:
                minutes = (work_end - work_start).total_seconds() / 60
                total_minutes += minutes
            
            # Move to next day
            current = current.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        return timedelta(minutes=total_minutes)




    def get_remaining_time(self):
        remaining = self.calculate_remaining_time()
        return remaining if remaining else timedelta(0)

    

    def check_sla_breach(self):
        """
        Check if SLA is breached, but ignore while paused or already breached.
        """
        # ❌ Skip if no due date or SLA is paused/breached/closed
        if not self.sla_due_date or self.sla_status in ['Paused', 'Breached', 'Stopped']:
            return False

        now = timezone.now()

        # 🚨 Case: SLA Breached
        if now > self.sla_due_date and not self.breached:
            self.breached = True
            self.sla_status = 'Breached'
            self.end_time = now
            self.save(update_fields=['breached', 'sla_status', 'end_time'])
            self.send_breach_notification()
            print(f"[DEBUG] SLA breached for {self.ticket.ticket_id}")
            return True

        # ⚠️ Warning case (75%)
        if not self.warning_sent:
            total_time = self.sla_due_date - self.start_time
            elapsed_time = now - self.start_time - self.total_paused_time

            # Calculate warning threshold (75% of total active time)
            if elapsed_time > total_time * 0.75:
                self.warning_sent = True
                self.save(update_fields=['warning_sent'])
                self.send_warning_notification()
                print(f"[DEBUG] SLA warning sent for {self.ticket.ticket_id}")

        return self.breached




    def send_warning_notification(self):
        from .tasks import send_sla_warning_notification
        if self.ticket.assignee and self.ticket.assignee.email:
            send_sla_warning_notification.delay(
                ticket_id=str(self.ticket.ticket_id),
                recipient_email=self.ticket.assignee.email,
                due_date=self.sla_due_date
            )

    def send_breach_notification(self):
        from .tasks import send_sla_breach_notification
        if self.ticket.assignee and self.ticket.assignee.email:
            send_sla_breach_notification.delay(
                ticket_id=str(self.ticket.ticket_id),
                recipient_email=self.ticket.assignee.email
            )

    # 7️⃣ ✅ NEW: SLA Due Date Considering Working Hours & Holidays
    def calculate_sla_due_with_working_hours(self, response_time=None):
        """
        Calculate SLA due date considering:
        - Working hours
        - Weekends
        - Holidays
        - Paused time
        """
        if not self.start_time or not self.ticket:
            print("[DEBUG] Missing start_time or ticket. Returning current time.")
            return timezone.now()

        if not response_time:
            response_time = self.ticket.priority.response_target_time or timedelta(hours=8)
        print(f"[DEBUG] Response Time: {response_time}")

        # Prefer an explicitly set SLA working_hours, then ticket organisation, then assignee organisation
        working_hours = getattr(self, 'working_hours', None)
        if not working_hours:
            working_hours = getattr(self.ticket, 'ticket_organization', None) and getattr(self.ticket.ticket_organization, 'working_hours', None)
        if not working_hours:
            working_hours = getattr(self.ticket.assignee, 'organisation', None) and getattr(self.ticket.assignee.organisation, 'working_hours', None)
        if not working_hours:
            print("[DEBUG] No working hours configured. Using default response time.")
            return self.start_time + response_time

        print(f"[DEBUG] Working Hours: {working_hours.start_hour} to {working_hours.end_hour}")
        
        # ✅ CRITICAL FIX: Convert to IST timezone for proper hour comparisons
        ist = pytz.timezone('Asia/Kolkata')
        current_time = self.start_time.astimezone(ist)
        print(f"[DEBUG] Start Time (IST): {current_time}")

        remaining_hours = response_time.total_seconds() / 3600
        # Do NOT add self.total_paused_time here - that would incorrectly extend the SLA
        print(f"[DEBUG] Remaining Hours: {remaining_hours}")

        # ✅ Adjust start time if outside working hours (now in IST)
        current_time = next_working_time(current_time, working_hours)
        print(f"[DEBUG] Adjusted Start Time (IST): {current_time}")

        while remaining_hours > 0:
            day_end = current_time.replace(
                hour=working_hours.end_hour.hour,
                minute=working_hours.end_hour.minute,
                second=0,
                microsecond=0
            )
            hours_left_today = (day_end - current_time).total_seconds() / 3600
            print(f"[DEBUG] Hours Left Today: {hours_left_today}")

            if hours_left_today >= remaining_hours:
                # Enough time left today to complete
                current_time += timedelta(hours=remaining_hours)
                remaining_hours = 0
            else:
                # Not enough time today - subtract what we have and move to next day
                remaining_hours -= max(hours_left_today, 0)
                # Move past end of today's working hours to force next_working_time to go to next day
                current_time = day_end + timedelta(hours=1)  # Move to next day
                # Get the start of next working day
                current_time = next_working_time(current_time, working_hours)

            print(f"[DEBUG] Next Working Day Start Time: {current_time}")

        # Return the calculated due date
        return current_time

    

    def should_start_sla(ticket, wh):
        ist = pytz.timezone('Asia/Kolkata')
        created_time_ist = ticket.created_at.astimezone(ist)
        created_time_only = created_time_ist.time()

        # Fix type if needed
        if isinstance(wh.end_hour, str):
            wh.end_hour = datetime.strptime(wh.end_hour, "%H:%M:%S").time()
        if isinstance(wh.start_hour, str):
            wh.start_hour = datetime.strptime(wh.start_hour, "%H:%M:%S").time()

        print("Working hours:", wh.start_hour, "to", wh.end_hour)
        print("Created time:", created_time_only)

        if wh.start_hour <= created_time_only <= wh.end_hour:
            print("✅ Created within working hours → Start SLA now")
            return True
        else:
            print("⏸ Outside working hours → Delay until next start")
            return False


class PauseLogs(models.Model):
    sla_timer = models.ForeignKey(SLATimer, on_delete=models.CASCADE, related_name="pause_logs")
    paused_time = models.DateTimeField(null=True,blank=True)
    resumed_time = models.DateTimeField(null=True, blank=True)
    pause_duration = models.DurationField(default=timedelta)

    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)
        
        
def nows():
    ist = pytz.timezone('Asia/Kolkata')
    current_time = timezone.now().astimezone(ist)
    return current_time

class TicketComment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    comment = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_internal = models.BooleanField(default=False)
 
class TicketCommentAttachment(models.Model):
    comment = models.ForeignKey(TicketComment, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='ticket_attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey("login_details.User", on_delete=models.CASCADE, null=True, blank=True)
