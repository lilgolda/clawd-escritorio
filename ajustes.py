"""Los ajustes de Clawd: se guardan en clawd_datos.json y se cambian desde una ventanita."""

import json
import os
import sys
import time
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import colorchooser, ttk

import dibujos as d
import windows

if getattr(sys, "frozen", False):
    # Dentro de Clawd.exe el código vive en una carpeta temporal que se borra al cerrar,
    # así que los ajustes se guardan al lado del .exe
    CARPETA = os.path.dirname(sys.executable)
else:
    CARPETA = os.path.dirname(os.path.abspath(__file__))
RUTA = os.path.join(CARPETA, "clawd_datos.json")

POR_DEFECTO = {
    "tamano": 6,                # tamaño de cada píxel
    "velocidad": 2.2,
    "color": "#D97757",
    "disfraz": "auto",
    "amigo": False,             # ¿viene Bit?
    "color_amigo": "#5DCAA5",
    "disfraz_amigo": "auto",
    "travesuras": 1.0,          # 0 = muy tranquilo, 3 = un terremoto
    "minutos_viaje": 2,         # cada cuánto (más o menos) te trae algo
    "pausas": True,
    "minutos_pausa": 60,
    "ciudad": "",
    "bailar": True,
    "esconder_pantalla_completa": True,
    "recordatorios": [],
}


def cargar():
    datos = dict(POR_DEFECTO)
    try:
        with open(RUTA, encoding="utf-8") as f:
            datos.update(json.load(f))
    except (OSError, ValueError):
        pass
    return datos


