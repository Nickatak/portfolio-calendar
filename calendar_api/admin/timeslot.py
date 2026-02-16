from django.contrib import admin
from ..models import TimeSlot


def delete_all_timeslots(modeladmin, request, queryset):
    """
    Admin action that deletes ALL timeslots from the database.
    
    WHAT IT DOES:
    - Deletes every TimeSlot object in the database (ignores the queryset selection)
    - Shows confirmation message in admin interface
    - Useful for bulk cleanup without using multiple selections
    
    WHEN TO USE:
    - In the admin list view, select ANY timeslot (selection doesn't matter)
    - Click the dropdown action menu
    - Select "Delete all timeslots"
    - Confirms deletion of entire database
    
    PARAMETERS:
    - modeladmin: Reference to the TimeSlotAdmin class instance
    - request: Django HTTP request object
    - queryset: Selected items (IGNORED - deletes everything)
    
    REGISTRATION:
    - Registered in TimeSlotAdmin.actions = [delete_all_timeslots]
    - Makes it available in admin interface dropdown
    """
    count, _ = TimeSlot.objects.all().delete()
    modeladmin.message_user(request, f"Successfully deleted {count} timeslot(s).")


delete_all_timeslots.short_description = "Delete all timeslots"


class TimeSlotAdmin(admin.ModelAdmin):
    """
    Admin interface configuration for TimeSlot model.
    
    EXTENSION DETAILS:
    - Extends: django.contrib.admin.ModelAdmin (Django's base model admin class)
    - Model: calendar_api.models.TimeSlot
    - Purpose: Customizes how timeslots appear and are edited in admin interface
    - Registration: Registered in calendar_api/admin/__init__.py with calendar_admin_site
    
    FEATURES CONFIGURED:
    
    1. LIST VIEW (displayed when browsing timeslots)
    2. FILTERING
    3. READ-ONLY FIELDS
    4. FIELDSETS (organize fields into sections)
    5. CUSTOM METHODS
    
    USAGE IN ADMIN:
    1. Navigate to /admin/calendar_api/timeslot/
    2. See list of all timeslots with columns defined in list_display
    3. Click a timeslot to edit it
    4. Fields are organized into sections as defined in fieldsets
    5. Fields in readonly_fields cannot be edited
    """
    
    # LIST VIEW CONFIGURATION
    # Columns shown in the list view of timeslots
    list_display = ('time', 'duration_minutes', 'get_end_time', 'contact', 'is_active', 'is_confirmed', 'is_processed')
    
    # FILTER SIDEBAR
    # Users can click these checkboxes to filter the list
    list_filter = ('is_active', 'is_confirmed', 'is_processed')
    
    # READ-ONLY FIELDS
    # These fields cannot be edited in the admin interface
    # They can only be viewed (useful for auto-generated fields like timestamps)
    readonly_fields = ('created_at', 'updated_at', 'get_end_time')
    
    # BULK ACTIONS
    # These actions appear in the dropdown menu when items are selected
    # User selects timeslots, then chooses action from dropdown
    actions = [delete_all_timeslots]
    
    # FIELDSETS ORGANIZATION
    # Groups fields into collapsible sections for better organization
    # Each fieldset is a tuple: (section_name, {'fields': (), 'classes': ()})
    fieldsets = (
        ('Availability', {
            # Core timeslot information
            'fields': ('time', 'duration_minutes', 'get_end_time', 'contact', 'topic', 'is_active', 'is_confirmed', 'is_processed')
        }),
        ('Metadata', {
            # Auto-generated timestamps - collapsed by default for cleaner interface
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)  # 'collapse' makes this section closeable
        }),
    )

    def get_end_time(self, obj):
        """
        CUSTOM DISPLAY METHOD
        
        WHAT IT DOES:
        - Calculates and displays the END time of the timeslot
        - TimeSlot model stores start time and duration, so end is computed dynamically
        - Shown in list view and edit form
        
        HOW IT WORKS:
        1. Called by Django admin for each TimeSlot object
        2. obj parameter is the TimeSlot instance
        3. Calls obj._get_end_time() (defined in TimeSlot model)
        4. Returns the end datetime to display
        
        VISIBILITY:
        - Appears in list_display: ('time', 'get_end_time', ...)
        - Appears in fieldsets: ('Availability', {'fields': ('time', 'get_end_time', ...)})
        - Read-only (cannot edit)
        
        EXAMPLE:
        If timeslot.time = "2026-01-29 10:00:00" and duration_minutes=60
        get_end_time returns "2026-01-29 11:00:00"
        
        Args:
            obj: TimeSlot instance being displayed
            
        Returns:
            datetime: End time (start time + 30 minutes)
        """
        end_dt = obj._get_end_time()
        return end_dt
    
    # Add short description for admin interface column header
    get_end_time.short_description = 'End Time'
