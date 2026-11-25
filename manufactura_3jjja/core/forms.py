# -*- coding: utf-8 -*-
"""
forms.py - Formularios con Validaciones de Seguridad
Manufacturera de Calzado 3-JJJ-A
"""

import re
from django import forms
from django.core.validators import MinLengthValidator, MaxLengthValidator
from django.core.exceptions import ValidationError
from django.utils.html import strip_tags, escape
from django.contrib.auth.hashers import make_password

from .models import (
    Incidente, Modelo, Material, LoteProduccion,
    Etapa, Maquinaria, Usuario,
    ROL_OPERARIO, ROL_GERENTE, ROL_SUBGERENTE,
    ROL_DIRECTOR_PRODUCCION, ROL_DIRECTOR_DESPACHO,
    TIPO_INCIDENTE_CHOICES, ESTADO_INCIDENTE_CHOICES,
    SEVERIDAD_CHOICES
)

# ============================================================
# HELPER: Validacion reutilizable de contrasenas seguras
# ============================================================
def validar_password_completa(password):
    """Valida que una contrasena cumpla TODOS los requisitos.

    Devuelve None si es valida, o un mensaje de error (str) si no lo es.
    Requisitos:
        - Entre 8 y 12 caracteres
        - Al menos una letra
        - Al menos un numero
        - Al menos un caracter especial
        - No puede ser completamente numerica
    """
    if not password:
        return 'La contrasena es obligatoria.'
    if len(password) < 8:
        return 'La contrasena debe tener al menos 8 caracteres.'
    if len(password) > 12:
        return 'La contrasena no puede exceder 12 caracteres.'
    if password.isdigit():
        return 'La contrasena no puede ser completamente numerica.'
    if not re.search(r'[a-zA-Z]', password):
        return 'La contrasena debe contener al menos una letra.'
    if not re.search(r'[0-9]', password):
        return 'La contrasena debe contener al menos un numero.'
    if not re.search(r'[!@#$%^&*(),.?":{}|<>\[\]\-_=+`~]', password):
        return 'La contrasena debe contener al menos un caracter especial.'
    return None





# ============================================================
# 1. FORMULARIO: REGISTRO DE INCIDENTE
# ============================================================
class IncidenteForm(forms.ModelForm):
    """Formulario para reportar incidentes de produccion."""

    descripcion = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control-dark',
            'rows': 4,
            'placeholder': 'Describa el incidente con el mayor detalle posible...',
            'maxlength': '800',
        }),
        validators=[
            MinLengthValidator(10, 'La descripcion debe tener al menos 10 caracteres.'),
            MaxLengthValidator(800, 'La descripcion no puede exceder 800 caracteres.'),
        ],
        label='Descripcion Detallada',
        help_text='Minimo 10 caracteres, maximo 800.'
    )

    class Meta:
        model = Incidente
        fields = ['tipo_incidente', 'severidad', 'descripcion', 'id_etapa', 'id_lote', 'id_maquina']
        widgets = {
            'tipo_incidente': forms.Select(attrs={'class': 'form-control-dark select-dark'}),
            'severidad': forms.Select(attrs={'class': 'form-control-dark select-dark'}),
            'id_etapa': forms.Select(attrs={'class': 'form-control-dark select-dark'}),
            'id_lote': forms.Select(attrs={'class': 'form-control-dark select-dark'}),
            'id_maquina': forms.Select(attrs={'class': 'form-control-dark select-dark'}),
        }
        labels = {
            'tipo_incidente': 'Tipo de Incidente',
            'severidad': 'Severidad',
            'id_etapa': 'Etapa o Area de Origen',
            'id_lote': 'Lote Relacionado (opcional)',
            'id_maquina': 'Maquina Relacionada (opcional)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['id_etapa'].queryset = Etapa.objects.all()
        self.fields['id_lote'].queryset = LoteProduccion.objects.all()
        self.fields['id_maquina'].queryset = Maquinaria.objects.all()
        self.fields['id_lote'].required = False
        self.fields['id_maquina'].required = False

    def clean_descripcion(self):
        descripcion = self.cleaned_data.get('descripcion', '').strip()
        if not descripcion:
            raise ValidationError('La descripcion es obligatoria.')
        descripcion = strip_tags(descripcion)
        descripcion = escape(descripcion)
        patrones_peligrosos = [
            r"(')|(')|(--)|(#)|(#)",
            r"UNION\s+SELECT", r"INSERT\s+INTO",
            r"DELETE\s+FROM", r"DROP\s+TABLE",
            r"<script", r"javascript:",
        ]
        for patron in patrones_peligrosos:
            if re.search(patron, descripcion, re.IGNORECASE):
                raise ValidationError('El texto contiene caracteres no permitidos por seguridad.')
        if len(descripcion) < 10:
            raise ValidationError('La descripcion debe tener al menos 10 caracteres validos.')
        return descripcion


# ============================================================
# 2. FORMULARIO: ACTUALIZAR ESTADO DE INCIDENTE
# ============================================================
class ActualizarIncidenteForm(forms.ModelForm):
    """Formulario para actualizar estado de incidente."""

    acciones_tomadas = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control-dark',
            'rows': 3,
            'placeholder': 'Describa la solucion aplicada...',
            'maxlength': '600',
        }),
        validators=[MaxLengthValidator(600)],
        label='Acciones Tomadas',
        required=False,
    )

    class Meta:
        model = Incidente
        fields = ['estado', 'acciones_tomadas']
        widgets = {
            'estado': forms.Select(attrs={'class': 'form-control-dark select-dark'}),
        }

    def clean_acciones_tomadas(self):
        notas = self.cleaned_data.get('acciones_tomadas', '').strip()
        if notas:
            notas = strip_tags(notas)
            notas = escape(notas)
            if re.search(r"<script|javascript:|UNION\s+SELECT|DROP\s+TABLE", notas, re.IGNORECASE):
                raise ValidationError('El texto contiene caracteres no permitidos.')
        return notas