def guardar(datos):
    try:
        with open(RUTA, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


class VentanaAjustes:
    def __init__(self, mundo):
        self.m = mundo
        aj = mundo.aj
        w = self.win = tk.Toplevel(mundo.raiz)
        w.title("Ajustes de Clawd")
        w.resizable(False, False)
        w.attributes("-topmost", True)
        w.protocol("WM_DELETE_WINDOW", self.cerrar)
        marco = ttk.Frame(w, padding=16)
        marco.pack(fill="both")
        self.marco = marco
        self.fila = 0

        self.titulo("Clawd")
        self.deslizador("Tamaño", "tamano", 3, 12, 1, "{}")
        self.deslizador("Velocidad", "velocidad", 1, 6, 0.1, "{:.1f}")
        self.selector_color("Color", "color")
        self.selector_disfraz("Disfraz", "disfraz")

        self.titulo("Su amigo Bit")
        self.casilla("Que venga Bit a jugar", "amigo")
        self.selector_color("Color de Bit", "color_amigo")
        self.selector_disfraz("Disfraz de Bit", "disfraz_amigo")

        self.titulo("Travesuras")
        self.deslizador("Ganas de travesuras", "travesuras", 0, 3, 0.1, "{:.1f}")
        self.deslizador("Te trae algo cada (min)", "minutos_viaje", 1, 10, 1, "{}")
        self.casilla("Bailar cuando suena música", "bailar")

        self.titulo("Cuidarte")
        self.casilla("Avisarme para hacer pausas", "pausas")
        self.deslizador("Una pausa cada (min)", "minutos_pausa", 15, 120, 5, "{}")
        ttk.Button(marco, text="Recordatorios...", command=lambda: VentanaRecordatorios(mundo)).grid(
            row=self.fila, column=0, sticky="w", pady=4)
        self.fila += 1

        self.titulo("El tiempo")
        ttk.Label(marco, text="Tu ciudad").grid(row=self.fila, column=0, sticky="w")
        self.var_ciudad = tk.StringVar(value=aj["ciudad"])
        ttk.Entry(marco, textvariable=self.var_ciudad, width=24).grid(row=self.fila, column=1, sticky="w", padx=8)
        ttk.Button(marco, text="Probar", command=self.probar_ciudad).grid(row=self.fila, column=2, sticky="w")
        self.fila += 1
        self.resultado_ciudad = ttk.Label(marco, foreground="#5F5E5A")
        self.resultado_ciudad.grid(row=self.fila, column=0, columnspan=3, sticky="w")
        self.fila += 1

        self.titulo("Windows")
        self.var_arranque = tk.BooleanVar(value=windows.arranque_activado())
        ttk.Checkbutton(marco, text="Arrancar con Windows", variable=self.var_arranque,
                        command=self.cambiar_arranque).grid(row=self.fila, column=0, columnspan=3, sticky="w")
        self.fila += 1
        self.aviso_arranque = ttk.Label(marco, foreground="#A32D2D", wraplength=380)
        self.aviso_arranque.grid(row=self.fila, column=0, columnspan=3, sticky="w")
        self.fila += 1
        self.casilla("Esconderse si juego o veo algo a pantalla completa", "esconder_pantalla_completa")

        ttk.Button(marco, text="Listo", command=self.cerrar).grid(row=self.fila, column=2, sticky="e", pady=(16, 0))

    # ----- piezas de la ventana -----

    def titulo(self, texto):
        ttk.Label(self.marco, text=texto, font=("Segoe UI", 11, "bold")).grid(
            row=self.fila, column=0, columnspan=3, sticky="w", pady=(14 if self.fila else 0, 4))
        self.fila += 1

    def deslizador(self, texto, clave, desde, hasta, paso, formato):
        aj = self.m.aj
        var = tk.DoubleVar(value=aj[clave])
        valor = ttk.Label(self.marco, width=5)

        def al_cambiar(_=None):
            v = round(var.get() / paso) * paso
            v = int(v) if paso >= 1 else round(v, 1)
            valor.config(text=formato.format(v))
            if aj[clave] != v:
                aj[clave] = v
                self.m.aplicar_ajustes()

        ttk.Label(self.marco, text=texto).grid(row=self.fila, column=0, sticky="w")
        ttk.Scale(self.marco, from_=desde, to=hasta, variable=var, command=al_cambiar, length=200).grid(
            row=self.fila, column=1, padx=8, pady=2)
        valor.grid(row=self.fila, column=2, sticky="w")
        al_cambiar()
        self.fila += 1

    def casilla(self, texto, clave):
        var = tk.BooleanVar(value=self.m.aj[clave])

        def al_cambiar():
            self.m.aj[clave] = var.get()
            self.m.aplicar_ajustes()

        ttk.Checkbutton(self.marco, text=texto, variable=var, command=al_cambiar).grid(
            row=self.fila, column=0, columnspan=3, sticky="w", pady=2)
        self.fila += 1

    def selector_color(self, texto, clave):
        muestra = tk.Label(self.marco, width=4, bg=self.m.aj[clave], relief="solid", bd=1)

        def elegir():
            _, hexa = colorchooser.askcolor(initialcolor=self.m.aj[clave], parent=self.win, title=texto)
            if hexa:
                self.m.aj[clave] = hexa
                muestra.config(bg=hexa)
                self.m.aplicar_ajustes()

        ttk.Label(self.marco, text=texto).grid(row=self.fila, column=0, sticky="w")
        ttk.Button(self.marco, text="Elegir...", command=elegir).grid(row=self.fila, column=1, sticky="w", padx=8)
        muestra.grid(row=self.fila, column=2, sticky="w")
        self.fila += 1

    def selector_disfraz(self, texto, clave):
        claves = list(d.DISFRACES)
        caja = ttk.Combobox(self.marco, values=list(d.DISFRACES.values()), state="readonly", width=30)
        caja.current(claves.index(self.m.aj[clave]) if self.m.aj[clave] in claves else 0)

        def al_cambiar(_):
            self.m.aj[clave] = claves[caja.current()]
            self.m.aplicar_ajustes()

        caja.bind("<<ComboboxSelected>>", al_cambiar)
        ttk.Label(self.marco, text=texto).grid(row=self.fila, column=0, sticky="w")
        caja.grid(row=self.fila, column=1, columnspan=2, sticky="w", padx=8, pady=2)
        self.fila += 1

    # ----- acciones -----

    def probar_ciudad(self):
        ciudad = self.var_ciudad.get().strip()
        self.m.aj["ciudad"] = ciudad
        self.m.aplicar_ajustes()
        if not ciudad:
            self.resultado_ciudad.config(text="Escribe el nombre de tu ciudad.")
            return
        self.resultado_ciudad.config(text="Mirando el cielo...")
        self.m.pedir_tiempo(al_terminar=self.mostrar_tiempo)

    def mostrar_tiempo(self, tiempo):
        if not self.win.winfo_exists():
            return
        if tiempo:
            self.resultado_ciudad.config(text=f"{tiempo['ciudad']}: {tiempo['temp']:.0f}° y {tiempo['descripcion']}")
        else:
            self.resultado_ciudad.config(text="No encontré esa ciudad (o no hay internet).")

    def cambiar_arranque(self):
        script = os.path.join(CARPETA, "clawd_escritorio.py")
        try:
            windows.poner_arranque(self.var_arranque.get(), script)
            temporal = "scratch-workspaces" in CARPETA
            self.aviso_arranque.config(text="Ojo: Clawd está en una carpeta temporal. Muévelo a una carpeta tuya "
                                            "o dejará de arrancar." if temporal and self.var_arranque.get() else "")
        except OSError:
            self.aviso_arranque.config(text="Windows no me dejó cambiarlo.")
            self.var_arranque.set(windows.arranque_activado())

    def cerrar(self):
        self.m.aj["ciudad"] = self.var_ciudad.get().strip()
        self.m.aplicar_ajustes()
        self.win.destroy()


class VentanaRecordatorios:
    def __init__(self, mundo):
        self.m = mundo
        w = self.win = tk.Toplevel(mundo.raiz)
        w.title("Recordatorios de Clawd")
        w.resizable(False, False)
        w.attributes("-topmost", True)
        marco = ttk.Frame(w, padding=16)
        marco.pack(fill="both")

        ttk.Label(marco, text="¿Qué te recuerdo?").grid(row=0, column=0, sticky="w")
        self.var_texto = tk.StringVar()
        entrada = ttk.Entry(marco, textvariable=self.var_texto, width=40)
        entrada.grid(row=1, column=0, columnspan=3, sticky="we", pady=(2, 8))
        entrada.focus_set()

        ttk.Label(marco, text="Dentro de").grid(row=2, column=0, sticky="w")
        self.var_minutos = tk.StringVar(value="20")
        ttk.Spinbox(marco, from_=1, to=1440, textvariable=self.var_minutos, width=6).grid(row=2, column=1, sticky="w")
        ttk.Label(marco, text="minutos").grid(row=2, column=2, sticky="w")
        ttk.Label(marco, text="o a las (HH:MM)").grid(row=3, column=0, sticky="w")
        self.var_hora = tk.StringVar()
        ttk.Entry(marco, textvariable=self.var_hora, width=8).grid(row=3, column=1, sticky="w", pady=4)

        self.error = ttk.Label(marco, foreground="#A32D2D")
        self.error.grid(row=4, column=0, columnspan=3, sticky="w")
        for var in (self.var_texto, self.var_minutos, self.var_hora):
            var.trace_add("write", lambda *_: self.error.config(text=""))
        ttk.Button(marco, text="Recuérdamelo", command=self.agregar).grid(row=5, column=0, sticky="w", pady=(4, 12))
        entrada.bind("<Return>", lambda e: self.agregar())

        ttk.Label(marco, text="Pendientes").grid(row=6, column=0, sticky="w")
        self.lista = tk.Listbox(marco, width=48, height=6)
        self.lista.grid(row=7, column=0, columnspan=3, sticky="we")
        ttk.Button(marco, text="Borrar el seleccionado", command=self.borrar).grid(row=8, column=0, sticky="w", pady=6)
        self.refrescar()

    def refrescar(self):
        self.lista.delete(0, "end")
        for r in sorted(self.m.aj["recordatorios"], key=lambda r: r["cuando"]):
            self.lista.insert("end", f"{time.strftime('%H:%M', time.localtime(r['cuando']))}  ·  {r['texto']}")

    def agregar(self):
        texto = self.var_texto.get().strip()
        if not texto:
            self.error.config(text="Escribe qué quieres que te recuerde.")
            return
        hora = self.var_hora.get().strip()
        if hora:
            try:
                h = datetime.strptime(hora, "%H:%M")
            except ValueError:
                self.error.config(text="La hora tiene que ser así: 17:30")
                return
            ahora = datetime.now()
            cuando = ahora.replace(hour=h.hour, minute=h.minute, second=0, microsecond=0)
            if cuando <= ahora:
                cuando += timedelta(days=1)  # si ya pasó hoy, mañana
            cuando = cuando.timestamp()
        else:
            try:
                minutos = float(self.var_minutos.get())
                if minutos <= 0:
                    raise ValueError
            except ValueError:
                self.error.config(text="Pon un número de minutos mayor que 0.")
                return
            cuando = time.time() + minutos * 60
        self.m.agregar_recordatorio(texto, cuando)
        self.var_texto.set("")
        self.var_hora.set("")
        self.refrescar()

    def borrar(self):
        seleccion = self.lista.curselection()
        if not seleccion:
            return
        ordenados = sorted(self.m.aj["recordatorios"], key=lambda r: r["cuando"])
        self.m.aj["recordatorios"].remove(ordenados[seleccion[0]])
        guardar(self.m.aj)
        self.refrescar()
