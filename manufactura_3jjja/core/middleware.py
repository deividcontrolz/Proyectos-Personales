# -*- coding: utf-8 -*-
"""
middleware.py - Proteccion de Sesiones y Validaciones de Seguridad
Manufacturera de Calzado 3-JJJ-A
Django 4.2 compatible
"""

import re
import logging
from django.shortcuts import redirect
from django.http import HttpResponseForbidden

logger = logging.getLogger(__name__)
SESSION_KEY = 'usuario_id'


def get_usuario_sesion_middleware(request):
    from .models import Usuario
    usuario_id = request.session.get(SESSION_KEY)
    if usuario_id:
        try:
            return Usuario.objects.get(id_usuario=usuario_id)
        except Usuario.DoesNotExist:
            pass
    return None


class SesionActivaMiddleware:
    """Verifica sesion activa usando modelo Usuario propio."""

    URLS_PUBLICAS = [
        '/login/',
        '/logout/',
        '/registro/',
        '/admin/',
        '/static/',
        '/media/',
        '/403/',
        '/redirect/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        es_url_publica = any(
            request.path.startswith(url) for url in self.URLS_PUBLICAS
        )

        if not es_url_publica:
            usuario = get_usuario_sesion_middleware(request)

            if not usuario:
                logger.warning(
                    "[SEGURIDAD] Acceso sin autenticacion: IP=%s, PATH=%s",
                    self._get_ip(request), request.path
                )
                if request.path.startswith('/api/'):
                    return HttpResponseForbidden("Sesion no activa")
                return redirect('/login/')

            if request.session.get_expiry_age() <= 0:
                if SESSION_KEY in request.session:
                    del request.session[SESSION_KEY]
                logger.warning("[SEGURIDAD] Sesion expirada")
                return redirect('/login/')

            request.usuario_actual = usuario

        response = self.get_response(request)
        return response

    def _get_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'desconocida')


class SeguridadEntradaMiddleware:
    """Sanitiza parametros GET y POST."""

    PATRONES_SQL = [
        r"(\%27)|(')|(\-\-)|(\%23)|(#)",
        r"UNION\s+SELECT",
        r"INSERT\s+INTO",
        r"DELETE\s+FROM",
        r"DROP\s+TABLE",
        r"exec\s+\w+",
    ]

    PATRONES_XSS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe",
        r"<object",
        r"<embed",
    ]

    def __init__(self, get_response):
        self.get_response = get_response
        self.patrones_sql = [re.compile(p, re.IGNORECASE) for p in self.PATRONES_SQL]
        self.patrones_xss = [re.compile(p, re.IGNORECASE) for p in self.PATRONES_XSS]

    def __call__(self, request):
        if request.method in ['POST', 'PUT', 'PATCH']:
            if hasattr(request, 'POST'):
                self._verificar_diccionario(request.POST, request)

        if request.method == 'GET':
            if hasattr(request, 'GET'):
                self._verificar_diccionario(request.GET, request)

        response = self.get_response(request)
        return response

    def _verificar_diccionario(self, datos, request):
        for key, valores in datos.lists() if hasattr(datos, 'lists') else [(k, [v]) for k, v in datos.items()]:
            if not isinstance(valores, list):
                valores = [valores]
            for valor in valores:
                valor_str = str(valor)
                for patron in self.patrones_sql:
                    if patron.search(valor_str):
                        logger.warning(
                            "[SEGURIDAD] SQL Injection: IP=%s, param=%s",
                            self._get_ip(request), key
                        )
                        return
                for patron in self.patrones_xss:
                    if patron.search(valor_str):
                        logger.warning(
                            "[SEGURIDAD] XSS: IP=%s, param=%s",
                            self._get_ip(request), key
                        )
                        return

    def _get_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'desconocida')


class SecurityHeadersMiddleware:
    """Agrega cabeceras de seguridad HTTP."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net fonts.googleapis.com; "
            "font-src 'self' fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self';"
        )

        if request.path.startswith('/dashboard/') or request.path.startswith('/catalogo/'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

        return response


# ============================================================
# Middleware de auditoría (auto-añadido)
# ============================================================
try:
    from .auditoria import set_current_user, clear_current_user
except ImportError:
    set_current_user = lambda u: None
    clear_current_user = lambda: None


class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = None
        try:
            uid = request.session.get('usuario_id')
            if uid:
                from .models import Usuario
                try:
                    user = Usuario.objects.get(id_usuario=uid)
                except Usuario.DoesNotExist:
                    user = None
        except Exception:
            user = None

        set_current_user(user)
        try:
            response = self.get_response(request)
        finally:
            clear_current_user()
        return response
