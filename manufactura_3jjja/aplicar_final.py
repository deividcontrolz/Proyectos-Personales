#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aplicar_final.py
================
Aplica los SVG inline a los templates REALES y actualiza el CSS de iconos.
Blindado contra carpetas backup_*, bak_*, *_backup, etc.

Rutas reales (según tu diagnóstico):
  - templates/admin/admin_usuarios.html
  - templates/registration/cambiar_password_temporal.html
  - static/css/3jjja-icons-mask.css
"""
import os, sys, shutil
from datetime import datetime

STAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
RAIZ = os.getcwd()

# Rutas EXACTAS (relativas a la raíz del proyecto)
PATH_ADMIN_TPL = os.path.join('templates', 'admin', 'admin_usuarios.html')
PATH_PWD_TPL   = os.path.join('templates', 'registration', 'cambiar_password_temporal.html')
PATH_CSS_ICON  = os.path.join('static', 'css', '3jjja-icons-mask.css')
PATH_CSS_ADMIN = os.path.join('static', 'css', 'admin_usuarios.css')
PATH_JS_ADMIN  = os.path.join('static', 'js',  'admin_usuarios.js')
PATH_CSS_PWD   = os.path.join('static', 'css', 'cambiar_password_temporal.css')
PATH_JS_PWD    = os.path.join('static', 'js',  'cambiar_password_temporal.js')

# ============================================================
# CONTENIDO DE LOS ARCHIVOS NUEVOS
# ============================================================

CSS_ADMIN = '''/* ============================================================
   admin_usuarios.css
   ============================================================ */

.input-icon-wrap.password-with-eye { position: relative; }
.input-icon-wrap.password-with-eye .form-control-dark { padding-right: 44px !important; }

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

.input-icon-wrap .toggle-password-eye svg {
    position: static !important;
    left: auto !important;
    top: auto !important;
    transform: none !important;
    color: inherit !important;
}

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

.error-msg {
    display: none;
    align-items: center;
    gap: 6px;
    color: #f87171;
    font-size: 0.8rem;
    margin-top: 6px;
}
.error-msg.visible { display: flex; }
.match-indicator { display: flex; align-items: center; gap: 6px; }
'''

JS_ADMIN = '''/* admin_usuarios.js */
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

CSS_PWD = '''/* cambiar_password_temporal.css */
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body {
    height: 100%;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    overflow: hidden;
}
.page-wrapper {
    display: flex; align-items: center; justify-content: center;
    width: 100%; height: 100vh;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
    position: relative;
}
.page-wrapper::before {
    content: ''; position: absolute; top: 50%; left: 0;
    width: 100%; height: 50%;
    background: linear-gradient(180deg,
        rgba(16,185,129,0.0) 0%, rgba(16,185,129,0.05) 15%,
        rgba(5,150,105,0.12) 40%, rgba(4,120,87,0.20) 65%,
        rgba(6,78,59,0.28) 100%);
    pointer-events: none;
}
.login-card {
    position: relative; width: 100%; max-width: 420px;
    background: rgba(30, 41, 59, 0.95);
    border: 1px solid rgba(16, 185, 129, 0.15);
    border-radius: 24px; padding: 40px 36px;
    box-shadow: 0 12px 40px rgba(0,0,0,0.3), 0 4px 12px rgba(0,0,0,0.15);
    backdrop-filter: blur(10px); z-index: 1;
}
.login-header { text-align: center; margin-bottom: 24px; }
.login-logo {
    width: 60px; height: 60px; margin: 0 auto 16px;
    background: linear-gradient(135deg, #f59e0b, #d97706);
    border-radius: 16px; display: flex; align-items: center; justify-content: center;
    color: white; box-shadow: 0 4px 15px rgba(245, 158, 11, 0.35);
}
.login-logo svg { width: 30px; height: 30px; }
.login-header h1 { color: #f1f5f9; font-size: 1.2rem; margin: 0 0 6px 0; font-weight: 700; }
.login-header p { color: #94a3b8; font-size: 0.82rem; margin: 0; }
.info-box {
    background: rgba(245, 158, 11, 0.12);
    border: 1px solid rgba(245, 158, 11, 0.3);
    color: #fbbf24; padding: 12px 14px; border-radius: 12px;
    font-size: 0.82rem; display: flex; align-items: flex-start; gap: 10px;
    margin-bottom: 20px; line-height: 1.4;
}
.info-box svg { width: 1.1rem; height: 1.1rem; flex-shrink: 0; margin-top: 2px; }
.form-group { margin-bottom: 18px; }
.form-group label {
    display: block; color: #cbd5e1; font-size: 0.78rem; font-weight: 600;
    margin-bottom: 7px; text-transform: uppercase; letter-spacing: 0.5px;
}
.form-control-dark {
    width: 100%; padding: 12px 44px 12px 16px;
    background: rgba(15, 23, 42, 0.8);
    border: 1.5px solid rgba(100, 116, 139, 0.3);
    border-radius: 12px; color: #f1f5f9; font-size: 0.9rem;
    transition: all 0.25s ease;
}
.form-control-dark:focus {
    outline: none; border-color: #10b981;
    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15);
    background: rgba(15, 23, 42, 0.95);
}
.form-control-dark::placeholder { color: #64748b; }
.password-input-wrapper {
    position: relative; display: flex; align-items: center; width: 100%;
}
.toggle-password-btn {
    position: absolute; right: 12px;
    background: transparent; border: none; color: #94a3b8;
    cursor: pointer; display: inline-flex; align-items: center; justify-content: center;
    padding: 4px; transition: color 0.2s ease; z-index: 2;
}
.toggle-password-btn svg { width: 20px; height: 20px; display: block; }
.toggle-password-btn:hover { color: #10b981; }
.toggle-password-btn .eye-open { display: none; }
.btn-login {
    width: 100%; padding: 13px;
    background: linear-gradient(135deg, #10b981, #059669);
    border: none; border-radius: 12px; color: white;
    font-size: 0.95rem; font-weight: 600; cursor: pointer;
    transition: all 0.3s ease;
    display: flex; align-items: center; justify-content: center; gap: 8px;
    margin-top: 8px; letter-spacing: 0.5px;
}
.btn-login svg { width: 1.1em; height: 1.1em; }
.btn-login:hover {
    background: linear-gradient(135deg, #059669, #047857);
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(16, 185, 129, 0.3);
}
.messages-container { margin-bottom: 18px; }
.alert {
    padding: 10px 14px; border-radius: 10px; font-size: 0.85rem;
    display: flex; align-items: center; gap: 8px; margin-bottom: 8px;
}
.alert svg { width: 1em; height: 1em; flex-shrink: 0; }
.alert-success {
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.3); color: #34d399;
}
.alert-error, .alert-info {
    background: rgba(239, 68, 68, 0.15);
    border: 1px solid rgba(239, 68, 68, 0.3); color: #f87171;
}
.alert-warning {
    background: rgba(245, 158, 11, 0.15);
    border: 1px solid rgba(245, 158, 11, 0.3); color: #fbbf24;
}
.fade-in { animation: fadeIn 0.4s ease; }
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(-8px); }
    to   { opacity: 1; transform: translateY(0); }
}
'''

JS_PWD = '''/* cambiar_password_temporal.js */
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

# Bloque adicional para el CSS de iconos (anti-conflicto + iconos faltantes)
CSS_ICONOS_EXTRA = '''

/* ===== ANTI-CONFLICTO + ICONOS FALTANTES ===== */
.bi::before, .bi::after,
[class^="bi-"]::before, [class*=" bi-"]::before,
[class^="bi-"]::after,  [class*=" bi-"]::after {
    content: none !important;
    display: none !important;
    font-family: inherit !important;
}
.bi {
    font-family: inherit !important;
    font-style: normal !important;
    font-weight: normal !important;
}
.bi-lock-fill {
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2216%22%20height%3D%2216%22%20fill%3D%22currentColor%22%20viewBox%3D%220%200%2016%2016%22%3E%3Cpath%20d%3D%22M8%201a2%202%200%200%201%202%202v4H6V3a2%202%200%200%201%202-2m3%206V3a3%203%200%200%200-6%200v4a2%202%200%200%200-2%202v5a2%202%200%200%200%202%202h6a2%202%200%200%200%202-2V9a2%202%200%200%200-2-2%22%2F%3E%3C%2Fsvg%3E");
    mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2216%22%20height%3D%2216%22%20fill%3D%22currentColor%22%20viewBox%3D%220%200%2016%2016%22%3E%3Cpath%20d%3D%22M8%201a2%202%200%200%201%202%202v4H6V3a2%202%200%200%201%202-2m3%206V3a3%203%200%200%200-6%200v4a2%202%200%200%200-2%202v5a2%202%200%200%200%202%202h6a2%202%200%200%200%202-2V9a2%202%200%200%200-2-2%22%2F%3E%3C%2Fsvg%3E");
}
.bi-unlock-fill {
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2216%22%20height%3D%2216%22%20fill%3D%22currentColor%22%20viewBox%3D%220%200%2016%2016%22%3E%3Cpath%20d%3D%22M11%201a2%202%200%200%200-2%202v4a2%202%200%200%201%202%202v5a2%202%200%200%201-2%202H3a2%202%200%200%201-2-2V9a2%202%200%200%201%202-2h5V3a3%203%200%200%201%206%200v4a.5.5%200%200%201-1%200V3a2%202%200%200%200-2-2%22%2F%3E%3C%2Fsvg%3E");
    mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2216%22%20height%3D%2216%22%20fill%3D%22currentColor%22%20viewBox%3D%220%200%2016%2016%22%3E%3Cpath%20d%3D%22M11%201a2%202%200%200%200-2%202v4a2%202%200%200%201%202%202v5a2%202%200%200%201-2%202H3a2%202%200%200%201-2-2V9a2%202%200%200%201%202-2h5V3a3%203%200%200%201%206%200v4a.5.5%200%200%201-1%200V3a2%202%200%200%200-2-2%22%2F%3E%3C%2Fsvg%3E");
}
.bi-info-circle-fill {
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2216%22%20height%3D%2216%22%20fill%3D%22currentColor%22%20viewBox%3D%220%200%2016%2016%22%3E%3Cpath%20d%3D%22M8%2016A8%208%200%201%200%208%200a8%208%200%200%200%200%2016m.93-9.412-1%204.705c-.07.34.029.533.304.533.194%200%20.487-.07.686-.246l-.088.416c-.287.346-.92.598-1.465.598-.703%200-1.002-.422-.808-1.319l.738-3.468c.064-.293.006-.399-.287-.47l-.451-.081.082-.381%202.29-.287zM8%205.5a1%201%200%201%201%200-2%201%201%200%200%201%200%202%22%2F%3E%3C%2Fsvg%3E");
    mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2216%22%20height%3D%2216%22%20fill%3D%22currentColor%22%20viewBox%3D%220%200%2016%2016%22%3E%3Cpath%20d%3D%22M8%2016A8%208%200%201%200%208%200a8%208%200%200%200%200%2016m.93-9.412-1%204.705c-.07.34.029.533.304.533.194%200%20.487-.07.686-.246l-.088.416c-.287.346-.92.598-1.465.598-.703%200-1.002-.422-.808-1.319l.738-3.468c.064-.293.006-.399-.287-.47l-.451-.081.082-.381%202.29-.287zM8%205.5a1%201%200%201%201%200-2%201%201%200%200%201%200%202%22%2F%3E%3C%2Fsvg%3E");
}
.bi-eye-slash {
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2216%22%20height%3D%2216%22%20fill%3D%22currentColor%22%20viewBox%3D%220%200%2016%2016%22%3E%3Cpath%20d%3D%22M13.359%2011.238C15.06%209.72%2016%208%2016%208s-3-5.5-8-5.5a7%207%200%200%200-2.79.588l.77.771A6%206%200%200%201%208%203.5c2.12%200%203.879%201.168%205.168%202.457A13%2013%200%200%201%2014.828%208q-.086.13-.195.288c-.335.48-.83%201.12-1.465%201.755q-.27.275-.57.535zM11.297%209.176a3.5%203.5%200%200%200-4.474-4.474l.823.823a2.5%202.5%200%200%201%202.829%202.829zm-2.943%201.299.822.822a3.5%203.5%200%200%201-4.474-4.474l.823.823a2.5%202.5%200%200%200%202.829%202.829%22%2F%3E%3Cpath%20d%3D%22M3.35%205.47q-.27.24-.518.487A13%2013%200%200%200%201.172%208l.195.288c.335.48.83%201.12%201.465%201.755C4.121%2011.332%205.881%2012.5%208%2012.5c.716%200%201.39-.133%202.02-.36l.77.772A7%207%200%200%201%208%2013.5C3%2013.5%200%208%200%208s.939-1.721%202.641-3.238l.708.709zm10.296%208.884-12-12%20.708-.708%2012%2012z%22%2F%3E%3C%2Fsvg%3E");
    mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2216%22%20height%3D%2216%22%20fill%3D%22currentColor%22%20viewBox%3D%220%200%2016%2016%22%3E%3Cpath%20d%3D%22M13.359%2011.238C15.06%209.72%2016%208%2016%208s-3-5.5-8-5.5a7%207%200%200%200-2.79.588l.77.771A6%206%200%200%201%208%203.5c2.12%200%203.879%201.168%205.168%202.457A13%2013%200%200%201%2014.828%208q-.086.13-.195.288c-.335.48-.83%201.12-1.465%201.755q-.27.275-.57.535zM11.297%209.176a3.5%203.5%200%200%200-4.474-4.474l.823.823a2.5%202.5%200%200%201%202.829%202.829zm-2.943%201.299.822.822a3.5%203.5%200%200%201-4.474-4.474l.823.823a2.5%202.5%200%200%200%202.829%202.829%22%2F%3E%3Cpath%20d%3D%22M3.35%205.47q-.27.24-.518.487A13%2013%200%200%200%201.172%208l.195.288c.335.48.83%201.12%201.465%201.755C4.121%2011.332%205.881%2012.5%208%2012.5c.716%200%201.39-.133%202.02-.36l.77.772A7%207%200%200%201%208%2013.5C3%2013.5%200%208%200%208s.939-1.721%202.641-3.238l.708.709zm10.296%208.884-12-12%20.708-.708%2012%2012z%22%2F%3E%3C%2Fsvg%3E");
}
'''


# ============================================================
# SVG PATHS + helper
# ============================================================
P_PEOPLE = '<path d="M15 14s1 0 1-1-1-4-5-4-5 3-5 4 1 1 1 1zm-7.978-1L7 12.996c.001-.264.167-1.03.76-1.72C8.312 10.629 9.282 10 11 10c1.717 0 2.687.63 3.24 1.276.593.69.758 1.457.76 1.72l-.008.002-.014.002zM11 7a2 2 0 1 0 0-4 2 2 0 0 0 0 4m3-2a3 3 0 1 1-6 0 3 3 0 0 1 6 0M6.936 9.28a6 6 0 0 0-1.23-.247A7 7 0 0 0 5 9c-4 0-5 3-5 4q0 1 1 1h4.216A2.24 2.24 0 0 1 5 13c0-1.01.377-2.042 1.09-2.904.243-.294.526-.569.846-.816M4.92 10A5.5 5.5 0 0 0 4 13H1c0-.26.164-1.03.76-1.724.545-.636 1.492-1.256 3.16-1.275ZM1.5 5.5a3 3 0 1 1 6 0 3 3 0 0 1-6 0m3-2a2 2 0 1 0 0 4 2 2 0 0 0 0-4"/>'
P_ARROW = '<path fill-rule="evenodd" d="M15 8a.5.5 0 0 0-.5-.5H2.707l3.147-3.146a.5.5 0 1 0-.708-.708l-4 4a.5.5 0 0 0 0 .708l4 4a.5.5 0 0 0 .708-.708L2.707 8.5H14.5A.5.5 0 0 0 15 8"/>'
P_FUNNEL = '<path d="M1.5 1.5A.5.5 0 0 1 2 1h12a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-.128.334L10 8.692V13.5a.5.5 0 0 1-.342.474l-3 1A.5.5 0 0 1 6 14.5V8.692L1.628 3.834A.5.5 0 0 1 1.5 3.5zm1 .5v1.308l4.372 4.858A.5.5 0 0 1 7 8.5v5.306l2-.666V8.5a.5.5 0 0 1 .128-.334L13.5 3.308V2z"/>'
P_XCIRCLE = '<path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16"/><path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708"/>'
P_LOCK = '<path d="M8 1a2 2 0 0 1 2 2v4H6V3a2 2 0 0 1 2-2m3 6V3a3 3 0 0 0-6 0v4a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2"/>'
P_TOGGLE = '<path d="M5 3a5 5 0 0 0 0 10h6a5 5 0 0 0 0-10zm6 9a4 4 0 1 1 0-8 4 4 0 0 1 0 8"/>'
P_CHECKCIRCLE = '<path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16"/><path d="m10.97 4.97-.02.022-3.473 4.425-2.093-2.094a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-1.071-1.05"/>'
P_XOCT = '<path d="M4.54.146A.5.5 0 0 1 4.893 0h6.214a.5.5 0 0 1 .353.146l4.394 4.394a.5.5 0 0 1 .146.353v6.214a.5.5 0 0 1-.146.353l-4.394 4.394a.5.5 0 0 1-.353.146H4.893a.5.5 0 0 1-.353-.146L.146 11.46A.5.5 0 0 1 0 11.107V4.893a.5.5 0 0 1 .146-.353zM5.1 1 1 5.1v5.8L5.1 15h5.8l4.1-4.1V5.1L10.9 1z"/><path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708"/>'
P_KEY = '<path d="M0 8a4 4 0 0 1 7.465-2H14a.5.5 0 0 1 .354.146l1.5 1.5a.5.5 0 0 1 0 .708l-1.5 1.5a.5.5 0 0 1-.708 0L13 9.207l-.646.647a.5.5 0 0 1-.708 0L11 9.207l-.646.647a.5.5 0 0 1-.708 0L9 9.207l-.646.647A.5.5 0 0 1 8 10h-.535A4 4 0 0 1 0 8m4-3a3 3 0 1 0 2.712 4.285A.5.5 0 0 1 7.163 9h.63l.853-.854a.5.5 0 0 1 .708 0l.646.647.646-.647a.5.5 0 0 1 .708 0l.646.647.646-.647a.5.5 0 0 1 .708 0l.646.647.793-.793-1-1h-6.63a.5.5 0 0 1-.451-.285A3 3 0 0 0 4 5"/><path d="M4 8a1 1 0 1 1-2 0 1 1 0 0 1 2 0"/>'
P_UNLOCK = '<path d="M11 1a2 2 0 0 0-2 2v4a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h5V3a3 3 0 0 1 6 0v4a.5.5 0 0 1-1 0V3a2 2 0 0 0-2-2"/>'
P_INBOX = '<path d="M4.98 4a.5.5 0 0 0-.39.188L1.54 8H6a.5.5 0 0 1 .5.5 1.5 1.5 0 1 0 3 0A.5.5 0 0 1 10 8h4.46l-3.05-3.812A.5.5 0 0 0 11.02 4zm9.954 5H10.45a2.5 2.5 0 0 1-4.9 0H1.066l.32 2.562a.5.5 0 0 0 .497.438h12.234a.5.5 0 0 0 .496-.438zM3.809 3.563A1.5 1.5 0 0 1 4.981 3h6.038a1.5 1.5 0 0 1 1.172.563l3.7 4.625a.5.5 0 0 1 .105.374l-.39 3.124A1.5 1.5 0 0 1 14.117 13H1.883a1.5 1.5 0 0 1-1.489-1.314l-.39-3.124a.5.5 0 0 1 .106-.374z"/>'
P_SHIELD = '<path d="M5.338 1.59a61 61 0 0 0-2.837.856.48.48 0 0 0-.328.39c-.554 4.157.726 7.19 2.253 9.188a10.7 10.7 0 0 0 2.287 2.233c.346.244.652.42.893.533q.18.085.293.118a1 1 0 0 0 .101.025 1 1 0 0 0 .1-.025q.114-.034.294-.118c.24-.113.547-.29.893-.533a10.7 10.7 0 0 0 2.287-2.233c1.527-1.997 2.807-5.031 2.253-9.188a.48.48 0 0 0-.328-.39c-.651-.213-1.75-.56-2.837-.855C9.552 1.29 8.531 1.067 8 1.067c-.53 0-1.552.223-2.662.524zM5.072.56C6.157.265 7.31 0 8 0s1.843.265 2.928.56c1.11.3 2.229.655 2.887.87a1.54 1.54 0 0 1 1.044 1.262c.596 4.477-.787 7.795-2.465 9.99a11.8 11.8 0 0 1-2.517 2.453 7 7 0 0 1-1.048.625c-.28.132-.581.24-.829.24s-.548-.108-.829-.24a7 7 0 0 1-1.048-.625 11.8 11.8 0 0 1-2.517-2.453C1.928 10.487.545 7.169 1.141 2.692A1.54 1.54 0 0 1 2.185 1.43 63 63 0 0 1 5.072.56"/><path d="M9.5 6.5a1.5 1.5 0 0 1-1 1.415l.385 1.99a.5.5 0 0 1-.491.595h-.788a.5.5 0 0 1-.49-.595l.384-1.99a1.5 1.5 0 1 1 2-1.415"/>'
P_INFO = '<path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16"/><path d="m8.93 6.588-2.29.287-.082.38.45.083c.294.07.352.176.288.469l-.738 3.468c-.194.897.105 1.319.808 1.319.545 0 1.178-.252 1.465-.598l.088-.416c-.2.176-.492.246-.686.246-.275 0-.375-.193-.304-.533zM9 4.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0"/>'
P_EXCL = '<path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16"/><path d="M7.002 11a1 1 0 1 1 2 0 1 1 0 0 1-2 0M7.1 4.995a.905.905 0 1 1 1.8 0l-.35 3.507a.552.552 0 0 1-1.1 0z"/>'
P_XLG = '<path d="M2.146 2.854a.5.5 0 1 1 .708-.708L8 7.293l5.146-5.147a.5.5 0 0 1 .708.708L8.707 8l5.147 5.146a.5.5 0 0 1-.708.708L8 8.707l-5.146 5.147a.5.5 0 0 1-.708-.708L7.293 8z"/>'
P_CHECKLG = '<path d="M12.736 3.97a.733.733 0 0 1 1.047 0c.286.289.29.756.01 1.05L7.88 12.01a.733.733 0 0 1-1.065.02L3.217 8.384a.757.757 0 0 1 0-1.06.733.733 0 0 1 1.047 0l3.052 3.093 5.4-6.425z"/>'
P_TRIANGLE = '<path d="M7.938 2.016A.13.13 0 0 1 8.002 2a.13.13 0 0 1 .063.016.15.15 0 0 1 .054.057l6.857 11.667c.036.06.035.124.002.183a.2.2 0 0 1-.054.06.1.1 0 0 1-.066.017H1.146a.1.1 0 0 1-.066-.017.2.2 0 0 1-.054-.06.18.18 0 0 1 .002-.183L7.884 2.073a.15.15 0 0 1 .054-.057m1.044-.45a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767z"/><path d="M7.002 12a1 1 0 1 1 2 0 1 1 0 0 1-2 0M7.1 5.995a.905.905 0 1 1 1.8 0l-.35 3.507a.552.552 0 0 1-1.1 0z"/>'
P_EYEOFF = '<path d="M13.359 11.238C15.06 9.72 16 8 16 8s-3-5.5-8-5.5a7 7 0 0 0-2.79.588l.77.771A6 6 0 0 1 8 3.5c2.12 0 3.879 1.168 5.168 2.457A13 13 0 0 1 14.828 8q-.086.13-.195.288c-.335.48-.83 1.12-1.465 1.755q-.27.275-.57.535zM11.297 9.176a3.5 3.5 0 0 0-4.474-4.474l.823.823a2.5 2.5 0 0 1 2.829 2.829zm-2.943 1.299.822.822a3.5 3.5 0 0 1-4.474-4.474l.823.823a2.5 2.5 0 0 0 2.829 2.829"/><path d="M3.35 5.47q-.27.24-.518.487A13 13 0 0 0 1.172 8l.195.288c.335.48.83 1.12 1.465 1.755C4.121 11.332 5.881 12.5 8 12.5c.716 0 1.39-.133 2.02-.36l.77.772A7 7 0 0 1 8 13.5C3 13.5 0 8 0 8s.939-1.721 2.641-3.238l.708.709zm10.296 8.884-12-12 .708-.708 12 12z"/>'
P_EYEON = '<path d="M16 8s-3-5.5-8-5.5S0 8 0 8s3 5.5 8 5.5S16 8 16 8M1.173 8a13 13 0 0 1 1.66-2.043C4.12 4.668 5.88 3.5 8 3.5s3.879 1.168 5.168 2.457A13 13 0 0 1 14.828 8q-.086.13-.195.288c-.335.48-.83 1.12-1.465 1.755C11.879 11.332 10.119 12.5 8 12.5s-3.879-1.168-5.168-2.457A13 13 0 0 1 1.172 8z"/><path d="M8 5.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5M4.5 8a3.5 3.5 0 1 1 7 0 3.5 3.5 0 0 1-7 0"/>'

def SVG(p, w='1em', h='1em', extra=''):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" fill="currentColor" viewBox="0 0 16 16" {extra} aria-hidden="true">{p}</svg>'


# ============================================================
# TEMPLATES (con SVG inline)
# ============================================================
def build_admin_template():
    return (
        "{% extends 'base.html' %}\n"
        "{% load static %}\n"
        "\n"
        "{% block title %}Gestionar Usuarios - 3-JJJ-A{% endblock %}\n"
        "{% block page_title %}Gestionar Usuarios{% endblock %}\n"
        "\n"
        "{% block content %}\n"
        "<link rel=\"stylesheet\" href=\"{% static 'css/admin_usuarios.css' %}\">\n"
        "\n"
        "<div class=\"admin-container\">\n"
        "  <div class=\"admin-header\">\n"
        "    <div>\n"
        "      <h1>" + SVG(P_PEOPLE, extra='style="vertical-align:-0.125em;"') + " Gestionar Usuarios</h1>\n"
        "      <p style=\"color: #94a3b8; margin: 4px 0 0 0; font-size: 0.85rem;\">Total: {{ total_usuarios }} usuarios | {{ usuario.nombre_completo }}</p>\n"
        "    </div>\n"
        "    <a href=\"{% url 'core:panel_admin' %}\" class=\"btn-back\">" + SVG(P_ARROW) + " Volver al Panel</a>\n"
        "  </div>\n"
        "\n"
        "  <div class=\"card\">\n"
        "    <form method=\"get\" class=\"filter-bar\">\n"
        "      <div class=\"filter-group\">\n"
        "        <label for=\"rol\">Rol</label>\n"
        "        <select name=\"rol\" id=\"rol\" class=\"form-control-dark select-dark\">\n"
        "          <option value=\"\">Todos los roles</option>\n"
        "          {% for valor, etiqueta in roles %}<option value=\"{{ valor }}\" {% if rol_filtro == valor %}selected{% endif %}>{{ etiqueta }}</option>{% endfor %}\n"
        "        </select>\n"
        "      </div>\n"
        "      <div class=\"filter-group\">\n"
        "        <label for=\"estado\">Estado</label>\n"
        "        <select name=\"estado\" id=\"estado\" class=\"form-control-dark select-dark\">\n"
        "          <option value=\"\">Todos</option>\n"
        "          <option value=\"activo\" {% if estado_filtro == 'activo' %}selected{% endif %}>Activos</option>\n"
        "          <option value=\"inactivo\" {% if estado_filtro == 'inactivo' %}selected{% endif %}>Inactivos</option>\n"
        "        </select>\n"
        "      </div>\n"
        "      <button type=\"submit\" class=\"btn-filter\">" + SVG(P_FUNNEL) + " Filtrar</button>\n"
        "      <a href=\"{% url 'core:admin_usuarios' %}\" class=\"btn-back\" style=\"align-self: flex-end;\">" + SVG(P_XCIRCLE) + " Limpiar</a>\n"
        "    </form>\n"
        "  </div>\n"
        "\n"
        "  <div class=\"card\">\n"
        "    <div style=\"overflow-x: auto;\">\n"
        "      <table class=\"data-table\">\n"
        "        <thead><tr><th>Usuario</th><th>Nombre</th><th>Rol</th><th>Etapa</th><th>Estado</th><th>Fecha Registro</th><th>Acciones</th></tr></thead>\n"
        "        <tbody>\n"
        "          {% for u in usuarios %}\n"
        "          <tr>\n"
        "            <td><strong>{{ u.id_usuario }}</strong></td>\n"
        "            <td>{{ u.nombre_completo }}</td>\n"
        "            <td>{{ u.get_rol_display }}</td>\n"
        "            <td>{{ u.etapa_asignada.nombre_etapa|default:\"N/A\" }}</td>\n"
        "            <td>\n"
        "              {% if u.is_active %}<span class=\"status-badge badge-activo\">Activo</span>{% else %}<span class=\"status-badge badge-inactivo\">Inactivo</span>{% endif %}\n"
        "              {% if u.is_staff %}<span class=\"status-badge badge-admin\">Admin</span>{% endif %}\n"
        "              {% if u.bloqueado %}\n"
        "                <span class=\"status-badge\" style=\"background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.5); margin-left: 4px; display:inline-flex; align-items:center; gap:4px;\" title=\"{{ u.motivo_bloqueo|default:'Bloqueado' }}{% if u.minutos_restantes %} ({{ u.minutos_restantes }} min){% endif %}\">" + SVG(P_LOCK, w='0.9em', h='0.9em') + " Bloqueado</span>\n"
        "              {% endif %}\n"
        "            </td>\n"
        "            <td>{{ u.fecha_registro|date:\"d/m/Y H:i\" }}</td>\n"
        "            <td>\n"
        "              <div class=\"action-group\">\n"
        "                <form method=\"post\" class=\"action-form\">\n"
        "                  {% csrf_token %}\n"
        "                  <input type=\"hidden\" name=\"usuario_id\" value=\"{{ u.id_usuario }}\">\n"
        "                  {% if u.is_active %}\n"
        "                    <button type=\"submit\" name=\"accion\" value=\"desactivar\" class=\"action-btn action-off\" title=\"Desactivar usuario\">" + SVG(P_TOGGLE) + "</button>\n"
        "                  {% else %}\n"
        "                    <button type=\"submit\" name=\"accion\" value=\"activar\" class=\"action-btn action-on\" title=\"Activar usuario\">" + SVG(P_CHECKCIRCLE) + "</button>\n"
        "                  {% endif %}\n"
        "                  {% if not u.is_staff %}\n"
        "                    <button type=\"button\" class=\"action-btn action-del\" title=\"Eliminar usuario\" onclick=\"abrirModalEliminar('{{ u.id_usuario }}', '{{ u.nombre_completo }}')\">" + SVG(P_XOCT) + "</button>\n"
        "                  {% endif %}\n"
        "                </form>\n"
        "                <button type=\"button\" class=\"action-btn action-pwd\" title=\"Cambiar contraseña\" onclick=\"abrirModalPassword('{{ u.id_usuario }}', '{{ u.nombre_completo }}')\">" + SVG(P_KEY) + "</button>\n"
        "                {% if u.bloqueado %}\n"
        "                  <form method=\"post\" action=\"{% url 'core:admin_desbloquear_usuario' u.id_usuario %}\" style=\"display:inline;\">\n"
        "                    {% csrf_token %}\n"
        "                    <button type=\"submit\" class=\"action-btn\" title=\"Desbloquear usuario\" style=\"background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3);\">" + SVG(P_UNLOCK) + "</button>\n"
        "                  </form>\n"
        "                {% endif %}\n"
        "              </div>\n"
        "            </td>\n"
        "          </tr>\n"
        "          {% empty %}\n"
        "          <tr><td colspan=\"7\" class=\"empty-state\">" + SVG(P_INBOX, w='2rem', h='2rem', extra='style="display:block; margin:0 auto 8px;"') + " No se encontraron usuarios</td></tr>\n"
        "          {% endfor %}\n"
        "        </tbody>\n"
        "      </table>\n"
        "    </div>\n"
        "  </div>\n"
        "</div>\n"
        "\n"
        "<!-- MODAL CAMBIAR CONTRASEÑA -->\n"
        "<div class=\"modal-overlay\" id=\"modalPassword\">\n"
        "  <div class=\"modal-box\">\n"
        "    <div class=\"modal-header\">\n"
        "      " + SVG(P_SHIELD, w='1.4em', h='1.4em', extra='style="color:#0ea5e9; flex-shrink:0;"') + "\n"
        "      <div><h3>Cambiar Contraseña</h3><p id=\"modalUserInfo\">Usuario</p></div>\n"
        "    </div>\n"
        "    <form method=\"post\" id=\"formCambiarPassword\" onsubmit=\"return validarPassword(event)\">\n"
        "      {% csrf_token %}\n"
        "      <input type=\"hidden\" name=\"accion\" value=\"cambiar_password\">\n"
        "      <input type=\"hidden\" name=\"usuario_id\" id=\"modalUsuarioId\">\n"
        "      <div class=\"form-group\">\n"
        "        <label for=\"nueva_password\">Nueva contraseña</label>\n"
        "        <div class=\"input-icon-wrap password-with-eye\">\n"
        "          <input type=\"password\" name=\"nueva_password\" id=\"nueva_password\" class=\"form-control-dark\" placeholder=\"Min. 4 caracteres\" minlength=\"4\" maxlength=\"50\" required oninput=\"checkStrength(); checkMatch();\">\n"
        "          <button type=\"button\" class=\"toggle-password-eye\" onclick=\"togglePasswordEye('nueva_password', this)\" title=\"Mostrar / ocultar contraseña\">\n"
        "            " + SVG(P_EYEOFF, w='20', h='20', extra='class="eye-icon eye-off"') + "\n"
        "            " + SVG(P_EYEON, w='20', h='20', extra='class="eye-icon eye-on" style="display:none;"') + "\n"
        "          </button>\n"
        "        </div>\n"
        "        <div class=\"strength-bar\"><div class=\"strength-bar-fill\" id=\"strengthFill\"></div></div>\n"
        "      </div>\n"
        "      <div class=\"form-group\">\n"
        "        <label for=\"confirmar_password\">Confirmar contraseña</label>\n"
        "        <div class=\"input-icon-wrap password-with-eye\">\n"
        "          <input type=\"password\" name=\"confirmar_password\" id=\"confirmar_password\" class=\"form-control-dark\" placeholder=\"Repite la contraseña\" minlength=\"4\" maxlength=\"50\" required oninput=\"checkMatch();\">\n"
        "          <button type=\"button\" class=\"toggle-password-eye\" onclick=\"togglePasswordEye('confirmar_password', this)\" title=\"Mostrar / ocultar contraseña\">\n"
        "            " + SVG(P_EYEOFF, w='20', h='20', extra='class="eye-icon eye-off"') + "\n"
        "            " + SVG(P_EYEON, w='20', h='20', extra='class="eye-icon eye-on" style="display:none;"') + "\n"
        "          </button>\n"
        "        </div>\n"
        "        <div class=\"match-indicator\" id=\"matchIndicator\">" + SVG(P_INFO, w='0.9em', h='0.9em') + " <span>Las contraseñas deben coincidir</span></div>\n"
        "      </div>\n"
        "      <div class=\"error-msg\" id=\"errorMsg\">" + SVG(P_EXCL, w='0.9em', h='0.9em') + " <span id=\"errorText\"></span></div>\n"
        "      <div class=\"modal-actions\">\n"
        "        <button type=\"button\" class=\"btn-modal-secondary\" onclick=\"cerrarModalPassword()\">" + SVG(P_XLG) + " Cancelar</button>\n"
        "        <button type=\"submit\" class=\"btn-modal-primary\">" + SVG(P_CHECKLG) + " Guardar Cambios</button>\n"
        "      </div>\n"
        "    </form>\n"
        "  </div>\n"
        "</div>\n"
        "\n"
        "<!-- MODAL ELIMINAR -->\n"
        "<div class=\"modal-del-overlay\" id=\"modalEliminar\">\n"
        "  <div class=\"modal-del-box\">\n"
        "    <div class=\"modal-del-icon\">" + SVG(P_TRIANGLE, w='1.6em', h='1.6em') + "</div>\n"
        "    <h3>¿Eliminar usuario?</h3>\n"
        "    <p>Estás a punto de eliminar permanentemente al usuario<br><span class=\"user-highlight\" id=\"delUserName\">usuario</span>.<br>Esta acción no se puede deshacer.</p>\n"
        "    <form method=\"post\" id=\"formEliminarUsuario\">\n"
        "      {% csrf_token %}\n"
        "      <input type=\"hidden\" name=\"accion\" value=\"eliminar\">\n"
        "      <input type=\"hidden\" name=\"usuario_id\" id=\"delUsuarioId\">\n"
        "      <div class=\"modal-del-actions\">\n"
        "        <button type=\"button\" class=\"btn-del-cancel\" onclick=\"cerrarModalEliminar()\">" + SVG(P_XLG) + " Cancelar</button>\n"
        "        <button type=\"submit\" class=\"btn-del-confirm\">" + SVG(P_XOCT) + " Sí, eliminar</button>\n"
        "      </div>\n"
        "    </form>\n"
        "  </div>\n"
        "</div>\n"
        "\n"
        "<script src=\"{% static 'js/admin_usuarios.js' %}\"></script>\n"
        "{% endblock %}\n"
    )


def build_pwd_template():
    return (
        "{% load static %}\n"
        "<!DOCTYPE html>\n"
        "<html lang=\"es\">\n"
        "<head>\n"
        "  <meta charset=\"UTF-8\">\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
        "  <title>Cambiar Contraseña - 3-JJJ-A</title>\n"
        "  <link rel=\"stylesheet\" href=\"{% static 'css/cambiar_password_temporal.css' %}\">\n"
        "</head>\n"
        "<body>\n"
        "  <div class=\"page-wrapper\">\n"
        "    <div class=\"login-card\">\n"
        "      <div class=\"login-header\">\n"
        "        <div class=\"login-logo\">" + SVG(P_SHIELD) + "</div>\n"
        "        <h1>Cambio de Contraseña Obligatorio</h1>\n"
        "        <p>Establezca una contraseña personal para continuar</p>\n"
        "      </div>\n"
        "      {% if messages %}\n"
        "      <div class=\"messages-container\">\n"
        "        {% for message in messages %}\n"
        "        <div class=\"alert alert-{{ message.tags }} fade-in\">\n"
        "          {% if message.tags == 'success' %}" + SVG(P_CHECKCIRCLE) + "\n"
        "          {% elif message.tags == 'error' %}" + SVG(P_XCIRCLE) + "\n"
        "          {% elif message.tags == 'warning' %}" + SVG(P_TRIANGLE) + "\n"
        "          {% else %}" + SVG(P_INFO) + "{% endif %}\n"
        "          {{ message }}\n"
        "        </div>\n"
        "        {% endfor %}\n"
        "      </div>\n"
        "      {% endif %}\n"
        "      <div class=\"info-box\">\n"
        "        " + SVG(P_INFO) + "\n"
        "        <div>Hola <strong>{{ usuario.nombre_completo }}</strong>, su contraseña actual fue asignada por el administrador como <em>temporal</em>. Por seguridad debe cambiarla antes de continuar.</div>\n"
        "      </div>\n"
        "      <form method=\"post\" novalidate>\n"
        "        {% csrf_token %}\n"
        "        <div class=\"form-group\">\n"
        "          <label for=\"id_password1\">Nueva Contraseña</label>\n"
        "          <div class=\"password-input-wrapper\">\n"
        "            {{ form.password1 }}\n"
        "            <button type=\"button\" class=\"toggle-password-btn\" onclick=\"togglePass('id_password1', this)\" aria-label=\"Ver contraseña\">\n"
        "              " + SVG(P_EYEOFF, w='20', h='20', extra='class="eye-closed"') + "\n"
        "              " + SVG(P_EYEON, w='20', h='20', extra='class="eye-open"') + "\n"
        "            </button>\n"
        "          </div>\n"
        "        </div>\n"
        "        <div class=\"form-group\">\n"
        "          <label for=\"id_password2\">Confirmar Contraseña</label>\n"
        "          <div class=\"password-input-wrapper\">\n"
        "            {{ form.password2 }}\n"
        "            <button type=\"button\" class=\"toggle-password-btn\" onclick=\"togglePass('id_password2', this)\" aria-label=\"Ver contraseña\">\n"
        "              " + SVG(P_EYEOFF, w='20', h='20', extra='class="eye-closed"') + "\n"
        "              " + SVG(P_EYEON, w='20', h='20', extra='class="eye-open"') + "\n"
        "            </button>\n"
        "          </div>\n"
        "        </div>\n"
        "        <button type=\"submit\" class=\"btn-login\">" + SVG(P_CHECKCIRCLE) + " Cambiar Contraseña</button>\n"
        "      </form>\n"
        "    </div>\n"
        "  </div>\n"
        "  <script src=\"{% static 'js/cambiar_password_temporal.js' %}\"></script>\n"
        "</body>\n"
        "</html>\n"
    )


# ============================================================
# UTILIDADES
# ============================================================
def backup(path):
    bak = f'{path}.bak_{STAMP}'
    try:
        shutil.copy2(path, bak)
        return bak
    except Exception as e:
        print(f"     ⚠ No se pudo crear backup: {e}")
        return None


def escribir(path, contenido, etiqueta='archivo'):
    full = os.path.join(RAIZ, path)
    os.makedirs(os.path.dirname(full) or '.', exist_ok=True)
    existe = os.path.isfile(full)
    if existe:
        bak = backup(full)
        if bak:
            print(f"  ✓ Backup: {os.path.basename(bak)}")
    try:
        with open(full, 'w', encoding='utf-8', newline='\n') as f:
            f.write(contenido)
        print(f"  ✓ {'Actualizado' if existe else 'Creado'}: {path}")
        return True
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        return False


def actualizar_css_iconos():
    full = os.path.join(RAIZ, PATH_CSS_ICON)
    if not os.path.isfile(full):
        print(f"  ✗ NO EXISTE: {PATH_CSS_ICON}")
        return False
    with open(full, 'r', encoding='utf-8') as f:
        txt = f.read()
    if 'ANTI-CONFLICTO + ICONOS FALTANTES' in txt:
        print(f"  ⓘ Ya tiene el bloque. Sin cambios.")
        return True
    bak = backup(full)
    if bak:
        print(f"  ✓ Backup: {os.path.basename(bak)}")
    if not txt.endswith('\n'):
        txt += '\n'
    txt += CSS_ICONOS_EXTRA
    with open(full, 'w', encoding='utf-8', newline='\n') as f:
        f.write(txt)
    print(f"  ✓ Actualizado: {PATH_CSS_ICON}")
    return True


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 70)
    print(" aplicar_final.py  —  fix de iconos en los TEMPLATES REALES")
    print("=" * 70)
    print(f"Raíz: {RAIZ}\n")

    if not os.path.isfile(os.path.join(RAIZ, 'manage.py')):
        print("⚠  No encuentro manage.py. ¿Estás en la raíz del proyecto?")
        return 1

    # Verificar que los archivos destino existan
    print("Verificando rutas destino:")
    for p in (PATH_ADMIN_TPL, PATH_PWD_TPL, PATH_CSS_ICON):
        full = os.path.join(RAIZ, p)
        marca = "✓" if os.path.isfile(full) else "✗"
        print(f"  {marca} {p}")
    print()

    # Confirmación
    print("Se va a hacer BACKUP y MODIFICAR:")
    print(f"  1. {PATH_ADMIN_TPL}")
    print(f"  2. {PATH_PWD_TPL}")
    print(f"  3. {PATH_CSS_ICON}")
    print(f"\nY crear los archivos nuevos:")
    print(f"  4. {PATH_CSS_ADMIN}")
    print(f"  5. {PATH_JS_ADMIN}")
    print(f"  6. {PATH_CSS_PWD}")
    print(f"  7. {PATH_JS_PWD}")
    print()
    r = input("¿Continuar? Escribí 'SI' para confirmar: ").strip()
    if r != 'SI':
        print("Cancelado.")
        return 0

    print()
    print("=" * 70)
    print(" APLICANDO")
    print("=" * 70)

    print("\n[1] CSS de iconos (3jjja-icons-mask.css):")
    actualizar_css_iconos()

    print("\n[2] Template admin_usuarios.html:")
    escribir(PATH_ADMIN_TPL, build_admin_template())

    print("\n[3] Template cambiar_password_temporal.html:")
    escribir(PATH_PWD_TPL, build_pwd_template())

    print("\n[4] Archivos estáticos nuevos:")
    escribir(PATH_CSS_ADMIN, CSS_ADMIN)
    escribir(PATH_JS_ADMIN, JS_ADMIN)
    escribir(PATH_CSS_PWD, CSS_PWD)
    escribir(PATH_JS_PWD, JS_PWD)

    print()
    print("=" * 70)
    print(" ✔ LISTO")
    print(f" Backups: *.bak_{STAMP}")
    print()
    print(" PRÓXIMOS PASOS:")
    print("   1) python manage.py collectstatic --noinput")
    print("   2) Ctrl + Shift + R  en el navegador (recarga forzada)")
    print("   3) Si sigue mal: F12 → Network → recargá → buscá")
    print("      '3jjja-icons-mask.css' y verificá que tenga el bloque nuevo al final.")
    print("=" * 70)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelado.")
        sys.exit(130)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)