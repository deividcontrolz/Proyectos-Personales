#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aplicar_fix_iconos.py
=====================
Aplica la solución completa de iconos SVG inline en los templates
admin_usuarios.html y cambiar_password_temporal.html, y crea los
archivos CSS/JS externos correspondientes.

Qué hace:
  1) Crea 4 archivos NUEVOS en static/css/ y static/js/:
        - static/css/admin_usuarios.css
        - static/js/admin_usuarios.js
        - static/css/cambiar_password_temporal.css
        - static/js/cambiar_password_temporal.js
  2) Reemplaza los 2 templates:
        - templates/admin_usuarios.html          (o donde estén)
        - templates/cambiar_password_temporal.html
  3) Hace BACKUP con timestamp de cada archivo antes de tocarlo.
  4) NUNCA toca archivos que parezcan LOG (.log, _log, -log, etc).
  5) Si los archivos nuevos ya existen, hace backup y los sobreescribe.

USO:
    cd /ruta/a/la/raiz/del/proyecto      (donde está manage.py)
    python aplicar_fix_iconos.py
"""

import os
import sys
import shutil
from datetime import datetime
from pathlib import Path

# ============================================================
# CONFIGURACIÓN
# ============================================================
STAMP = datetime.now().strftime('%Y%m%d_%H%M%S')

LOG_MARKERS = ('.log', '_log', '-log', '.access', '.error', 'debug.log')

SKIP_DIRS = {
    '.git', '.hg', '.svn', 'node_modules', '__pycache__',
    '.venv', 'venv', 'env', '.env', '.idea', '.vscode',
    'media', 'migrations', 'staticfiles',
}

# Nombres exactos de los templates a reemplazar
TEMPLATE_NAMES = ('admin_usuarios.html', 'cambiar_password_temporal.html')

# ============================================================
# CONTENIDO DE LOS ARCHIVOS
# ============================================================

CSS_ADMIN_USUARIOS = r'''/* ============================================================
   admin_usuarios.css
   Estilos del modal "Cambiar contraseña" y del modal eliminar
   ============================================================ */

/* --- Campo de contraseña con botón de ojo --- */
.input-icon-wrap.password-with-eye {
    position: relative;
}

.input-icon-wrap.password-with-eye .form-control-dark {
    padding-right: 44px !important;
}

.toggle-password-eye {
    position: absolute !important;
    right: 10px !important;
    left: auto !important;
    top: 50% !important;
    transform: translateY(-50%) !important;
    background: transparent !important;
    border: none !important;
    color: #94a3b8 !important;
    cursor: pointer !important;
    padding: 4px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 28px;
    height: 28px;
    z-index: 5 !important;
    transition: color 0.2s ease;
}

.toggle-password-eye:hover { color: #10b981 !important; }
.toggle-password-eye:focus { outline: none !important; }
.toggle-password-eye svg { display: block; pointer-events: none; }

/* Neutraliza la regla '.input-icon-wrap i' que posicionaba <i> a la izquierda */
.input-icon-wrap .toggle-password-eye svg {
    position: static !important;
    left: auto !important;
    top: auto !important;
    transform: none !important;
    color: inherit !important;
}

/* --- Espaciado para iconos SVG inline junto a texto --- */
.btn-back svg,
.btn-filter svg,
.action-btn svg,
.btn-modal-primary svg,
.btn-modal-secondary svg,
.btn-del-cancel svg,
.btn-del-confirm svg {
    flex-shrink: 0;
    vertical-align: -0.125em;
}

.action-btn svg { vertical-align: middle; }

.btn-back,
.btn-filter,
.btn-modal-primary,
.btn-modal-secondary,
.btn-del-cancel,
.btn-del-confirm {
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

/* --- Mensajes de error del modal --- */
.error-msg {
    display: none;
    align-items: center;
    gap: 6px;
    color: #f87171;
    font-size: 0.8rem;
    margin-top: 6px;
}

.error-msg.visible { display: flex; }

.match-indicator {
    display: flex;
    align-items: center;
    gap: 6px;
}
'''

JS_ADMIN_USUARIOS = r'''/* ============================================================
   admin_usuarios.js
   Lógica del modal de cambio de contraseña
   ============================================================ */

/* ============================================================
   TOGGLE OJO: mostrar / ocultar contraseña
   ============================================================ */
function togglePasswordEye(inputId, btn) {
    var input = document.getElementById(inputId);
    if (!input) return;
    var offIcon = btn.querySelector('.eye-off');
    var onIcon  = btn.querySelector('.eye-on');
    if (input.type === 'password') {
        input.type = 'text';
        if (offIcon) offIcon.style.display = 'none';
        if (onIcon)  onIcon.style.display  = 'block';
    } else {
        input.type = 'password';
        if (offIcon) offIcon.style.display = 'block';
        if (onIcon)  onIcon.style.display  = 'none';
    }
}

/* ============================================================
   Reset del ojo al cerrar el modal (envuelve cerrarModalPassword
   sin romperla, porque app.js la define al cargar el documento)
   ============================================================ */
(function () {
    var timer = setInterval(function () {
        if (typeof window.cerrarModalPassword === 'function' && !window.__ojoFix) {
            window.__ojoFix = true;
            var _orig = window.cerrarModalPassword;
            window.cerrarModalPassword = function () {
                try { _orig(); } catch (e) {}
                ['nueva_password', 'confirmar_password'].forEach(function (id) {
                    var inp = document.getElementById(id);
                    if (inp) inp.type = 'password';
                });
                document.querySelectorAll('.toggle-password-eye').forEach(function (b) {
                    var off = b.querySelector('.eye-off');
                    var on  = b.querySelector('.eye-on');
                    if (off) off.style.display = 'block';
                    if (on)  on.style.display  = 'none';
                });
            };
            clearInterval(timer);
        }
    }, 100);
    setTimeout(function () { clearInterval(timer); }, 5000);
})();
'''

CSS_CAMBIAR_PWD = r'''/* ============================================================
   cambiar_password_temporal.css
   Estilos de la pantalla de cambio de contraseña obligatorio
   ============================================================ */

* { margin: 0; padding: 0; box-sizing: border-box; }

html, body {
    height: 100%;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    overflow: hidden;
}

.page-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100vh;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
    position: relative;
}

.page-wrapper::before {
    content: '';
    position: absolute;
    top: 50%; left: 0;
    width: 100%; height: 50%;
    background: linear-gradient(180deg,
        rgba(16,185,129,0.0) 0%,
        rgba(16,185,129,0.05) 15%,
        rgba(5,150,105,0.12) 40%,
        rgba(4,120,87,0.20) 65%,
        rgba(6,78,59,0.28) 100%);
    pointer-events: none;
}

.login-card {
    position: relative;
    width: 100%;
    max-width: 420px;
    background: rgba(30, 41, 59, 0.95);
    border: 1px solid rgba(16, 185, 129, 0.15);
    border-radius: 24px;
    padding: 40px 36px;
    box-shadow: 0 12px 40px rgba(0,0,0,0.3),
                0 4px 12px rgba(0,0,0,0.15);
    backdrop-filter: blur(10px);
    z-index: 1;
}

.login-header { text-align: center; margin-bottom: 24px; }

.login-logo {
    width: 60px; height: 60px;
    margin: 0 auto 16px;
    background: linear-gradient(135deg, #f59e0b, #d97706);
    border-radius: 16px;
    display: flex; align-items: center; justify-content: center;
    color: white;
    box-shadow: 0 4px 15px rgba(245, 158, 11, 0.35);
}
.login-logo svg { width: 30px; height: 30px; }

.login-header h1 {
    color: #f1f5f9;
    font-size: 1.2rem;
    margin: 0 0 6px 0;
    font-weight: 700;
}
.login-header p {
    color: #94a3b8;
    font-size: 0.82rem;
    margin: 0;
}

.info-box {
    background: rgba(245, 158, 11, 0.12);
    border: 1px solid rgba(245, 158, 11, 0.3);
    color: #fbbf24;
    padding: 12px 14px;
    border-radius: 12px;
    font-size: 0.82rem;
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 20px;
    line-height: 1.4;
}
.info-box svg {
    width: 1.1rem;
    height: 1.1rem;
    flex-shrink: 0;
    margin-top: 2px;
}

.form-group { margin-bottom: 18px; }

.form-group label {
    display: block;
    color: #cbd5e1;
    font-size: 0.78rem;
    font-weight: 600;
    margin-bottom: 7px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.form-control-dark {
    width: 100%;
    padding: 12px 44px 12px 16px;
    background: rgba(15, 23, 42, 0.8);
    border: 1.5px solid rgba(100, 116, 139, 0.3);
    border-radius: 12px;
    color: #f1f5f9;
    font-size: 0.9rem;
    transition: all 0.25s ease;
}
.form-control-dark:focus {
    outline: none;
    border-color: #10b981;
    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15);
    background: rgba(15, 23, 42, 0.95);
}
.form-control-dark::placeholder { color: #64748b; }

.password-input-wrapper {
    position: relative;
    display: flex;
    align-items: center;
    width: 100%;
}

.toggle-password-btn {
    position: absolute;
    right: 12px;
    background: transparent;
    border: none;
    color: #94a3b8;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 4px;
    transition: color 0.2s ease;
    z-index: 2;
}
.toggle-password-btn svg { width: 20px; height: 20px; display: block; }
.toggle-password-btn:hover { color: #10b981; }
.toggle-password-btn .eye-open { display: none; }

.btn-login {
    width: 100%;
    padding: 13px;
    background: linear-gradient(135deg, #10b981, #059669);
    border: none;
    border-radius: 12px;
    color: white;
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    margin-top: 8px;
    letter-spacing: 0.5px;
}
.btn-login svg { width: 1.1em; height: 1.1em; }
.btn-login:hover {
    background: linear-gradient(135deg, #059669, #047857);
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(16, 185, 129, 0.3);
}

.messages-container { margin-bottom: 18px; }

.alert {
    padding: 10px 14px;
    border-radius: 10px;
    font-size: 0.85rem;
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
}
.alert svg { width: 1em; height: 1em; flex-shrink: 0; }

.alert-success {
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.3);
    color: #34d399;
}
.alert-error, .alert-info {
    background: rgba(239, 68, 68, 0.15);
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #f87171;
}
.alert-warning {
    background: rgba(245, 158, 11, 0.15);
    border: 1px solid rgba(245, 158, 11, 0.3);
    color: #fbbf24;
}

.fade-in { animation: fadeIn 0.4s ease; }
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(-8px); }
    to   { opacity: 1; transform: translateY(0); }
}
'''

JS_CAMBIAR_PWD = r'''/* ============================================================
   cambiar_password_temporal.js
   Mostrar / ocultar contraseña con SVG inline
   ============================================================ */

function togglePass(id, btn) {
    var input = document.getElementById(id);
    if (!input) return;
    var closed = btn.querySelector('.eye-closed');
    var open   = btn.querySelector('.eye-open');
    if (input.type === 'password') {
        input.type = 'text';
        if (closed) closed.style.display = 'none';
        if (open)   open.style.display = 'block';
    } else {
        input.type = 'password';
        if (closed) closed.style.display = 'block';
        if (open)   open.style.display = 'none';
    }
}
'''

# ============================================================
# SVG PATHS REUTILIZABLES (evitan repetir 40 veces la misma ruta)
# ============================================================
SVG_PEOPLE = '<path d="M15 14s1 0 1-1-1-4-5-4-5 3-5 4 1 1 1 1zm-7.978-1L7 12.996c.001-.264.167-1.03.76-1.72C8.312 10.629 9.282 10 11 10c1.717 0 2.687.63 3.24 1.276.593.69.758 1.457.76 1.72l-.008.002-.014.002zM11 7a2 2 0 1 0 0-4 2 2 0 0 0 0 4m3-2a3 3 0 1 1-6 0 3 3 0 0 1 6 0M6.936 9.28a6 6 0 0 0-1.23-.247A7 7 0 0 0 5 9c-4 0-5 3-5 4q0 1 1 1h4.216A2.24 2.24 0 0 1 5 13c0-1.01.377-2.042 1.09-2.904.243-.294.526-.569.846-.816M4.92 10A5.5 5.5 0 0 0 4 13H1c0-.26.164-1.03.76-1.724.545-.636 1.492-1.256 3.16-1.275ZM1.5 5.5a3 3 0 1 1 6 0 3 3 0 0 1-6 0m3-2a2 2 0 1 0 0 4 2 2 0 0 0 0-4"/>'
SVG_ARROW_LEFT = '<path fill-rule="evenodd" d="M15 8a.5.5 0 0 0-.5-.5H2.707l3.147-3.146a.5.5 0 1 0-.708-.708l-4 4a.5.5 0 0 0 0 .708l4 4a.5.5 0 0 0 .708-.708L2.707 8.5H14.5A.5.5 0 0 0 15 8"/>'
SVG_FUNNEL = '<path d="M1.5 1.5A.5.5 0 0 1 2 1h12a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-.128.334L10 8.692V13.5a.5.5 0 0 1-.342.474l-3 1A.5.5 0 0 1 6 14.5V8.692L1.628 3.834A.5.5 0 0 1 1.5 3.5zm1 .5v1.308l4.372 4.858A.5.5 0 0 1 7 8.5v5.306l2-.666V8.5a.5.5 0 0 1 .128-.334L13.5 3.308V2z"/>'
SVG_X_CIRCLE = '<path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16"/><path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708"/>'
SVG_LOCK_FILL = '<path d="M8 1a2 2 0 0 1 2 2v4H6V3a2 2 0 0 1 2-2m3 6V3a3 3 0 0 0-6 0v4a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2"/>'
SVG_TOGGLE_ON = '<path d="M5 3a5 5 0 0 0 0 10h6a5 5 0 0 0 0-10zm6 9a4 4 0 1 1 0-8 4 4 0 0 1 0 8"/>'
SVG_CHECK_CIRCLE = '<path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16"/><path d="m10.97 4.97-.02.022-3.473 4.425-2.093-2.094a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-1.071-1.05"/>'
SVG_X_OCTAGON = '<path d="M4.54.146A.5.5 0 0 1 4.893 0h6.214a.5.5 0 0 1 .353.146l4.394 4.394a.5.5 0 0 1 .146.353v6.214a.5.5 0 0 1-.146.353l-4.394 4.394a.5.5 0 0 1-.353.146H4.893a.5.5 0 0 1-.353-.146L.146 11.46A.5.5 0 0 1 0 11.107V4.893a.5.5 0 0 1 .146-.353zM5.1 1 1 5.1v5.8L5.1 15h5.8l4.1-4.1V5.1L10.9 1z"/><path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708"/>'
SVG_KEY = '<path d="M0 8a4 4 0 0 1 7.465-2H14a.5.5 0 0 1 .354.146l1.5 1.5a.5.5 0 0 1 0 .708l-1.5 1.5a.5.5 0 0 1-.708 0L13 9.207l-.646.647a.5.5 0 0 1-.708 0L11 9.207l-.646.647a.5.5 0 0 1-.708 0L9 9.207l-.646.647A.5.5 0 0 1 8 10h-.535A4 4 0 0 1 0 8m4-3a3 3 0 1 0 2.712 4.285A.5.5 0 0 1 7.163 9h.63l.853-.854a.5.5 0 0 1 .708 0l.646.647.646-.647a.5.5 0 0 1 .708 0l.646.647.646-.647a.5.5 0 0 1 .708 0l.646.647.793-.793-1-1h-6.63a.5.5 0 0 1-.451-.285A3 3 0 0 0 4 5"/><path d="M4 8a1 1 0 1 1-2 0 1 1 0 0 1 2 0"/>'
SVG_UNLOCK_FILL = '<path d="M11 1a2 2 0 0 0-2 2v4a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h5V3a3 3 0 0 1 6 0v4a.5.5 0 0 1-1 0V3a2 2 0 0 0-2-2"/>'
SVG_INBOX = '<path d="M4.98 4a.5.5 0 0 0-.39.188L1.54 8H6a.5.5 0 0 1 .5.5 1.5 1.5 0 1 0 3 0A.5.5 0 0 1 10 8h4.46l-3.05-3.812A.5.5 0 0 0 11.02 4zm9.954 5H10.45a2.5 2.5 0 0 1-4.9 0H1.066l.32 2.562a.5.5 0 0 0 .497.438h12.234a.5.5 0 0 0 .496-.438zM3.809 3.563A1.5 1.5 0 0 1 4.981 3h6.038a1.5 1.5 0 0 1 1.172.563l3.7 4.625a.5.5 0 0 1 .105.374l-.39 3.124A1.5 1.5 0 0 1 14.117 13H1.883a1.5 1.5 0 0 1-1.489-1.314l-.39-3.124a.5.5 0 0 1 .106-.374z"/>'
SVG_SHIELD_LOCK = '<path d="M5.338 1.59a61 61 0 0 0-2.837.856.48.48 0 0 0-.328.39c-.554 4.157.726 7.19 2.253 9.188a10.7 10.7 0 0 0 2.287 2.233c.346.244.652.42.893.533q.18.085.293.118a1 1 0 0 0 .101.025 1 1 0 0 0 .1-.025q.114-.034.294-.118c.24-.113.547-.29.893-.533a10.7 10.7 0 0 0 2.287-2.233c1.527-1.997 2.807-5.031 2.253-9.188a.48.48 0 0 0-.328-.39c-.651-.213-1.75-.56-2.837-.855C9.552 1.29 8.531 1.067 8 1.067c-.53 0-1.552.223-2.662.524zM5.072.56C6.157.265 7.31 0 8 0s1.843.265 2.928.56c1.11.3 2.229.655 2.887.87a1.54 1.54 0 0 1 1.044 1.262c.596 4.477-.787 7.795-2.465 9.99a11.8 11.8 0 0 1-2.517 2.453 7 7 0 0 1-1.048.625c-.28.132-.581.24-.829.24s-.548-.108-.829-.24a7 7 0 0 1-1.048-.625 11.8 11.8 0 0 1-2.517-2.453C1.928 10.487.545 7.169 1.141 2.692A1.54 1.54 0 0 1 2.185 1.43 63 63 0 0 1 5.072.56"/><path d="M9.5 6.5a1.5 1.5 0 0 1-1 1.415l.385 1.99a.5.5 0 0 1-.491.595h-.788a.5.5 0 0 1-.49-.595l.384-1.99a1.5 1.5 0 1 1 2-1.415"/>'
SVG_INFO_CIRCLE = '<path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16"/><path d="m8.93 6.588-2.29.287-.082.38.45.083c.294.07.352.176.288.469l-.738 3.468c-.194.897.105 1.319.808 1.319.545 0 1.178-.252 1.465-.598l.088-.416c-.2.176-.492.246-.686.246-.275 0-.375-.193-.304-.533zM9 4.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0"/>'
SVG_EXCLAMATION_CIRCLE = '<path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16"/><path d="M7.002 11a1 1 0 1 1 2 0 1 1 0 0 1-2 0M7.1 4.995a.905.905 0 1 1 1.8 0l-.35 3.507a.552.552 0 0 1-1.1 0z"/>'
SVG_X_LG = '<path d="M2.146 2.854a.5.5 0 1 1 .708-.708L8 7.293l5.146-5.147a.5.5 0 0 1 .708.708L8.707 8l5.147 5.146a.5.5 0 0 1-.708.708L8 8.707l-5.146 5.147a.5.5 0 0 1-.708-.708L7.293 8z"/>'
SVG_CHECK_LG = '<path d="M12.736 3.97a.733.733 0 0 1 1.047 0c.286.289.29.756.01 1.05L7.88 12.01a.733.733 0 0 1-1.065.02L3.217 8.384a.757.757 0 0 1 0-1.06.733.733 0 0 1 1.047 0l3.052 3.093 5.4-6.425z"/>'
SVG_EXCLAMATION_TRIANGLE = '<path d="M7.938 2.016A.13.13 0 0 1 8.002 2a.13.13 0 0 1 .063.016.15.15 0 0 1 .054.057l6.857 11.667c.036.06.035.124.002.183a.2.2 0 0 1-.054.06.1.1 0 0 1-.066.017H1.146a.1.1 0 0 1-.066-.017.2.2 0 0 1-.054-.06.18.18 0 0 1 .002-.183L7.884 2.073a.15.15 0 0 1 .054-.057m1.044-.45a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767z"/><path d="M7.002 12a1 1 0 1 1 2 0 1 1 0 0 1-2 0M7.1 5.995a.905.905 0 1 1 1.8 0l-.35 3.507a.552.552 0 0 1-1.1 0z"/>'
SVG_EYE_OFF = '<path d="M13.359 11.238C15.06 9.72 16 8 16 8s-3-5.5-8-5.5a7 7 0 0 0-2.79.588l.77.771A6 6 0 0 1 8 3.5c2.12 0 3.879 1.168 5.168 2.457A13 13 0 0 1 14.828 8q-.086.13-.195.288c-.335.48-.83 1.12-1.465 1.755q-.27.275-.57.535zM11.297 9.176a3.5 3.5 0 0 0-4.474-4.474l.823.823a2.5 2.5 0 0 1 2.829 2.829zm-2.943 1.299.822.822a3.5 3.5 0 0 1-4.474-4.474l.823.823a2.5 2.5 0 0 0 2.829 2.829"/><path d="M3.35 5.47q-.27.24-.518.487A13 13 0 0 0 1.172 8l.195.288c.335.48.83 1.12 1.465 1.755C4.121 11.332 5.881 12.5 8 12.5c.716 0 1.39-.133 2.02-.36l.77.772A7 7 0 0 1 8 13.5C3 13.5 0 8 0 8s.939-1.721 2.641-3.238l.708.709zm10.296 8.884-12-12 .708-.708 12 12z"/>'
SVG_EYE_ON = '<path d="M16 8s-3-5.5-8-5.5S0 8 0 8s3 5.5 8 5.5S16 8 16 8M1.173 8a13 13 0 0 1 1.66-2.043C4.12 4.668 5.88 3.5 8 3.5s3.879 1.168 5.168 2.457A13 13 0 0 1 14.828 8q-.086.13-.195.288c-.335.48-.83 1.12-1.465 1.755C11.879 11.332 10.119 12.5 8 12.5s-3.879-1.168-5.168-2.457A13 13 0 0 1 1.172 8z"/><path d="M8 5.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5M4.5 8a3.5 3.5 0 1 1 7 0 3.5 3.5 0 0 1-7 0"/>'

def svg(path, w='1em', h='1em', extra=''):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'fill="currentColor" viewBox="0 0 16 16" {extra} aria-hidden="true">'
            f'{path}</svg>')

# ============================================================
# TEMPLATE: admin_usuarios.html
# ============================================================
TEMPLATE_ADMIN_USUARIOS = (
    "{% extends 'base.html' %}\n"
    "{% load static %}\n"
    "\n"
    "{% block title %}Gestionar Usuarios - 3-JJJ-A{% endblock %}\n"
    "\n"
    "{% block page_title %}Gestionar Usuarios{% endblock %}\n"
    "\n"
    "{% block content %}\n"
    "<!-- CSS específico de esta página -->\n"
    "<link rel=\"stylesheet\" href=\"{% static 'css/admin_usuarios.css' %}\">\n"
    "\n"
    "<div class=\"admin-container\">\n"
    "    <!-- Header -->\n"
    "    <div class=\"admin-header\">\n"
    "        <div>\n"
    "            <h1>\n"
    f"                {svg(SVG_PEOPLE, extra='style=\"vertical-align:-0.125em;\"')}\n"
    "                Gestionar Usuarios\n"
    "            </h1>\n"
    "            <p style=\"color: #94a3b8; margin: 4px 0 0 0; font-size: 0.85rem;\">\n"
    "                Total: {{ total_usuarios }} usuarios | {{ usuario.nombre_completo }}\n"
    "            </p>\n"
    "        </div>\n"
    "        <a href=\"{% url 'core:panel_admin' %}\" class=\"btn-back\">\n"
    f"            {svg(SVG_ARROW_LEFT, extra='style=\"vertical-align:-0.125em;\"')}\n"
    "            Volver al Panel\n"
    "        </a>\n"
    "    </div>\n"
    "\n"
    "    <!-- Filtros -->\n"
    "    <div class=\"card\">\n"
    "        <form method=\"get\" class=\"filter-bar\">\n"
    "            <div class=\"filter-group\">\n"
    "                <label for=\"rol\">Rol</label>\n"
    "                <select name=\"rol\" id=\"rol\" class=\"form-control-dark select-dark\">\n"
    "                    <option value=\"\">Todos los roles</option>\n"
    "                    {% for valor, etiqueta in roles %}\n"
    "                    <option value=\"{{ valor }}\" {% if rol_filtro == valor %}selected{% endif %}>\n"
    "                        {{ etiqueta }}\n"
    "                    </option>\n"
    "                    {% endfor %}\n"
    "                </select>\n"
    "            </div>\n"
    "            <div class=\"filter-group\">\n"
    "                <label for=\"estado\">Estado</label>\n"
    "                <select name=\"estado\" id=\"estado\" class=\"form-control-dark select-dark\">\n"
    "                    <option value=\"\">Todos</option>\n"
    "                    <option value=\"activo\" {% if estado_filtro == 'activo' %}selected{% endif %}>Activos</option>\n"
    "                    <option value=\"inactivo\" {% if estado_filtro == 'inactivo' %}selected{% endif %}>Inactivos</option>\n"
    "                </select>\n"
    "            </div>\n"
    "            <button type=\"submit\" class=\"btn-filter\">\n"
    f"                {svg(SVG_FUNNEL, extra='style=\"vertical-align:-0.125em;\"')}\n"
    "                Filtrar\n"
    "            </button>\n"
    "            <a href=\"{% url 'core:admin_usuarios' %}\" class=\"btn-back\" style=\"align-self: flex-end;\">\n"
    f"                {svg(SVG_X_CIRCLE, extra='style=\"vertical-align:-0.125em;\"')}\n"
    "                Limpiar\n"
    "            </a>\n"
    "        </form>\n"
    "    </div>\n"
    "\n"
    "    <!-- Tabla de Usuarios -->\n"
    "    <div class=\"card\">\n"
    "        <div style=\"overflow-x: auto;\">\n"
    "            <table class=\"data-table\">\n"
    "                <thead>\n"
    "                    <tr>\n"
    "                        <th>Usuario</th>\n"
    "                        <th>Nombre</th>\n"
    "                        <th>Rol</th>\n"
    "                        <th>Etapa</th>\n"
    "                        <th>Estado</th>\n"
    "                        <th>Fecha Registro</th>\n"
    "                        <th>Acciones</th>\n"
    "                    </tr>\n"
    "                </thead>\n"
    "                <tbody>\n"
    "                    {% for u in usuarios %}\n"
    "                    <tr>\n"
    "                        <td><strong>{{ u.id_usuario }}</strong></td>\n"
    "                        <td>{{ u.nombre_completo }}</td>\n"
    "                        <td>{{ u.get_rol_display }}</td>\n"
    "                        <td>{{ u.etapa_asignada.nombre_etapa|default:\"N/A\" }}</td>\n"
    "                        <td>\n"
    "                            {% if u.is_active %}\n"
    "                                <span class=\"status-badge badge-activo\">Activo</span>\n"
    "                            {% else %}\n"
    "                                <span class=\"status-badge badge-inactivo\">Inactivo</span>\n"
    "                            {% endif %}\n"
    "                            {% if u.is_staff %}\n"
    "                                <span class=\"status-badge badge-admin\">Admin</span>\n"
    "                            {% endif %}\n"
    "                            {% if u.bloqueado %}\n"
    "                                <span class=\"status-badge\" style=\"background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.5); margin-left: 4px; display:inline-flex; align-items:center; gap:4px;\" title=\"{{ u.motivo_bloqueo|default:'Bloqueado' }}{% if u.minutos_restantes %} ({{ u.minutos_restantes }} min){% endif %}\">\n"
    f"                                    {svg(SVG_LOCK_FILL, w='0.9em', h='0.9em')}\n"
    "                                    Bloqueado\n"
    "                                </span>\n"
    "                            {% endif %}\n"
    "                        </td>\n"
    "                        <td>{{ u.fecha_registro|date:\"d/m/Y H:i\" }}</td>\n"
    "                        <td>\n"
    "                            <div class=\"action-group\">\n"
    "                                <form method=\"post\" class=\"action-form\">\n"
    "                                    {% csrf_token %}\n"
    "                                    <input type=\"hidden\" name=\"usuario_id\" value=\"{{ u.id_usuario }}\">\n"
    "                                    {% if u.is_active %}\n"
    "                                        <button type=\"submit\" name=\"accion\" value=\"desactivar\" class=\"action-btn action-off\" title=\"Desactivar usuario\">\n"
    f"                                            {svg(SVG_TOGGLE_ON)}\n"
    "                                        </button>\n"
    "                                    {% else %}\n"
    "                                        <button type=\"submit\" name=\"accion\" value=\"activar\" class=\"action-btn action-on\" title=\"Activar usuario\">\n"
    f"                                            {svg(SVG_CHECK_CIRCLE)}\n"
    "                                        </button>\n"
    "                                    {% endif %}\n"
    "                                    {% if not u.is_staff %}\n"
    "                                        <button type=\"button\" class=\"action-btn action-del\" title=\"Eliminar usuario\"\n"
    "                                            onclick=\"abrirModalEliminar('{{ u.id_usuario }}', '{{ u.nombre_completo }}')\">\n"
    f"                                            {svg(SVG_X_OCTAGON)}\n"
    "                                        </button>\n"
    "                                    {% endif %}\n"
    "                                </form>\n"
    "                                <button type=\"button\" class=\"action-btn action-pwd\" title=\"Cambiar contraseña\"\n"
    "                                    onclick=\"abrirModalPassword('{{ u.id_usuario }}', '{{ u.nombre_completo }}')\">\n"
    f"                                    {svg(SVG_KEY)}\n"
    "                                </button>\n"
    "                                {% if u.bloqueado %}\n"
    "                                <form method=\"post\" action=\"{% url 'core:admin_desbloquear_usuario' u.id_usuario %}\" style=\"display:inline;\">\n"
    "                                    {% csrf_token %}\n"
    "                                    <button type=\"submit\" class=\"action-btn\" title=\"Desbloquear usuario\"\n"
    "                                        style=\"background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3);\">\n"
    f"                                        {svg(SVG_UNLOCK_FILL)}\n"
    "                                    </button>\n"
    "                                </form>\n"
    "                                {% endif %}\n"
    "                            </div>\n"
    "                        </td>\n"
    "                    </tr>\n"
    "                    {% empty %}\n"
    "                    <tr>\n"
    "                        <td colspan=\"7\" class=\"empty-state\">\n"
    f"                            {svg(SVG_INBOX, w='2rem', h='2rem', extra='style=\"display:block; margin:0 auto 8px;\"')}\n"
    "                            No se encontraron usuarios\n"
    "                        </td>\n"
    "                    </tr>\n"
    "                    {% endfor %}\n"
    "                </tbody>\n"
    "            </table>\n"
    "        </div>\n"
    "    </div>\n"
    "</div>\n"
    "\n"
    "<!-- ===== MODAL CAMBIAR CONTRASEÑA ===== -->\n"
    "<div class=\"modal-overlay\" id=\"modalPassword\">\n"
    "    <div class=\"modal-box\">\n"
    "        <div class=\"modal-header\">\n"
    f"            {svg(SVG_SHIELD_LOCK, w='1.4em', h='1.4em', extra='style=\"color:#0ea5e9; flex-shrink:0;\"')}\n"
    "            <div>\n"
    "                <h3>Cambiar Contraseña</h3>\n"
    "                <p id=\"modalUserInfo\">Usuario</p>\n"
    "            </div>\n"
    "        </div>\n"
    "\n"
    "        <form method=\"post\" id=\"formCambiarPassword\" onsubmit=\"return validarPassword(event)\">\n"
    "            {% csrf_token %}\n"
    "            <input type=\"hidden\" name=\"accion\" value=\"cambiar_password\">\n"
    "            <input type=\"hidden\" name=\"usuario_id\" id=\"modalUsuarioId\">\n"
    "\n"
    "            <div class=\"form-group\">\n"
    "                <label for=\"nueva_password\">Nueva contraseña</label>\n"
    "                <div class=\"input-icon-wrap password-with-eye\">\n"
    "                    <input type=\"password\" name=\"nueva_password\" id=\"nueva_password\"\n"
    "                        class=\"form-control-dark\" placeholder=\"Min. 4 caracteres\"\n"
    "                        minlength=\"4\" maxlength=\"50\" required\n"
    "                        oninput=\"checkStrength(); checkMatch();\">\n"
    "                    <button type=\"button\" class=\"toggle-password-eye\"\n"
    "                        onclick=\"togglePasswordEye('nueva_password', this)\"\n"
    "                        title=\"Mostrar / ocultar contraseña\"\n"
    "                        aria-label=\"Mostrar u ocultar contraseña\">\n"
    f"                        {svg(SVG_EYE_OFF, w='20', h='20', extra='class=\"eye-icon eye-off\"')}\n"
    f"                        {svg(SVG_EYE_ON, w='20', h='20', extra='class=\"eye-icon eye-on\" style=\"display:none;\"')}\n"
    "                    </button>\n"
    "                </div>\n"
    "                <div class=\"strength-bar\">\n"
    "                    <div class=\"strength-bar-fill\" id=\"strengthFill\"></div>\n"
    "                </div>\n"
    "            </div>\n"
    "\n"
    "            <div class=\"form-group\">\n"
    "                <label for=\"confirmar_password\">Confirmar contraseña</label>\n"
    "                <div class=\"input-icon-wrap password-with-eye\">\n"
    "                    <input type=\"password\" name=\"confirmar_password\" id=\"confirmar_password\"\n"
    "                        class=\"form-control-dark\" placeholder=\"Repite la contraseña\"\n"
    "                        minlength=\"4\" maxlength=\"50\" required\n"
    "                        oninput=\"checkMatch();\">\n"
    "                    <button type=\"button\" class=\"toggle-password-eye\"\n"
    "                        onclick=\"togglePasswordEye('confirmar_password', this)\"\n"
    "                        title=\"Mostrar / ocultar contraseña\"\n"
    "                        aria-label=\"Mostrar u ocultar contraseña\">\n"
    f"                        {svg(SVG_EYE_OFF, w='20', h='20', extra='class=\"eye-icon eye-off\"')}\n"
    f"                        {svg(SVG_EYE_ON, w='20', h='20', extra='class=\"eye-icon eye-on\" style=\"display:none;\"')}\n"
    "                    </button>\n"
    "                </div>\n"
    "                <div class=\"match-indicator\" id=\"matchIndicator\">\n"
    f"                    {svg(SVG_INFO_CIRCLE, w='0.9em', h='0.9em')}\n"
    "                    <span>Las contraseñas deben coincidir</span>\n"
    "                </div>\n"
    "            </div>\n"
    "\n"
    "            <div class=\"error-msg\" id=\"errorMsg\">\n"
    f"                {svg(SVG_EXCLAMATION_CIRCLE, w='0.9em', h='0.9em')}\n"
    "                <span id=\"errorText\"></span>\n"
    "            </div>\n"
    "\n"
    "            <div class=\"modal-actions\">\n"
    "                <button type=\"button\" class=\"btn-modal-secondary\" onclick=\"cerrarModalPassword()\">\n"
    f"                    {svg(SVG_X_LG)}\n"
    "                    Cancelar\n"
    "                </button>\n"
    "                <button type=\"submit\" class=\"btn-modal-primary\">\n"
    f"                    {svg(SVG_CHECK_LG)}\n"
    "                    Guardar Cambios\n"
    "                </button>\n"
    "            </div>\n"
    "        </form>\n"
    "    </div>\n"
    "</div>\n"
    "\n"
    "<!-- ===== MODAL CONFIRMAR ELIMINACIÓN ===== -->\n"
    "<div class=\"modal-del-overlay\" id=\"modalEliminar\">\n"
    "    <div class=\"modal-del-box\">\n"
    "        <div class=\"modal-del-icon\">\n"
    f"            {svg(SVG_EXCLAMATION_TRIANGLE, w='1.6em', h='1.6em')}\n"
    "        </div>\n"
    "        <h3>¿Eliminar usuario?</h3>\n"
    "        <p>\n"
    "            Estás a punto de eliminar permanentemente al usuario<br>\n"
    "            <span class=\"user-highlight\" id=\"delUserName\">usuario</span>.<br>\n"
    "            Esta acción no se puede deshacer.\n"
    "        </p>\n"
    "        <form method=\"post\" id=\"formEliminarUsuario\">\n"
    "            {% csrf_token %}\n"
    "            <input type=\"hidden\" name=\"accion\" value=\"eliminar\">\n"
    "            <input type=\"hidden\" name=\"usuario_id\" id=\"delUsuarioId\">\n"
    "            <div class=\"modal-del-actions\">\n"
    "                <button type=\"button\" class=\"btn-del-cancel\" onclick=\"cerrarModalEliminar()\">\n"
    f"                    {svg(SVG_X_LG)}\n"
    "                    Cancelar\n"
    "                </button>\n"
    "                <button type=\"submit\" class=\"btn-del-confirm\">\n"
    f"                    {svg(SVG_X_OCTAGON)}\n"
    "                    Sí, eliminar\n"
    "                </button>\n"
    "            </div>\n"
    "        </form>\n"
    "    </div>\n"
    "</div>\n"
    "\n"
    "<!-- JS específico de esta página (va al final para que el DOM ya exista) -->\n"
    "<script src=\"{% static 'js/admin_usuarios.js' %}\"></script>\n"
    "\n"
    "{% endblock %}\n"
)

# ============================================================
# TEMPLATE: cambiar_password_temporal.html
# ============================================================
TEMPLATE_CAMBIAR_PWD = (
    "{% load static %}\n"
    "<!DOCTYPE html>\n"
    "<html lang=\"es\">\n"
    "<head>\n"
    "    <meta charset=\"UTF-8\">\n"
    "    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
    "    <title>Cambiar Contraseña - 3-JJJ-A</title>\n"
    "    <link rel=\"stylesheet\" href=\"{% static 'css/cambiar_password_temporal.css' %}\">\n"
    "</head>\n"
    "<body>\n"
    "    <div class=\"page-wrapper\">\n"
    "        <div class=\"login-card\">\n"
    "            <div class=\"login-header\">\n"
    "                <div class=\"login-logo\">\n"
    f"                    {svg(SVG_SHIELD_LOCK)}\n"
    "                </div>\n"
    "                <h1>Cambio de Contraseña Obligatorio</h1>\n"
    "                <p>Establezca una contraseña personal para continuar</p>\n"
    "            </div>\n"
    "\n"
    "            {% if messages %}\n"
    "            <div class=\"messages-container\">\n"
    "                {% for message in messages %}\n"
    "                <div class=\"alert alert-{{ message.tags }} fade-in\">\n"
    "                    {% if message.tags == 'success' %}\n"
    f"                        {svg(SVG_CHECK_CIRCLE)}\n"
    "                    {% elif message.tags == 'error' %}\n"
    f"                        {svg(SVG_X_CIRCLE)}\n"
    "                    {% elif message.tags == 'warning' %}\n"
    f"                        {svg(SVG_EXCLAMATION_TRIANGLE)}\n"
    "                    {% else %}\n"
    f"                        {svg(SVG_INFO_CIRCLE)}\n"
    "                    {% endif %}\n"
    "                    {{ message }}\n"
    "                </div>\n"
    "                {% endfor %}\n"
    "            </div>\n"
    "            {% endif %}\n"
    "\n"
    "            <div class=\"info-box\">\n"
    f"                {svg(SVG_INFO_CIRCLE)}\n"
    "                <div>\n"
    "                    Hola <strong>{{ usuario.nombre_completo }}</strong>, su contraseña actual\n"
    "                    fue asignada por el administrador como <em>temporal</em>.\n"
    "                    Por seguridad debe cambiarla antes de continuar.\n"
    "                </div>\n"
    "            </div>\n"
    "\n"
    "            <form method=\"post\" novalidate>\n"
    "                {% csrf_token %}\n"
    "\n"
    "                <div class=\"form-group\">\n"
    "                    <label for=\"id_password1\">Nueva Contraseña</label>\n"
    "                    <div class=\"password-input-wrapper\">\n"
    "                        {{ form.password1 }}\n"
    "                        <button type=\"button\" class=\"toggle-password-btn\"\n"
    "                                onclick=\"togglePass('id_password1', this)\" aria-label=\"Ver contraseña\">\n"
    f"                            {svg(SVG_EYE_OFF, w='20', h='20', extra='class=\"eye-closed\"')}\n"
    f"                            {svg(SVG_EYE_ON, w='20', h='20', extra='class=\"eye-open\"')}\n"
    "                        </button>\n"
    "                    </div>\n"
    "                </div>\n"
    "\n"
    "                <div class=\"form-group\">\n"
    "                    <label for=\"id_password2\">Confirmar Contraseña</label>\n"
    "                    <div class=\"password-input-wrapper\">\n"
    "                        {{ form.password2 }}\n"
    "                        <button type=\"button\" class=\"toggle-password-btn\"\n"
    "                                onclick=\"togglePass('id_password2', this)\" aria-label=\"Ver contraseña\">\n"
    f"                            {svg(SVG_EYE_OFF, w='20', h='20', extra='class=\"eye-closed\"')}\n"
    f"                            {svg(SVG_EYE_ON, w='20', h='20', extra='class=\"eye-open\"')}\n"
    "                        </button>\n"
    "                    </div>\n"
    "                </div>\n"
    "\n"
    "                <button type=\"submit\" class=\"btn-login\">\n"
    f"                    {svg(SVG_CHECK_CIRCLE)}\n"
    "                    Cambiar Contraseña\n"
    "                </button>\n"
    "            </form>\n"
    "        </div>\n"
    "    </div>\n"
    "\n"
    "    <script src=\"{% static 'js/cambiar_password_temporal.js' %}\"></script>\n"
    "</body>\n"
    "</html>\n"
)


# ============================================================
# UTILIDADES
# ============================================================
def es_log(path):
    p = str(path).lower()
    return any(k in p for k in LOG_MARKERS)


def backup(path):
    """Crea copia de seguridad con timestamp. Devuelve la ruta del backup o None."""
    if not os.path.isfile(path):
        return None
    bak = f'{path}.bak_{STAMP}'
    try:
        shutil.copy2(path, bak)
        return bak
    except Exception as e:
        print(f"    [WARN] No se pudo crear backup: {e}")
        return None


def escribir(path, contenido, hacer_backup=True):
    """
    Escribe un archivo, creando directorios si hacen falta.
    Si el archivo ya existe y hacer_backup, guarda copia antes.
    """
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    existia = os.path.isfile(path)
    bak = backup(path) if (existia and hacer_backup) else None

    try:
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(contenido)
    except Exception as e:
        print(f"    [ERROR] {path}: {e}")
        return False

    if bak:
        print(f"    ✓ Actualizado:  {os.path.relpath(path)}")
        print(f"      Backup:      {os.path.basename(bak)}")
    elif existia:
        print(f"    ✓ Actualizado:  {os.path.relpath(path)}")
    else:
        print(f"    ✓ Creado:       {os.path.relpath(path)}")
    return True


def buscar_archivo(nombre, raiz):
    """
    Busca un archivo por nombre en el proyecto, excluyendo dirs ignorados
    y archivos que parezcan logs. Devuelve la primera coincidencia o None.
    """
    for dp, dn, fn in os.walk(raiz):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        if nombre in fn:
            full = os.path.join(dp, nombre)
            if not es_log(full):
                return full
    return None


# ============================================================
# PROCESO PRINCIPAL
# ============================================================
def main():
    raiz = os.getcwd()
    print("=" * 68)
    print(" aplicar_fix_iconos.py")
    print(" Solución completa de iconos SVG inline para 3-JJJ-A")
    print("=" * 68)
    print(f"Raíz: {raiz}")
    print()

    # ------------------------------------------------------------
    # PASO 1: Verificación mínima
    # ------------------------------------------------------------
    if not os.path.isfile(os.path.join(raiz, 'manage.py')):
        print("⚠  ATENCIÓN: no encuentro 'manage.py' en este directorio.")
        print("   Asegurate de ejecutar el script desde la RAÍZ del proyecto.")
        r = input("   ¿Continuar de todas formas? [s/N]: ").strip().lower()
        if r != 's':
            return 1
        print()

    # ------------------------------------------------------------
    # PASO 2: Crear los 4 archivos estáticos
    # ------------------------------------------------------------
    print("[1/2] Creando archivos estáticos (CSS + JS)...")
    print()

    estaticos = [
        (os.path.join('static', 'css', 'admin_usuarios.css'),            CSS_ADMIN_USUARIOS),
        (os.path.join('static', 'js',  'admin_usuarios.js'),             JS_ADMIN_USUARIOS),
        (os.path.join('static', 'css', 'cambiar_password_temporal.css'), CSS_CAMBIAR_PWD),
        (os.path.join('static', 'js',  'cambiar_password_temporal.js'),  JS_CAMBIAR_PWD),
    ]

    for rel, contenido in estaticos:
        # Buscar si ya existe en algún static/ del proyecto (por si hay varios)
        candidato = None
        for dp, dn, fn in os.walk(raiz):
            dn[:] = [d for d in dn if d not in SKIP_DIRS]
            nombre = os.path.basename(rel)
            subdir = os.path.basename(os.path.dirname(rel))  # 'css' o 'js'
            if nombre in fn and subdir in dp.split(os.sep):
                full = os.path.join(dp, nombre)
                if not es_log(full):
                    candidato = full
                    break

        target = candidato if candidato else os.path.join(raiz, rel)
        escribir(target, contenido)

    print()

    # ------------------------------------------------------------
    # PASO 3: Reemplazar los 2 templates
    # ------------------------------------------------------------
    print("[2/2] Reemplazando templates...")
    print()

    templates = [
        ('admin_usuarios.html',            TEMPLATE_ADMIN_USUARIOS),
        ('cambiar_password_temporal.html', TEMPLATE_CAMBIAR_PWD),
    ]

    for nombre, contenido in templates:
        existente = buscar_archivo(nombre, raiz)
        if existente:
            escribir(existente, contenido)
        else:
            # No existe: lo creamos en templates/ por defecto
            target = os.path.join(raiz, 'templates', nombre)
            print(f"    (no encontrado, creando en templates/)")
            escribir(target, contenido, hacer_backup=False)

    print()

    # ------------------------------------------------------------
    # REPORTE FINAL
    # ------------------------------------------------------------
    print("=" * 68)
    print(" ✔ LISTO.")
    print()
    print(" ESTRUCTURA CREADA:")
    print("   static/css/admin_usuarios.css")
    print("   static/js/admin_usuarios.js")
    print("   static/css/cambiar_password_temporal.css")
    print("   static/js/cambiar_password_temporal.js")
    print("   templates/admin_usuarios.html           (reemplazado)")
    print("   templates/cambiar_password_temporal.html (reemplazado)")
    print()
    print(f" BACKUPS: cada archivo modificado quedó como *.bak_{STAMP}")
    print()
    print(" PRÓXIMOS PASOS:")
    print("   1) python manage.py collectstatic --noinput")
    print("   2) Recargá el navegador con  Ctrl + F5")
    print("   3) Verificá que los iconos se vean (candado, ojo, etc)")
    print()
    print(" PARA DESHACER:")
    print(f"   Renombrá los *.bak_{STAMP} al nombre original.")
    print("=" * 68)

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nCancelado por el usuario.")
        sys.exit(130)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)