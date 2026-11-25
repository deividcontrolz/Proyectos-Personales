# -*- coding: utf-8 -*-
"""
MusiKat - Reproductor de musica (VERSION CORREGIDA 2)
=====================================================
Pensado para maquinas modestas (Canaima / Windows 7 / Python 3.8 o menor):
no usa nada que no exista en Python 3.8 ni en pygame 1.9/2.x.

Correcciones de rendimiento de la v1 (se conservan):
1. La duracion se lee con mutagen (solo metadatos, ~1 ms por cancion)
   en vez de pygame.mixer.Sound(), que decodificaba el MP3 COMPLETO
   en memoria (~35 MB por cancion) -> agotaba la RAM.
2. Un solo ThreadPoolExecutor con 4 trabajadores en vez de lanzar
   UN HILO POR CANCION (cientos de hilos decodificando a la vez
   colgaban el programa).
3. Las filas de la lista se crean POR LOTES con root.after(), asi la
   interfaz nunca se congela al cargar carpetas grandes. Ademas se
   muestra un contador "Cargando...".

Correcciones de bugs de la v2:
4. playlist_songs tiene indice UNICO (playlist_id, path) y las claves
   foraneas se activan con PRAGMA foreign_keys = ON. Antes el
   "INSERT OR IGNORE" no ignoraba nada (se duplicaban canciones) y el
   "ON DELETE CASCADE" no borraba nada (quedaban filas huerfanas).
   Se limpian los duplicados/huerfanos que hubieran quedado.
5. Ningun hilo de trabajo toca widgets de Tkinter (no es thread-safe):
   los resultados pasan por una queue.Queue y el hilo principal los
   aplica con root.after(). Antes se llamaba label.after() desde los
   hilos, lo que puede colgar la app de forma aleatoria.
6. El progreso ya no usa get_pos() a secas (devuelve tiempo transcurrido
   desde el play, sin contar el offset del seek): se lleva pos_base y se
   corrige tambien al pausar. Antes la barra retrocedia al hacer seek.
7. El estado de reproduccion es explicito (detenido/reproduciendo/pausado)
   en vez de deducirse del texto del boton, y el fin de cancion se detecta
   con get_busy() sobre ese estado (con margen tras el play). No se usa
   pygame.event, que exigiria inicializar el subsistema de video de SDL.
8. El resaltado de la fila activa usa un mapa idx -> fila, no el orden de
   winfo_children() (que incluia el label "Cargando..." y desplazaba todo).
9. El escaneo de carpetas corre en un hilo: en un disco lento o una carpeta
   de red ya no se congela la ventana.
10. Los errores ya no se silencian con "except: pass": se registran en
    musikat.log (con codificacion UTF-8 explicita para Windows).
11. La base de datos y la config viven en el directorio de datos del
    usuario (APPDATA en Windows), no junto al .exe, que puede estar en una
    carpeta de solo lectura: antes la app "olvidaba" todo sin avisar.
    Los archivos de la v1 se migran automaticamente si existen.
12. Al cerrar se cancelan las tareas pendientes del pool (sin depender de
    cancel_futures, que no existe en Python 3.8).
13. El audio se carga tambien desde un file object: en Windows 7 con
    pygame antiguo, los temas con tildes o enie fallaban al abrir.

Playlists (v3):
14. Crear playlists con el nombre que el usuario escriba, desde un boton
    visible en la barra lateral (antes solo estaba el "+" pequeno de la
    cabecera PLAYLISTS, facil de no ver).
15. Renombrar una playlist desde el menu contextual (clic derecho), con
    aviso si el nombre ya esta usado.
"""

import json
import logging
import os
import queue
import shutil
import sqlite3
import sys

import pygame
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from concurrent.futures import ThreadPoolExecutor

# mutagen: lectura rapida de metadatos  ->  pip install mutagen
try:
    from mutagen.mp3 import MP3
    MUTAGEN_DISPONIBLE = True
except ImportError:
    MUTAGEN_DISPONIBLE = False

# ============================================================
# RUTAS COMPATIBLES CON .EXE (PyInstaller) Y DESARROLLO
# ============================================================
def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


def get_data_dir():
    """Carpeta de datos del usuario. La carpeta del .exe puede ser de solo
    lectura (Program Files, o el propio instalador de la Canaima): escribir
    ahi hacia que se perdieran la config y las playlists sin ningun aviso."""
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        destino = os.path.join(base, "MusiKat")
    elif sys.platform == "darwin":
        destino = os.path.join(os.path.expanduser("~/Library/Application Support"),
                               "MusiKat")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.join(
            os.path.expanduser("~"), ".local", "share")
        destino = os.path.join(base, "musikat")
    try:
        os.makedirs(destino, exist_ok=True)
    except OSError:
        destino = get_app_dir()
    return destino


APP_DIR = get_app_dir()
DATA_DIR = get_data_dir()
DB_PATH = os.path.join(DATA_DIR, "musikat.db")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
LOG_PATH = os.path.join(DATA_DIR, "musikat.log")


def configurar_log():
    """Log a archivo. En Windows 7 el FileHandler usa la codificacion del
    sistema (cp1252) y cualquier ruta con tildes reventaba; de ahi el
    encoding explicito."""
    try:
        handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    except OSError:
        logging.basicConfig(level=logging.INFO)
        logging.warning("No se pudo abrir %s; el log va a stderr", LOG_PATH)
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[handler],
    )


def migrar_datos_antiguos():
    """La v1 guardaba musikat.db y config.json junto al .exe. Si existen y
    todavia no hay nada en el directorio de datos, se mueven para no perder
    las playlists del usuario."""
    if os.path.abspath(DATA_DIR) == os.path.abspath(APP_DIR):
        return
    for nombre in ("musikat.db", "config.json"):
        viejo = os.path.join(APP_DIR, nombre)
        nuevo = os.path.join(DATA_DIR, nombre)
        if os.path.exists(viejo) and not os.path.exists(nuevo):
            try:
                shutil.move(viejo, nuevo)
                logging.info("Migrado %s -> %s", viejo, nuevo)
            except (OSError, shutil.Error):
                logging.exception("No se pudo migrar %s", viejo)


configurar_log()
migrar_datos_antiguos()

