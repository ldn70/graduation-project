from django.urls import path

from .views import DeleteAccountView, LoginView, ProfileView, RegisterView, SecurityLogExportView, SecurityLogListView

urlpatterns = [
    path("register", RegisterView.as_view(), name="user-register"),
    path("login", LoginView.as_view(), name="user-login"),
    path("profile", ProfileView.as_view(), name="user-profile"),
    path("delete", DeleteAccountView.as_view(), name="user-delete"),
    path("security-logs", SecurityLogListView.as_view(), name="user-security-logs"),
    path("security-logs/export", SecurityLogExportView.as_view(), name="user-security-logs-export"),
]
