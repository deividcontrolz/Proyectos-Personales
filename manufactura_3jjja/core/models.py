# -*- coding: utf-8 -*-
"""
models.py - Sistema de Gestion de Produccion
Manufacturera de Calzado 3-JJJ-A

Modelos principales:
  - Usuario: Sistema de autenticación propio con roles
  - Material: Materiales de producción
  - Modelo: Catálogo de modelos de calzado
  - MaterialModelo: Relación materiales por modelo
  - LoteProduccion: Órdenes de producción
  - Etapa: Etapas del proceso productivo
  - RegistroEtapa: Registro de entrada/salida por etapa
  - DesperdicioMaterial: Merma de materiales
  - Maquinaria: Equipos de la planta
  - Incidente: Registro de alertas y fallas

Django 4.2 compatible - Windows 7
"""

from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone

from .auditoria import AuditoriaMixin


# ============================================================
# CONSTANTES DE ROLES
# ============================================================
ROL_OPERARIO = 'OPERARIO'
ROL_GERENTE = 'GERENTE'
ROL_SUBGERENTE = 'SUBGERENTE'
ROL_DIRECTOR_PRODUCCION = 'DIRECTOR_PRODUCCION'
ROL_DIRECTOR_DESPACHO = 'DIRECTOR_DESPACHO'

ROLES_CHOICES = [
    (ROL_OPERARIO, 'Operario de Planta'),
    (ROL_GERENTE, 'Gerente de Planta'),
    (ROL_SUBGERENTE, 'Subgerente de Planta'),
    (ROL_DIRECTOR_PRODUCCION, 'Director de Produccion'),
    (ROL_DIRECTOR_DESPACHO, 'Director de Despacho'),
]

TIPO_INCIDENTE_CHOICES = [
    ('FALLA_MAQUINA', 'Falla de Maquinaria'),
    ('FALTA_MATERIAL', 'Falta de Material'),
    ('ACCIDENTE_LABORAL', 'Accidente Laboral'),
    ('RETRASO_PRODUCCION', 'Retraso en Produccion'),
    ('DEFECTO_CALIDAD', 'Defecto de Calidad Detectado'),
    ('PARADA_EMERGENCIA', 'Parada de Emergencia'),
    ('OTRO', 'Otro'),
]

ESTADO_INCIDENTE_CHOICES = [
    ('PENDIENTE', 'Pendiente'),
    ('EN_PROCESO', 'En Proceso'),
    ('RESUELTO', 'Resuelto'),
    ('ESCALADO', 'Escalado a Supervisor'),
]

SEVERIDAD_CHOICES = [
    ('BAJA', 'Baja'),
    ('MEDIA', 'Media'),
    ('ALTA', 'Alta'),
    ('CRITICA', 'Critica'),
]


# ============================================================
# 1. MODELO: USUARIO (Autenticación propia con roles)
# ============================================================
class Usuario(AuditoriaMixin):
    """
    Modelo de usuario personalizado para el sistema de producción.
    Sustituye al User de Django para un control total de roles.
    """
    id_usuario = models.CharField(max_length=50, primary_key=True)
    nombre_completo = models.CharField(max_length=150)
    contrasenia = models.CharField(max_length=128)
    rol = models.CharField(max_length=50, choices=ROLES_CHOICES, default=ROL_OPERARIO)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    # Campos adicionales para asignación de etapa (operarios)
    etapa_asignada = models.ForeignKey(
        'Etapa',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios_asignados',
        verbose_name='Etapa Asignada'
    )

    def set_password(self, raw_password):
        self.contrasenia = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.contrasenia)

    def __str__(self):
        return f"{self.nombre_completo} ({self.get_rol_display()})"

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @property
    def is_superuser(self):
        return self.is_staff

    def has_role(self, *roles):
        return self.rol in roles

    def has_perm(self, perm, obj=None):
        return self.is_staff

    def has_module_perms(self, app_label):
        return self.is_staff

    @property
    def username(self):
        return self.id_usuario

    @property
    def first_name(self):
        nombres = self.nombre_completo.split()
        return nombres[0] if nombres else ''

    @property
    def last_name(self):
        nombres = self.nombre_completo.split()
        return ' '.join(nombres[1:]) if len(nombres) > 1 else ''

    @property
    def email(self):
        return f"{self.id_usuario}@3jjja.local"

    @property
    def get_full_name(self):
        return self.nombre_completo

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['-fecha_registro']


# ============================================================
# 2. MODELO: MATERIAL
# ============================================================
class Material(AuditoriaMixin):
    id_material = models.AutoField(primary_key=True)
    nombre_material = models.CharField(max_length=100)
    unidad_medida = models.CharField(max_length=20, default='m')

    def __str__(self):
        return f"{self.nombre_material} ({self.unidad_medida})"

    class Meta:
        verbose_name = 'Material'
        verbose_name_plural = 'Materiales'


# ============================================================
# 3. MODELO: MODELO DE CALZADO
# ============================================================
class Modelo(AuditoriaMixin):
    id_modelo = models.CharField(max_length=50, primary_key=True)
    nombre = models.CharField(max_length=100)
    materiales = models.ManyToManyField(Material, through='MaterialModelo')
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Modelo de Calzado'
        verbose_name_plural = 'Modelos de Calzado'


# ============================================================
# 4. MODELO: MATERIAL POR MODELO (Receta)
# ============================================================
class MaterialModelo(AuditoriaMixin):
    id_material_modelo = models.AutoField(primary_key=True)
    id_modelo = models.ForeignKey(Modelo, on_delete=models.CASCADE, db_column='id_modelo')
    id_material = models.ForeignKey(Material, on_delete=models.CASCADE, db_column='id_material')
    cantidad_por_par = models.DecimalField(max_digits=10, decimal_places=3)

    def __str__(self):
        return f"{self.id_modelo.nombre} - {self.id_material.nombre_material}"

    class Meta:
        verbose_name = 'Material por Modelo'
        verbose_name_plural = 'Materiales por Modelo'


