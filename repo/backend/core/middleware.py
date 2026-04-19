from threading import local


_request_state = local()


def get_current_organization_id():
    return getattr(_request_state, "organization_id", None)


class OrganizationContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        organization_id = None
        if request.user.is_authenticated:
            organization_id = getattr(request.user, "organization_id", None)

        _request_state.organization_id = organization_id
        request.organization_id = organization_id
        response = self.get_response(request)
        return response
