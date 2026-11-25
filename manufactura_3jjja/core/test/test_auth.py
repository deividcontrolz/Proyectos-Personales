# -*- coding: utf-8 -*-
"""
Tests de autenticacion: login, logout, password temporal, intentos fallidos,
registro de usuarios.

Requisitos para correr:
    python manage.py test core.tests.test_auth

Nota: los helpers de contrasena temporal e intentos fallidos guardan su
estado en MEDIA_ROOT/sistema/*.json. En estos tests MEDIA_ROOT se redirige
a un directorio temporal para no tocar datos reales.
"""
import json
import shutil
import tempfile

from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.messages import get_messages
from django.utils import timezone

from core import views
from core.models import Usuario, Etapa, ROL_OPERARIO, ROL_GERENTE


def mensajes(response):
    """Extrae los mensajes flash de una respuesta del test client."""
    return [str(m) for m in get_messages(response.wsgi_request)]


def crear_usuario(pk='op1', rol=ROL_OPERARIO, etapa=None, staff=False,
                  password='clave1234', activo=True):
    u = Usuario(id_usuario=pk, nombre_completo='Usuario ' + pk, rol=rol,
                etapa_asignada=etapa, is_staff=staff, is_active=activo)
    u.set_password(password)
    u.save()
    return u


def login_sesion(client, pk):
    """Autentica usando la sesion propia del sistema (SESSION_KEY)."""
    s = client.session
    s[views.SESSION_KEY] = pk
    s.save()


class MediaTempMixin:
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def setUp(self):
        super().setUp()
        self._ovr = override_settings(MEDIA_ROOT=self.tmpdir)
        self._ovr.enable()
        self.addCleanup(self._ovr.disable)


# ---------------------------------------------------------------
# 1. Helpers JSON de contrasena temporal
# ---------------------------------------------------------------
class PasswordTemporalJSONTests(MediaTempMixin, TestCase):
    def test_marcar_y_verificar(self):
        views.marcar_password_temporal('op1')
        self.assertTrue(views.tiene_password_temporal('op1'))
        self.assertFalse(views.tiene_password_temporal('otro'))

    def test_quitar_marca(self):
        views.marcar_password_temporal('op1')
        views.quitar_password_temporal('op1')
        self.assertFalse(views.tiene_password_temporal('op1'))

    def test_marcar_dos_veces_no_duplica(self):
        views.marcar_password_temporal('op1')
        views.marcar_password_temporal('op1')
        with open(views._ruta_archivo_temporales(), encoding='utf-8') as f:
            data = json.load(f)
        self.assertEqual(data, ['op1'])

    def test_archivo_corrupto_devuelve_lista_vacia(self):
        ruta = views._ruta_archivo_temporales()
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write('{json invalido')
        self.assertEqual(views._cargar_temporales(), [])


# ---------------------------------------------------------------
# 2. Politica de intentos fallidos
# ---------------------------------------------------------------
class IntentosFallidosTests(MediaTempMixin, TestCase):
    def test_admin_se_suspende_al_tercer_intento_y_reinicia(self):
        for _ in range(3):
            info = views.registrar_intento_fallido('admin1', es_admin=True)
        bloqueado, motivo, minutos = views.esta_bloqueado('admin1')
        self.assertTrue(bloqueado)
        self.assertEqual(motivo, 'temporal')
        self.assertGreater(minutos, 0)
        self.assertEqual(info['intentos'], 0)  # el admin SI reinicia

    def test_usuario_queda_bloqueado_permanente_al_quinto(self):
        for _ in range(5):
            views.registrar_intento_fallido('op1', es_admin=False)
        bloqueado, motivo, _ = views.esta_bloqueado('op1')
        self.assertTrue(bloqueado)
        self.assertEqual(motivo, 'permanente')

    def test_usuario_NO_reinicia_intentos_tras_suspension(self):
        """BUG DOCUMENTADO: a diferencia del admin, el usuario normal conserva
        'intentos=3' tras la suspension, asi que solo le quedan 2 intentos
        mas antes del bloqueo permanente (comportamiento inconsistente)."""
        info = None
        for _ in range(3):
            info = views.registrar_intento_fallido('op1', es_admin=False)
        self.assertIsNotNone(info['bloqueado_hasta'])
        self.assertEqual(info['intentos'], 3)  # <- debio reiniciarse a 0

    def test_desbloquear(self):
        views.registrar_intento_fallido('op1')
        self.assertTrue(views.desbloquear_usuario('op1'))
        self.assertFalse(views.esta_bloqueado('op1')[0])
        self.assertFalse(views.desbloquear_usuario('op1'))  # ya no habia nada

    def test_login_exitoso_limpia_intentos(self):
        views.registrar_intento_fallido('op1')
        views.limpiar_intentos('op1')
        self.assertEqual(views.get_info_intentos('op1')['intentos'], 0)


