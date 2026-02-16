# Calendar Admin Documentation

## Quick Reference Guide

This document serves as a quick reference for understanding the custom admin interface. For detailed documentation, see inline comments in the admin files.

---

## File Structure

```
calendar_api/admin/
├── __init__.py              # Main entry point - imports and registers everything
├── sites.py                 # CalendarAdminSite class (dashboard with calendar view)
├── timeslot.py              # TimeSlotAdmin class (timeslot model interface)
├── contact.py               # ContactAdmin class (contact model interface)
└── settings.py              # SettingsAdmin class (user settings interface)
```

---

## Key Classes and What They Do

### 1. CalendarAdminSite (in sites.py)

**Extends:** `django.contrib.admin.AdminSite`

**Purpose:** Creates a custom admin dashboard that replaces Django's default admin

**Key Methods:**
| Method | Purpose | How to Reference |
|--------|---------|-----------------|
| `get_urls()` | Adds custom API endpoints | Used internally by Django |
| `generate_timeslots_view()` | AJAX endpoint to generate random timeslots | `{% url "calendar_admin:generate_timeslots" %}` |
| `delete_inactive_timeslots_view()` | AJAX endpoint to delete inactive timeslots | `{% url "calendar_admin:delete_inactive_timeslots" %}` |
| `_generate_random_timeslots()` | Creates ~25-30 random timeslots (PRIVATE) | Called by `generate_timeslots_view()` |
| `_generate_calendar()` | Builds 30-day calendar data (PRIVATE) | Called by `index()` method |
| `index()` | Main dashboard page override | Called automatically by Django at `/admin/` |
| `app_index()` | Redirects app-specific page to main dashboard | Called by Django internally |

**Instance:** `calendar_admin_site` - registered in config/urls.py at `/admin/`

---

### 2. TimeSlotAdmin (in timeslot.py)

**Extends:** `django.contrib.admin.ModelAdmin`

**Purpose:** Configures how TimeSlot model appears in admin interface

**Key Attributes:**
- `list_display`: Columns shown in list view
- `list_filter`: Filter options in sidebar
- `readonly_fields`: Fields that cannot be edited
- `actions`: Bulk actions available
- `fieldsets`: Organize fields into sections

**Custom Methods:**
- `get_end_time()`: Displays calculated end time of timeslot (start + 30 min)

---

### 3. ContactAdmin (in contact.py)

**Extends:** `django.contrib.admin.ModelAdmin`

**Purpose:** Configures how Contact model appears in admin interface

**Key Attributes:**
- `list_display`: Show full_name, email, phone, timezone
- `search_fields`: Search by first_name, last_name, email, phone
- `readonly_fields`: created_at, updated_at cannot be edited
- `fieldsets`: Organize contact info into sections

**Custom Methods:**
- `full_name()`: Displays combined first + last name

---

### 4. SettingsAdmin (in settings.py)

**Extends:** `django.contrib.admin.ModelAdmin`

**Purpose:** Configures how Settings model appears in admin interface

**Registration:** Uses `@admin.register(Settings)` decorator (auto-registers with default admin)

**Key Attributes:**
- `list_display`: Show user, timezone, dark_mode, email_daily_summary, updated_at
- `search_fields`: Search by user's username, email, first/last name
- `fieldsets`: Organize settings into 6 categories

**Fieldset Categories:**
1. User - which user these settings belong to
2. Timezone Settings - user's timezone preference
3. Notification Preferences - email notification choices
4. Display Preferences - UI/UX settings (dark mode, items per page)
5. Calendar Preferences - calendar-specific view options
6. Metadata - auto-generated timestamps (collapsed)

---

## How the Admin Works

### Access Point
- URL: `http://localhost:8000/admin/`
- Requires: Staff user login
- Displays: Custom calendar dashboard (not default Django admin)

### Dashboard Features

**Control Panel:**
- Status Filter dropdown - filter timeslots by status
- Generate button - creates ~25 random inactive timeslots
- Delete Inactive button - removes all inactive timeslots
- Additional buttons for future features

**Statistics Cards:**
- Total timeslots (based on filter)
- Confirmed timeslots count
- Pending timeslots count
- Processed timeslots count
- Total contacts
- Active contacts (with at least one timeslot)

**Calendar View:**
- 30-day calendar grid
- Shows timeslots for each day
- Color-coded by status (pending/confirmed/processed)
- Click timeslot to edit details

**Recent Items:**
- Last 5 timeslots
- Last 5 contacts
- Click to view/edit details

---

## Status Filter Options

Filter by selecting in dropdown and page refreshes with new data:

