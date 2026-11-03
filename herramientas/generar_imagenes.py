"""
Genera las animaciones y fotos del README (carpeta docs/).

Arranca a Clawd de verdad, le hace hacer cada cosa y, en cada fotograma, copia su dibujo
sobre un fondo limpio con Pillow. Así las imágenes no muestran nada de tu escritorio.

    py herramientas/generar_imagenes.py
"""

import os
import random
import sys
import time

CARPETA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, CARPETA)

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import ajustes  # noqa: E402
import clawd_escritorio as ce  # noqa: E402
import dibujos as d  # noqa: E402
from cosas import Galleta, pintar_cartel  # noqa: E402
from fisica import COLOR_HILO, LARGO_HILO, Hilo  # noqa: E402

DOCS = os.path.join(CARPETA, "docs")
FONDO, SUELO = (237, 230, 219), (217, 207, 193)
random.seed(7)
os.makedirs(DOCS, exist_ok=True)
ajustes.RUTA = os.path.join(DOCS, "_ajustes_temporales.json")  # no toca tus ajustes de verdad
ce.windows.se_pulso_alguna_tecla = lambda: False  # que no reaccione a lo que escribas mientras graba

m = ce.Mundo()
m.aj.update(travesuras=0, pausas=False, minutos_viaje=999, disfraz="ninguno", disfraz_amigo="ninguno")
c = m.clawds[0]
c.proximo_viaje = time.time() + 99999
X0 = (m.izq + m.der) // 2
raton = [X0, m.suelo - 330]
m.raiz.winfo_pointerxy = lambda: tuple(raton)
m.escuchar_musica = lambda ahora: None
letra = ImageFont.truetype("segoeui.ttf", 13)


def lienzo(region):
    x, y, w, h = region
    img = Image.new("RGB", (w, h), FONDO)
    ImageDraw.Draw(img).rectangle([0, m.suelo - y, w, h], fill=SUELO)
    return img


def pintar_mundo(img, region, raton_visible=False):
    rx, ry, _, _ = region
    dib = ImageDraw.Draw(img)
    for g in m.galletas:
        q = Galleta.TAM
        x0, y0 = g.x - 4 * q - rx, g.y - 8 * q - ry
        for f, fila in enumerate(d.GALLETA):
            for col, letra_g in enumerate(fila[:max(0, 8 - g.mordiscos * 3)]):
                if letra_g in d.COLORES_GALLETA:
                    dib.rectangle([x0 + col * q, y0 + f * q, x0 + col * q + q - 1, y0 + f * q + q - 1],
                                  fill=d.COLORES_GALLETA[letra_g])
    for k in m.clawds:
        if k.hilo:
            puntos = [(x - rx, y - ry) for x, y in k.hilo.puntos]
            dib.line(puntos, fill=d.OJO, width=4, joint="curve")
            dib.line(puntos, fill=COLOR_HILO, width=2, joint="curve")
    for k in m.clawds:
        wx, wy = int(k.x - k.W / 2) - rx, int(k.y - k.H) - ry
        for x, y, w, h, color in k.comandos:
            dib.rectangle([wx + x, wy + y, wx + x + w - 1, wy + y + h - 1], fill=color)
        if k.burbuja.visible:
            texto = k.burbuja.etiqueta.cget("text")
            iz, ar, de, ab = dib.textbbox((0, 0), texto, font=letra)
            tw, th = de - iz + 16, ab - ar + 10
            bx, by = k.x - rx - tw / 2, wy + k.fila_arriba * k.P - 6 - th
            dib.rectangle([bx, by, bx + tw, by + th], fill="white", outline=d.OJO)
            dib.text((bx + 8, by + 4 - ar), texto, font=letra, fill=d.OJO)
    if raton_visible:  # una flechita de ratón
        mx, my = raton[0] - rx, raton[1] - ry
        flecha = [(mx, my), (mx, my + 17), (mx + 4, my + 13), (mx + 7, my + 20), (mx + 10, my + 19),
                  (mx + 7, my + 12), (mx + 12, my + 12)]
        dib.polygon(flecha, fill="white", outline="black")


escenas = []


def escena(nombre, preparar, fotogramas, ancho=360, alto=220, cada_fotograma=None, raton_visible=False):
    escenas.append(dict(nombre=nombre, preparar=preparar, fotogramas=fotogramas, ancho=ancho, alto=alto,
                        cada=cada_fotograma, raton=raton_visible))


def quieto_en(x):
    c.x, c.y, c.vx, c.vy = x, m.suelo, 0, 0
    c.cambiar("quieto", 999)


# ----- las escenas -----

def prep_caminar():
    quieto_en(X0 - 110)
    c.cambiar("caminar")
    c.objetivo = X0 + 110
escena("caminar", prep_caminar, 100)


def prep_laptop():
    quieto_en(X0)
    c.sacar_laptop()
def teclear(i):
    if i < 70 and i % 3 == 0:
        m.ultima_tecla = time.time()
escena("laptop", prep_laptop, 135, cada_fotograma=teclear)


def prep_telarana():
    raton[:] = [X0 - 60, m.suelo - 330]
    c.hilo = Hilo((raton[0], raton[1] + 3), (raton[0] + 150, raton[1] + 90), LARGO_HILO)
    c.mareo = 0
    c.cambiar("colgado_raton", 999)
def latigazo(i):
    if 55 <= i < 61:
        raton[0] += 25  # un tirón brusco a la derecha
escena("telarana", prep_telarana, 150, ancho=420, alto=360, cada_fotograma=latigazo, raton_visible=True)


def prep_dormir():
    quieto_en(X0)
    c.dormir()
escena("dormir", prep_dormir, 100)


