from django.urls import path

from hub_platform.notifications import views

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="notification-list"),
    path("read/", views.NotificationReadView.as_view(), name="notification-read"),
]
