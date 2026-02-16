from django.db import models
from django.contrib.auth.models import User


class Settings(models.Model):
    """
    User settings for the calendar application.
    Stores user-specific preferences and configurations.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='calendar_settings')
    
    # Timezone settings
    timezone = models.CharField(
        max_length=50,
        default='America/Los_Angeles',
        help_text='Timezone for displaying timeslots'
    )
    
    # Notification preferences
    email_on_confirmation = models.BooleanField(
        default=True,
        help_text='Send email when a timeslot is confirmed'
    )
    email_on_cancellation = models.BooleanField(
        default=True,
        help_text='Send email when a timeslot is cancelled'
    )
    email_daily_summary = models.BooleanField(
        default=False,
        help_text='Send daily summary of timeslots'
    )
    
    # Display preferences
    items_per_page = models.IntegerField(
        default=10,
        help_text='Number of items to display per page'
    )
    dark_mode = models.BooleanField(
        default=True,
        help_text='Enable dark mode in the admin panel'
    )
    
    # Calendar preferences
    calendar_show_weekends = models.BooleanField(
        default=True,
        help_text='Show weekends in calendar view'
    )
    calendar_start_hour = models.IntegerField(
        default=10,
        help_text='Start hour for calendar (0-23)'
    )
    calendar_end_hour = models.IntegerField(
        default=18,
        help_text='End hour for calendar (0-23)'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Settings'
        verbose_name_plural = 'User Settings'

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}'s Settings"
