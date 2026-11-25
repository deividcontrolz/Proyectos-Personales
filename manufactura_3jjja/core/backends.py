# -*- coding: utf-8 -*-
"""
backends.py - Backend de autenticacion custom para el modelo Usuario
Manufacturera de Calzado 3-JJJ-A

Permite autenticar usuarios usando el modelo Usuario custom
en lugar del User de Django.

Django 4.2 compatible
"""

from django.contrib.auth.backends import BaseBackend
from .models import Usuario


class UsuarioAuthBackend(BaseBackend):
    """
    Backend de autenticacion que usa el modelo Usuario custom.
    Permite login con id_usuario y contrasenia.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Autentica un usuario usando id_usuario y contrasenia.
        """
        if not username or not password:
            return None

        try:
            user = Usuario.objects.get(id_usuario=username, is_active=True)
        except Usuario.DoesNotExist:
            return None

        if user.check_password(password):
            return user
        return None

    def get_user(self, user_id):
        """
        Recupera un usuario por su ID (id_usuario).
        """
        try:
            return Usuario.objects.get(pk=user_id)
        except Usuario.DoesNotExist:
            return None
