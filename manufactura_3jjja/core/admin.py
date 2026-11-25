# -*- coding: utf-8 -*-
"""
admin.py - Configuracion del Panel de Administracion Django
Manufacturera de Calzado 3-JJJ-A

Personalizacion del admin para gestionar:
  - Usuario: Sistema de autenticacion propio
  - Modelo: Catalogo de productos
  - Material: Materiales de produccion
  - LoteProduccion: Ordenes de produccion
  - Etapa: Estaciones de trabajo
  - RegistroEtapa: Registro de entrada/salida
  - Maquinaria: Equipos de la planta
  - Incidente: Registro de alertas y fallas

Django 4.2 compatible - Windows 7
"""

from django.contrib import admin
from .models import (
    Usuario, Material, Modelo, MaterialModelo,
    LoteProduccion, Etapa, RegistroEtapa,
    DesperdicioMaterial, Maquinaria, Incidente
)


# ============================================================
# 1. ADMIN: USUARIO
# ============================================================
@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    """Panel de administracion para usuarios del sistema."""
    list_display = [
        'id_usuario',
        'nombre_completo',
        'rol',
        'etapa_asignada',
        'is_active',
        'is_staff',
        'fecha_registro',
    ]
    list_filter = ['rol', 'is_active', 'is_staff', 'fecha_registro']
    search_fields = ['id_usuario', 'nombre_completo']
    ordering = ['-fecha_registro']
    date_hierarchy = 'fecha_registro'

    fieldsets = (
        ('Informacion Principal', {
            'fields': ('id_usuario', 'nombre_completo', 'rol', 'etapa_asignada')
        }),
        ('Estado y Permisos', {
            'fields': ('is_active', 'is_staff'),
        }),
        ('Seguridad', {
            'fields': ('contrasenia',),
            'classes': ('collapse',),
            'description': 'La contrasena esta hasheada. Use el formulario para cambiarla.'
        }),
    )

    readonly_fields = ['fecha_registro']

    def save_model(self, request, obj, form, change):
        """Asigna contrasena hasheada si se proporciona."""
        if 'contrasenia' in form.changed_data and obj.contrasenia:
            # Solo hashear si no esta ya hasheada
            if not obj.contrasenia.startswith('pbkdf2'):
                obj.set_password(obj.contrasenia)
        super().save_model(request, obj, form, change)


# ============================================================
# 2. ADMIN: MATERIAL
# ============================================================
@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    """Panel de administracion para materiales."""
    list_display = ['id_material', 'nombre_material', 'unidad_medida']
    search_fields = ['nombre_material']
    ordering = ['nombre_material']


# ============================================================
# 3. ADMIN: MODELO DE CALZADO
# ============================================================
@admin.register(Modelo)
class ModeloAdmin(admin.ModelAdmin):
    """Panel de administracion para el catalogo de modelos."""
    list_display = ['id_modelo', 'nombre', 'fecha_registro']
    search_fields = ['id_modelo', 'nombre']
    ordering = ['-fecha_registro']
    date_hierarchy = 'fecha_registro'


# ============================================================
# 4. ADMIN: MATERIAL POR MODELO
# ============================================================
@admin.register(MaterialModelo)
class MaterialModeloAdmin(admin.ModelAdmin):
    """Panel de administracion para recetas de materiales."""
    list_display = ['id_material_modelo', 'id_modelo', 'id_material', 'cantidad_por_par']
    list_filter = ['id_modelo']
    search_fields = ['id_modelo__nombre', 'id_material__nombre_material']


# ============================================================
# 5. ADMIN: LOTE DE PRODUCCION
# ============================================================
@admin.register(LoteProduccion)
class LoteProduccionAdmin(admin.ModelAdmin):
    """Panel de administracion para lotes de produccion."""
    list_display = ['id_lote', 'id_modelo', 'cant_solicitada', 'estado_actual', 'fecha_creacion']
    list_filter = ['estado_actual', 'fecha_creacion']
    search_fields = ['id_lote', 'id_modelo__nombre']
    ordering = ['-fecha_creacion']
    date_hierarchy = 'fecha_creacion'