| Option | Shows | is_active | is_confirmed | is_processed |
|--------|-------|-----------|--------------|--------------|
| Active Only (DEFAULT) | Active timeslots only | True | any | any |
| Every Timeslot | All timeslots | any | any | any |
| Pending | Unconfirmed timeslots | any | False | False |
| Confirmed | Confirmed but not processed | any | True | False |
| Processed | Processed timeslots | any | any | True |

**URL Parameter:** `?status_filter=active` (or all, pending, confirmed, processed)

---

## How Functions Are Called

### From Template (templates/admin/index.html)
```html
<!-- Generate button calls JavaScript function -->
<button onclick="generateTimeslots()">Generate</button>

<!-- Delete button calls JavaScript function -->
<button onclick="deleteInactiveTimeslots()">Delete Inactive</button>

<!-- Status filter dropdown -->
<select onchange="filterCalendar()">

<!-- URL references in templates -->
{% url "calendar_admin:generate_timeslots" %}
{% url "calendar_admin:delete_inactive_timeslots" %}
```

### From JavaScript (in template)
```javascript
// Fetch custom endpoint and reload page
fetch('{% url "calendar_admin:generate_timeslots" %}')
    .then(response => response.json())
    .then(data => { 
        if(data.success) location.reload(); 
    });
```

### From Django Code
```python
# Manually call generation
from calendar_api.admin.sites import calendar_admin_site
count = calendar_admin_site._generate_random_timeslots(randomness=0.15)
```

---

## Data Flow Example: Generating Timeslots

1. **User clicks "Generate" button** → Browser
2. **JavaScript calls fetch()** → JavaScript
3. **Browser makes HTTP GET request** to `/admin/generate-timeslots/`
4. **Django routes to** → `CalendarAdminSite.generate_timeslots_view()`
5. **View checks permissions** → `request.user.is_staff`
6. **View calls** → `self._generate_random_timeslots(randomness=0.15)`
7. **Method generates timeslots** → Database insert
8. **Returns JSON response** → `{"success": true, "count": 25}`
9. **JavaScript receives response** → Reloads page
10. **index() method called** → Recalculates statistics with new timeslots
11. **Dashboard updates** → Shows new calendar with timeslots

---

## Extending the Admin

### Add a New Button/Action

1. **Add view method to CalendarAdminSite:**
   ```python
   def my_action_view(self, request):
       if not request.user.is_staff:
           return JsonResponse({'error': 'Permission denied'}, status=403)
       # Do something...
       return JsonResponse({'success': True, 'data': something})
   ```

2. **Register URL in get_urls():**
   ```python
   path('my-action/', self.my_action_view, name='my_action'),
   ```

3. **Add JavaScript function in template:**
   ```javascript
   function myAction() {
       fetch('{% url "calendar_admin:my_action" %}')
           .then(r => r.json())
           .then(d => { if(d.success) location.reload(); });
   }
   ```

4. **Add button in HTML:**
   ```html
   <button onclick="myAction()">My Action</button>
   ```

5. **Pass data to template in index():**
   ```python
   extra_context['my_data'] = computed_value
   ```

---

## Common Tasks

### Find the timeslot model admin interface
- Path: `/admin/calendar_api/timeslot/`
- Configure in: `calendar_api/admin/timeslot.py`

### Find the contact model admin interface
- Path: `/admin/calendar_api/contact/`
- Configure in: `calendar_api/admin/contact.py`

### Find the user settings interface
- Path: `/admin/calendar_api/settings/`
- Configure in: `calendar_api/admin/settings.py`

### Edit a timeslot
1. Go to `/admin/calendar_api/timeslot/`
2. Click the timeslot date/time in list
3. Edit fields in form
4. Save

### Edit a contact
1. Go to `/admin/calendar_api/contact/`
2. Click the contact name in list (or search for them)
3. Edit contact information
4. Save

### Change user settings
1. Go to `/admin/calendar_api/settings/`
2. Click user to edit their settings
3. Expand sections to see all options
4. Change timezone, notifications, display prefs, etc.
5. Save

---

## Important Notes

1. **Custom admin replaces default** - The only admin interface is the custom calendar admin at `/admin/`

2. **No drag-and-drop yet** - Calendar view is read-only. Edit timeslots through model admin.

3. **Inactive = hidden by default** - Generated timeslots are inactive and won't show unless you select "Every Timeslot" filter

4. **Staff permission required** - All admin actions require `request.user.is_staff = True`

5. **No bulk editing on dashboard** - Select multiple timeslots in `/admin/calendar_api/timeslot/` to use bulk actions

---

## Files for Reference

- Full documentation in code comments: `calendar_api/admin/`
- Dashboard template: `templates/admin/index.html`
- URL configuration: `config/urls.py`
- Models being managed: `calendar_api/models/`

