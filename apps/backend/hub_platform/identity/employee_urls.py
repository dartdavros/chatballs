from django.urls import path

from hub_platform.identity import employee_views

urlpatterns = [
    path("", employee_views.employee_list_view, name="employee-list"),
    path("operators/", employee_views.create_operator_view, name="employee-create-operator"),
    path("<int:user_id>/block/", employee_views.block_employee_view, name="employee-block"),
]