# ============================================================
# CONFIGURACION DE COLORES - ESTILO YOUTUBE MUSIC + MORADO
# ============================================================
COLORS = {
    "bg_primary": "#0f0f0f",
    "bg_sidebar": "#000000",
    "bg_card": "#1f1f1f",
    "bg_hover": "#2a2a2a",
    "bg_player": "#181818",
    "accent": "#8b5cf6",
    "accent_light": "#a78bfa",
    "accent_dark": "#7c3aed",
    "text_primary": "#ffffff",
    "text_secondary": "#b3b3b3",
    "border": "#272727",
    "progress_bg": "#4d4d4d",
    "progress_fill": "#8b5cf6",
}

# Cuantos hilos leen metadatos a la vez. En un Atom de una sola alma mas de
# 4 no aporta nada y solo compite por el disco.
MAX_HILOS_METADATOS = 4

# ============================================================
# INICIALIZACION PYGAME (audio)
# ============================================================
AUDIO_DISPONIBLE = False
try:
    # buffer mas grande que 512: en equipos viejos 512 provocaba cortes.
    pygame.mixer.pre_init(44100, -16, 2, 1024)
    pygame.mixer.init()
    AUDIO_DISPONIBLE = True
except Exception:
    logging.exception("Error inicializando pygame (la app abre sin audio)")