# ============================================================
# 3. FORMULARIO: MODELO DE CALZADO (SOLO nombre + imagen, SIN BD extra)
# ============================================================
class ModeloCalzadoForm(forms.ModelForm):
    """
    Formulario para registrar/editar modelos de calzado.
    El campo 'imagen' NO esta en el modelo (no toca la BD).
    Se maneja manualmente en la vista guardando el archivo en media/modelos/.
    """

    imagen = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control-dark',
            'accept': 'image/jpeg,image/png,image/webp'
        })
    )

    class Meta:
        model = Modelo
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control-dark',
                'placeholder': 'Nombre completo del modelo',
                'maxlength': '100',
            }),
        }
        labels = {
            'nombre': 'Nombre del Modelo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['imagen'].required = False

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '').strip()
        if not nombre:
            raise ValidationError('El nombre es obligatorio.')
        nombre = strip_tags(nombre)
        nombre = escape(nombre)
        if not re.match(r"^[\w\s\-'\.áéíóúÁÉÍÓÚñÑ]+$", nombre):
            raise ValidationError('El nombre contiene caracteres no permitidos.')
        return nombre


# ============================================================
# 4. FORMULARIO: BUSQUEDA DE MODELOS
# ============================================================
class BusquedaModeloForm(forms.Form):
    """Formulario simple para buscar modelos en el catalogo."""

    q = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control-dark search-dark',
            'placeholder': 'Buscar por codigo o nombre...',
            'autocomplete': 'off',
        }),
        label=''
    )

    def clean_q(self):
        q = self.cleaned_data.get('q', '').strip()
        if q:
            q = strip_tags(q)
            q = escape(q)
            q = re.sub(r"[^\w\s\-\_áéíóúÁÉÍÓÚñÑ]", '', q)
        return q


