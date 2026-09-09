from django.urls import path

from chatballs.notifications import views

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="notification-list"),
    path("read/", views.NotificationReadView.as_view(), name="notification-read"),
    path("messenger-bindings/", views.MessengerBindingListView.as_view(), name="messenger-binding-list"),
    path("messenger-bindings/<int:integration_id>/", views.MessengerBindingDetailView.as_view(), name="messenger-binding-detail"),
]
