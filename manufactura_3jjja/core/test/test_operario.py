# -*- coding: utf-8 -*-
"""
Tests de la terminal del operario (operario_etapa_view y operario_redirect_view).

    python manage.py test core.tests.test_operario
"""
import re
import shutil
import tempfile
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.messages import get_messages

from core import views
from core.models import (
    Usuario, Etapa, Modelo, LoteProduccion, RegistroEtapa, Maquinaria,
    ROL_OPERARIO, ROL_GERENTE,
)


def mensajes(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


def crear_usuario(pk='op1', rol=ROL_OPERARIO, etapa=None, staff=False,
                  password='clave1234'):
    u = Usuario(id_usuario=pk, nombre_completo='Usuario ' + pk, rol=rol,
                etapa_asignada=etapa, is_staff=staff)
    u.set_password(password)
    u.save()
    return u


def login_sesion(client, pk):
    s = client.session
    s[views.SESSION_KEY] = pk
    s.save()


DATOS_OPERARIO = {
    'movimientos': [],
    'lotes_activos': [],
    'total_pares_hoy': 0,
    'total_aprobados_hoy': 0,
    'total_rechazados_hoy': 0,
    'eficiencia_turno': 0,
    'total_registros_hoy': 0,
}


class OperarioEtapaTests(TestCase):
    def setUp(self):
        self.etapa = Etapa.objects.create(
            id_etapa='ETP-1', nombre_etapa='Corte', secuencia=1)
        self.operario = crear_usuario('op1', etapa=self.etapa)
        self.modelo = Modelo.objects.create(id_modelo='MOD-001', nombre='Test')
        self.lote = LoteProduccion.objects.create(
            id_lote='LOT-001', id_modelo=self.modelo, cant_solicitada=100)
        Maquinaria.objects.create(
            id_maquina='MQ-1', potencia_kw=2.0, factor_carga=1.0,
            id_etapa=self.etapa)
        # Aislamos la vista del servicio (se prueba aparte)
        patcher = patch('core.views.obtener_datos_operario')
        self.mock_datos = patcher.start()
        self.mock_datos.return_value = dict(DATOS_OPERARIO)
        self.addCleanup(patcher.stop)

    def url(self, etapa_id=None):
        return reverse('core:operario_etapa',
                       kwargs={'etapa_id': etapa_id or 'ETP-1'})

    # ---------- Permisos ----------
    def test_sin_sesion_redirige_a_login(self):
        r = self.client.get(self.url())
        self.assertRedirects(r, reverse('core:login'))

    def test_usuario_de_otra_etapa_es_redirigido(self):
        otra = Etapa.objects.create(id_etapa='ETP-2', nombre_etapa='Suela',
                                  secuencia=2)
        crear_usuario('op2', etapa=otra)
        login_sesion(self.client, 'op2')
        r = self.client.get(self.url())
        self.assertRedirects(r, reverse('core:operario'))

    def test_operario_sin_etapa_puede_acceder_a_cualquiera(self):
        """COMPORTAMIENTO DOCUMENTADO: sin etapa asignada no hay restriccion
        por URL (coincide con la vista de seleccion de etapa)."""
        crear_usuario('libre', etapa=None)
        login_sesion(self.client, 'libre')
        r = self.client.get(self.url())
        self.assertEqual(r.status_code, 200)

    def test_rol_no_operario_recibe_403(self):
        crear_usuario('g1', rol=ROL_GERENTE, etapa=None)
        login_sesion(self.client, 'g1')
        r = self.client.get(self.url())
        self.assertEqual(r.status_code, 403)

    # ---------- Funcionalidad ----------
    def test_get_muestra_terminal(self):
        login_sesion(self.client, 'op1')
        r = self.client.get(self.url())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Corte')

    def test_entrada_crea_registro_en_proceso(self):
        login_sesion(self.client, 'op1')
        r = self.client.post(self.url(), {'accion': 'Entrada', 'lote_id': 'LOT-001'})
        self.assertRedirects(r, self.url())
        reg = RegistroEtapa.objects.get(id_lote=self.lote, id_etapa=self.etapa)
        self.assertEqual(reg.estado_actual, 'EN_PROCESO')
        self.assertIsNone(reg.hora_salida)

    def test_entrada_duplicada_no_deberia_permitirse(self):
        """BUG ESPERADO: la vista NO verifica si ya hay una entrada abierta,
        asi que este test FALLA hasta que se agregue la validacion."""
        login_sesion(self.client, 'op1')
        self.client.post(self.url(), {'accion': 'Entrada', 'lote_id': 'LOT-001'})
        self.client.post(self.url(), {'accion': 'Entrada', 'lote_id': 'LOT-001'})
        abiertos = RegistroEtapa.objects.filter(
            id_lote=self.lote, id_etapa=self.etapa, hora_salida__isnull=True)
        self.assertEqual(abiertos.count(), 1)  # actualmente se crean 2

    def test_salida_sin_entrada_muestra_error(self):
        login_sesion(self.client, 'op1')
        r = self.client.post(self.url(), {'accion': 'Salida', 'lote_id': 'LOT-001'})
        self.assertTrue(any('No se encontro entrada activa' in m
                            for m in mensajes(r)))
        self.assertFalse(RegistroEtapa.objects.filter(
            id_lote=self.lote, id_etapa=self.etapa).exists())

    def test_entrada_y_salida_completan_el_registro(self):
        login_sesion(self.client, 'op1')
        self.client.post(self.url(), {'accion': 'Entrada', 'lote_id': 'LOT-001'})
        r = self.client.post(self.url(), {'accion': 'Salida', 'lote_id': 'LOT-001'})
        reg = RegistroEtapa.objects.get(id_lote=self.lote, id_etapa=self.etapa)
        self.assertEqual(reg.estado_actual, 'COMPLETADO')
        self.assertIsNotNone(reg.hora_salida)
        self.assertRegex(reg.tiempo_total_etapa or '', r'^\d+h \d+m$')
        self.assertIsNotNone(reg.consumo_energetico_kwh)

    def test_salida_cierra_solo_el_registro_mas_reciente(self):
        """Complemento del bug de entrada duplicada: con 2 entradas abiertas,
        la salida solo cierra la ultima y la primera queda abierta."""
        login_sesion(self.client, 'op1')
        self.client.post(self.url(), {'accion': 'Entrada', 'lote_id': 'LOT-001'})
        self.client.post(self.url(), {'accion': 'Entrada', 'lote_id': 'LOT-001'})
        self.client.post(self.url(), {'accion': 'Salida', 'lote_id': 'LOT-001'})
        abiertos = RegistroEtapa.objects.filter(
            id_lote=self.lote, id_etapa=self.etapa, hora_salida__isnull=True)
        self.assertEqual(abiertos.count(), 0)  # FAIL actual: queda 1 abierto

    def test_lote_inexistente_muestra_error(self):
        login_sesion(self.client, 'op1')
        r = self.client.post(self.url(), {'accion': 'Entrada', 'lote_id': 'NO-EXISTE'})
        self.assertTrue(any('no encontrado' in m for m in mensajes(r)))

    def test_lote_id_es_case_insensitive(self):
        login_sesion(self.client, 'op1')
        self.client.post(self.url(), {'accion': 'Entrada', 'lote_id': 'lot-001'})
        self.assertTrue(RegistroEtapa.objects.filter(id_lote=self.lote).exists())


class OperarioRedirectTests(TestCase):
    def setUp(self):
        self.etapa = Etapa.objects.create(
            id_etapa='ETP-1', nombre_etapa='Corte', secuencia=1)

    def test_con_etapa_redirige_a_terminal(self):
        crear_usuario('op1', etapa=self.etapa)
        login_sesion(self.client, 'op1')
        r = self.client.get(reverse('core:operario'))
        self.assertRedirects(r, reverse('core:operario_etapa',
                                        kwargs={'etapa_id': 'ETP-1'}))

    def test_sin_etapa_muestra_selector(self):
        crear_usuario('op1', etapa=None)
        login_sesion(self.client, 'op1')
        r = self.client.get(reverse('core:operario'))
        self.assertEqual(r.status_code, 200)
