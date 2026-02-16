from rest_framework import viewsets, filters, status
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import datetime

from ..models import TimeSlot, Contact
from ..serializers import TimeSlotSerializer


class TimeSlotViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing availability time slots.
    
    Endpoints:
    - GET /api/timeslots/ - List all time slots
    - POST /api/timeslots/ - Create a new time slot
    - GET /api/timeslots/{id}/ - Retrieve a specific time slot
    - PUT /api/timeslots/{id}/ - Update a time slot
    - DELETE /api/timeslots/{id}/ - Delete a time slot
    - GET /api/timeslots/by-day/?date=YYYY-MM-DD - Get all time slots for a specific date
    - POST /api/timeslots/with-contact/ - Create a contact and timeslot together
    """
    queryset = TimeSlot.objects.all()
    serializer_class = TimeSlotSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['time']
    ordering = ['time']

    def get_queryset(self):
        """Filter by active status if specified."""
        queryset = super().get_queryset()
        is_active = self.request.query_params.get('is_active')
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset

    def create(self, request, *args, **kwargs):
        """
        Override default create to handle optional contact creation.
        
        Accepts contact and timeslot data together:
           {
               "contact": {"first_name": "...", "last_name": "...", "email": "..."},
               "timeslot": {
                   "start_time": "2026-01-27T10:00:00Z",
                   "end_time": "2026-01-27T10:45:00Z",
                   "topic": "..."
               }
           }
        """
        # Check if this is a with-contact request
        if 'contact' in request.data and isinstance(request.data.get('contact'), dict):
            contact_data = request.data.get('contact')
            timeslot_data = request.data.get('timeslot')
            
            if not timeslot_data:
                return Response(
                    {'error': 'timeslot data is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create or get contact
            try:
                contact, _ = Contact.objects.get_or_create(
                    email=contact_data.get('email'),
                    defaults={
                        'first_name': contact_data.get('firstName'),
                        'last_name': contact_data.get('lastName'),
                        'phone_number': contact_data.get('phone', '')
                    }
                )
            except Exception as e:
                return Response(
                    {'error': f'Failed to create/get contact: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create timeslot with the contact
            try:
                timeslot_data['contact'] = contact.id
                serializer = self.get_serializer(
                    data=timeslot_data,
                    context={**self.get_serializer_context(), 'enforce_public_policy': True},
                )
                serializer.is_valid(raise_exception=True)
                serializer.save()
                
                return Response(
                    {
                        'contact': {
                            'id': contact.id,
                            'first_name': contact.first_name,
                            'last_name': contact.last_name,
                            'email': contact.email,
                            'phone_number': contact.phone_number
                        },
                        'timeslot': serializer.data
                    },
                    status=status.HTTP_201_CREATED
                )
            except Exception as e:
                return Response(
                    {'error': f'Failed to create timeslot: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Standard create with contact ID
        return super().create(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def by_day(self, request):
        """
        Get all time slots for a specific date.
        
        Query parameters:
        - date: Date in YYYY-MM-DD format (required)
        
        Example: GET /api/timeslots/by-day/?date=2026-01-27
        """
        date_str = request.query_params.get('date')
        
        if date_str is None:
            return Response({'error': 'date parameter is required (format: YYYY-MM-DD)'}, status=400)
        
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'date must be in YYYY-MM-DD format'}, status=400)
        
        queryset = self.get_queryset().filter(time__date=date_obj)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
