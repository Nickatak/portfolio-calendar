from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TimeSlotViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'timeslots', TimeSlotViewSet, basename='timeslot')

urlpatterns = [
    path('timeslots/by-day', TimeSlotViewSet.as_view({'get': 'by_day'}), name='timeslot-by-day'),
    path('', include(router.urls)),
]