# ============================================================
# BASE DE DATOS SQLITE (playlists)
# ============================================================
def _connect():
    """Todas las conexiones activan las claves foraneas. Sin este PRAGMA el
    ON DELETE CASCADE no hace nada y borrar una playlist dejaba sus filas
    para siempre."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = _connect()
    try:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS playlist_songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                playlist_id INTEGER NOT NULL,
                path TEXT NOT NULL,
                FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE
            )
        """)
        c.execute("INSERT OR IGNORE INTO playlists (name) VALUES ('Favoritos')")
        # Limpieza de lo que dejo la v1 (sin indice unico y sin FK).
        c.execute("""
            DELETE FROM playlist_songs WHERE id NOT IN (
                SELECT MIN(id) FROM playlist_songs GROUP BY playlist_id, path
            )
        """)
        c.execute("""
            DELETE FROM playlist_songs WHERE playlist_id NOT IN (
                SELECT id FROM playlists
            )
        """)
        # A partir de aqui, INSERT OR IGNORE si funciona y el CASCADE tambien.
        c.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_playlist_songs_unique
            ON playlist_songs (playlist_id, path)
        """)
        conn.commit()
    finally:
        conn.close()


def get_playlists():
    try:
        conn = _connect()
        try:
            c = conn.cursor()
            c.execute("SELECT id, name FROM playlists ORDER BY name")
            return c.fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        logging.exception("No se pudieron leer las playlists")
        return []


def create_playlist(name):
    """Devuelve el id, o None si ya existe una playlist con ese nombre."""
    conn = _connect()
    try:
        c = conn.cursor()
        c.execute("INSERT INTO playlists (name) VALUES (?)", (name,))
        conn.commit()
        return c.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def rename_playlist(pid, name):
    """Devuelve True si se renombro, False si ya hay otra playlist con ese
    nombre (la columna name es UNIQUE)."""
    conn = _connect()
    try:
        cur = conn.execute("UPDATE playlists SET name = ? WHERE id = ?", (name, pid))
        conn.commit()
        return cur.rowcount > 0
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def delete_playlist(pid):
    conn = _connect()
    try:
        conn.execute("DELETE FROM playlists WHERE id = ?", (pid,))
        conn.commit()
    finally:
        conn.close()


def get_playlist_songs(pid):
    conn = _connect()
    try:
        c = conn.cursor()
        c.execute("SELECT path FROM playlist_songs WHERE playlist_id = ? ORDER BY id", (pid,))
        rows = [r[0] for r in c.fetchall()]
        return rows
    finally:
        conn.close()


def add_song_to_playlist(pid, path):
    """Devuelve True si se agrego, False si ya estaba (antes se duplicaba)."""
    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT OR IGNORE INTO playlist_songs (playlist_id, path) VALUES (?, ?)",
            (pid, path))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def remove_song_from_playlist(pid, path):
    conn = _connect()
    try:
        conn.execute(
            "DELETE FROM playlist_songs WHERE playlist_id = ? AND path = ?",
            (pid, path))
        conn.commit()
    finally:
        conn.close()


# ============================================================
# METADATOS MP3
# ============================================================
def get_mp3_duration(path):
    """mutagen lee solo los metadatos (rapido, casi sin memoria).

    El respaldo con pygame.mixer.Sound() de la v1 decodificaba el MP3
    completo en RAM (~35 MB por cancion) y era justo el bug que agotaba la
    memoria, asi que ya no se usa: si mutagen no esta, se devuelve 0 y la
    fila muestra "--:--".
    """
    if not MUTAGEN_DISPONIBLE:
        return 0.0
    try:
        return float(MP3(path).info.length)
    except Exception as e:
        # Hay MP3 rotos, VBR sin cabecera, etc. Se registra y se sigue.
        logging.warning("Duracion ilegible en %s (%s)", path, e)
        return 0.0


def format_time(seconds):
    m = int(seconds // 60)
    s = int(seconds % 60)
    return "{0}:{1:02d}".format(m, s)


def get_filename(path):
    return os.path.splitext(os.path.basename(path))[0]


# ============================================================
# APLICACION PRINCIPAL
# ============================================================
class MusiKatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MusiKat")
        self.root.geometry("900x600")
        self.root.configure(bg=COLORS["bg_primary"])
        self.root.minsize(800, 500)

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TScrollbar", background=COLORS["bg_card"],
                          troughcolor=COLORS["bg_primary"], bordercolor=COLORS["bg_primary"])

        self.cancion_actual = None
        self.canciones = []
        self.indice_actual = -1
        self.modo_repetir = False
        self.modo_aleatorio = False
        self.volumen = 1.0
        self.current_view = "inicio"
        self.current_playlist_id = None
        self.running = True
        self.after_id = None
        self.after_id_cola = None

        # >>> CORREGIDO: estado explicito en vez de mirar el texto del boton.
        self.estado = "detenido"          # detenido | reproduciendo | pausado
        self.duracion_total = 0.0
        self._pos_base = 0.0              # offset del seek (bug del progreso)
        self._pos_pausa = 0.0
        self._ticks_desde_play = 0
        self._archivo_audio = None

        # >>> CORREGIDO: pool acotado para metadatos (antes: 1 hilo por cancion).
        self.executor = ThreadPoolExecutor(max_workers=MAX_HILOS_METADATOS,
                                           thread_name_prefix="musikat")
        # >>> CORREGIDO: los hilos dejan resultados aqui y solo el hilo
        #     principal toca Tkinter.
        self.cola = queue.Queue()
        self._futuros = set()

        # Contadores de generacion: invalidan lotes y escaneos pendientes.
        self._carga_gen = 0
        self._scan_gen = 0
        self.lbl_cargando = None
        self.filas = {}                   # idx -> {"frame":..., "duracion":...}

        # INICIALIZAR BASE DE DATOS ANTES DE CONSTRUIR LA UI
        init_db()

        self.build_ui()
        self.start_progress_loop()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        if not MUTAGEN_DISPONIBLE:
            self.root.after(300, self._avisar_mutagen)

    def _avisar_mutagen(self):
        messagebox.showwarning(
            "Falta mutagen",
            "No se pudo importar mutagen, asi que no se mostraran las "
            "duraciones de las canciones.\n\nInstalalo con:\n\n"
            "    pip install mutagen",
            parent=self.root)

    def build_ui(self):
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        # SIDEBAR
        self.sidebar = tk.Frame(self.root, bg=COLORS["bg_sidebar"], width=200)
        self.sidebar.grid(row=0, column=0, sticky="nswe")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(5, weight=1)

        logo_frame = tk.Frame(self.sidebar, bg=COLORS["bg_sidebar"], height=60)
        logo_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))
        logo = tk.Label(logo_frame, text="MusiKat", font=("Segoe UI", 18, "bold"),
                       bg=COLORS["bg_sidebar"], fg=COLORS["accent_light"])
        logo.pack(anchor="w")

        sep = tk.Frame(self.sidebar, bg=COLORS["border"], height=1)
        sep.grid(row=1, column=0, sticky="ew", padx=15, pady=10)

        self.nav_buttons = []
        self.btn_inicio = self.create_nav_button("Inicio", 2, lambda: self.show_inicio())
        self.btn_biblioteca = self.create_nav_button("Biblioteca", 3, lambda: self.show_biblioteca())

        playlist_header = tk.Frame(self.sidebar, bg=COLORS["bg_sidebar"])
        playlist_header.grid(row=4, column=0, sticky="ew", padx=15, pady=(20, 5))
        tk.Label(playlist_header, text="PLAYLISTS", font=("Segoe UI", 9, "bold"),
                bg=COLORS["bg_sidebar"], fg=COLORS["text_secondary"]).pack(side="left")
        btn_add_pl = tk.Label(playlist_header, text="+", font=("Segoe UI", 14, "bold"),
                             bg=COLORS["bg_sidebar"], fg=COLORS["accent_light"], cursor="hand2")
        btn_add_pl.pack(side="right")
        btn_add_pl.bind("<Button-1>", lambda e: self.crear_playlist())

        pl_container = tk.Frame(self.sidebar, bg=COLORS["bg_sidebar"])
        pl_container.grid(row=5, column=0, sticky="nswe", padx=15, pady=5)
        pl_container.grid_rowconfigure(0, weight=1)
        pl_container.grid_columnconfigure(0, weight=1)

        self.pl_canvas = tk.Canvas(pl_container, bg=COLORS["bg_sidebar"], highlightthickness=0)
        self.pl_canvas.grid(row=0, column=0, sticky="nswe")
        pl_scroll = ttk.Scrollbar(pl_container, orient="vertical", command=self.pl_canvas.yview)
        pl_scroll.grid(row=0, column=1, sticky="ns")
        self.pl_canvas.configure(yscrollcommand=pl_scroll.set)

        self.pl_list_frame = tk.Frame(self.pl_canvas, bg=COLORS["bg_sidebar"])
        self.pl_canvas.create_window((0, 0), window=self.pl_list_frame, anchor="nw", width=170)
        self.pl_list_frame.bind("<Configure>", lambda e: self.pl_canvas.configure(scrollregion=self.pl_canvas.bbox("all")))

        self.refresh_playlists_sidebar()

        # >>> NUEVO: boton visible para crear playlists. El nombre lo escribe
        #     el usuario en el dialogo.
        self.btn_nueva_playlist = tk.Label(self.sidebar, text="+  Nueva playlist",
                                          font=("Segoe UI", 10),
                                          bg=COLORS["bg_sidebar"], fg=COLORS["accent_light"],
                                          padx=15, pady=8, cursor="hand2", anchor="w")
        self.btn_nueva_playlist.grid(row=6, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.btn_nueva_playlist.bind(
            "<Enter>", lambda e: self.btn_nueva_playlist.config(bg=COLORS["bg_hover"]))
        self.btn_nueva_playlist.bind(
            "<Leave>", lambda e: self.btn_nueva_playlist.config(bg=COLORS["bg_sidebar"]))
        self.btn_nueva_playlist.bind("<Button-1>", lambda e: self.crear_playlist())

        # CONTENIDO
        self.content = tk.Frame(self.root, bg=COLORS["bg_primary"])
        self.content.grid(row=0, column=1, sticky="nswe")
        self.content.grid_rowconfigure(1, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.header = tk.Frame(self.content, bg=COLORS["bg_primary"], height=60)
        self.header.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 0))
        self.header.grid_propagate(False)
        self.header.grid_columnconfigure(0, weight=1)

        self.header_title = tk.Label(self.header, text="Inicio", font=("Segoe UI", 20, "bold"),
                                    bg=COLORS["bg_primary"], fg=COLORS["text_primary"])
        self.header_title.grid(row=0, column=0, sticky="w")

        self.btn_add_folder = tk.Label(self.header, text="Agregar carpeta", font=("Segoe UI", 10),
                                      bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                                      padx=12, pady=6, cursor="hand2")
        self.btn_add_folder.grid(row=0, column=1, sticky="e")
        self.btn_add_folder.bind("<Enter>", lambda e: self.btn_add_folder.config(bg=COLORS["bg_hover"]))
        self.btn_add_folder.bind("<Leave>", lambda e: self.btn_add_folder.config(bg=COLORS["bg_card"]))
        self.btn_add_folder.bind("<Button-1>", lambda e: self.agregar_carpeta())

        songs_container = tk.Frame(self.content, bg=COLORS["bg_primary"])
        songs_container.grid(row=1, column=0, sticky="nswe", padx=20, pady=10)
        songs_container.grid_rowconfigure(0, weight=1)
        songs_container.grid_columnconfigure(0, weight=1)

        self.songs_canvas = tk.Canvas(songs_container, bg=COLORS["bg_primary"], highlightthickness=0)
        self.songs_canvas.grid(row=0, column=0, sticky="nswe")
        songs_scroll = ttk.Scrollbar(songs_container, orient="vertical", command=self.songs_canvas.yview)
        songs_scroll.grid(row=0, column=1, sticky="ns")
        self.songs_canvas.configure(yscrollcommand=songs_scroll.set)

        self.songs_frame = tk.Frame(self.songs_canvas, bg=COLORS["bg_primary"])
        self.songs_canvas.create_window((0, 0), window=self.songs_frame, anchor="nw", width=660)
        self.songs_frame.bind("<Configure>", lambda e: self.songs_canvas.configure(scrollregion=self.songs_canvas.bbox("all")))

        self.refresh_playlists_sidebar()
        self._vincular_rueda(self.pl_canvas, self.pl_canvas)
        self._vincular_rueda(self.pl_list_frame, self.pl_canvas)
        # PLAYER BAR
        self.player_bar = tk.Frame(self.root, bg=COLORS["bg_player"], height=90)
        self.player_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.player_bar.grid_propagate(False)
        self.player_bar.grid_columnconfigure(1, weight=1)

        self.info_frame = tk.Frame(self.player_bar, bg=COLORS["bg_player"], width=220)
        self.info_frame.grid(row=0, column=0, sticky="nswe", padx=15, pady=10)
        self.info_frame.grid_propagate(False)

        self.lbl_song_title = tk.Label(self.info_frame, text="MusiKat", font=("Segoe UI", 11, "bold"),
                                      bg=COLORS["bg_player"], fg=COLORS["accent_light"], anchor="w", wraplength=200)
        self.lbl_song_title.pack(anchor="w")

        self.lbl_song_artist = tk.Label(self.info_frame, text="Selecciona una cancion", font=("Segoe UI", 9),
                                       bg=COLORS["bg_player"], fg=COLORS["text_secondary"], anchor="w")
        self.lbl_song_artist.pack(anchor="w", pady=(2, 0))

        controls_frame = tk.Frame(self.player_bar, bg=COLORS["bg_player"])
        controls_frame.grid(row=0, column=1, sticky="nswe", pady=8)
        controls_frame.grid_rowconfigure(1, weight=1)

        btn_frame = tk.Frame(controls_frame, bg=COLORS["bg_player"])
        btn_frame.pack()

        self.btn_shuffle = self.create_control_button(btn_frame, "aleatorio.png", self.toggle_shuffle)
        self.btn_prev = self.create_control_button(btn_frame, "anterior.png", self.cancion_anterior)
        self.btn_play = self.create_control_button(btn_frame, "play.png", self.toggle_play, big=True)
        self.btn_next = self.create_control_button(btn_frame, "siguiente.png", self.cancion_siguiente)
        self.btn_repeat = self.create_control_button(btn_frame, "repetir.png", self.toggle_repeat)

        progress_frame = tk.Frame(controls_frame, bg=COLORS["bg_player"])
        progress_frame.pack(fill="x", padx=40, pady=(5, 0))

        self.lbl_time_current = tk.Label(progress_frame, text="0:00", font=("Segoe UI", 9),
                                          bg=COLORS["bg_player"], fg=COLORS["text_secondary"])
        self.lbl_time_current.pack(side="left")

        self.progress_canvas = tk.Canvas(progress_frame, bg=COLORS["progress_bg"],
                                        height=4, highlightthickness=0)
        self.progress_canvas.pack(side="left", fill="x", expand=True, padx=10)
        self.progress_canvas.bind("<Button-1>", self.seek_click)

        self.lbl_time_total = tk.Label(progress_frame, text="0:00", font=("Segoe UI", 9),
                                        bg=COLORS["bg_player"], fg=COLORS["text_secondary"])
        self.lbl_time_total.pack(side="left")

        vol_frame = tk.Frame(self.player_bar, bg=COLORS["bg_player"], width=120)
        vol_frame.grid(row=0, column=2, sticky="nswe", padx=15, pady=10)
        vol_frame.grid_propagate(False)

        self.lbl_vol = tk.Label(vol_frame, text="Vol", font=("Segoe UI", 10),
                                 bg=COLORS["bg_player"], fg=COLORS["text_primary"])
        self.lbl_vol.pack(side="left", padx=(0, 5))

        self.vol_scale = tk.Scale(vol_frame, from_=0, to=100, orient="horizontal",
                                 bg=COLORS["bg_player"], fg=COLORS["accent_light"],
                                 highlightthickness=0, troughcolor=COLORS["bg_card"],
                                 activebackground=COLORS["accent"], sliderlength=12,
                                 width=8, command=self.cambiar_volumen, showvalue=0)
        self.vol_scale.set(100)
        self.vol_scale.pack(side="left", fill="x", expand=True)

    def create_nav_button(self, text, row, command):
        btn = tk.Label(self.sidebar, text=text, font=("Segoe UI", 11),
                      bg=COLORS["bg_sidebar"], fg=COLORS["text_secondary"],
                      padx=15, pady=8, cursor="hand2", anchor="w")
        btn.grid(row=row, column=0, sticky="ew", padx=10, pady=2)
        btn.bind("<Enter>", lambda e, b=btn: b.config(bg=COLORS["bg_hover"], fg=COLORS["text_primary"]))
        btn.bind("<Leave>", lambda e, b=btn: b.config(bg=COLORS["bg_sidebar"], fg=COLORS["text_secondary"]))
        btn.bind("<Button-1>", lambda e: command())
        self.nav_buttons.append(btn)
        return btn

    def create_control_button(self, parent, image_name, command, big=False):
        image_path = os.path.join(APP_DIR, "img", image_name)
        img = None
        
        # Verificamos si el archivo realmente existe en esa ruta
        if os.path.exists(image_path):
            try:
                img = tk.PhotoImage(file=image_path)
                
                # Aplica tu factor de reducción aquí (ej: factor 4 o 5)
                factor = 6
                img = img.subsample(factor, factor)
            except Exception as e:
                print(f"Error cargando la imagen {image_name}: {e}")
        else:
            print(f"¡ATENCIÓN! No se encontró la imagen en la ruta: {image_path}")

        btn = tk.Label(parent, image=img,
                      bg=COLORS["bg_player"],
                      cursor="hand2",
                      padx=2, pady=2)
        
        # Guardamos la referencia para evitar al recolector de basura
        btn.image = img 
        btn.pack(side="left", padx=6)
        
        btn.bind("<Enter>", lambda e, b=btn: b.config(bg=COLORS["bg_hover"]))
        btn.bind("<Leave>", lambda e, b=btn: b.config(bg=COLORS["bg_player"]))
        btn.bind("<Button-1>", lambda e: command())
        return btn

    def show_inicio(self):
        self.current_view = "inicio"
        self.current_playlist_id = None
        self.header_title.config(text="Inicio")
        self.btn_add_folder.config(text="Agregar carpeta")
        self.btn_add_folder.bind("<Button-1>", lambda e: self.agregar_carpeta())
        self.cargar_canciones_ultima_carpeta()

    def show_biblioteca(self):
        self.current_view = "biblioteca"
        self.current_playlist_id = None
        self.header_title.config(text="Biblioteca")
        self.btn_add_folder.config(text="Agregar carpeta")
        self.btn_add_folder.bind("<Button-1>", lambda e: self.agregar_carpeta())
        self.cargar_canciones_ultima_carpeta()

    def show_playlist(self, pid, name):
        self.current_view = "playlist"
        self.current_playlist_id = pid
        self.header_title.config(text=name)
        self.btn_add_folder.config(text="Agregar cancion")
        self.btn_add_folder.bind("<Button-1>", lambda e: self.agregar_cancion_a_playlist())
        songs = get_playlist_songs(pid)
        self.cargar_lista_canciones(songs)

    def refresh_playlists_sidebar(self):
        for widget in self.pl_list_frame.winfo_children():
            widget.destroy()
        playlists = get_playlists()
        for pid, name in playlists:
            pl_btn = tk.Label(self.pl_list_frame, text="  " + name, font=("Segoe UI", 10),
                             bg=COLORS["bg_sidebar"], fg=COLORS["text_secondary"],
                             padx=5, pady=5, cursor="hand2", anchor="w")
            pl_btn.pack(fill="x", pady=1)
            pl_btn.bind("<Enter>", lambda e, b=pl_btn: b.config(bg=COLORS["bg_hover"], fg=COLORS["text_primary"]))
            pl_btn.bind("<Leave>", lambda e, b=pl_btn: b.config(bg=COLORS["bg_sidebar"], fg=COLORS["text_secondary"]))
            pl_btn.bind("<Button-1>", lambda e, p=pid, n=name: self.show_playlist(p, n))
            pl_btn.bind("<Button-3>", lambda e, p=pid, n=name: self.playlist_context_menu(e, p, n))

    def playlist_context_menu(self, event, pid, name):
        menu = tk.Menu(self.root, tearoff=0, bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                      activebackground=COLORS["accent"], activeforeground=COLORS["text_primary"])
        # NUEVO: el nombre de una playlist ya creada tambien se puede cambiar.
        menu.add_command(label="Renombrar playlist",
                        command=lambda: self.renombrar_playlist(pid, name))
        menu.add_separator()
        menu.add_command(label="Eliminar playlist", command=lambda: self.eliminar_playlist(pid))
        menu.tk_popup(event.x_root, event.y_root)

    def crear_playlist(self):
        """Pide el nombre al usuario y crea la playlist con ese nombre."""
        name = simpledialog.askstring("Nueva Playlist",
                                      "Nombre de la playlist:\n"
                                      "(lo eliges tu; por ejemplo: Rock, Bailable, "
                                      "Para la buseta)",
                                      parent=self.root)
        if not name or not name.strip():
            return
        nombre = name.strip()
        
        # Capturamos el ID de la nueva playlist
        nuevo_id = create_playlist(nombre)
        if nuevo_id is None:
            messagebox.showinfo("Playlist existente",
                                "Ya existe una playlist llamada '" + nombre + "'.",
                                parent=self.root)
            return
            
        self.refresh_playlists_sidebar()
        
        # NUEVO: Abrir automáticamente la playlist recién creada
        self.show_playlist(nuevo_id, nombre)

    def renombrar_playlist(self, pid, nombre_actual):
        """Permite cambiar el nombre de una playlist ya creada."""
        nuevo = simpledialog.askstring("Renombrar playlist",
                                       "Nuevo nombre para '" + nombre_actual + "':",
                                       initialvalue=nombre_actual,
                                       parent=self.root)
        if nuevo is None:
            return
        nuevo = nuevo.strip()
        if not nuevo or nuevo == nombre_actual:
            return
        if not rename_playlist(pid, nuevo):
            messagebox.showinfo("Nombre en uso",
                                "Ya existe una playlist llamada '" + nuevo + "'.",
                                parent=self.root)
            return
        self.refresh_playlists_sidebar()
        if self.current_playlist_id == pid:
            self.header_title.config(text=nuevo)

    def eliminar_playlist(self, pid):
        if messagebox.askyesno("Eliminar", "Eliminar esta playlist?"):
            delete_playlist(pid)
            self.refresh_playlists_sidebar()
            if self.current_playlist_id == pid:
                self.show_inicio()

    def agregar_carpeta(self):
        folder = filedialog.askdirectory(title="Seleccionar carpeta de musica")
        if not folder:
            return
        self.guardar_ultima_carpeta(folder)
        self.escanear_carpeta(folder)

    def guardar_ultima_carpeta(self, folder):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump({"last_folder": folder}, f)
        except OSError:
            # >>> CORREGIDO: antes esto se tragaba el error y el usuario no
            #     entendia por que la app "olvidaba" la carpeta.
            logging.exception("No se pudo guardar %s", CONFIG_PATH)

    def cargar_canciones_ultima_carpeta(self):
        folder = ""
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                folder = json.load(f).get("last_folder", "")
        except (OSError, ValueError):
            logging.exception("No se pudo leer %s", CONFIG_PATH)
        if folder and os.path.exists(folder):
            self.escanear_carpeta(folder)
            return
        self.limpiar_lista_canciones()
        self.mostrar_mensaje_vacio("Agrega una carpeta para empezar")

    # --------------------------------------------------------
    # ESCANEO EN SEGUNDO PLANO
    # --------------------------------------------------------
    def escanear_carpeta(self, folder):
        """>>> CORREGIDO: os.walk en un hilo. En un disco lento o una carpeta
        de red, recorrerla en el hilo de la interfaz congelaba la ventana."""
        self.limpiar_lista_canciones()
        self._scan_gen += 1
        gen = self._scan_gen
        self.mostrar_mensaje_vacio("Buscando archivos MP3...")
        self._enviar(self._trabajo_escaneo, gen, folder)

    def _trabajo_escaneo(self, gen, folder):
        """Hilo de trabajo: no toca ningun widget."""
        paths = []
        try:
            for root_dir, dirs, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith(".mp3"):
                        paths.append(os.path.join(root_dir, file))
        except Exception:
            # Nunca dejar el aviso "Buscando..." colgado para siempre.
            logging.exception("Error escaneando %s", folder)
        self.cola.put(("escaneo", gen, paths))

    def _trabajo_duracion(self, gen, idx, path):
        """Hilo de trabajo: no toca ningun widget."""
        dur = get_mp3_duration(path)
        self.cola.put(("duracion", gen, idx, dur))

    def _enviar(self, fn, *args):
        futuro = self.executor.submit(fn, *args)
        self._futuros.add(futuro)
        futuro.add_done_callback(self._futuros.discard)
        return futuro

    def _procesar_cola(self):
        """>>> CORREGIDO: los resultados de los hilos se aplican aqui, en el
        hilo principal. Tkinter no es thread-safe."""
        if not self.running:
            return
        procesados = 0
        while procesados < 400:
            try:
                msg = self.cola.get_nowait()
            except queue.Empty:
                break
            procesados += 1
            try:
                if msg[0] == "duracion":
                    _, gen, idx, dur = msg
                    if gen != self._carga_gen:
                        continue
                    fila = self.filas.get(idx)
                    if fila is None:
                        continue
                    fila["duracion"].config(
                        text=format_time(dur) if dur > 0 else "--:--")
                elif msg[0] == "escaneo":
                    _, gen, paths = msg
                    if gen != self._scan_gen:
                        continue
                    if paths:
                        self.cargar_lista_canciones(paths)
                    else:
                        self.limpiar_lista_canciones()
                        self.mostrar_mensaje_vacio("No se encontraron archivos MP3")
            except tk.TclError:
                logging.exception("Widget destruido al aplicar un resultado")
            except Exception:
                # Si algo revienta aqui y se escapa, el bucle de la cola se
                # detendria y la lista dejaria de actualizarse para siempre.
                logging.exception("Error aplicando un resultado de la cola")
        self.after_id_cola = self.root.after(50, self._procesar_cola)

    # --------------------------------------------------------
    # LISTA DE CANCIONES
    # --------------------------------------------------------
    def cargar_lista_canciones(self, paths):
        """Las filas se crean por lotes con root.after() para que la interfaz
        no se congele, y se muestra un contador de progreso."""
        self.limpiar_lista_canciones()
        self.canciones = list(paths)
        if not self.canciones:
            self.mostrar_mensaje_vacio("Sin canciones")
            return
        self._carga_gen += 1
        gen = self._carga_gen
        self.lbl_cargando = tk.Label(self.songs_frame,
                                     text="Cargando {0} canciones...".format(len(self.canciones)),
                                     font=("Segoe UI", 11),
                                     bg=COLORS["bg_primary"], fg=COLORS["accent_light"])
        self.lbl_cargando.pack(pady=20)
        self._cargar_lote(gen, 0)

    def _cargar_lote(self, gen, inicio):
        """Crea FIN_LOTE filas y cede el control a la interfaz con after().
        El numero de generacion (gen) invalida lotes pendientes si el usuario
        cambia de vista mientras se carga."""
        if gen != self._carga_gen:
            return
        FIN_LOTE = 40
        fin = min(inicio + FIN_LOTE, len(self.canciones))
        for i in range(inicio, fin):
            self.crear_fila_cancion(i, self.canciones[i], gen)
        if self.lbl_cargando is not None and self.lbl_cargando.winfo_exists():
            self.lbl_cargando.config(
                text="Cargando... {0}/{1}".format(fin, len(self.canciones)))
        if fin < len(self.canciones):
            self.root.after(1, lambda: self._cargar_lote(gen, fin))
        else:
            if self.lbl_cargando is not None and self.lbl_cargando.winfo_exists():
                self.lbl_cargando.destroy()
            self.lbl_cargando = None

    def limpiar_lista_canciones(self):
        self._carga_gen += 1   # invalida cualquier lote pendiente
        self._scan_gen += 1    # y cualquier escaneo en curso
        for widget in self.songs_frame.winfo_children():
            widget.destroy()
        self.filas.clear()
        self.lbl_cargando = None
        self.canciones = []
        self.indice_actual = -1

    def mostrar_mensaje_vacio(self, msg):
        lbl = tk.Label(self.songs_frame, text=msg, font=("Segoe UI", 12),
                      bg=COLORS["bg_primary"], fg=COLORS["text_secondary"])
        lbl.pack(pady=50)

    def crear_fila_cancion(self, idx, path, gen):
        row = tk.Frame(self.songs_frame, bg=COLORS["bg_card"], height=50)
        row.pack(fill="x", pady=2, padx=5)
        row.pack_propagate(False)
        row.bind("<Enter>", lambda e, i=idx: self._hover_fila(i, True))
        row.bind("<Leave>", lambda e, i=idx: self._hover_fila(i, False))
        row.bind("<Button-1>", lambda e, i=idx: self.reproducir_indice(i))

        num_lbl = tk.Label(row, text=str(idx + 1), font=("Segoe UI", 10),
                          bg=COLORS["bg_card"], fg=COLORS["text_secondary"], width=3)
        num_lbl.pack(side="left", padx=(10, 5))
        num_lbl.bind("<Button-1>", lambda e, i=idx: self.reproducir_indice(i))

        name = get_filename(path)
        name_lbl = tk.Label(row, text=name, font=("Segoe UI", 10),
                           bg=COLORS["bg_card"], fg=COLORS["text_primary"], anchor="w")
        name_lbl.pack(side="left", fill="x", expand=True, padx=5)
        name_lbl.bind("<Button-1>", lambda e, i=idx: self.reproducir_indice(i))

        row.bind("<Button-3>", lambda e, p=path: self.song_context_menu(e, p))
        name_lbl.bind("<Button-3>", lambda e, p=path: self.song_context_menu(e, p))

        dur_lbl = tk.Label(row, text="--:--", font=("Segoe UI", 9),
                          bg=COLORS["bg_card"], fg=COLORS["text_secondary"], width=8)
        dur_lbl.pack(side="right", padx=10)

        # >>> CORREGIDO: mapa idx -> fila, para resaltar sin depender del
        #     orden de winfo_children() (que incluye el label "Cargando...").
        self.filas[idx] = {"frame": row, "duracion": dur_lbl}

        # La duracion se lee en el pool; el resultado se aplica en _procesar_cola.
        self._enviar(self._trabajo_duracion, gen, idx, path)

    def _pintar_fila(self, fila, color):
        try:
            fila.config(bg=color)
            for child in fila.winfo_children():
                child.config(bg=color)
        except tk.TclError:
            logging.exception("No se pudo pintar una fila")

    def _hover_fila(self, idx, dentro):
        info = self.filas.get(idx)
        if info is None:
            return
        if idx == self.indice_actual:
            color = COLORS["accent_dark"]      # el resaltado manda sobre el hover
        else:
            color = COLORS["bg_hover"] if dentro else COLORS["bg_card"]
        self._pintar_fila(info["frame"], color)

    def resaltar_fila_activa(self):
        for idx, info in self.filas.items():
            color = COLORS["accent_dark"] if idx == self.indice_actual else COLORS["bg_card"]
            self._pintar_fila(info["frame"], color)

    def song_context_menu(self, event, path):
        menu = tk.Menu(self.root, tearoff=0, bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                      activebackground=COLORS["accent"], activeforeground=COLORS["text_primary"])
        playlists = get_playlists()
        submenu = tk.Menu(menu, tearoff=0, bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                         activebackground=COLORS["accent"])
        for pid, pname in playlists:
            submenu.add_command(label=pname,
                                command=lambda p=pid: self._agregar_a_playlist(p, path))
        menu.add_cascade(label="Agregar a playlist", menu=submenu)
        if self.current_view == "playlist" and self.current_playlist_id:
            menu.add_command(label="Quitar de esta playlist",
                           command=lambda: self.quitar_de_playlist(path))
        menu.tk_popup(event.x_root, event.y_root)

    def _agregar_a_playlist(self, pid, path):
        # Feedback minimo para saber que paso algo (antes era silencioso).
        if add_song_to_playlist(pid, path):
            # NUEVO: Mensaje de confirmación en la barra inferior
            self.lbl_song_artist.config(text="¡Canción agregada a la playlist!")
        else:
            self.lbl_song_artist.config(text="La canción ya estaba en la playlist")

    def quitar_de_playlist(self, path):
        if self.current_playlist_id:
            remove_song_from_playlist(self.current_playlist_id, path)
            self.show_playlist(self.current_playlist_id, self.header_title.cget("text"))

    def agregar_cancion_a_playlist(self):
        if not self.current_playlist_id:
            return
        path = filedialog.askopenfilename(filetypes=[("MP3", "*.mp3")])
        if path:
            add_song_to_playlist(self.current_playlist_id, path)
            self.show_playlist(self.current_playlist_id, self.header_title.cget("text"))

    def _on_mousewheel(self, event, canvas):
        if event.delta:
            # Windows / macOS
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        else:
            # Linux (Canaima / Debian)
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

    def _vincular_rueda(self, widget, canvas):
        widget.bind("<MouseWheel>", lambda e: self._on_mousewheel(e, canvas))
        widget.bind("<Button-4>", lambda e: self._on_mousewheel(e, canvas))
        widget.bind("<Button-5>", lambda e: self._on_mousewheel(e, canvas))

    # --------------------------------------------------------
    # REPRODUCCION
    # --------------------------------------------------------
    def reproducir_indice(self, idx):
        if 0 <= idx < len(self.canciones):
            self.indice_actual = idx
            self.cancion_actual = self.canciones[idx]
            self.reproducir_cancion(self.cancion_actual)

    def _cargar_audio(self, path):
        """>>> CORREGIDO: en Windows 7 con pygame antiguo, mixer.music.load()
        abre el archivo con la codificacion ANSI del sistema y fallaba con
        nombres que llevan tildes o enie. Cargando desde un file object se
        evita; si el backend no lo acepta, se vuelve a la ruta."""
        try:
            pygame.mixer.music.stop()
        except pygame.error:
            pass
        self._cerrar_archivo_audio()
        fh = None
        try:
            fh = open(path, "rb")
            pygame.mixer.music.load(fh)
            self._archivo_audio = fh   # debe seguir abierto mientras suena
            return
        except (OSError, pygame.error) as e:
            logging.warning("Carga directa fallo en %s (%s); probando por ruta", path, e)
            if fh is not None:
                try:
                    fh.close()
                except OSError:
                    logging.exception("No se pudo cerrar %s", path)
        pygame.mixer.music.load(path)

    def _cerrar_archivo_audio(self):
        if self._archivo_audio is not None:
            try:
                self._archivo_audio.close()
            except OSError:
                logging.exception("No se pudo cerrar el archivo de audio")
            self._archivo_audio = None

    def reproducir_cancion(self, path):
        try:
            self._cargar_audio(path)
            pygame.mixer.music.set_volume(self.volumen)
            pygame.mixer.music.play()
            # >>> CORREGIDO: estado y offsets explicitos (progreso tras seek).
            self.estado = "reproduciendo"
            self._pos_base = 0.0
            self._pos_pausa = 0.0
            self._ticks_desde_play = 0
            name = get_filename(path)
            self.lbl_song_title.config(text=name)
            self.lbl_song_artist.config(text="Reproduciendo...")
            self.btn_play.config(text="Pausa")
            dur = get_mp3_duration(path)
            self.duracion_total = dur
            self.lbl_time_total.config(text=format_time(dur) if dur > 0 else "--:--")
            self.lbl_time_current.config(text="0:00")
            self._dibujar_progreso(0.0)
            self.resaltar_fila_activa()
        except Exception as e:
            logging.exception("No se pudo reproducir %s", path)
            self.estado = "detenido"
            self.lbl_song_artist.config(text="Error: " + str(e))

    def _posicion_actual(self):
        """>>> CORREGIDO: get_pos() devuelve el tiempo transcurrido desde el
        play() y NO tiene en cuenta el offset del seek, asi que se suma
        _pos_base. En pausa se devuelve la posicion congelada."""
        if self.estado == "pausado":
            return self._pos_pausa
        if self.estado != "reproduciendo":
            return 0.0
        ms = pygame.mixer.music.get_pos()
        if ms < 0:
            return max(0.0, self._pos_base)
        pos = self._pos_base + ms / 1000.0
        if self.duracion_total > 0:
            pos = min(pos, self.duracion_total)
        return max(0.0, pos)

    def _dibujar_progreso(self, ratio):
        ratio = max(0.0, min(1.0, ratio))
        width = self.progress_canvas.winfo_width()
        self.progress_canvas.delete("all")
        if width <= 1:
            return
        self.progress_canvas.create_rectangle(0, 0, width * ratio, 4,
                                            fill=COLORS["progress_fill"], outline="")
        self.progress_canvas.create_rectangle(width * ratio, 0, width, 4,
                                            fill=COLORS["progress_bg"], outline="")

    def toggle_play(self):
        if not AUDIO_DISPONIBLE:
            self.lbl_song_artist.config(text="Sin dispositivo de audio")
            return
        if not self.cancion_actual:
            if self.canciones:
                self.reproducir_indice(0)
            return
        if self.estado == "reproduciendo":
            self._pos_pausa = self._posicion_actual()
            pygame.mixer.music.pause()
            self.estado = "pausado"
            self.btn_play.config(text="Play")
            self.lbl_song_artist.config(text="Pausado")
        elif self.estado == "pausado":
            pygame.mixer.music.unpause()
            ms = pygame.mixer.music.get_pos()
            # Reajustar el offset: get_pos no se detiene durante la pausa.
            self._pos_base = self._pos_pausa - (ms / 1000.0 if ms >= 0 else 0.0)
            self.estado = "reproduciendo"
            self.btn_play.config(text="Pausa")
            self.lbl_song_artist.config(text="Reproduciendo...")
        else:
            self.reproducir_cancion(self.cancion_actual)

    def cancion_siguiente(self):
        if not self.canciones:
            return
        if self.modo_aleatorio:
            import random
            idx = random.randint(0, len(self.canciones) - 1)
        else:
            idx = self.indice_actual + 1
            if idx >= len(self.canciones):
                idx = 0
        self.reproducir_indice(idx)

    def cancion_anterior(self):
        if not self.canciones:
            return
        idx = self.indice_actual - 1
        if idx < 0:
            idx = len(self.canciones) - 1
        self.reproducir_indice(idx)

    def toggle_shuffle(self):
        self.modo_aleatorio = not self.modo_aleatorio
        color = COLORS["accent_light"] if self.modo_aleatorio else COLORS["text_primary"]
        self.btn_shuffle.config(fg=color)

    def toggle_repeat(self):
        self.modo_repetir = not self.modo_repetir
        color = COLORS["accent_light"] if self.modo_repetir else COLORS["text_primary"]
        self.btn_repeat.config(fg=color)

    def cambiar_volumen(self, val):
        self.volumen = int(val) / 100.0
        try:
            pygame.mixer.music.set_volume(self.volumen)
        except pygame.error:
            logging.exception("No se pudo cambiar el volumen")

    def seek_click(self, event):
        if self.estado == "detenido" or not self.cancion_actual or self.duracion_total <= 0:
            return
        width = max(1, self.progress_canvas.winfo_width())
        ratio = max(0.0, min(1.0, event.x / width))
        objetivo = ratio * self.duracion_total
        try:
            pygame.mixer.music.set_pos(objetivo)
        except pygame.error:
            # set_pos no esta soportado en todos los formatos/backends.
            logging.warning("Seek no soportado para este archivo")
            return
        ms = pygame.mixer.music.get_pos()
        # >>> CORREGIDO: fijar el offset para que el contador siga desde aqui
        #     y no vuelva a cero (el bug del progreso tras el seek).
        self._pos_base = objetivo - (ms / 1000.0 if ms >= 0 else 0.0)
        self._pos_pausa = objetivo
        self.lbl_time_current.config(text=format_time(objetivo))
        self._dibujar_progreso(ratio)

    def start_progress_loop(self):
        self.update_progress()
        self.after_id_cola = self.root.after(50, self._procesar_cola)

    def _fin_de_cancion(self):
        if self.estado != "reproduciendo":
            return
        self.estado = "detenido"
        if self.duracion_total > 0:
            self.lbl_time_current.config(text=format_time(self.duracion_total))
        self._dibujar_progreso(0.0)
        if not self.cancion_actual:
            return
        if self.modo_repetir:
            self.reproducir_cancion(self.cancion_actual)
        else:
            self.cancion_siguiente()

    def update_progress(self):
        """>>> CORREGIDO: el fin de cancion se detecta por get_busy() sobre el
        estado explicito, no mirando el texto del boton. No se usa
        pygame.event: exigiria inicializar el video de SDL (una app Tkinter
        no lo hace) y fallaba con "video system not initialized"."""
        if not self.running:
            return
        try:
            if self.duracion_total > 0:
                if self.estado == "reproduciendo":
                    pos = self._posicion_actual()
                    self.lbl_time_current.config(text=format_time(pos))
                    self._dibujar_progreso(pos / self.duracion_total)
                elif self.estado == "pausado":
                    self.lbl_time_current.config(text=format_time(self._pos_pausa))
                    self._dibujar_progreso(self._pos_pausa / self.duracion_total)
            if self.estado == "reproduciendo" and AUDIO_DISPONIBLE:
                self._ticks_desde_play += 1
                # Margen de 2 sondeos (~1 s) para no confundir el arranque
                # del stream con su final.
                if self._ticks_desde_play > 2 and not pygame.mixer.music.get_busy():
                    self._fin_de_cancion()
        except Exception:
            # >>> CORREGIDO: antes era "except: pass" y ocultaba todo.
            logging.exception("Error actualizando el progreso")
        self.after_id = self.root.after(500, self.update_progress)

    def on_close(self):
        self.running = False
        for after_id in (self.after_id, self.after_id_cola):
            if after_id:
                try:
                    self.root.after_cancel(after_id)
                except tk.TclError:
                    logging.exception("No se pudo cancelar un after")
        # >>> CORREGIDO: cancelar lo pendiente. cancel_futures no existe en
        #     Python 3.8 (el ultimo que corre en Windows 7), asi que se
        #     cancelan los futuros a mano.
        for futuro in list(self._futuros):
            futuro.cancel()
        self._futuros.clear()
        try:
            self.executor.shutdown(wait=False)
        except Exception:
            logging.exception("Error cerrando el pool de hilos")
        try:
            # Primero se detiene el audio y despues se cierra el archivo:
            # cerrarlo con la reproduccion activa es pedirle problemas a SDL.
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        except pygame.error:
            logging.exception("Error cerrando el audio")
        self._cerrar_archivo_audio()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = MusiKatApp(root)
    root.mainloop()