# ---------------------------------------------------------------
# 3. Vista de login
# ---------------------------------------------------------------
class LoginViewTests(MediaTempMixin, TestCase):
    def setUp(self):
        super().setUp()
        crear_usuario('op1', password='clave1234')

    def test_get_muestra_login(self):
        r = self.client.get(reverse('core:login'))
        self.assertEqual(r.status_code, 200)

    def test_usuario_inexistente(self):
        r = self.client.post(reverse('core:login'),
                             {'username': 'nadie', 'password': 'x'})
        self.assertEqual(r.status_code, 200)
        self.assertIn('USUARIO INEXISTENTE.', mensajes(r))

    def test_password_incorrecta_registra_intento(self):
        r = self.client.post(reverse('core:login'),
                             {'username': 'op1', 'password': 'incorrecta'})
        self.assertIn('CONTRASEÑA INCORRECTA.', mensajes(r))
        self.assertEqual(views.get_info_intentos('op1')['intentos'], 1)

    def test_login_exitoso_crea_sesion_y_redirige(self):
        r = self.client.post(reverse('core:login'),
                             {'username': 'op1', 'password': 'clave1234'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.client.session.get(views.SESSION_KEY), 'op1')

    def test_login_con_password_temporal_redirige_a_cambio(self):
        views.marcar_password_temporal('op1')
        r = self.client.post(reverse('core:login'),
                             {'username': 'op1', 'password': 'clave1234'})
        self.assertRedirects(r, reverse('core:cambiar_password_temporal'))

    def test_login_bloqueado_permanente_rechaza(self):
        for _ in range(5):
            views.registrar_intento_fallido('op1')
        r = self.client.post(reverse('core:login'),
                             {'username': 'op1', 'password': 'clave1234'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(any('BLOQUEADA' in m for m in mensajes(r)))

    def test_login_exitoso_limpia_intentos_previos(self):
        views.registrar_intento_fallido('op1')
        self.client.post(reverse('core:login'),
                         {'username': 'op1', 'password': 'clave1234'})
        self.assertEqual(views.get_info_intentos('op1')['intentos'], 0)

    def test_usuario_inactivo_cuenta_como_password_incorrecta(self):
        """COMPORTAMIENTO DOCUMENTADO: un usuario inactivo suma intento fallido
        y muestra 'CONTRASEÑA INCORRECTA.' en vez de avisar que esta inactivo."""
        crear_usuario('inact', password='clave1234', activo=False)
        r = self.client.post(reverse('core:login'),
                             {'username': 'inact', 'password': 'clave1234'})
        self.assertIn('CONTRASEÑA INCORRECTA.', mensajes(r))
        self.assertEqual(views.get_info_intentos('inact')['intentos'], 1)


# ---------------------------------------------------------------
# 4. Logout
# ---------------------------------------------------------------
class LogoutViewTests(MediaTempMixin, TestCase):
    def test_logout_borra_sesion(self):
        crear_usuario('op1')
        login_sesion(self.client, 'op1')
        r = self.client.get(reverse('core:logout'))
        self.assertRedirects(r, reverse('core:login'))
        self.assertIsNone(self.client.session.get(views.SESSION_KEY))


# ---------------------------------------------------------------
# 5. Cambio obligatorio de contrasena temporal
# ---------------------------------------------------------------
class CambiarPasswordTemporalTests(MediaTempMixin, TestCase):
    def setUp(self):
        super().setUp()
        crear_usuario('op1', password='temporal1')

    def test_sin_sesion_redirige_a_login(self):
        r = self.client.get(reverse('core:cambiar_password_temporal'))
        self.assertRedirects(r, reverse('core:login'))

    def test_sin_password_temporal_redirige_al_sistema(self):
        login_sesion(self.client, 'op1')
        r = self.client.get(reverse('core:cambiar_password_temporal'))
        self.assertEqual(r.status_code, 302)
        self.assertNotEqual(r.url, reverse('core:cambiar_password_temporal'))

    def test_cambio_exitoso(self):
        views.marcar_password_temporal('op1')
        login_sesion(self.client, 'op1')
        r = self.client.post(reverse('core:cambiar_password_temporal'), {
            'password1': 'NuevaPass123!',
            'password2': 'NuevaPass123!',
        })
        self.assertEqual(r.status_code, 302)
        op1 = Usuario.objects.get(id_usuario='op1')
        self.assertTrue(op1.check_password('NuevaPass123!'))
        self.assertFalse(views.tiene_password_temporal('op1'))

    def test_passwords_no_coinciden(self):
        views.marcar_password_temporal('op1')
        login_sesion(self.client, 'op1')
        r = self.client.post(reverse('core:cambiar_password_temporal'), {
            'password1': 'NuevaPass123!',
            'password2': 'OtraDistinta1!',
        })
        self.assertEqual(r.status_code, 200)
        op1 = Usuario.objects.get(id_usuario='op1')
        self.assertTrue(op1.check_password('temporal1'))  # no cambio


# ---------------------------------------------------------------
# 6. Redireccion por rol
# ---------------------------------------------------------------
class RedirectPorRolTests(MediaTempMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.etapa = Etapa.objects.create(
            id_etapa='ETP-1', nombre_etapa='Corte', secuencia=1)

    def test_operario_con_etapa_va_a_su_terminal(self):
        crear_usuario('op1', rol=ROL_OPERARIO, etapa=self.etapa)
        login_sesion(self.client, 'op1')
        r = self.client.get(reverse('core:redirect_por_rol'))
        self.assertRedirects(
            r, reverse('core:operario_etapa', kwargs={'etapa_id': 'ETP-1'}))

    def test_operario_sin_etapa_va_a_seleccion(self):
        crear_usuario('op1', rol=ROL_OPERARIO, etapa=None)
        login_sesion(self.client, 'op1')
        r = self.client.get(reverse('core:redirect_por_rol'))
        self.assertRedirects(r, reverse('core:operario'))

    def test_gerente_va_al_dashboard(self):
        crear_usuario('g1', rol=ROL_GERENTE)
        login_sesion(self.client, 'g1')
        r = self.client.get(reverse('core:redirect_por_rol'))
        self.assertRedirects(r, reverse('core:dashboard'))

    def test_sin_sesion_redirige_a_login(self):
        r = self.client.get(reverse('core:redirect_por_rol'))
        self.assertRedirects(r, reverse('core:login'))


# ---------------------------------------------------------------
# 7. Registro de usuario
# ---------------------------------------------------------------
class RegistroViewTests(MediaTempMixin, TestCase):
    def _data(self, **over):
        base = {
            'id_usuario': 'nuevo1',
            'nombre_completo': 'Usuario Nuevo',
            'rol': ROL_OPERARIO,
            'etapa_asignada': '',
            'password1': 'temporal1',
            'password': 'temporal1',
        }
        base.update(over)
        return base

    def test_get_muestra_formulario(self):
        r = self.client.get(reverse('core:registro'))
        self.assertEqual(r.status_code, 200)

    def test_registro_exitoso_anonimo_redirige_a_login(self):
        """COMPORTAMIENTO DOCUMENTADO: cualquiera puede autoregistrarse
        (ver posible hueco de seguridad #5 en el analisis)."""
        r = self.client.post(reverse('core:registro'), self._data())
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Usuario.objects.filter(id_usuario='nuevo1').exists())

    def test_registro_por_admin_marca_password_temporal(self):
        crear_usuario('admin1', rol=ROL_GERENTE, staff=True)
        login_sesion(self.client, 'admin1')
        r = self.client.post(reverse('core:registro'), self._data())
        self.assertRedirects(r, reverse('core:admin_usuarios'))
        self.assertTrue(views.tiene_password_temporal('nuevo1'))

    def test_registro_duplicado_falla(self):
        crear_usuario('nuevo1')
        r = self.client.post(reverse('core:registro'), self._data())
        self.assertEqual(r.status_code, 200)  # re-renderiza con errores
        self.assertEqual(
            Usuario.objects.filter(id_usuario='nuevo1').count(), 1)
