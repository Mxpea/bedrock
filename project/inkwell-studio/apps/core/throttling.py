from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle


class LoginThrottle(SimpleRateThrottle):
    scope = "login"

    def get_cache_key(self, request, view):
        username = request.data.get("username", "anonymous")
        ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": f"{ident}:{username}"}


class BurstUserThrottle(UserRateThrottle):
    scope = "burst_user"