def prep_bailar():
    quieto_en(X0)
    m.hay_musica = True
    c.cambiar("bailar", 999)
escena("bailar", prep_bailar, 90)


def prep_galleta():
    m.hay_musica = False
    quieto_en(X0 - 120)
    m.galletas.append(Galleta(X0 + 100, m.suelo - 200))
escena("galleta", prep_galleta, 150)


def prep_bit():
    m.galletas.clear()
    m.aj["amigo"] = True
    m.aplicar_ajustes(guardar=False)
    bit = m.clawds[1]
    quieto_en(X0 - 60)
    bit.x, bit.y = X0 + 60, m.suelo
    bit.cambiar("quieto", 999)
    c.jugar_con(bit)
escena("bit", prep_bit, 180, ancho=640)


# ----- el grabador -----

estado = {"i": -1, "f": 0, "frames": [], "region": None}


def grabar():
    if estado["i"] >= len(escenas):
        return  # ya terminó
    e = escenas[estado["i"]] if estado["i"] >= 0 else None
    if e is None or estado["f"] >= e["fotogramas"]:
        if e:
            ruta = os.path.join(DOCS, e["nombre"] + ".gif")
            estado["frames"][0].save(ruta, save_all=True, append_images=estado["frames"][1:],
                                     duration=33, loop=0, optimize=True)
            print("guardado", ruta)
        estado["i"] += 1
        if estado["i"] >= len(escenas):
            m.raiz.after(10, terminar)
            return
        e = escenas[estado["i"]]
        e["preparar"]()
        estado.update(f=0, frames=[], region=(X0 - e["ancho"] // 2, m.suelo - e["alto"] + 20, e["ancho"], e["alto"]))
        return
    if e["cada"]:
        e["cada"](estado["f"])
    img = lienzo(estado["region"])
    pintar_mundo(img, estado["region"], e["raton"])
    estado["frames"].append(img)
    estado["f"] += 1


def disfraces():
    """Una foto con todos los disfraces en fila."""
    m.aj["amigo"] = False
    m.aplicar_ajustes(guardar=False)
    lista = [k for k in d.DISFRACES if k not in ("auto",)]
    hoja = Image.new("RGB", (110 * len(lista), 150), FONDO)
    dib = ImageDraw.Draw(hoja)
    pequena = ImageFont.truetype("segoeui.ttf", 12)
    quieto_en(X0)
    for n, nombre in enumerate(lista):
        m.aj["disfraz"] = nombre
        c.t = 0
        c.moviendo = nombre == "capa"
        c.dir = 1
        c.dibujar()
        for x, y, w, h, color in c.comandos:
            dib.rectangle([n * 110 - 5 + x, y - 10, n * 110 - 5 + x + w - 1, y - 10 + h - 1], fill=color)
        texto = d.DISFRACES[nombre]
        ancho_t = dib.textlength(texto, font=pequena)
        dib.text((n * 110 + 55 - ancho_t / 2, 120), texto, font=pequena, fill=d.OJO)
    hoja.save(os.path.join(DOCS, "disfraces.png"))
    print("guardado disfraces.png")


def captura_de(win, ruta):
    """Hace una foto de la pantalla justo donde está esa ventana (con lo que tenga encima)."""
    import subprocess
    win.update()
    x, y, w, h = win.winfo_rootx(), win.winfo_rooty(), win.winfo_width(), win.winfo_height()
    # se usa el capturador de Windows porque es el que ve bien las ventanas con partes transparentes
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Add-Type -AssemblyName System.Drawing; "
                    f"$b = New-Object System.Drawing.Bitmap {w},{h}; "
                    "$g = [System.Drawing.Graphics]::FromImage($b); "
                    f"$g.CopyFromScreen({x},{y},0,0,$b.Size); $b.Save('{ruta}')"], check=True)


def carteles_y_ajustes():
    import tkinter as tk
    # Los carteles se pintan con la misma función que usa la app, pero en una ventana normal
    # con el fondo del README (las ventanas transparentes no salen bien en las capturas)
    fondo = tk.Toplevel(m.raiz)
    fondo.overrideredirect(True)
    fondo.wm_attributes("-topmost", True)
    fondo.geometry(f"600x260+{m.izq + 40}+{m.arr + 40}")
    for i, (titulo, texto, pie) in enumerate([
            ("¡No lo olvides!", "Llamar a mamá a las 6", "Clawd · 17:42"),
            ("Hora de una pausa", "Mira algo lejano 20 segundos. Tus ojos te lo agradecen.", "Clawd te cuida")]):
        lienzo_cartel = tk.Canvas(fondo, width=300, height=260, bg="#EDE6DB", highlightthickness=0)
        lienzo_cartel.place(x=i * 300, y=0)
        pintar_cartel(lienzo_cartel, titulo, texto, pie)
        lienzo_cartel.move("all", 10, 10)
    m.raiz.update()
    time.sleep(0.4)
    captura_de(fondo, os.path.join(DOCS, "carteles.png"))
    fondo.destroy()
    m.aj.update({k: v for k, v in ajustes.POR_DEFECTO.items() if k != "recordatorios"})  # valores normales
    v = ajustes.VentanaAjustes(m)
    m.raiz.update()
    time.sleep(0.3)
    captura_de(v.win, os.path.join(DOCS, "ajustes.png"))
    v.win.destroy()
    print("guardado carteles.png y ajustes.png")


def terminar():
    disfraces()
    carteles_y_ajustes()
    m.salir()
    try:
        os.remove(ajustes.RUTA)
    except OSError:
        pass


original = m.dibujar_capa
def capa_y_grabar():
    original()
    if m.fotograma > 60:  # deja que caiga y se coloque antes de empezar
        grabar()
m.dibujar_capa = capa_y_grabar
m.empezar()
