from django.urls import path

from hub_platform.identity import auth

urlpatterns = [
    path("session/", auth.SessionView.as_view(), name="auth-session"),
    path("login/", auth.LoginView.as_view(), name="auth-login"),
    path("logout/", auth.LogoutView.as_view(), name="auth-logout"),
    path("password-reset/request/", auth.PasswordResetRequestView.as_view(), name="auth-password-reset-request"),
    path("password-reset/validate/", auth.PasswordResetValidateView.as_view(), name="auth-password-reset-validate"),
    path("password-reset/confirm/", auth.PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
    path("profile/update/", auth.ProfileUpdateView.as_view(), name="auth-profile-update"),
    path("profile/appearance/", auth.ProfileAppearanceView.as_view(), name="auth-profile-appearance"),
    path("profile/password/", auth.ProfilePasswordView.as_view(), name="auth-profile-password"),
    path("profile/totp/start/", auth.ProfileTotpStartView.as_view(), name="auth-profile-totp-start"),
    path("profile/totp/disable/", auth.ProfileTotpDisableView.as_view(), name="auth-profile-totp-disable"),
    path("profile/sessions/revoke-other/", auth.ProfileRevokeOtherSessionsView.as_view(), name="auth-profile-revoke-other-sessions"),
    path("change-temporary-password/", auth.ChangeTemporaryPasswordView.as_view(), name="auth-change-temp-password"),
    path("totp/setup/", auth.TotpSetupView.as_view(), name="auth-totp-setup"),
    path("totp/confirm/", auth.TotpConfirmView.as_view(), name="auth-totp-confirm"),
    path("totp/verify/", auth.TotpVerifyView.as_view(), name="auth-totp-verify"),
    path("invitations/accept/", auth.InvitationAcceptView.as_view(), name="auth-invitation-accept"),
]
