"""
URL configuration for campuscode project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    Add an import:  from my_app import views
    Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    Add an import:  from other_app.views import Home
    Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    Import the include() function: from django.urls import include, path
    Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('', include('core.urls')),
]