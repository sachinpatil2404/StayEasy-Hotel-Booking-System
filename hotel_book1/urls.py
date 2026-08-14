from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns

from django.views.generic import RedirectView

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('accounts/login/', RedirectView.as_view(url='/login/', permanent=False)),
    path('accounts/logout/', RedirectView.as_view(url='/logout/', permanent=False)),
    path('accounts/', include('django.contrib.auth.urls')),
    path("chatbot/", include("chatbot.urls")),
    path("api/", include("api.urls")),
]

# ✅ MAIN APP ROUTES (WITH LANGUAGE SUPPORT)
urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('', include('bookings.urls')),
)

# ✅ MEDIA FILES
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)