from django.urls import path

from hub_platform.identity import employee_views

urlpatterns = [
    path("", employee_views.employee_list_view, name="employee-list"),
    path("operators/", employee_views.create_operator_view, name="employee-create-operator"),
    path("<int:user_id>/update/", employee_views.update_employee_view, name="employee-update"),
    path("<int:user_id>/reset-password/", employee_views.reset_employee_password_view, name="employee-reset-password"),
    path("<int:user_id>/revoke-sessions/", employee_views.revoke_employee_sessions_view, name="employee-revoke-sessions"),
    path("<int:user_id>/block/", employee_views.block_employee_view, name="employee-block"),
    path("<int:user_id>/unblock/", employee_views.unblock_employee_view, name="employee-unblock"),
]
