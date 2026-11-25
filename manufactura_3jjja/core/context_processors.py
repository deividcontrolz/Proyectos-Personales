# -*- coding: utf-8 -*-
"""
context_processors.py - Variables globales para templates
Manufacturera de Calzado 3-JJJ-A
"""

from .models import Usuario

SESSION_KEY = 'usuario_id'


def usuario_sesion(request):
    """
    Context processor que agrega 'usuario' al contexto de todas las templates.
    Usa la sesion propia (no django.contrib.auth).
    """
    usuario_id = request.session.get(SESSION_KEY)
    usuario = None
    if usuario_id:
        try:
            usuario = Usuario.objects.get(id_usuario=usuario_id)
        except Usuario.DoesNotExist:
            pass
    return {'usuario': usuario}
