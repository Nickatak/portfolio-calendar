from django.http import JsonResponse
from django.urls import include, path
from calendar_api.admin.sites import calendar_admin_site


def healthz(_request):
    return JsonResponse({'status': 'ok'})


urlpatterns = [
    path('healthz', healthz, name='healthz'),
    path('admin/', calendar_admin_site.urls),
    path('api/', include('calendar_api.urls')),
]
