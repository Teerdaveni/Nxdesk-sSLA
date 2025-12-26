from django.views.static import serve
from django.conf import settings
from django.contrib import admin
from django.urls import path,include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('user/', include('login_details.urls')),
    path('ticket/', include('timer.urls')),
    path('roles/', include('roles_creation.urls')),
    path('org/', include('organisation_details.urls')),
    path('category/', include('category.urls')),
    path('solution_grp/', include('solution_groups.urls')), 
    path('priority/', include('priority.urls')),
    path('knowledge_article/', include('knowledge_article.urls')),
    path('details/', include('personal_details.urls')),
    path('project/', include('project_details.urls')),
    path('resolution/', include('resolution.urls')),
    path('five_notifications/', include('five_notifications.urls')),
    path('ticket/', include('history.urls')),
    path('services/', include('services.urls')),
    path("notifications/", include("whatsapp_notifications.urls")),
]

# ✅ Serve media files in production (DEBUG = False)
if not settings.DEBUG:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]

# ✅ React frontend fallback (put AFTER all other routes)
urlpatterns += [
    re_path(
        r'^(?!media/).*$',  # ← explicitly skip media paths
        TemplateView.as_view(template_name='index.html')
    ),
]
