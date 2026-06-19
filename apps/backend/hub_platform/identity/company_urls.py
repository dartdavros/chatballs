from django.urls import path

from hub_platform.identity import company_views

urlpatterns = [
    path("departments/", company_views.department_list_view, name="department-list"),
]
