# -*- coding: utf-8 -*-
"""
auditoria.py
============
Sistema de auditoría automática.

Campos añadidos a cada modelo que herede de AuditoriaMixin:
    - fecha_creacion
    - usuario_creacion
    - fecha_modificacion
    - usuario_modificacion
    - activo
"""

import threading
from django.db import models
from django.db.models.signals import class_prepared, pre_save
from django.utils import timezone


_thread_locals = threading.local()


def set_current_user(user):
    _thread_locals.user = user


def get_current_user():
    return getattr(_thread_locals, 'user', None)


def clear_current_user():
    if hasattr(_thread_locals, 'user'):
        del _thread_locals.user


class AuditoriaMixin(models.Model):
    fecha_creacion = models.DateTimeField(
        default=timezone.now, null=True, blank=True,
        verbose_name='Fecha de creación',
    )
    usuario_creacion = models.ForeignKey(
        'Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='%(app_label)s_%(class)s_creados',
        verbose_name='Usuario que creó',
    )
    fecha_modificacion = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Fecha de modificación',
    )
    usuario_modificacion = models.ForeignKey(
        'Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='%(app_label)s_%(class)s_modificados',
        verbose_name='Usuario que modificó',
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo',
    )

    class Meta:
        abstract = True


def _fill_audit_fields(sender, instance, **kwargs):
    user = get_current_user()
    uid = getattr(user, 'id_usuario', None) if user else None

    if instance._state.adding:
        if getattr(instance, 'fecha_creacion', None) is None:
            instance.fecha_creacion = timezone.now()
        if uid and getattr(instance, 'usuario_creacion_id', None) is None:
            instance.usuario_creacion_id = uid
    else:
        if hasattr(instance, 'fecha_modificacion'):
            instance.fecha_modificacion = timezone.now()
        if uid and hasattr(instance, 'usuario_modificacion_id'):
            instance.usuario_modificacion_id = uid


def _connect_audit_signal(sender, **kwargs):
    try:
        if issubclass(sender, AuditoriaMixin) and not sender._meta.abstract:
            pre_save.connect(
                _fill_audit_fields,
                sender=sender,
                weak=False,
                dispatch_uid=f'audit_{sender.__module__}_{sender.__name__}',
            )
    except Exception:
        pass


class_prepared.connect(_connect_audit_signal, weak=False)