# ============================================================
# 5. MODELO: LOTE DE PRODUCCION
# ============================================================
class LoteProduccion(AuditoriaMixin):
    id_lote = models.CharField(max_length=50, primary_key=True)
    cant_solicitada = models.IntegerField()
    estado_actual = models.CharField(max_length=50, default='PENDIENTE')
    id_modelo = models.ForeignKey(Modelo, on_delete=models.CASCADE, db_column='id_modelo')
    # fecha_creacion viene del mixin AuditoriaMixin

    def __str__(self):
        return f"Lote {self.id_lote}"

    class Meta:
        verbose_name = 'Lote de Produccion'
        verbose_name_plural = 'Lotes de Produccion'


# ============================================================
# 6. MODELO: ETAPA (Estación de trabajo)
# ============================================================
class Etapa(AuditoriaMixin):
    id_etapa = models.CharField(max_length=50, primary_key=True)
    nombre_etapa = models.CharField(max_length=100)
    secuencia = models.IntegerField()

    def __str__(self):
        return self.nombre_etapa

    class Meta:
        verbose_name = 'Etapa'
        verbose_name_plural = 'Etapas'
        ordering = ['secuencia']


# ============================================================
# 7. MODELO: REGISTRO DE ETAPA (Entrada/Salida)
# ============================================================
class RegistroEtapa(AuditoriaMixin):
    id_registro = models.AutoField(primary_key=True)
    hora_entrada = models.DateTimeField()
    hora_salida = models.DateTimeField(null=True, blank=True)
    pares_aprobados = models.IntegerField(default=0)
    pares_rechazados = models.IntegerField(default=0)
    estado_actual = models.CharField(max_length=50, default='EN_PROCESO')
    tiempo_total_etapa = models.CharField(max_length=50, null=True, blank=True)
    consumo_energetico_kwh = models.FloatField(default=0.0)
    id_lote = models.ForeignKey(LoteProduccion, on_delete=models.CASCADE, db_column='id_lote')
    id_etapa = models.ForeignKey(Etapa, on_delete=models.CASCADE, db_column='id_etapa')
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_usuario')

    def __str__(self):
        return f"Reg {self.id_registro} - Lote {self.id_lote_id}"

    class Meta:
        verbose_name = 'Registro de Etapa'
        verbose_name_plural = 'Registros de Etapa'
        ordering = ['-hora_entrada']


# ============================================================
# 8. MODELO: DESPERDICIO DE MATERIAL
# ============================================================
class DesperdicioMaterial(AuditoriaMixin):
    id_desperdicio = models.AutoField(primary_key=True)
    id_registro_etapa = models.ForeignKey(RegistroEtapa, on_delete=models.CASCADE, db_column='id_registro')
    id_material = models.ForeignKey(Material, on_delete=models.CASCADE, db_column='id_material')
    cantidad_desperdiciada = models.DecimalField(max_digits=12, decimal_places=3)
    fecha_reporte = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Merma Reg {self.id_registro_etapa_id}"

    class Meta:
        verbose_name = 'Desperdicio de Material'
        verbose_name_plural = 'Desperdicios de Material'


# ============================================================
# 9. MODELO: MAQUINARIA
# ============================================================
class Maquinaria(AuditoriaMixin):
    id_maquina = models.CharField(max_length=50, primary_key=True)
    potencia_kw = models.FloatField(blank=True, null=True)
    nombre = models.CharField(max_length=100, default="Maquina")
    factor_carga = models.FloatField(blank=True, null=True)
    id_etapa = models.ForeignKey(Etapa, on_delete=models.CASCADE, db_column='id_etapa')

    def __str__(self):
        return f"Maquina {self.id_maquina}"

    class Meta:
        verbose_name = 'Maquinaria'
        verbose_name_plural = 'Maquinarias'


# ============================================================
# 10. MODELO: INCIDENTE
# ============================================================
class Incidente(AuditoriaMixin):
    id_incidente = models.AutoField(primary_key=True)
    tipo_incidente = models.CharField(max_length=50, choices=TIPO_INCIDENTE_CHOICES)
    severidad = models.CharField(max_length=20, choices=SEVERIDAD_CHOICES, default='MEDIA')
    descripcion = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADO_INCIDENTE_CHOICES, default='PENDIENTE')
    fecha_reporte = models.DateTimeField(auto_now_add=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    acciones_tomadas = models.TextField(blank=True, null=True)
    notificado_dashboard = models.BooleanField(default=False)

    id_usuario_reporta = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        db_column='id_usuario_reporta',
        related_name='incidentes_reportados'
    )
    id_etapa = models.ForeignKey(
        Etapa,
        on_delete=models.CASCADE,
        db_column='id_etapa',
        null=True,
        blank=True
    )
    id_lote = models.ForeignKey(
        LoteProduccion,
        on_delete=models.SET_NULL,
        db_column='id_lote',
        null=True,
        blank=True
    )
    id_maquina = models.ForeignKey(
        Maquinaria,
        on_delete=models.SET_NULL,
        db_column='id_maquina',
        null=True,
        blank=True
    )

    leido_por_gerente = models.BooleanField(default=False)
    fecha_lectura = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Incidente #{self.id_incidente} - {self.get_tipo_incidente_display()} ({self.severidad})"

    class Meta:
        ordering = ['-fecha_reporte']
        verbose_name = 'Incidente'
        verbose_name_plural = 'Incidentes'
