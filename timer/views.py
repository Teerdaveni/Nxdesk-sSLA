import re
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from history.serializers import TicketHistorySerializer

from roles_creation.models import UserRole
from roles_creation.serializers import UserRoleSerializer
from organisation_details.serializers import EmployeeSerializer
from organisation_details.models import Employee
from .serializers import SLATimerSerializer,TicketSerializer,AssignTicketSerializer
from .models import Ticket, SLATimer,PauseLogs
from  login_details.serializers import LoginSerializer
from  login_details.models import User
from datetime import timedelta, datetime
from django.shortcuts import render, get_object_or_404
from .tasks import send_ticket_creation_email 
from .tasks import send_assignment_email        # celery---assigning to developer
from rest_framework.exceptions import APIException, NotFound
from django.contrib.auth import get_user_model
User = get_user_model()
from roles_creation.permissions import HasRolePermission
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import LimitOffsetPagination
from .tasks import send_status_change_email_async
from django.db import transaction
from priority.models import Priority
from .models import TicketComment, Ticket
from .serializers import (
    TicketCommentCreateSerializer,
    TicketCommentListSerializer
)
from rest_framework import serializers
from rest_framework.serializers import ValidationError
from django.db.models import Q
from .tasks import send_auto_assignment_email_to_dispatcher,send_dispatch_assignment_emails,send_ticket_reassignment_email
from organisation_details.models import Organisation
from solution_groups.models import SolutionGroup
 
 




def increment_id(id_str):
        match = re.match(r"([A-Za-z]+)(\d+)", id_str)
        if match:
            prefix, num = match.groups()
            new_num = str(int(num) + 1).zfill(len(num))  # Preserve leading zeros
            return f"{prefix}{new_num}"
        return id_str

