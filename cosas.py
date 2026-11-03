"""Las cosas que rodean a Clawd: su globo de texto, lo que te trae y las galletas."""

import random
import time
import tkinter as tk
from tkinter import font as tkfont

import dibujos as d

MENSAJES = [
    "¿Ya tomaste agua hoy?",
    "Los errores también enseñan. Hasta los rojos.",
    "Hoy es buen día para crear algo.",
    "Respira y estira la espalda un momento.",
    "Un píxel a la vez.",
    "Guarda tu trabajo, por si acaso.",
    "Eres más creativo de lo que crees.",
    "¿Y si dibujas algo hoy?",
    "Programar también es una forma de arte.",
    "Lo que hoy te cuesta, mañana te sale solo.",
]
FRASES = ["¡Hola!", "¡Yuju!", "Bip bup", "¿Programamos algo?", "¡Cosquillas!"]
PAUSAS = [
    "Mira algo lejano 20 segundos. Tus ojos te lo agradecen.",
    "Levántate y estira las piernas un poquito.",
    "Toma un vaso de agua.",
    "Hombros abajo, espalda recta, respira hondo.",
    "Cierra los ojos un ratito y descansa.",
]
PALETAS_POSTAL = [  # (cielo arriba, cielo abajo, sol)
    ("#1B1F4A", "#F08A5D", "#FFD07F"),
    ("#0F3D3E", "#E2A16F", "#FFF0C9"),
    ("#2E1A47", "#D4537E", "#FAC775"),
    ("#08304F", "#5DCAA5", "#E1F5EE"),
    ("#3C3489", "#F0997B", "#FAEEDA"),
]


def mezclar(a, b, t):
    """Mezcla dos colores "#rrggbb": t=0 da a, t=1 da b."""
    a = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def letra_manuscrita():
    """La primera letra "escrita a mano" que tenga tu Windows."""
    instaladas = set(tkfont.families())
    for nombre in ("Ink Free", "Segoe Print", "Segoe Script", "Comic Sans MS"):
        if nombre in instaladas:
            return nombre
    return "TkDefaultFont"


