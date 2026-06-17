from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse


def live(request):
    return JsonResponse({"status": "ok", "service": "hub-backend"})


def ready(request):
    checks = {"database": False, "redis": False}

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        checks["database"] = cursor.fetchone()[0] == 1

    cache.set("healthcheck", "ok", timeout=5)
    checks["redis"] = cache.get("healthcheck") == "ok"

    status_code = 200 if all(checks.values()) else 503
    return JsonResponse({"status": "ok" if status_code == 200 else "degraded", "checks": checks}, status=status_code)
