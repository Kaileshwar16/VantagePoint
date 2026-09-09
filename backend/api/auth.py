from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
import json


@require_http_methods(['GET', 'POST', 'DELETE'])
@csrf_protect
def session(request):
    if request.method == 'POST':
        from rest_framework.throttling import AnonRateThrottle
        throttle = AnonRateThrottle()
        if not throttle.allow_request(request, None):
            return JsonResponse({'detail': 'Too many sign-in attempts. Try again later.'}, status=429)
        try:
            payload = json.loads(request.body)
            if not isinstance(payload, dict):
                raise ValueError
            username, password = payload.get('username'), payload.get('password')
            if not isinstance(username, str) or not isinstance(password, str):
                raise ValueError
        except (ValueError, TypeError):
            return JsonResponse({'detail': 'Provide username and password.'}, status=400)
        user = authenticate(request, username=username, password=password)
        if user is None or not user.is_staff:
            return JsonResponse({'detail': 'Invalid credentials or workspace access unavailable.'}, status=403)
        login(request, user)
    elif request.method == 'DELETE':
        logout(request)
    return JsonResponse({'authenticated': request.user.is_authenticated and request.user.is_staff,
                         'username': request.user.get_username() if request.user.is_authenticated else None,
                         'csrfToken': get_token(request)})
