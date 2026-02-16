"""
CALENDAR API ADMIN CONFIGURATION
==================================

This module configures the custom admin interface for the calendar application.

ARCHITECTURE OVERVIEW:
======================

The admin interface has two layers:

1. CUSTOM ADMIN SITE (CalendarAdminSite)
   - File: sites.py
   - Purpose: Custom dashboard with calendar view and stats
   - Replaces: Default Django admin at /admin/
   - Features: Calendar visualization, timeslot generation, status filtering
   - Instance: calendar_admin_site

2. MODEL ADMIN CLASSES (TimeSlotAdmin, ContactAdmin, SettingsAdmin)
   - Files: timeslot.py, contact.py, settings.py
   - Purpose: Configure how individual models appear in admin interface
   - Registered: With calendar_admin_site (not default admin)
   - Features: List views, search, filters, custom methods

REGISTRATION FLOW:
==================

1. Import the custom admin site instance
   from .sites import calendar_admin_site

2. Import the model admin classes
   from .timeslot import TimeSlotAdmin
   from .contact import ContactAdmin
   from .settings import SettingsAdmin

3. Register models with the custom admin site
   calendar_admin_site.register(TimeSlot, TimeSlotAdmin)
   calendar_admin_site.register(Contact, ContactAdmin)
   calendar_admin_site.register(Settings, SettingsAdmin)

4. The custom admin site is wired in config/urls.py
   from calendar_api.admin.sites import calendar_admin_site
   urlpatterns = [
       path('admin/', calendar_admin_site.urls),  # Uses custom admin, not default Django
   ]

HOW TO ACCESS THE ADMIN:
========================

1. Development server must be running
   python manage.py runserver

2. Navigate to: http://localhost:8000/admin/

3. Login with staff/superuser account

4. You'll see the custom calendar dashboard (not default Django admin)

CUSTOM DASHBOARD FEATURES:
==========================

Dashboard Elements (at /admin/):
- Control Panel with filter dropdown and action buttons
- Timeslot statistics (total, confirmed, pending, processed)
- Contact statistics (total, active with timeslots)
- 30-day calendar view with timeslot visualization
- Recent timeslots and contacts lists

Control Buttons:
- Generate: Creates ~25 random timeslots (all inactive)
- Delete Inactive: Removes all inactive timeslots
- Add Timeslot: Coming soon
- Add Contact: Coming soon
- Export Data: Coming soon
- Settings: Coming soon

Status Filter Dropdown:
- Every Timeslot: Show all timeslots regardless of status
- Pending: Show unconfirmed timeslots
- Confirmed: Show confirmed but unprocessed timeslots
- Processed: Show processed timeslots
- Active Only: Show only active timeslots (DEFAULT)

EXTENDING THE ADMIN:
====================

To add new features to the admin interface:

1. ADD A NEW ENDPOINT:
   In sites.py, add to get_urls():
   path('my-action/', self.my_action_view, name='my_action'),

2. ADD A NEW VIEW:
   In sites.py, add the view method:
   def my_action_view(self, request):
       # Check permissions
       if not request.user.is_staff:
           return JsonResponse({'error': 'Permission denied'}, status=403)
       # Do something
       return JsonResponse({'success': True})

3. ADD A BUTTON TO DASHBOARD:
   In templates/admin/index.html, add JavaScript function:
   function myAction() {
       fetch('{% url "calendar_admin:my_action" %}')
       .then(response => response.json())
       .then(data => { if(data.success) location.reload(); })
   }
   
   Add button in HTML:
   <button onclick="myAction()">My Action</button>

4. PASS DATA TO TEMPLATE:
   In index() method of CalendarAdminSite, add to extra_context:
   extra_context['my_data'] = computed_data
   
   Use in template:
   {{ my_data }}

FILE STRUCTURE:
===============

calendar_api/admin/
├── __init__.py              (THIS FILE - imports and registration)
├── sites.py                 (CalendarAdminSite - custom dashboard)
├── timeslot.py             (TimeSlotAdmin - timeslot model config)
├── contact.py              (ContactAdmin - contact model config)
└── settings.py             (SettingsAdmin - user settings config)

IMPORTANT NOTES:
================

1. This custom admin REPLACES the default Django admin
   - Only calendar_admin_site is active
   - Default admin (/admin/) is not used

2. Staff users CAN edit all data in admin
   - No special permissions currently configured
   - Consider adding permission checks for sensitive operations

3. The calendar is read-only visualization
   - Timeslots can only be edited in the individual admin forms
   - Cannot drag/drop to create/move timeslots on dashboard

4. Bulk operations are available
   - In timeslot admin: "Delete all timeslots" action
   - In model lists: Standard Django bulk actions
"""

from django.contrib.auth.models import User, Group
from django.contrib import admin

# Import models that need admin interfaces
from ..models import TimeSlot, Contact, Settings

# Import admin configuration classes
from .sites import calendar_admin_site
from .timeslot import TimeSlotAdmin
from .contact import ContactAdmin
from .settings import SettingsAdmin

# Register models with custom admin site
# Syntax: calendar_admin_site.register(ModelClass, AdminConfigClass)
calendar_admin_site.register(TimeSlot, TimeSlotAdmin)
calendar_admin_site.register(Contact, ContactAdmin)
calendar_admin_site.register(Settings, SettingsAdmin)

# Unregister User and Group from default admin
# These were auto-registered by Django in the default admin
# We unregister them so they don't appear in the default admin location
# (Note: They're also not registered with calendar_admin_site,
#  so they won't appear in custom admin either)
admin.site.unregister(User)
admin.site.unregister(Group)
