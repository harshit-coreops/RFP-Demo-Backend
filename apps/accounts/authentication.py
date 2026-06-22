from rest_framework.authentication import SessionAuthentication


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """Session auth without CSRF enforcement.

    The SPA talks to the API over a same-origin proxy and manages its own login
    flow; disabling DRF's CSRF check keeps authenticated POST/PATCH simple for
    the MVP. (A production deployment would issue and send the CSRF token.)"""

    def enforce_csrf(self, request):
        return
