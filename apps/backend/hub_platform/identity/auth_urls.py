from django.urls import path

from hub_platform.identity import auth_views

urlpatterns = [
    path("session/", auth_views.SessionView.as_view(), name="auth-session"),
    path("login/", auth_views.LoginView.as_view(), name="auth-login"),
    path("logout/", auth_views.LogoutView.as_view(), name="auth-logout"),
    path("password-reset/request/", auth_views.PasswordResetRequestView.as_view(), name="auth-password-reset-request"),
    path("password-reset/validate/", auth_views.PasswordResetValidateView.as_view(), name="auth-password-reset-validate"),
    path("password-reset/confirm/", auth_views.PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
    path("profile/update/", auth_views.ProfileUpdateView.as_view(), name="auth-profile-update"),
    path("profile/password/", auth_views.ProfilePasswordView.as_view(), name="auth-profile-password"),
    path("profile/totp/start/", auth_views.ProfileTotpStartView.as_view(), name="auth-profile-totp-start"),
    path("profile/totp/disable/", auth_views.ProfileTotpDisableView.as_view(), name="auth-profile-totp-disable"),
    path("profile/sessions/revoke-other/", auth_views.ProfileRevokeOtherSessionsView.as_view(), name="auth-profile-revoke-other-sessions"),
    path("change-temporary-password/", auth_views.ChangeTemporaryPasswordView.as_view(), name="auth-change-temp-password"),
    path("totp/setup/", auth_views.TotpSetupView.as_view(), name="auth-totp-setup"),
    path("totp/confirm/", auth_views.TotpConfirmView.as_view(), name="auth-totp-confirm"),
    path("totp/verify/", auth_views.TotpVerifyView.as_view(), name="auth-totp-verify"),
]
