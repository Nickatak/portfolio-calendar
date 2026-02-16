from django.contrib.admin import AdminSite
from django.db.models import Count, Q
from django.shortcuts import redirect
from django.http import JsonResponse
from django.urls import path
from datetime import datetime, timedelta
from calendar_api.models import TimeSlot, Contact
import random


class CalendarAdminSite(AdminSite):
    """
    Custom admin site that extends Django's AdminSite to create a calendar-focused dashboard.
    
    EXTENSION DETAILS:
    - Extends: django.contrib.admin.AdminSite (Django's base admin site class)
    - Purpose: Replaces the default Django admin with a custom calendar dashboard
    - Location: Referenced in config/urls.py and registered as 'calendar_admin'
    - Template: templates/admin/index.html (custom dashboard template)
    
    This class provides:
    1. Custom URL routing for generate and delete operations
    2. A custom dashboard index with calendar visualization
    3. Statistics aggregation for timeslots and contacts
    4. Status filtering (active, pending, confirmed, processed, all timeslots)
    """
    
    site_header = "Calendar Administration"
    site_title = "Calendar Admin"
    index_title = "Dashboard"
    
    def get_urls(self):
        """
        Override Django's URL routing to add custom admin endpoints.
        
        WHAT IT DOES:
        - Extends the default admin URLs with custom view handlers
        - Allows API-style endpoints for dashboard operations
        
        CUSTOM ENDPOINTS ADDED:
        - /admin/generate-timeslots/  -> generate_timeslots_view()
        - /admin/delete-inactive-timeslots/  -> delete_inactive_timeslots_view()
        
        HOW TO REFERENCE:
        - In templates: {% url "calendar_admin:generate_timeslots" %}
        - In templates: {% url "calendar_admin:delete_inactive_timeslots" %}
        - In Python: reverse('calendar_admin:generate_timeslots')
        
        Returns:
            list: Combined list of parent URLs + custom URLs
        """
        urls = super().get_urls()
        custom_urls = [
            path('generate-timeslots/', self.generate_timeslots_view, name='generate_timeslots'),
            path('delete-inactive-timeslots/', self.delete_inactive_timeslots_view, name='delete_inactive_timeslots'),
        ]
        return custom_urls + urls
    
    def generate_timeslots_view(self, request):
        """
        AJAX endpoint that generates random timeslots for the next 30 days.
        
        WHAT IT DOES:
        - Creates ~20-30 random timeslots distributed across the next 30 weekdays
        - All generated timeslots are created as INACTIVE (is_active=False)
        - Creates a default contact if none exist
        - Returns JSON response with success/error status
        
        PERMISSIONS:
        - Requires staff user status (checked via request.user.is_staff)
        - Returns 403 Permission Denied if user is not staff
        
        HOW IT'S CALLED:
        - Via JavaScript fetch() from template: {% url "calendar_admin:generate_timeslots" %}
        - Called by "Generate" button on dashboard
        
        REQUEST:
        - HTTP Method: GET or POST
        - Parameters: None
        
        RESPONSE:
        - Success: {"success": true, "count": 25, "message": "Generated 25 timeslots"}
        - Error: {"success": false, "error": "error message"}
        
        Args:
            request: Django HTTP request object
            
        Returns:
            JsonResponse: JSON with success flag and count/error message
        """
        if not request.user.is_staff:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        try:
            generated_count = self._generate_random_timeslots(randomness=0.15)
            return JsonResponse({
                'success': True,
                'message': f'Generated {generated_count} timeslots',
                'count': generated_count
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    def delete_inactive_timeslots_view(self, request):
        """
        AJAX endpoint that deletes all inactive timeslots from the database.
        
        WHAT IT DOES:
        - Finds all timeslots where is_active=False
        - Deletes them permanently from the database
        - Returns count of deleted timeslots
        
        PERMISSIONS:
        - Requires staff user status (checked via request.user.is_staff)
        - Returns 403 Permission Denied if user is not staff
        
        HOW IT'S CALLED:
        - Via JavaScript fetch() from template: {% url "calendar_admin:delete_inactive_timeslots" %}
        - Called by "Delete Inactive" button on dashboard
        
        REQUEST:
        - HTTP Method: GET or POST
        - Parameters: None
        
        RESPONSE:
        - Success: {"success": true, "count": 25, "message": "Deleted 25 inactive timeslot(s)"}
        - Error: {"success": false, "error": "error message"}
        
        Args:
            request: Django HTTP request object
            
        Returns:
            JsonResponse: JSON with success flag and count/error message
        """
        if not request.user.is_staff:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        try:
            inactive_timeslots = TimeSlot.objects.filter(is_active=False)
            count = inactive_timeslots.count()
            inactive_timeslots.delete()
            return JsonResponse({
                'success': True,
                'message': f'Deleted {count} inactive timeslot(s)',
                'count': count
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    def _generate_random_timeslots(self, randomness=0.15):
        """
        Internal helper method that generates random timeslots across the next 30 days.
        
        WHAT IT DOES:
        1. Calculates today's date and loops through the next 30 days
        2. Skips weekends (Saturday and Sunday)
        3. For each remaining day, iterates through available hours (10 AM - 6 PM)
        4. Has a random probability (15% default) to create a timeslot for each hour
        5. If timeslot is created, randomly assigns it a contact
        6. All timeslots are created as INACTIVE (is_active=False)
        7. If no contacts exist, creates a "Default Contact" automatically
        
        VISIBILITY:
        - This is a PRIVATE/INTERNAL method (starts with underscore _)
        - Should NOT be called directly from templates or external code
        - Only called by generate_timeslots_view()
        
        PARAMETERS:
        - randomness (float): Probability of creating each timeslot (0.15 = 15%)
          - Default: 0.15 (15% chance for each available slot)
          - Typical result: ~25-30 timeslots per generation
        
        TIMESLOT DETAILS:
        - Times: Random :00 or :30 minute (30-minute slots)
        - Status: Always created as is_active=False (inactive)
        - Confirmation: Randomly confirmed or pending
        - Contact: Randomly assigned from existing contacts
        
        ALGORITHM:
        1. Get list of all existing contacts
        2. If no contacts exist, create default contact
        3. Loop 30 days starting from today
        4. Skip weekends
        5. Loop through hours 10-17 (10 AM - 5 PM)
        6. For each hour slot, randomly decide whether to create timeslot
        7. Return total count of created timeslots
        
        Args:
            randomness (float, optional): Probability of creating each timeslot. Defaults to 0.15.
            
        Returns:
            int: Total number of timeslots created
        """
        today = datetime.now().date()
        generated_count = 0
        
        # Get all contacts, or create a default one if none exist
        contacts = list(Contact.objects.all())
        if not contacts:
            # Create a default contact
            default_contact = Contact.objects.create(
                first_name='Default',
                last_name='Contact',
                email='default@example.com'
            )
            contacts = [default_contact]
        
        # Hours available for scheduling (10 AM to 6 PM)
        available_hours = list(range(10, 18))  # 10-17
        
        for day_offset in range(30):
            current_date = today + timedelta(days=day_offset)
            
            # Skip weekends if desired
            if current_date.weekday() >= 5:  # Saturday=5, Sunday=6
                continue
            
            # For each hour, potentially create a timeslot
            for hour in available_hours:
                # Random chance to create timeslot (15% by default)
                if random.random() < randomness:
                    # Random choice between :00 and :30
                    minute = random.choice([0, 30])
                    
                    slot_datetime = datetime.combine(
                        current_date,
                        datetime.min.time().replace(hour=hour, minute=minute)
                    )
                    
                    # Randomly select a contact
                    contact = random.choice(contacts)
                    
                    # Try to create the timeslot
                    try:
                        TimeSlot.objects.get_or_create(
                            time=slot_datetime,
                            contact=contact,
                            defaults={
                                'topic': '',
                                'is_confirmed': random.choice([True, False]),
                                'is_processed': False,
                                'is_active': False,
                            }
                        )
                        generated_count += 1
                    except Exception as e:
                        # Log the error but continue
                        print(f"Error creating timeslot: {e}")
                        continue
        
        return generated_count
    
    def _generate_calendar(self, status_filter=None):
        """
        Internal helper method that generates calendar data for dashboard display.
        
        WHAT IT DOES:
        - Creates a 30-day calendar view starting from today
        - Fetches timeslots for each day based on the status filter
        - Organizes data into day objects with timeslot information
        - Prepares data structure for rendering in the dashboard template
        
        VISIBILITY:
        - This is a PRIVATE/INTERNAL method (starts with underscore _)
        - Should NOT be called directly from templates or external code
        - Only called by index() method
        
        FILTERING:
        The status_filter parameter determines which timeslots appear:
        - 'all': Shows ALL timeslots regardless of status
        - 'active': Shows only timeslots where is_active=True (DEFAULT)
        - 'pending': Shows unconfirmed and unprocessed timeslots
        - 'confirmed': Shows confirmed but unprocessed timeslots
        - 'processed': Shows only processed timeslots
        - None: Defaults to 'active' filter
        
        DATA STRUCTURE:
        Returns a list of day dictionaries with this structure:
        {
            'date': datetime.date object,
            'day_name': 'Mon', 'Tue', etc.,
            'day_num': 1-31,
            'month': 'Jan', 'Feb', etc.,
            'is_today': True/False,
            'timeslots': [list of TimeSlot objects],
            'has_timeslots': True/False,
            'timeslot_count': integer count,
        }
        
        USAGE IN TEMPLATE:
        In templates/admin/index.html:
        {% for day in calendar_days %}
            {{ day.date }}  - displays the date
            {{ day.timeslot_count }}  - shows how many timeslots
            {% for timeslot in day.timeslots %}  - loop through timeslots
        {% endfor %}
        
        Args:
            status_filter (str, optional): Filter type ('all', 'active', 'pending', 
                                          'confirmed', 'processed'). Defaults to 'active'.
            
        Returns:
            list: List of 30 day dictionaries with timeslot information
        """
        today = datetime.now().date()
        days = []
        
        for i in range(30):
            current_date = today + timedelta(days=i)
            
            # Start with all timeslots for this date
            timeslots = TimeSlot.objects.filter(time__date=current_date)
            
            # Apply filter based on status_filter parameter
            if status_filter == 'all':
                # Show all timeslots
                pass
            elif status_filter == 'active':
                timeslots = timeslots.filter(is_active=True)
            elif status_filter == 'pending':
                timeslots = timeslots.filter(is_confirmed=False, is_processed=False)
            elif status_filter == 'confirmed':
                timeslots = timeslots.filter(is_confirmed=True, is_processed=False)
            elif status_filter == 'processed':
                timeslots = timeslots.filter(is_processed=True)
            else:
                # Default to active only
                timeslots = timeslots.filter(is_active=True)
            
            timeslots = timeslots.select_related('contact').order_by('time')
            
            timeslots_list = list(timeslots)
            
            days.append({
                'date': current_date,
                'day_name': current_date.strftime('%a'),
                'day_num': current_date.day,
                'month': current_date.strftime('%b'),
                'is_today': current_date == today,
                'timeslots': timeslots_list,
                'has_timeslots': len(timeslots_list) > 0,
                'timeslot_count': len(timeslots_list),
            })
        
        return days
    
    def index(self, request, extra_context=None):
        """
        Override Django's admin index page with a custom calendar dashboard.
        
        WHAT IT DOES:
        - Extends Django's default admin.index() method (called when visiting /admin/)
        - Computes timeslot and contact statistics
        - Generates calendar visualization
        - Applies status filtering based on URL parameter
        - Renders custom dashboard template with all the data
        
        EXTENSION DETAILS:
        - Extends: AdminSite.index() (parent class method from Django)
        - Called By: Django automatically when user visits /admin/
        - Template: templates/admin/index.html (custom dashboard template)
        
        URL FILTERING:
        The status_filter comes from the URL query parameter: ?status_filter=XXX
        - ?status_filter=active (DEFAULT) - shows only active timeslots
        - ?status_filter=all - shows all timeslots
        - ?status_filter=pending - shows unconfirmed timeslots
        - ?status_filter=confirmed - shows confirmed timeslots
        - ?status_filter=processed - shows processed timeslots
        
        DATA PROVIDED TO TEMPLATE:
        The index() method passes these variables to templates/admin/index.html:
        
        timeslot_stats (dict):
            - 'total': Total count based on filter
            - 'confirmed': Count of confirmed timeslots
            - 'pending': Count of unconfirmed timeslots
            - 'processed': Count of processed timeslots
        
        contact_stats (dict):
            - 'total': Total contacts in system
            - 'active': Contacts with at least one timeslot
        
        recent_timeslots (QuerySet):
            - Last 5 timeslots, sorted by time (most recent first)
        
        recent_contacts (QuerySet):
            - Last 5 contacts added, sorted by creation date
        
        calendar_days (list):
            - 30-day calendar data from _generate_calendar()
        
        status_filter (str):
            - Current filter value being applied
        
        FLOW:
        1. Get status_filter from URL query parameter
        2. Build base_query based on filter type
        3. Calculate statistics from filtered query
        4. Generate calendar data
        5. Add all data to extra_context
        6. Call parent index() method to render template
        
        Args:
            request: Django HTTP request object
            extra_context (dict, optional): Additional context to pass to template
            
        Returns:
            TemplateResponse: Rendered admin/index.html with dashboard data
        """
        extra_context = extra_context or {}
        
        # Get status filter from query parameter (default to 'active')
        status_filter = request.GET.get('status_filter', 'active')
        
        # Get timeslot statistics based on filter
        if status_filter == 'all':
            base_query = TimeSlot.objects.all()
        elif status_filter == 'active':
            base_query = TimeSlot.objects.filter(is_active=True)
        elif status_filter == 'pending':
            base_query = TimeSlot.objects.filter(is_confirmed=False, is_processed=False)
        elif status_filter == 'confirmed':
            base_query = TimeSlot.objects.filter(is_confirmed=True, is_processed=False)
        elif status_filter == 'processed':
            base_query = TimeSlot.objects.filter(is_processed=True)
        else:
            # Default to active
            base_query = TimeSlot.objects.filter(is_active=True)
            status_filter = 'active'
        
        total_timeslots = base_query.count()
        confirmed_timeslots = base_query.filter(is_confirmed=True).count()
        pending_timeslots = base_query.filter(is_confirmed=False).count()
        processed_timeslots = base_query.filter(is_processed=True).count()
        
        # Get contact statistics
        total_contacts = Contact.objects.count()
        active_contacts = Contact.objects.annotate(
            timeslot_count=Count('timeslots')
        ).filter(timeslot_count__gt=0).count()
        
        # Get recent timeslots based on filter
        recent_timeslots = base_query.select_related('contact').order_by('-time')[:5]
        
        # Get recent contacts
        recent_contacts = Contact.objects.order_by('-created_at')[:5]
        
        # Generate calendar data with filter
        calendar_days = self._generate_calendar(status_filter=status_filter)
        
        extra_context.update({
            'timeslot_stats': {
                'total': total_timeslots,
                'confirmed': confirmed_timeslots,
                'pending': pending_timeslots,
                'processed': processed_timeslots,
            },
            'contact_stats': {
                'total': total_contacts,
                'active': active_contacts,
            },
            'recent_timeslots': recent_timeslots,
            'recent_contacts': recent_contacts,
            'calendar_days': calendar_days,
            'status_filter': status_filter,
        })
        
        return super().index(request, extra_context)
    
    def app_index(self, request, app_label, extra_context=None):
        """
        Override app-specific index page redirect.
        
        WHAT IT DOES:
        - Django calls this when user visits /admin/calendar_api/
        - Instead of showing app-specific page, redirects to main dashboard
        - Ensures consistent user experience with single dashboard
        
        EXTENSION DETAILS:
        - Extends: AdminSite.app_index() (parent class method from Django)
        - Called By: Django automatically for app-specific admin pages
        
        WHY:
        - Prevents duplicate page navigation
        - All calendar functionality is on main dashboard
        - Cleaner UX with single entry point
        
        Args:
            request: Django HTTP request object
            app_label (str): App name ('calendar_api')
            extra_context (dict, optional): Additional context (unused here)
            
        Returns:
            HttpResponseRedirect: Redirect to calendar_admin:index
        """
        return redirect('calendar_admin:index')


# Create instance of custom admin site
# This instance is registered in config/urls.py and replaces the default Django admin
calendar_admin_site = CalendarAdminSite(name='calendar_admin')
