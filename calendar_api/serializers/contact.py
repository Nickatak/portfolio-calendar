from rest_framework import serializers
from ..models import Contact


class ContactSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = Contact
        fields = ['id', 'first_name', 'last_name', 'full_name', 'email', 'phone_number', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def validate_email(self, value):
        """Validate that email is unique."""
        if Contact.objects.filter(email=value).exists():
            raise serializers.ValidationError("A contact with this email already exists.")
        return value
