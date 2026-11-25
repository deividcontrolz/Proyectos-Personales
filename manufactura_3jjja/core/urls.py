# -*- coding: utf-8 -*-
"""
urls.py - Enrutamiento del Sistema de Gestion de Produccion
Manufacturera de Calzado 3-JJJ-A

Django 4.2 compatible - Windows 7
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # ============================================================
    # AUTENTICACION
    # ============================================================
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/', views.registro_view, name='registro'),
    path('redirect/', views.redirect_por_rol, name='redirect_por_rol'),
    path('cambiar-password-temporal/', views.cambiar_password_temporal_view,
         name='cambiar_password_temporal'),

    # ============================================================
    # DASHBOARD
    # ============================================================
    path('', views.dashboard_view, name='dashboard'),
    path('dashboard/', views.dashboard_view, name='dashboard_alt'),
    path('produccion/', views.dashboard_view, name='produccion'),

    # ============================================================
    # CONFIGURACION
    # ============================================================
    path('configuracion/', views.configuracion_view, name='configuracion'),

    # ============================================================
    # OPERARIO
    # ============================================================
    path('operario/', views.operario_redirect_view, name='operario'),
    path('operario/<str:etapa_id>/', views.operario_etapa_view, name='operario_etapa'),

    # ============================================================
    # CALIDAD
    # ============================================================
    path('calidad/', views.calidad_view, name='calidad'),

    # ============================================================
    # INCIDENTES
    # ============================================================
    path('incidentes/reportar/', views.reportar_incidente_view, name='reportar_incidente'),
    path('incidentes/historial/', views.historial_incidentes_view, name='historial_incidentes'),
    path('incidentes/api/actualizar/<int:pk>/', views.api_actualizar_incidente, name='api_actualizar_incidente'),

    # ============================================================
    # CATALOGO
    # ============================================================
    path('catalogo/', views.catalogo_modelos_view, name='catalogo_modelos'),
    path('catalogo/registrar/', views.registrar_modelo_view, name='registrar_modelo'),
    path('catalogo/editar/<str:pk>/', views.editar_modelo_view, name='editar_modelo'),
    path('catalogo/detalle/<str:pk>/', views.detalle_modelo_view, name='detalle_modelo'),

    # ============================================================
    # TRAZABILIDAD
    # ============================================================
    path('trazabilidad/', views.trazabilidad_view, name='trazabilidad'),

    # ============================================================
    # PANEL ADMIN
    # ============================================================
    path('panel-admin/', views.panel_admin_view, name='panel_admin'),
    path('panel-admin/usuarios/', views.admin_usuarios_view, name='admin_usuarios'),
    path('panel-admin/usuarios/desbloquear/<str:usuario_id>/', views.admin_desbloquear_usuario_view, name='admin_desbloquear_usuario'),

    # ============================================================
    # REPORTES PDF
    # ============================================================
    path('reportes/', views.panel_reportes_view, name='panel_reportes'),
    path('reportes/usuarios/', views.reporte_usuarios_pdf, name='reporte_usuarios_pdf'),
    path('reportes/modelos/', views.reporte_modelos_pdf, name='reporte_modelos_pdf'),
    path('reportes/lotes/', views.reporte_lotes_pdf, name='reporte_lotes_pdf'),
    path('reportes/incidentes/', views.reporte_incidentes_pdf, name='reporte_incidentes_pdf'),
    path('reportes/materiales/', views.reporte_materiales_pdf, name='reporte_materiales_pdf'),
    path('reportes/etapas/', views.reporte_etapas_pdf, name='reporte_etapas_pdf'),
    path('reportes/auditoria/', views.reporte_auditoria_pdf, name='reporte_auditoria_pdf'),
    # ============================================================
    # ERRORES
    # ============================================================
    path('403/', views.error_403_view, name='error_403'),
]
