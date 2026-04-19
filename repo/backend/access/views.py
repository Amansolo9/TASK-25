from rest_framework.response import Response
from rest_framework.views import APIView

from access.models import Role
from access.serializers import RoleSerializer


class MyRolesView(APIView):
    def get(self, request):
        roles = (
            Role.objects.filter(userrole__user=request.user)
            .prefetch_related("role_permissions__permission")
            .order_by("name")
        )
        return Response(RoleSerializer(roles, many=True).data)