# ============================================================
# 6. ADMIN: ETAPA
# ============================================================
@admin.register(Etapa)
class EtapaAdmin(admin.ModelAdmin):
    """Panel de administracion para etapas de produccion."""
    list_display = ['id_etapa', 'nombre_etapa', 'secuencia']
    ordering = ['secuencia']


# ============================================================
# 7. ADMIN: REGISTRO DE ETAPA
# ============================================================
@admin.register(RegistroEtapa)
class RegistroEtapaAdmin(admin.ModelAdmin):
    """Panel de administracion para registros de entrada/salida."""
    list_display = [
        'id_registro',
        'id_lote',
        'id_etapa',
        'hora_entrada',
        'hora_salida',
        'pares_aprobados',
        'pares_rechazados',
        'estado_actual',
        'consumo_energetico_kwh',
        'id_usuario',
    ]
    list_filter = ['id_etapa', 'estado_actual', 'hora_entrada']
    search_fields = ['id_lote__id_lote', 'id_usuario__nombre_completo']
    ordering = ['-hora_entrada']
    date_hierarchy = 'hora_entrada'

    readonly_fields = ['tiempo_total_etapa']


# ============================================================
# 8. ADMIN: DESPERDICIO DE MATERIAL
# ============================================================
@admin.register(DesperdicioMaterial)
class DesperdicioMaterialAdmin(admin.ModelAdmin):
    """Panel de administracion para mermas."""
    list_display = ['id_desperdicio', 'id_registro_etapa', 'id_material', 'cantidad_desperdiciada', 'fecha_reporte']
    ordering = ['-fecha_reporte']


# ============================================================
# 9. ADMIN: MAQUINARIA
# ============================================================
@admin.register(Maquinaria)
class MaquinariaAdmin(admin.ModelAdmin):
    """Panel de administracion para maquinaria."""
    list_display = ['id_maquina', 'nombre', 'potencia_kw', 'factor_carga', 'id_etapa']
    list_filter = ['id_etapa']
    search_fields = ['id_maquina', 'nombre']


# ============================================================
# 10. ADMIN: INCIDENTE
# ============================================================
@admin.register(Incidente)
class IncidenteAdmin(admin.ModelAdmin):
    """Panel de administracion para incidentes de produccion."""
    list_display = [
        'id_incidente',
        'tipo_incidente',
        'severidad',
        'estado_coloreado',
        'id_etapa',
        'id_usuario_reporta',
        'fecha_reporte',
    ]
    list_filter = ['estado', 'tipo_incidente', 'severidad', 'id_etapa', 'fecha_reporte']
    search_fields = ['descripcion', 'id_usuario_reporta__nombre_completo', 'acciones_tomadas']
    ordering = ['-fecha_reporte']
    date_hierarchy = 'fecha_reporte'

    fieldsets = (
        ('Informacion del Incidente', {
            'fields': ('tipo_incidente', 'severidad', 'descripcion')
        }),
        ('Relaciones', {
            'fields': ('id_usuario_reporta', 'id_etapa', 'id_lote', 'id_maquina'),
        }),
        ('Gestion y Resolucion', {
            'fields': ('estado', 'acciones_tomadas', 'notificado_dashboard'),
            'classes': ('wide',)
        }),
        ('Auditoria (Solo lectura)', {
            'fields': ('fecha_reporte', 'fecha_resolucion', 'leido_por_gerente', 'fecha_lectura'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['fecha_reporte', 'fecha_resolucion', 'fecha_lectura']

    def estado_coloreado(self, obj):
        """Muestra el estado con colores en el listado del admin."""
        colores = {
            'PENDIENTE': 'red',
            'EN_PROCESO': 'orange',
            'RESUELTO': 'green',
            'ESCALADO': 'purple',
        }
        color = colores.get(obj.estado, 'gray')
        return f'<span style="color: {color}; font-weight: bold;">{obj.get_estado_display()}</span>'
    estado_coloreado.allow_tags = True
    estado_coloreado.short_description = 'Estado'
