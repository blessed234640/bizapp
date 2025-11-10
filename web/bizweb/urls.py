from django.contrib import admin
from django.urls import path, include  # ← ДОБАВЬТЕ include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
]