def pintar_postal(lienzo, ancho, alto, b=6):
    """Pinta un paisaje en píxeles distinto cada vez: cielo, estrellas, sol y montañas."""
    cielo_arriba, cielo_abajo, sol = random.choice(PALETAS_POSTAL)
    cols, filas = ancho // b, alto // b

    def px(c, f, color):
        lienzo.create_rectangle(c * b, f * b, c * b + b, f * b + b, fill=color, outline="")

    for f in range(filas):
        color = mezclar(cielo_arriba, cielo_abajo, f / (filas - 1))
        lienzo.create_rectangle(0, f * b, ancho, f * b + b, fill=color, outline="")
    for _ in range(random.randint(0, 12)):
        px(random.randrange(cols), random.randrange(filas // 3), mezclar(sol, "#FFFFFF", 0.6))

    sc, sf, r = random.randint(5, cols - 5), random.randint(3, filas // 2), random.randint(2, 4)
    for i in range(-r, r + 1):
        for j in range(-r, r + 1):
            if i * i + j * j <= r * r + 1:
                px(sc + i, sf + j, sol)

    # tres capas de montañas, de la más lejana (clara) a la más cercana (oscura)
    colores = [mezclar(cielo_abajo, cielo_arriba, 0.55),
               mezclar(cielo_arriba, "#000000", 0.25),
               mezclar(cielo_arriba, "#000000", 0.55)]
    for capa, color in enumerate(colores):
        altura = filas * (0.45 - capa * 0.12)
        for c in range(cols):
            altura = max(2, min(filas - 2, altura + random.choice((-1, 0, 0, 1))))
            lienzo.create_rectangle(c * b, (filas - int(altura)) * b, c * b + b, alto,
                                    fill=color, outline="")


def pintar_cartel(lienzo, titulo, texto, pie):
    """Un papelito pegado con cinta y escrito a mano. Devuelve su alto."""
    letra = letra_manuscrita()
    tinta, papel = "#3A2A1E", "#FBF1DC"
    t1 = lienzo.create_text(140, 22, text=titulo, font=(letra, 17, "bold"), fill="#993C1D", anchor="n",
                            width=230, justify="center")
    _, _, _, abajo = lienzo.bbox(t1)
    x1, _, x2, _ = lienzo.bbox(t1)
    # subrayado temblón, como hecho a pulso
    puntos = []
    for i in range(9):
        puntos += [x1 + (x2 - x1) * i / 8, abajo + 2 + random.uniform(-1.5, 1.5)]
    lienzo.create_line(*puntos, fill=d.COLORES["Y"], width=2, smooth=True)
    t2 = lienzo.create_text(140, abajo + 12, text=texto, font=(letra, 15), fill=tinta, width=230, anchor="n")
    _, _, _, abajo = lienzo.bbox(t2)
    t3 = lienzo.create_text(262, abajo + 10, text=pie, font=(letra, 10), fill="#8A5A2B", anchor="ne")
    _, _, _, abajo = lienzo.bbox(t3)
    fondo = lienzo.create_rectangle(10, 10, 270, abajo + 12, fill=papel, outline="#8A5A2B", width=2)
    lienzo.tag_lower(fondo)
    # dos trocitos de cinta adhesiva torcidos en las esquinas
    for cx, giro in ((34, -1), (246, 1)):
        lienzo.create_polygon(cx - 20, 4 + 6 * giro, cx + 20, 4 - 6 * giro,
                              cx + 22, 16 - 6 * giro, cx - 18, 16 + 6 * giro,
                              fill="#F3E3A1", outline="")
    return abajo + 16


class Objeto:
    """Una ventanita con lo que Clawd te trae: mensaje, postal, foto o cartel."""

    def __init__(self, raiz, tipo, dato=None):
        self.tipo = tipo
        self.creado = time.time()
        self.dura = {"mensaje": 45, "cartel": None}.get(tipo, 120)  # None = hasta que le hagas clic
        self.vivo = True
        self.win = tk.Toplevel(raiz)
        self.win.overrideredirect(True)
        self.win.wm_attributes("-topmost", True)
        self.win.geometry("+-3000+-3000")  # nace fuera de la pantalla

        if tipo == "cartel":
            titulo, texto, pie, dura = dato
            self.dura = dura
            self.win.wm_attributes("-transparentcolor", d.TRANSPARENTE)
            lienzo = tk.Canvas(self.win, width=280, height=400, bg=d.TRANSPARENTE, highlightthickness=0)
            lienzo.pack()
            lienzo.config(height=pintar_cartel(lienzo, titulo, texto, pie))
            lienzo.bind("<Button-1>", lambda e: self.cerrar())
        else:
            fondo = "#FFF4E6"
            marco = tk.Frame(self.win, bg=fondo, padx=8, pady=8,
                             highlightbackground="#D97757", highlightthickness=2)
            marco.pack()
            if tipo == "mensaje":
                tk.Label(marco, text=dato, bg=fondo, fg="#4A1B0C", font=("Segoe UI", 12),
                         wraplength=220, justify="left").pack()
            elif tipo == "foto":
                self.imagen = dato  # hay que guardar la imagen o Tkinter la borra
                tk.Label(marco, image=dato, bd=0).pack()
            else:
                lienzo = tk.Canvas(marco, width=240, height=150, highlightthickness=0)
                lienzo.pack()
                pintar_postal(lienzo, 240, 150)
            tk.Label(marco, text="— Clawd · clic para cerrar", bg=fondo, fg="#993C1D",
                     font=("Segoe UI", 9)).pack(anchor="e", pady=(6, 0))
            for w in (self.win, marco, *marco.winfo_children()):
                w.bind("<Button-1>", lambda e: self.cerrar())

        self.win.update_idletasks()
        self.ancho = self.win.winfo_reqwidth()
        self.alto = self.win.winfo_reqheight()

    def caducado(self, ahora):
        return not self.vivo or (self.dura is not None and ahora - self.creado > self.dura)

    def mover(self, x, y):
        if self.vivo:
            # con el tamaño incluido: si no, Windows a veces ignora el primer movimiento de los carteles
            self.win.geometry(f"{self.ancho}x{self.alto}+{int(x)}+{int(y)}")

    def mostrar(self, visible):
        if self.vivo:
            self.win.deiconify() if visible else self.win.withdraw()

    def cerrar(self):
        if self.vivo:
            self.vivo = False
            self.win.destroy()


class Burbuja:
    """El globito de texto que sale encima de Clawd cuando habla."""

    def __init__(self, raiz):
        self.win = tk.Toplevel(raiz)
        self.win.overrideredirect(True)
        self.win.wm_attributes("-topmost", True)
        self.etiqueta = tk.Label(self.win, bg="white", fg=d.OJO, font=("Segoe UI", 10), padx=8, pady=4,
                                 highlightbackground=d.OJO, highlightthickness=1)
        self.etiqueta.pack()
        self.hasta = 0
        self.visible = False
        self.pos = None
        self.win.withdraw()

    def decir(self, texto, segundos=3):
        self.etiqueta.config(text=texto)
        self.hasta = time.time() + segundos
        if not self.visible:
            self.win.deiconify()
            self.visible = True

    def esconder(self):
        self.hasta = 0
        if self.visible:
            self.win.withdraw()
            self.visible = False

    def seguir(self, x, y_arriba, y_abajo, techo):
        """Se coloca centrada en x, encima de Clawd (y_arriba) o, si no cabe, debajo (y_abajo)."""
        if time.time() > self.hasta:
            self.esconder()
            return
        w, h = self.etiqueta.winfo_reqwidth(), self.etiqueta.winfo_reqheight()
        y = y_arriba - h if y_arriba - h >= techo else y_abajo
        pos = (int(x - w / 2), int(y))
        if pos != self.pos:  # solo se recoloca si de verdad se movió
            self.win.geometry(f"+{pos[0]}+{pos[1]}")
            self.pos = pos


class Galleta:
    """Una galleta que cae desde arriba. Se dibuja en la capa transparente de la pantalla."""

    TAM = 4  # tamaño de cada píxel de la galleta

    def __init__(self, x, y):
        self.x, self.y = x, y  # x = centro, y = parte de abajo
        self.vy = 0.0
        self.en_suelo = False
        self.mordiscos = 0
        self.duena = None  # el Clawd que va a por ella

    def caer(self, suelo):
        if not self.en_suelo:
            self.vy += 0.6
            self.y += self.vy
            if self.y >= suelo:
                self.y = suelo
                self.en_suelo = True

    def dibujar(self, lienzo, dx, dy):
        q = self.TAM
        quedan = 8 - self.mordiscos * 3  # cada mordisco le quita un trozo
        x0, y0 = self.x - 4 * q - dx, self.y - 8 * q - dy
        for f, fila in enumerate(d.GALLETA):
            for c, letra in enumerate(fila[:max(0, quedan)]):
                if letra in d.COLORES_GALLETA:
                    lienzo.create_rectangle(x0 + c * q, y0 + f * q, x0 + c * q + q, y0 + f * q + q,
                                            fill=d.COLORES_GALLETA[letra], outline="")
