/* ============================================================
   password-limits.js
   Impone MIN=8 y MAX=12 caracteres en TODOS los campos de
   contraseña del sistema (login, registro, admin, cambio de
   contraseña temporal, etc.) de forma defensiva.
   - No modifica ninguna lógica existente.
   - Se aplica también a campos creados dinámicamente (modales).
   ============================================================ */
(function () {
    'use strict';

    var MIN_PASS = 8;
    var MAX_PASS = 12;

    function aplicarLimite(input) {
        if (!input || input.dataset.passLimitBound === '1') return;

        input.setAttribute('maxlength', MAX_PASS);
        if (!input.hasAttribute('minlength')) {
            input.setAttribute('minlength', MIN_PASS);
        }

        input.addEventListener('input', function () {
            if (this.value.length > MAX_PASS) {
                this.value = this.value.slice(0, MAX_PASS);
            }
        });

        input.addEventListener('paste', function (e) {
            var clipboard = (e.clipboardData || window.clipboardData);
            if (!clipboard) return;
            var pegado = clipboard.getData('text') || '';
            var actual = this.value;
            var ini = this.selectionStart || 0;
            var fin = this.selectionEnd || 0;
            var resultado = actual.slice(0, ini) + pegado + actual.slice(fin);
            if (resultado.length > MAX_PASS) {
                e.preventDefault();
                this.value = resultado.slice(0, MAX_PASS);
            }
        });

        input.dataset.passLimitBound = '1';
    }

    function aplicarATodos() {
        var selector = 'input[type="password"], ' +
                       'input[name*="password" i], ' +
                       'input[id*="password" i], ' +
                       'input[name*="contrasenia" i], ' +
                       'input[id*="contrasenia" i]';
        var inputs = document.querySelectorAll(selector);
        for (var i = 0; i < inputs.length; i++) {
            aplicarLimite(inputs[i]);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', aplicarATodos);
    } else {
        aplicarATodos();
    }

    if (window.MutationObserver) {
        document.addEventListener('DOMContentLoaded', function () {
            var observer = new MutationObserver(function () {
                aplicarATodos();
            });
            observer.observe(document.body, { childList: true, subtree: true });
        });
    }
})();
