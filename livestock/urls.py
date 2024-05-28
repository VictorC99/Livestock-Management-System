from django.contrib import admin
from django.urls import path

urlpatterns = [
    path('admin/', admin.site.urls),
]
from django.urls import path, include
from rest_framework import routers
from .  import views

app_name='dairy'

router = routers.DefaultRouter()
router.register(r'cows', views.CowViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