# ============================================================
# 5. FORMULARIO: REGISTRO DE USUARIO (Modelo Usuario propio)
# ============================================================
class RegistroUsuarioForm(forms.ModelForm):
    """
    Formulario para registrar nuevos usuarios con el modelo Usuario propio.
    """

    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control-dark',
            'placeholder': 'Contraseña (8 a 12 caracteres)',
            'autocomplete': 'new-password',
            'maxlength': '12',
            'minlength': '8',
        }),
        label='Contraseña',
        validators=[
            MinLengthValidator(8, 'La contraseña debe tener al menos 8 caracteres.'),
            MaxLengthValidator(12, 'La contraseña no puede exceder 12 caracteres.'),
        ]
    )

    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control-dark',
            'placeholder': 'Confirmar contraseña (8 a 12 caracteres)',
            'autocomplete': 'new-password',
            'maxlength': '12',
            'minlength': '8',
        }),
        label='Confirmar Contraseña',
        validators=[
            MinLengthValidator(8, 'La confirmación debe tener al menos 8 caracteres.'),
            MaxLengthValidator(12, 'La confirmación no puede exceder 12 caracteres.'),
        ]
    )

    id_usuario = forms.CharField(
        max_length=50,
        min_length=3,
        widget=forms.TextInput(attrs={
            'class': 'form-control-dark',
            'placeholder': 'Nombre de usuario (ej: juan.perez)',
            'maxlength': '50',
            'minlength': '3',
        }),
        label='Nombre de Usuario',
        validators=[
            MinLengthValidator(3, 'El usuario debe tener al menos 3 caracteres.'),
            MaxLengthValidator(50, 'El usuario no puede exceder 50 caracteres.'),
        ]
    )

    nombre_completo = forms.CharField(
        max_length=150,
        min_length=3,
        widget=forms.TextInput(attrs={
            'class': 'form-control-dark',
            'placeholder': 'Nombres y Apellidos',
            'maxlength': '150',
            'minlength': '3',
        }),
        label='Nombre Completo',
        validators=[
            MinLengthValidator(3, 'El nombre debe tener al menos 3 caracteres.'),
            MaxLengthValidator(150, 'El nombre no puede exceder 150 caracteres.'),
        ]
    )

    ROL_CHOICES_FORM = [
        ('', '--- Seleccione un rol ---'),
        (ROL_OPERARIO, 'Operario de Planta'),
        (ROL_GERENTE, 'Gerente de Planta'),
        (ROL_SUBGERENTE, 'Subgerente de Planta'),
        (ROL_DIRECTOR_PRODUCCION, 'Director de Produccion'),
        (ROL_DIRECTOR_DESPACHO, 'Director de Despacho'),
    ]

    rol = forms.ChoiceField(
        choices=ROL_CHOICES_FORM,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control-dark select-dark'}),
        label='Rol / Cargo en la Empresa',
        help_text='Seleccione el rol que tendra el usuario en el sistema.'
    )

    etapa_asignada = forms.ModelChoiceField(
        queryset=Etapa.objects.all(),
        required=False,
        empty_label='--- Seleccione una etapa ---',
        widget=forms.Select(attrs={'class': 'form-control-dark select-dark'}),
        label='Etapa Asignada (solo para Operarios)',
        help_text='Seleccione la etapa donde trabajara el operario.'
    )

    class Meta:
        model = Usuario
        fields = ['id_usuario', 'nombre_completo', 'rol', 'etapa_asignada']
        labels = {
            'id_usuario': 'Nombre de Usuario',
            'nombre_completo': 'Nombre Completo',
        }

    def clean_id_usuario(self):
        username = self.cleaned_data.get('id_usuario', '').strip().lower()
        if not username:
            raise ValidationError('El nombre de usuario es obligatorio.')
        username = strip_tags(username)
        username = escape(username)
        if re.match(r'^[0-9]+$', username):
            raise ValidationError('El nombre de usuario no puede ser totalmente numérico.')
        if not re.match(r'^[\w.@+-]+$', username):
            raise ValidationError('El usuario solo puede contener letras, numeros y @/./+/-/_.')
        if Usuario.objects.filter(id_usuario=username).exists():
            raise ValidationError('Este nombre de usuario ya esta registrado.')
        return username

    def clean_nombre_completo(self):
        nombre = self.cleaned_data.get('nombre_completo', '').strip()
        if not nombre:
            raise ValidationError('El nombre completo es obligatorio.')
        nombre = strip_tags(nombre)
        nombre = escape(nombre)
        if re.search(r'[0-9]', nombre):
            raise ValidationError('El nombre completo no puede contener numeros. Solo se permiten letras y espacios.')
        if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s\-'\.]+$", nombre):
            raise ValidationError('El nombre solo puede contener letras, espacios, guiones y apostrofos.')
        if len(nombre) < 3:
            raise ValidationError('El nombre debe tener al menos 3 caracteres.')
        return nombre

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1', '')
        p2 = self.cleaned_data.get('password2', '')
        if len(p1) < 8:
            raise ValidationError('La contraseña debe tener al menos 8 caracteres.')
        if len(p1) > 12:
            raise ValidationError('La contraseña no puede exceder 12 caracteres.')
        if p1 != p2:
            raise ValidationError('Las contraseñas no coinciden.')
        if not re.search(r'[a-zA-Z]', p1):
            raise ValidationError('La contraseña debe contener al menos una letra.')
        if not re.search(r'[0-9]', p1):
            raise ValidationError('La contraseña debe contener al menos un número.')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>\[\]\-_=+`~]', p1):
            raise ValidationError('La contraseña debe contener al menos un caracter especial.')
        return p2

    def clean_rol(self):
        rol = self.cleaned_data.get('rol', '')
        if not rol:
            raise ValidationError('Debe seleccionar un rol para el usuario.')
        return rol

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    """Formulario de inicio de sesion simplificado.

    Las validaciones de complejidad de contraseña se realizan al crear o
    actualizar un usuario. En el login NO se valida la complejidad: cualquier
    credencial incorrecta debe llegar a la vista para registrarse como
    intento fallido y aplicar la politica de bloqueo.
    """

    username = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control-dark',
            'placeholder': 'Nombre de usuario',
            'autocomplete': 'username',
            'maxlength': '50',
            'id': 'id_username',
        }),
        label='Usuario',
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control-dark',
            'placeholder': 'Contraseña',
            'autocomplete': 'current-password',
            'maxlength': '12',
            'id': 'id_password',
        }),
        label='Contraseña',
    )

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip().lower()
        if not username:
            raise ValidationError('El nombre de usuario es obligatorio.')
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        if not password:
            raise ValidationError('La contraseña es obligatoria.')
        # IMPORTANTE: sin validacion de complejidad aqui a proposito.
        # Si la credencial es incorrecta, la vista de login se encarga de
        # registrar el intento fallido y aplicar la politica de bloqueo.
        return password


# ============================================================
# 6. FORMULARIO: REGISTRO DE MAQUINARIA
# ============================================================
class MaquinariaForm(forms.ModelForm):
    """Formulario para registrar nuevas maquinarias en el sistema."""

    class Meta:
        model = Maquinaria
        fields = ['id_maquina', 'nombre', 'potencia_kw', 'factor_carga', 'id_etapa']
        widgets = {
            'id_maquina': forms.TextInput(attrs={
                'class': 'form-control-dark',
                'placeholder': 'Ej. maq-corte-01',
                'maxlength': '50',
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control-dark',
                'placeholder': 'Ej. Maquina de Corte CNC',
                'maxlength': '100',
            }),
            'potencia_kw': forms.NumberInput(attrs={
                'class': 'form-control-dark',
                'step': '0.01',
                'placeholder': 'Ej. 15.5',
            }),
            'factor_carga': forms.NumberInput(attrs={
                'class': 'form-control-dark',
                'step': '0.01',
                'placeholder': 'Ej. 0.85',
                'min': '0',
                'max': '1',
            }),
            'id_etapa': forms.Select(attrs={
                'class': 'form-control-dark select-dark',
            }),
        }
        labels = {
            'id_maquina': 'ID de Maquina',
            'nombre': 'Nombre de la Maquina',
            'potencia_kw': 'Potencia (kW)',
            'factor_carga': 'Factor de Carga',
            'id_etapa': 'Etapa Asignada',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['id_etapa'].queryset = Etapa.objects.all().order_by('secuencia')
        self.fields['id_etapa'].empty_label = '--- Seleccione una etapa ---'
        self.fields['id_etapa'].required = True

    def clean_id_maquina(self):
        id_maquina = self.cleaned_data.get('id_maquina', '').strip().upper()
        if not id_maquina:
            raise ValidationError('El ID de la maquina es obligatorio.')
        id_maquina = strip_tags(id_maquina)
        id_maquina = escape(id_maquina)
        if not re.match(r'^[A-Z0-9\-\_]+$', id_maquina):
            raise ValidationError('El ID solo puede contener letras mayusculas, numeros, guiones y guiones bajos.')
        if Maquinaria.objects.filter(id_maquina=id_maquina).exists():
            raise ValidationError('Ya existe una maquina con este ID.')
        return id_maquina

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '').strip()
        if not nombre:
            raise ValidationError('El nombre es obligatorio.')
        nombre = strip_tags(nombre)
        nombre = escape(nombre)
        if not re.match(r"^[\w\s\-'\.áéíóúÁÉÍÓÚñÑ]+$", nombre):
            raise ValidationError('El nombre contiene caracteres no permitidos.')
        return nombre

    def clean_factor_carga(self):
        factor = self.cleaned_data.get('factor_carga')
        if factor is not None and (factor < 0 or factor > 1):
            raise ValidationError('El factor de carga debe estar entre 0 y 1.')
        return factor


# ============================================================
# FORM: CAMBIO DE CONTRASEÑA TEMPORAL
# ============================================================
class CambiarPasswordTemporalForm(forms.Form):
    password1 = forms.CharField(
        label='Nueva Contrasena',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control-dark',
            'placeholder': 'Entre 8 y 12 caracteres',
            'id': 'id_password1',
            'minlength': '8',
            'maxlength': '12',
            'autocomplete': 'new-password',
        }),
        min_length=8,
        max_length=12,
        error_messages={
            'min_length': 'La contrasena debe tener al menos 8 caracteres.',
            'max_length': 'La contrasena no puede exceder 12 caracteres.',
        },
    )
    password2 = forms.CharField(
        label='Confirmar Contrasena',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control-dark',
            'placeholder': 'Repita la contrasena (8 a 12 caracteres)',
            'id': 'id_password2',
            'minlength': '8',
            'maxlength': '12',
            'autocomplete': 'new-password',
        }),
        min_length=8,
        max_length=12,
        error_messages={
            'min_length': 'La confirmacion debe tener al menos 8 caracteres.',
            'max_length': 'La confirmacion no puede exceder 12 caracteres.',
        },
    )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')

        # Validacion completa (letra, numero, especial, no 100% numerica)
        error = validar_password_completa(p1)
        if error:
            raise forms.ValidationError(error)

        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Las contrasenas no coinciden.')

        return cleaned

