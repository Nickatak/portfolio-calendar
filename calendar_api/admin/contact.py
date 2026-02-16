from django.contrib import admin
from ..models import Contact


class ContactAdmin(admin.ModelAdmin):
    """
    Admin interface configuration for Contact model.
    
    EXTENSION DETAILS:
    - Extends: django.contrib.admin.ModelAdmin (Django's base model admin class)
    - Model: calendar_api.models.Contact
    - Purpose: Customizes how contacts appear and are edited in admin interface
    - Registration: Registered in calendar_api/admin/__init__.py with calendar_admin_site
    
    FEATURES CONFIGURED:
    
    1. LIST VIEW (displayed when browsing contacts)
    2. SEARCH (find contacts by multiple fields)
    3. READ-ONLY FIELDS (auto-generated timestamps)
    4. FIELDSETS (organize fields into sections)
    5. CUSTOM METHODS (computed properties for display)
    
    USAGE IN ADMIN:
    1. Navigate to /admin/calendar_api/contact/
    2. See list of contacts with name, email, phone, timezone
    3. Use search bar to find contacts by name or email
    4. Click a contact to edit details
    5. Auto-generated dates are read-only
    """
    
    # LIST VIEW CONFIGURATION
    # Columns shown in the list view of contacts
    # These can be field names, model properties, or custom methods
    list_display = ('full_name', 'email', 'phone_number', 'timezone')
    
    # SEARCH FUNCTIONALITY
    # Clicking search box lets users search across these fields
    # Searches any of these fields for partial matches
    # Useful with many contacts in the database
    search_fields = ('first_name', 'last_name', 'email', 'phone_number')
    
    # READ-ONLY FIELDS
    # These fields cannot be edited in the admin interface
    # Prevents accidental modification of auto-generated timestamps
    readonly_fields = ('created_at', 'updated_at')
    
    # FIELDSETS ORGANIZATION
    # Groups fields into sections for better organization and clarity
    # Each fieldset is a tuple: (section_name, {'fields': (), 'classes': ()})
    fieldsets = (
        ('Contact Information', {
            # User-editable contact details
            'fields': ('first_name', 'last_name', 'email', 'phone_number', 'timezone')
        }),
        ('Metadata', {
            # Auto-generated timestamps - collapsed by default
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)  # 'collapse' makes this section closeable
        }),
    )

    def full_name(self, obj):
        """
        CUSTOM DISPLAY METHOD
        
        WHAT IT DOES:
        - Displays the full name of a contact (first + last name)
        - Used in the list_display to show a combined name field
        - Contact model has full_name property that we're displaying here
        
        HOW IT WORKS:
        1. Called by Django admin for each Contact object
        2. obj parameter is the Contact instance
        3. Returns obj.full_name which is computed from first_name + last_name
        4. Displayed in the admin list view
        
        WHY NEEDED:
        - list_display can't directly reference model properties
        - Must use a method to access the property
        - Allows controlling how the property is displayed
        
        EXAMPLE:
        Contact with first_name="John" and last_name="Doe"
        full_name method returns "John Doe"
        
        Args:
            obj: Contact instance being displayed
            
        Returns:
            str: Full name (e.g., "John Doe")
        """
        return obj.full_name
    
    # Add short description for admin interface column header
    full_name.short_description = 'Full Name'