class TicketAPI_Delegated(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def get(self, request):
        
        tickets = User.objects.all()
        login_id = LoginSerializer(tickets,many=True)
        final_user_list=[ {i['id']:i['username']} for i in login_id.data]
        print(login_id.data)
        tickets = Ticket.objects.filter(status='Delegated')
        serializer = TicketSerializer(tickets, many=True)
        final_data=serializer.data
        for i in final_data:
            i['all_assignee']=final_user_list
        return Response(final_data) 

    def post(self, request):
        """POST method to create or update a ticket"""                       
        ticket_id = request.data.get("ticket_id")   
        data = dict(request.data)
        assignee = data.get("assignee")
        new_assignee = data.get("newassignee")
        pre_assignee = data.get("pre_assignee", [])
        if new_assignee[0]  in [pre_assignee][-1]:
            return Response('Cant assign to the same assignee', status=status.HTTP_400_BAD_REQUEST)
        if isinstance(pre_assignee, list):
            pre_assignee = [item for sublist in pre_assignee for item in (sublist if isinstance(sublist, list) else [sublist])]
        if assignee[0] not in pre_assignee:
            pre_assignee.append(assignee[0])
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
 
        
       
        processed_data= {'csrfmiddlewaretoken':request.data['csrfmiddlewaretoken'],
                         'assignee':new_assignee[0],
                         'status':'open',
                         'pre_assignee':pre_assignee,
                         'ticket_id':ticket_id}
        print(processed_data)
        if ticket_id:
            ticket = Ticket.objects.filter(ticket_id=ticket_id).first()
            print(ticket)
            data ={"title":f"{request.username} delegated Ticket", "ticket":ticket_id,"created_by":request.user}

            if ticket:
                serializer = TicketSerializer(ticket, data=processed_data, partial=True
                                              )
                
                if serializer.is_valid():
                    serializer.save()
                    serializer_history = TicketHistorySerializer(data=data)

                    if serializer_history.is_valid():
                        print("history is validadedtdttdtdtddddddddddd")
                        serializer_history.save(modified_by=request.user)
                    else:
                        print("NOOOOOOOOOO")
                    return Response(serializer.data, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # If no `ticket_id`, create a new ticket
        serializer = TicketSerializer(data=request.data)
        if serializer.is_valid():  # ✅ This must be called before accessing `.data`
            serializer.save()
           
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ReferenceTicketAPILIST(APIView):
    permission_classes = [IsAuthenticated] 
    authentication_classes = [JWTAuthentication]
    def get(self, request):
            # Assuming the related field in the Ticket model is `created_by`
            tickets = Ticket.objects.all()
            serializer = TicketSerializer(tickets, many=True)
            final_data = [{'ticket_id': i['ticket_id'], 'summary': i['summary']} for i in serializer.data]
            return Response(final_data)
        
        
    
class TicketAPIID(APIView):
    permission_classes = [IsAuthenticated] 
    authentication_classes = [JWTAuthentication]
    def get(self, request):
        try:

            data = dict(request.GET)
            org_data = (data['id'][0])
        except:
            org_data = 'S'
        tickets = Ticket.objects.all()
        serializer = TicketSerializer(tickets, many=True)
        final_data = [i['ticket_id'] for i in serializer.data ]
        filtered_data = [item for item in final_data if item.startswith(org_data)]
        if len(filtered_data)==0:
            filtered_data.append(f'{org_data}'+'00000000')
        final_id=sorted(filtered_data)[-1]
        new_id= increment_id(final_id)
        return Response(new_id)  
    
class GetAssignee(APIView):
    def get(self, request):
        try:
            
            data =dict( request.GET)
            org_data = (data['org'][0])
        except:
            org_data = 'All'
        tickets = Employee.objects.filter(organisation__organisation_name=org_data)
        print(tickets)
        serializer = EmployeeSerializer(tickets,many=True)
        
        print(serializer.data)
        d=[]
        for i in serializer.data:
            
            d.append(i['user_role'])
        users = UserRole.objects.filter(user_role_idsin=d)
        users_names= UserRoleSerializer(users,many=True)
        print(users_names.data)
    
        # final_data = [i['ticket_id'] for i in serializer.data ]
        # filtered_data = [item for item in final_data if item.startswith(org_data)]
       
        return Response(users_names.data)  
# class TicketAPIView(APIView):
#     """Handles GET and POST for tickets"""
#     def get(self, request):
#         """get method to get all ticket objects"""
#         tickets = Ticket.objects.all()
#         serializer = TicketSerializer(tickets, many=True)
#         return Response(serializer.data)
from .models import Attachment
from project_details.models import ProjectsDetails  
class CreateTicketAPIView(APIView):
    """API for creating a ticket"""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Get assigned projects for the current user
        assigned_projects_qs = ProjectsDetails.objects.filter(
            projects__project_asignee=request.user,
            projects__is_active=True
        ).distinct()

        assigned_projects = []
        for project in assigned_projects_qs:
            assigned_projects.append({
                "project_id": project.project_id,
                "project_name": project.project_name,
                "product_mail": project.product_mail or "",  # Make sure this field exists in your model
            })

        return Response({
            "assigned_projects": assigned_projects
        })

    def post(self, request):
        self.permission_required = "create_ticket"
        if not HasRolePermission.has_permission(self, request, self.permission_required):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        data = {k: v for k, v in request.data.items() if not hasattr(v, 'read')}
        data['created_by'] = request.user.id
        print(f"DEBUG: Request data before processing: {data}")

        # Auto-increment Ticket ID if needed
        ticket_id = data.get("ticket_id", "")
        prefix = ''.join([c for c in ticket_id if c.isalpha()])
        existing_ids = Ticket.objects.filter(ticket_id__startswith=prefix).values_list('ticket_id', flat=True)
        if ticket_id in existing_ids:
            last_id = sorted(existing_ids)[-1]
            data["ticket_id"] = increment_id(last_id)

        # Handle attachments
        attachments_data = []

        for key, value in request.data.items():
            if key.endswith('[file]') and hasattr(value, 'read'):
                attachments_data.append(value)

        if not attachments_data:
            for key, file_obj in request.FILES.items():
                if '[file]' in key or key in ['attachments', 'attachment']:
                    attachments_data.append(file_obj)

        # Remove attachment keys from main data
        keys_to_remove = [key for key in request.data.keys() if key.startswith('attachments[')]
        for key in keys_to_remove:
            del request.data[key]

        # Assignee logic
        assignee_input = str(data.get('assignee', '')).strip().lower()
        dispatcher_user = None
        if not assignee_input or assignee_input == 'auto':
            dispatcher_role = UserRole.objects.filter(role__name="Dispatcher", is_active=True).select_related('user').first()
            if dispatcher_role and dispatcher_role.user:
                data['assignee'] = dispatcher_role.user.id
                dispatcher_user = dispatcher_role.user
            else:
                return Response({"error": "No active dispatcher available for auto-assignment."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                data['assignee'] = int(data['assignee'])
            except ValueError:
                return Response({"error": "Assignee must be a valid user ID."}, status=status.HTTP_400_BAD_REQUEST)

        # Save the ticket
        serializer = TicketSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        ticket = serializer.save(
            created_by=request.user,
            modified_by=request.user,
            is_active=True
        )

        # Save attachments with ticket
        attachments_created = 0
        for file in attachments_data:
            try:
                Attachment.objects.create(ticket=ticket, file=file)
                attachments_created += 1
            except Exception as e:
                print(f"[ERROR] Failed to create attachment: {str(e)}")

        # Email notifications
        if ticket.assignee:
            engineer_email = str(ticket.assignee.email)
            requester_email = str(request.user.email)
            dev_org_email = str(ticket.assignee.organisation.organisation_mail) if ticket.assignee.organisation else None

            from .tasks import send_ticket_creation_email
            send_ticket_creation_email.delay(
                str(ticket.ticket_id),
                engineer_email,
                requester_email,
                dev_org_email
            )

            if dispatcher_user:
                from .tasks import send_auto_assignment_email_to_dispatcher
                send_auto_assignment_email_to_dispatcher.delay(str(ticket.ticket_id), str(dispatcher_user.email))

        # Ticket history
        history_data = {
            "title": f"{request.user.username} created Ticket",
            "ticket": ticket.ticket_id,
            "created_by": request.user.id
        }

        history_serializer = TicketHistorySerializer(data=history_data)
        if history_serializer.is_valid():
            history_serializer.save(modified_by=request.user)

        return Response({
            "message": "Ticket created successfully",
            "ticket_id": ticket.ticket_id,
            "attachments_created": attachments_created
        }, status=status.HTTP_201_CREATED)



class ListTicketAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
     
    def get(self, request, assignee=None):
        self.permission_required = "view_ticket"
        HasRolePermission.has_permission(self, request, self.permission_required)
 
        print(f"Logged-in user: {request.user}")
        print(f"User ID: {request.user.id}")
        print(request.query_params.get)
 
        # If user is Admin, return all active tickets
        if UserRole.objects.filter(user=request.user, role__name='Admin', is_active=True).exists():
            all_tickets = Ticket.objects.filter(is_active=True)
            paginator = LimitOffsetPagination()
            paginated = paginator.paginate_queryset(all_tickets, request, view=self)
            serializer = TicketSerializer(paginated, many=True)
            return paginator.get_paginated_response({
                "all_tickets": serializer.data
            })
 
        # If user is not admin, get created, assigned, and all tickets involving the user
        created_tickets = Ticket.objects.filter(created_by=request.user)
        assigned_tickets = Ticket.objects.filter(assignee=request.user).exclude(
            ticket_id__in=created_tickets.values_list('ticket_id', flat=True)
        )
        all_tickets_user = Ticket.objects.filter(
            Q(created_by=request.user) | Q(assignee=request.user)
        ).distinct()
 
        # Pagination
        paginator_created = LimitOffsetPagination()
        paginator_assigned = LimitOffsetPagination()
        paginator_all = LimitOffsetPagination()
 
        paginated_created = paginator_created.paginate_queryset(created_tickets, request, view=self)
        paginated_assigned = paginator_assigned.paginate_queryset(assigned_tickets, request, view=self)
        paginated_all = paginator_all.paginate_queryset(all_tickets_user, request, view=self)
 
        created_serializer = TicketSerializer(paginated_created, many=True)
        assigned_serializer = TicketSerializer(paginated_assigned, many=True)
        all_serializer = TicketSerializer(paginated_all, many=True)
 
        # Filter by query param
        if request.query_params.get('created') == 'True':
            return paginator_created.get_paginated_response({
                "all_tickets": created_serializer.data
            })
        elif request.query_params.get('assignee') == 'True':
            return paginator_assigned.get_paginated_response({
                "all_tickets": assigned_serializer.data
            })
        else:
            return paginator_all.get_paginated_response({
                "all_tickets": all_serializer.data
            })
 
 
 
 
            

class DashboardTicketAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        # User organization setup
        org = request.user.organisation
        self.permission_required = "view_sla"
        HasRolePermission.has_permission(self, request, self.permission_required)
        
        """get method to get all SLA timer objects"""
        all_tickets = Ticket.objects.filter(is_active=True, developer_organization=org)
        serializer = TicketSerializer(all_tickets, many=True)
        final_data = serializer.data
        
        # Process each ticket to calculate pause times
        for i in range(len(final_data)):
            ticket = final_data[i]['ticket_id']
            sla_timer = SLATimer.objects.filter(ticket=ticket).first()
            
            if not sla_timer:
                # Instead of returning error immediately, set a default value and continue
                final_data[i]['total_paused_time'] = "0:00:00"
                continue
                
            pause_times = [p for p in sla_timer.get_all_paused_times() if p]
            resume_times = [r for r in sla_timer.get_all_resumed_times() if r]
            
            total_paused_time = timedelta()
            used_resumes = set()
            
            for pause in pause_times:
                matching_resume = None
                for resume in resume_times:
                    if resume > pause and resume not in used_resumes:
                        matching_resume = resume
                        used_resumes.add(resume)
                        break
                        
                if matching_resume:
                    total_paused_time += (matching_resume - pause)
                else:
                    # Still paused (no resume yet)
                    current_time = datetime.utcnow().replace(tzinfo=pause.tzinfo)
                    total_paused_time += (current_time - pause)
                    
            final_data[i]['total_paused_time'] = str(total_paused_time)
        
        # Calculate totals and averages
        valid_tickets = 0
        total_solve_time = timedelta()
        total_paused_time = timedelta()
        
        for ticket in final_data:
            try:
                created = datetime.fromisoformat(ticket["created_at"])
                modified = datetime.fromisoformat(ticket["modified_at"])
                
                # Parse the paused time string safely
                paused_parts = ticket["total_paused_time"].split(":")
                if len(paused_parts) >= 3:
                    # Handle potential day information in timedelta string
                    if " " in paused_parts[0]:
                        days_str, hours_str = paused_parts[0].split(" ", 1)
                        days = int(days_str.replace("days,", "").replace("day,", ""))
                        hours = int(hours_str)
                    else:
                        days = 0
                        hours = int(paused_parts[0])
                    
                    minutes = int(paused_parts[1])
                    # Handle potential fractional seconds
                    seconds_str = paused_parts[2].split(".", 1)[0]
                    seconds = int(seconds_str)
                    
                    paused = timedelta(
                        days=days,
                        hours=hours,
                        minutes=minutes,
                        seconds=seconds
                    )
                    
                    solve_time = modified - created
                    resume_time = solve_time - paused
                    
                    total_solve_time += solve_time
                    total_paused_time += paused
                    valid_tickets += 1
            except (ValueError, IndexError, KeyError) as e:
                # Skip this ticket if there's an error parsing the time values
                print(f"Error processing ticket: {e}")
                continue
        
        # Prevent division by zero
        if valid_tickets > 0:
            avg_solve_time = total_solve_time / valid_tickets
            avg_paused_time = total_paused_time / valid_tickets
            avg_resume_time = avg_solve_time - avg_paused_time
        else:
            avg_solve_time = timedelta()
            avg_paused_time = timedelta()
            avg_resume_time = timedelta()
        
        return Response({
            "avg_solve_time": format_timedelta(avg_solve_time),
            "avg_paused_time": format_timedelta(avg_paused_time),
            "avg_resume_time": format_timedelta(avg_resume_time),
            "processed_tickets": valid_tickets,
            "total_tickets": len(final_data)
        }, status=status.HTTP_200_OK)
def format_timedelta(td):
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours}:{minutes}:{seconds}"




class dispatcherAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        self.permission_required = "update_assignment"
        HasRolePermission.has_permission(self, request, self.permission_required)
 
        print(f"Logged-in user: {request.user}")
        print(f"User ID: {request.user.id}")
        print(request.query_params.get)
 
        if UserRole.objects.filter(user=request.user).exists():
            all_tickets = Ticket.objects.filter(
                Q(assignee__isnull=True) | Q(assignee=request.user),
                is_active=True
            )
 
            print("Filtered tickets:", all_tickets)
 
            paginator = LimitOffsetPagination()
            paginated = paginator.paginate_queryset(all_tickets, request, view=self)
            serializer = TicketSerializer(paginated, many=True)
            return paginator.get_paginated_response({
                "all_tickets": serializer.data
            })
 
        return Response({"detail": "No tickets or invalid role."}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, *args, **kwargs):
        self.permission_required = "create_ticket"
        ticket_id = request.data.get("ticket_id")

        if not ticket_id:
            return Response({"error": "Ticket ID is required for update."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ticket = Ticket.objects.get(ticket_id=ticket_id)
        except Ticket.DoesNotExist:
            return Response({"error": "Ticket not found."}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        incoming_assignee = data.get("assignee")
        print(f"➡️ Incoming Assignee ID from request: {incoming_assignee}")

        developer_email = None
        dispatcher_email = None

        if incoming_assignee:
            try:
                assignee_user = User.objects.get(id=incoming_assignee)
                print(f"🧾 Assignee Found: {assignee_user.username} (ID: {assignee_user.id})")
                developer_email = assignee_user.email
            except User.DoesNotExist:
                return Response({"error": "Invalid assignee."}, status=400)
        elif not ticket.assignee:
            dispatcher = UserRole.objects.filter(role__name="Dispatcher", is_active=True).first()
            if dispatcher:
                data["assignee"] = dispatcher.user.id
                dispatcher_email = dispatcher.user.email
                developer_email = dispatcher.user.email
                send_auto_assignment_email_to_dispatcher.delay(ticket.ticket_id, dispatcher_email)
                print(f"🛠️ Auto-assigned to dispatcher: {dispatcher.user.username} (ID: {dispatcher.user.id})")
            else:
                return Response({"error": "No active dispatcher available for automatic assignment."}, status=400)

        serializer = TicketSerializer(ticket, data=data, partial=True)

        if serializer.is_valid():
            try:
                updated_ticket = serializer.save(modified_by=request.user)
            except ValueError as e:
                # Handle working hours restriction errors
                return Response({
                    "error": str(e),
                    "error_type": "working_hours_restriction"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Send emails after saving
            if not developer_email:
                developer = updated_ticket.assignee
                if developer:
                    developer_email = developer.email
            if not dispatcher_email:
                dispatcher_user = UserRole.objects.filter(role__name="Dispatcher", is_active=True).first()
                if dispatcher_user:
                    dispatcher_email = dispatcher_user.user.email

            # Trigger async email task
            send_dispatch_assignment_emails.delay(
                ticket_id=updated_ticket.ticket_id,
                developer_email=developer_email,
                dispatcher_email=dispatcher_email
            )

            return Response({
                "message": "Ticket updated successfully",
                "ticket_id": updated_ticket.ticket_id
            }, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
 
            
class TotalTicketsAPIViewCount(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        total_tickets = Ticket.objects.count()

        open_tickets = Ticket.objects.filter(status='open').count()
        inprogress_tickets = Ticket.objects.filter(status='Working in Progress').count()
        resolved_tickets = Ticket.objects.filter(status='Resolved').count()
        critical_tickets = Ticket.objects.filter(impact='A').count()
        medium_impact_tickets = Ticket.objects.filter(impact='B').count()
        low_impact_tickets = Ticket.objects.filter(impact='C').count()
        

        ticket_counts = {
            "total_tickets": total_tickets,
            "open": open_tickets,
            "inprogress": inprogress_tickets,
            "resolved": resolved_tickets,
            "critical": critical_tickets,
            "medium": medium_impact_tickets,
            "low": low_impact_tickets,
            
        }

        return Response(ticket_counts, status=status.HTTP_200_OK)
    
class AllTicketsAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get all tickets in the system
        tickets = Ticket.objects.all()
        
        # Initialize pagination (you can adjust this as needed)
        paginator = LimitOffsetPagination()
        paginated_tickets = paginator.paginate_queryset(tickets, request, view=self)
        
        # Serialize the tickets
        serializer =TicketSerializer(paginated_tickets, many=True)
        
        # Return the paginated response
        return paginator.get_paginated_response(serializer.data)
    
class TicketByStatusAPIView(APIView):
    def get(self, request):
        status_param = request.query_params.get('status')
        if not status_param:
            return Response({'error': 'Status is required as a query param'}, status=status.HTTP_400_BAD_REQUEST)
        
        tickets = Ticket.objects.filter(status=status_param)
        serializer = TicketSerializer(tickets, many=True)
        return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)


"Assigning ticket to developer"
class AssignTicketAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def put(self, request, ticket_id):
        self.permission_required = "update_ticket"  
        if not HasRolePermission().has_permission(request, self.permission_required):
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            ticket = get_object_or_404(Ticket, ticket_id=ticket_id)
            engineer_id = request.data.get("assignee")
            if not engineer_id:
                return Response(
                    {"error": "assignee field is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Validate if the engineer (user) exists
            engineer = User.objects.filter(id=engineer_id).first() 
            if not engineer:
                return Response(
                    {"error": "The specified engineer does not exist."},
                    status=status.HTTP_404_NOT_FOUND,
                )
 
            # Proceed with the ticket assignment
            serializer = AssignTicketSerializer(ticket, data=request.data, partial=True)
            if serializer.is_valid():
                try:
                    serializer.save()
                except ValueError as e:
                    # Handle working hours restriction errors
                    return Response({
                        "error": str(e),
                        "error_type": "working_hours_restriction"
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Send email via Celery
                if engineer.email:
                   
                    send_assignment_email(
                            ticket.ticket_id,
                            engineer_username=engineer.username,
                            engineer_email=engineer.email,
                            ticket_summary=ticket.summary,
                            ticket_description=ticket.description
                            # ticket_creator_email=ticket.created_by.email if ticket.created_by and ticket.created_by.email else ""
                        )
                data ={"title":f"Assigneed ticket to {engineer.username}", "ticket":ticket,"created_by":request.user}
                serializer_history = TicketHistorySerializer(data=data)
                if serializer_history.is_valid():
                    serializer_history.save(modified_by=request.user)
                return Response(
                    {
                        "message": "Ticket assigned successfully.",
                        "engineer_username": engineer.username,
                    },
                    status=status.HTTP_200_OK,
                )

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except APIException as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # def put(self, request, ticket_id):
    #     self.permission_required = "update_ticket"
    #     if not HasRolePermission().has_permission(request, self.permission_required):
    #         return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    #     ticket = get_object_or_404(Ticket, ticket_id=ticket_id)
    #     engineer_id = request.data.get("assignee")
    #     if not engineer_id:
    #         return Response({"error": "assignee field is required."}, status=status.HTTP_400_BAD_REQUEST)

    #     engineer = User.objects.filter(id=engineer_id).first()
    #     if not engineer:
    #         return Response({"error": "The specified engineer does not exist."}, status=status.HTTP_404_NOT_FOUND)

    #     serializer = AssignTicketSerializer(ticket, data=request.data, partial=True)
    #     if serializer.is_valid():
    #         serializer.save()

    #         # Send email to assignee, requester, and Admin(s)
    #         send_assignment_email.delay(ticket.ticket_id)

    #         # Save history
    #         data = {"title": f"Assigned ticket to {engineer.username}", "ticket": ticket, "created_by": request.user}
    #         serializer_history = TicketHistorySerializer(data=data)
    #         if serializer_history.is_valid():
    #             serializer_history.save(modified_by=request.user)

    #         return Response({"message": "Ticket assigned successfully.", "engineer_username": engineer.username}, status=status.HTTP_200_OK)

    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TicketDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    """Handles GET, PUT, DELETE for a single ticket"""
    def get(self, request, ticket_id):
        """GET method to retrieve a ticket object by string ID"""
        ticket = self.get_object(ticket_id)
        if not ticket:
            return Response({"error": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = TicketSerializer(ticket)
        return Response(serializer.data)

    def get_object(self, ticket_id):
        try:
            return Ticket.objects.get(ticket_id=ticket_id)
        except Ticket.DoesNotExist:
            return None

    def put(self, request, ticket_id):
        ticket = self.get_object(ticket_id)
        if not ticket:
            return Response({"error": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)
        if ticket.status == "breached" and "status" in request.data:
            return Response({"error": "Cannot change status of a breached ticket."}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data.copy()

        # Handle assignee logic (similar to POST method)
        if 'assignee' in data:
            assignee_input = str(data.get('assignee', '')).strip().lower()
            dispatcher_user = None
            
            # Check for auto-assignment or empty assignee
            if not assignee_input or assignee_input == 'auto':
                dispatcher_role = UserRole.objects.filter(role__name="Dispatcher", is_active=True).select_related('user').first()
                if dispatcher_role and dispatcher_role.user:
                    data['assignee'] = dispatcher_role.user.id
                    dispatcher_user = dispatcher_role.user
                    print(f"DEBUG: Auto-assigned to dispatcher: {dispatcher_user.username} (ID: {dispatcher_user.id})")
                else:
                    return Response({"error": "No active dispatcher available for auto-assignment."}, status=status.HTTP_400_BAD_REQUEST)
            else:
                # Validate assignee ID
                try:
                    assignee_id = int(data['assignee'])
                    data['assignee'] = assignee_id
                    
                    # Additional debug info
                    print(f"DEBUG: Looking for User with pk={assignee_id}")
                    # Check if the user exists with more detailed logging
                    user_exists = User.objects.filter(pk=assignee_id).exists()
                    print(f"DEBUG: User exists: {user_exists}")
                    
                    # Try to get the actual user object for more info
                    try:
                        user = User.objects.get(pk=assignee_id)
                        print(f"DEBUG: Found user: {user.username} (ID: {user.id})")
                    except User.DoesNotExist:
                        print(f"DEBUG: User with ID {assignee_id} does not exist")
                        # Let's see what users actually exist
                        all_users = User.objects.all().values_list('id', 'username')
                        print(f"DEBUG: Available users: {list(all_users)}")
                        return Response({"assignee": ["Invalid pk - user does not exist."]}, status=status.HTTP_400_BAD_REQUEST)
                    except Exception as e:
                        print(f"DEBUG: Error fetching user: {e}")
                        return Response({"assignee": ["Error validating user."]}, status=status.HTTP_400_BAD_REQUEST)
                        
                except ValueError:
                    return Response({"error": "Assignee must be a valid user ID or 'auto'."}, status=status.HTTP_400_BAD_REQUEST)

        # Convert developer_organization ID to name
        if 'developer_organization' in data:
            org_id = data['developer_organization']
            # Skip processing if empty string
            if org_id == "":
                print("DEBUG: Empty developer_organization, skipping conversion")
            else:
                try:
                    org_id = int(org_id)
                    org = Organisation.objects.get(pk=org_id)
                    data['developer_organization'] = org.organisation_name  # Use the name, not ID
                    print(f"DEBUG: Converted org ID {org_id} to name: {org.organisation_name}")
                except (Organisation.DoesNotExist, ValueError, TypeError):
                    return Response({
                        "developer_organization": [f"Organisation with ID {org_id} does not exist."]
                    }, status=status.HTTP_400_BAD_REQUEST)

        # Convert solution_grp ID to name  
        if 'solution_grp' in data:
            grp_id = data['solution_grp']
            # Skip processing if empty string
            if grp_id == "":
                print("DEBUG: Empty solution_grp, skipping conversion")
            else:
                try:
                    grp_id = int(grp_id)
                    grp = SolutionGroup.objects.get(pk=grp_id)
                    data['solution_grp'] = grp.group_name  # Use the name, not ID
                    print(f"DEBUG: Converted group ID {grp_id} to name: {grp.group_name}")
                except (SolutionGroup.DoesNotExist, ValueError, TypeError):
                    return Response({
                        "solution_grp": [f"Solution Group with ID {grp_id} does not exist."]
                    }, status=status.HTTP_400_BAD_REQUEST)

        print(f"DEBUG: Data after conversion: {data}")
        
        # Store original assignee for comparison
        original_assignee = ticket.assignee
        
        # FIXED: Pass request context to serializer
        serializer = TicketSerializer(ticket, data=data, partial=True, context={'request': request})
        if serializer.is_valid():
            try:
                updated_ticket = serializer.save(modified_by=request.user)
            except ValueError as e:
                # Handle working hours restriction errors
                error_message = str(e)
                return Response({
                    "error": error_message,
                    "error_type": "working_hours_restriction",
                    "current_status": ticket.status
                }, status=status.HTTP_400_BAD_REQUEST)

            # Handle assignee change notifications
            if 'assignee' in data and updated_ticket.assignee != original_assignee:
                # Send notification to new assignee
                if updated_ticket.assignee and updated_ticket.assignee.email:
                    from .tasks import send_ticket_reassignment_email
                    send_ticket_reassignment_email.delay(
                        str(updated_ticket.ticket_id),
                        str(updated_ticket.assignee.email),
                        str(request.user.username)  # Who made the reassignment
                    )
                
                # If it was auto-assigned to dispatcher, send dispatcher notification
                if dispatcher_user:
                    from .tasks import send_auto_assignment_email_to_dispatcher
                    send_auto_assignment_email_to_dispatcher.delay(
                        str(updated_ticket.ticket_id), 
                        str(dispatcher_user.email)
                    )
                
                # Add history entry for assignee change
                if original_assignee != updated_ticket.assignee:
                    assignee_change_msg = f"{request.user.username} reassigned ticket"
                    if original_assignee:
                        assignee_change_msg += f" from {original_assignee.username}"
                    if updated_ticket.assignee:
                        assignee_change_msg += f" to {updated_ticket.assignee.username}"
                    else:
                        assignee_change_msg += " (unassigned)"
                    
                    history_data = {
                        "title": assignee_change_msg,
                        "ticket": ticket_id,
                        "created_by": request.user.id
                    }
                    serializer_history = TicketHistorySerializer(data=history_data)
                    if serializer_history.is_valid():
                        serializer_history.save(modified_by=request.user)

            # Handle status change (existing logic)
            if 'status' in data:
                if ticket.created_by and ticket.created_by.email:
                    send_status_change_email_async.delay(ticket.ticket_id, ticket.status, ticket.created_by.email)
                if ticket.assignee and ticket.assignee.email:
                    send_status_change_email_async.delay(ticket.ticket_id, ticket.status, ticket.assignee.email)

                history_data = {
                    "title": f"{request.user.username} changed status to {data['status']}.",
                    "ticket": ticket_id,
                    "created_by": request.user.id
                }
                serializer_history = TicketHistorySerializer(data=history_data)
                if serializer_history.is_valid():
                    serializer_history.save(modified_by=request.user)

            return Response(serializer.data)

        print(f"DEBUG: Serializer errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
        
    def delete(self, request, ticket_id):
        """delete method to delete the ticket object"""
        ticket = self.get_object(ticket_id)
        if not ticket:
            return Response({"error": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)
        ticket.delete()
        return Response({"message": "Ticket deleted successfully"}, status=status.HTTP_204_NO_CONTENT) 
    
"API for dropdown "
class TicketChoicesAPIView(APIView):
    permission_classes = [IsAuthenticated] 
    authentication_classes = [JWTAuthentication]
    def get(self, request):
        priority_choices = Priority.objects.values("priority_id", "urgency_name")
        choices = {
            "status_choices": Ticket.STATUS_CHOICES,
            # "issue_type_choices": Ticket.ISSUE_TYPE,
            "support_team_choices": Ticket.SUPPORT,
            # "contact_mode_choices": Ticket._meta.get_field("contact_mode").choices
            "impact_choices":Ticket.IMPACT, #change 1
             "priority_choices":list(priority_choices),
        
        }
        return Response(choices)
    


class CloseTicketAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @transaction.atomic
    def post(self, request, ticket_id):
        self.permission_required = "close_ticket"
        if not HasRolePermission().has_permission(request, self.permission_required):
          return Response({'error': 'Permission denied.'}, status=403)
        # self.required_permission = "delete_ticket"  
        # self.check_permissions(request) 
        ticket = get_object_or_404(Ticket, ticket_id=ticket_id)
        
        if ticket.customer != request.user:
            return Response({"message": "You are not authorized to close this ticket."}, status=status.HTTP_403_FORBIDDEN)

        ticket.is_resolved = True
        ticket.status = 'Resolved'
        ticket.save()

        # Stop SLA timer when the ticket is closed
        ticket.sla_timer.stop_sla()
        data ={"title":f"{request.user.username} closed ticket", "ticket":ticket,"created_by":request.user}
        serializer_history = TicketHistorySerializer(data=data)
        if serializer_history.is_valid():
            serializer_history.save(modified_by=request.user)

        return Response({"message": "Ticket has been closed."}, status=status.HTTP_200_OK)
    

class SLATimerAPIView(APIView):
    permission_classes = [IsAuthenticated] 
    authentication_classes = [JWTAuthentication]
    """Handles GET and POST for SLA timers"""
    def get(self,request):
        self.permission_required = "view_sla"  
        HasRolePermission.has_permission(self,request,self.permission_required)
        """get method to get all SLA timer objects"""
        sla_timers = SLATimer.objects.all()
        serializer = SLATimerSerializer(sla_timers, many=True)
        final_data=serializer.data
        
        for i  in range(len(serializer.data)):
            ticket = serializer.data[i]['ticket']
            sla_timer = SLATimer.objects.filter(ticket=ticket).first()  
            if not sla_timer:
                return Response({"error": "SLA Timer not found"}, status=status.HTTP_404_NOT_FOUND)

            pause_times = sla_timer.get_all_paused_times()
            resume_times = sla_timer.get_all_resumed_times()

            pause_times = [p for p in sla_timer.get_all_paused_times() if p]
            resume_times = [r for r in sla_timer.get_all_resumed_times() if r]

            total_paused_time = timedelta()
            used_resumes = set()

            for pause in pause_times:
                matching_resume = None
                for resume in resume_times:
                    if resume > pause and resume not in used_resumes:
                        matching_resume = resume
                        used_resumes.add(resume)
                        break
                
                if matching_resume:
                    total_paused_time += (matching_resume - pause)
                else:
                    # Still paused (no resume yet)
                    current_time = datetime.utcnow().replace(tzinfo=pause.tzinfo)
                    total_paused_time += (current_time - pause)
            final_data[i]['total_paused_time']=str(total_paused_time)
            
            
        
        
        return Response(serializer.data)
    def post(self, request):
        """post method to create a new SLA timer object"""
        serializer = SLATimerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class SLATimerDetailAPIView(APIView):
   
    # def get(self, request, *args, **kwargs):
    #     ticket_id = kwargs.get("ticket_id")  # ✅ Ensure we get ticket_id
    #     if not ticket_id:
    #         return Response({"error": "ticket_id is required"}, status=400)

    #     try:
    #         sla_timer = SLATimer.objects.get(ticket_id=ticket_id)  # ✅ Correct field name
    #         # return Response({"sla_due_date": sla_timer.sla_due_date})
    #         final_data = SLATimerSerializer(sla_timer).data
        

     
    #         sla_timer = SLATimer.objects.filter(ticket=ticket_id).first()  
    #         if not sla_timer:
    #             return Response({"error": "SLA Timer not found"}, status=status.HTTP_404_NOT_FOUND)

    #         pause_times = sla_timer.get_all_paused_times()
    #         resume_times = sla_timer.get_all_resumed_times()

    #         pause_times = [p for p in sla_timer.get_all_paused_times() if p]
    #         resume_times = [r for r in sla_timer.get_all_resumed_times() if r]

    #         total_paused_time = timedelta()
    #         used_resumes = set()

    #         for pause in pause_times:
    #             matching_resume = None
    #             for resume in resume_times:
    #                 if resume > pause and resume not in used_resumes:
    #                     matching_resume = resume
    #                     used_resumes.add(resume)
    #                     break
                
    #             if matching_resume:
    #                 total_paused_time += (matching_resume - pause)
    #             else:
    #                 # Still paused (no resume yet)
    #                 current_time = datetime.utcnow().replace(tzinfo=pause.tzinfo)
    #                 total_paused_time += (current_time - pause)
    #         final_data['total_paused_time']=str(total_paused_time)
            
    #         return Response(final_data)
    #     except SLATimer.DoesNotExist:
    #         return Response({"error": "SLA Timer not found"}, status=404)

    def get(self, request, *args, **kwargs):
        ticket_id = kwargs.get("ticket_id")
        if not ticket_id:
            return Response({"error": "ticket_id is required"}, status=400)

        try:
            # 🎯 Fetch the SLA Timer for this ticket
            sla_timer = SLATimer.objects.get(ticket_id=ticket_id)
            
            # 🎯 Serialize existing SLA data
            serializer = SLATimerSerializer(sla_timer)
            data = serializer.data

            # 🕒 Add dynamically calculated remaining time
            data["remaining_time"] = str(sla_timer.get_remaining_time())

            # 🧮 (Optional) Add total paused time if you want
            data["total_paused_time"] = str(sla_timer.total_paused_time)

            return Response(data, status=200)

        except SLATimer.DoesNotExist:
            return Response({"error": "SLA Timer not found"}, status=404)



    def put(self, request, ticket_id):
        """put method to update the SLA timer object"""
        sla_timer = self.get_object(ticket_id)
        if not sla_timer:
            return Response({"error": "SLA Timer not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = SLATimerSerializer(sla_timer, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    def delete(self,request, ticket_id):
        """delete method to delete the SLA timer object"""
        sla_timer = self.get_object(ticket_id)
        if not sla_timer:
            return Response({"error": "SLA Timer not found"}, status=status.HTTP_404_NOT_FOUND)
        sla_timer.delete()
        data ={"title":f"{request.user.username} deleted ticket", "ticket":ticket_id,"created_by":request.user}
        serializer_history = TicketHistorySerializer(data=data)
        if serializer_history.is_valid():
            serializer_history.save(modified_by=request.user)
        return Response({"message": "SLA Timer deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    


from django.utils import timezone

    

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
class SLABreachStatusAPIView(APIView):
    # ✅ Force JWT authentication for this view only
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, ticket_id):
        # Debugging: check token and user
        print("Authorization header:", request.META.get("HTTP_AUTHORIZATION"))
        print("User:", request.user)

        try:
            # Get the SLA timer for this ticket
            sla_timer = SLATimer.objects.get(ticket__ticket_id=ticket_id)
            breached = sla_timer.check_sla_breach()

            if breached:
                ticket = sla_timer.ticket
                # Update ticket status if not already resolved/closed/breached
                if ticket.status not in ["resolved", "closed", "breached"]:
                    ticket.status = "breached"
                    ticket.breached_at = timezone.now()  # optional
                    ticket.save()

                # Save SLA breach history
                data = {
                    "title": "Ticket has breached SLA",
                    "ticket": ticket_id,
                    # ❌ Do NOT pass created_by here (read_only in serializer)
                }
                serializer_history = TicketHistorySerializer(data=data)
                if serializer_history.is_valid():
                    # Assign created_by / modified_by in save()
                    serializer_history.save(
                        created_by=request.user,
                        modified_by=request.user,
                    )
                else:
                    print("Serializer errors:", serializer_history.errors)

            return Response({
                "ticket_id": ticket_id,
                "sla_breached": sla_timer.breached,
                "sla_due_date": sla_timer.sla_due_date,
                "sla_status": sla_timer.sla_status
            })

        except SLATimer.DoesNotExist:
            return Response(
                {"error": "SLA Timer not found"},
                status=status.HTTP_404_NOT_FOUND
            )
class TicketCommentAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
 
    def get(self, request):
        ticket_id = request.query_params.get('ticket')
        if not ticket_id:
            return Response({"error": "Missing 'ticket' query parameter."}, status=status.HTTP_400_BAD_REQUEST)
 
        ticket = get_object_or_404(Ticket, id=ticket_id)
        comments = TicketComment.objects.filter(ticket=ticket).select_related('created_by').prefetch_related('attachments')
        serializer = TicketCommentListSerializer(comments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
 
    def post(self, request):
        serializer = TicketCommentCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response({"message": "Comment added successfully."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
 


from .serializers import WorkingHoursSerializer
from .models import WorkingHours
class WorkingHoursAPIView(APIView):
    permission_classes = [IsAuthenticated] 
    authentication_classes = [JWTAuthentication]
    """Handles GET and POST for Working Hours"""
    def get(self,request):
        # self.permission_required = "view_working_hours"  
        # HasRolePermission.has_permission(self,request,self.permission_required)
        # """get method to get all Working Hours objects"""
        working_hours = WorkingHours.objects.all()
        serializer = WorkingHoursSerializer(working_hours, many=True)
        return Response(serializer.data)
    def post(self, request):
        """post method to create a new Working Hours object"""
        serializer = WorkingHoursSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        """put method to update the Working Hours object"""
        working_hours = get_object_or_404(WorkingHours, pk=pk)
        serializer = WorkingHoursSerializer(working_hours, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self,request, pk):
        """delete method to delete the Working Hours object"""
        working_hours = get_object_or_404(WorkingHours, pk=pk)
        working_hours.delete()
        return Response({"message": "Working Hours deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    

from .serializers import HolidaySerializer
from .models import Holiday
class HolidayAPIView(APIView):
    permission_classes = [IsAuthenticated] 
    authentication_classes = [JWTAuthentication]
    """Handles GET and POST for Holidays"""
    def get(self,request):
        self.permission_required = "view_holidays"  
        HasRolePermission.has_permission(self,request,self.permission_required)
        """get method to get all Holiday objects"""
        holidays = Holiday.objects.all()
        serializer = HolidaySerializer(holidays, many=True)
        return Response(serializer.data)
    def post(self, request):
        """post method to create a new Holiday object"""
        serializer = HolidaySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        """put method to update the Holiday object"""
        holiday = get_object_or_404(Holiday, pk=pk)
        serializer = HolidaySerializer(holiday, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self,request, pk):
        """delete method to delete the Holiday object"""
        holiday = get_object_or_404(Holiday, pk=pk)
        holiday.delete()
        return Response({"message": "Holiday deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
