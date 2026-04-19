from django.urls import path

from access.views import MyRolesView

urlpatterns = [
    path("me/roles/", MyRolesView.as_view(), name="my-roles"),
]
