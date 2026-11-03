"""
Genera el banner del README (docs/banner.png) y la imagen para compartir el enlace (docs/social.png).

Usa los mismos dibujos en píxeles que la app, así que si cambias a Clawd, el banner cambia con él.

    py herramientas/generar_banner.py
"""

import os
import random
import sys

CARPETA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, CARPETA)

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import dibujos as d  # noqa: E402

DOCS = os.path.join(CARPETA, "docs")
FUENTES = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
NARANJA, VERDE = "#D97757", "#5DCAA5"


def hexa(color):
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def mezclar(a, b, t):
    a, b = hexa(a), hexa(b)
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def sprite(dib, filas, x0, y0, P, color):
    """Pinta un dibujo de dibujos.py: cada letra, un cuadradito de P píxeles."""
    for f, fila in enumerate(filas):
        for c, letra in enumerate(fila):
            relleno = color if letra == "X" else d.COLORES.get(letra)
            if relleno:
                dib.rectangle([x0 + c * P, y0 + f * P, x0 + c * P + P - 1, y0 + f * P + P - 1], fill=relleno)


def banner(ancho, alto, escala, ruta):
    random.seed(3)
    img = Image.new("RGB", (ancho, alto))
    dib = ImageDraw.Draw(img)
    b = 8 * escala // 4  # tamaño de los "píxeles" del paisaje

    # cielo de atardecer en franjas, estrellas y montañas, como las postales de Clawd
    for y in range(0, alto, b):
        dib.rectangle([0, y, ancho, y + b], fill=mezclar("#1B1F4A", "#F08A5D", (y / alto) ** 1.4))
    for _ in range(70):
        x, y = random.randrange(0, ancho, b), random.randrange(0, int(alto * 0.45), b)
        dib.rectangle([x, y, x + b // 2, y + b // 2], fill=mezclar("#FFD07F", "#FFFFFF", 0.6))
    suelo = alto - 5 * b
    for capa, (color, base) in enumerate([(mezclar("#F08A5D", "#1B1F4A", 0.55), 0.42), (mezclar("#1B1F4A", "#000000", 0.35), 0.28)]):
        h = alto * base
        for x in range(0, ancho, b):
            h = max(alto * 0.12, min(alto * 0.6, h + random.choice((-b, 0, 0, b))))
            dib.rectangle([x, alto - h, x + b, alto], fill=color)
    dib.rectangle([0, suelo, ancho, alto], fill=mezclar("#1B1F4A", "#000000", 0.55))

    # Clawd colgado de su hilo de telaraña
    P = 13 * escala // 4
    ojos = "..XXEXXXXEXX.."
    colgado = d.MANOS_RATON + [d.ARRIBA, ojos, d.CUERPO, d.CUERPO, d.CUERPO] + d.PATAS_COLGANDO[-1]
    cx, cy = int(ancho * 0.74), int(alto * 0.30)
    manos = (cx + 7 * P, cy)
    ancla = (manos[0] - 60 * escala // 4, -10)
    curva = [(ancla[0] + (manos[0] - ancla[0]) * t / 20 + 18 * escala / 4 * (t / 20) * (1 - t / 20) * 4,
              ancla[1] + (manos[1] - ancla[1]) * t / 20) for t in range(21)]
    dib.line(curva, fill=d.OJO, width=max(4, escala + 2), joint="curve")
    dib.line(curva, fill="#F5F5F5", width=max(2, escala), joint="curve")
    sprite(dib, colgado, cx, cy, P, NARANJA)
    for k, (dx, dy) in enumerate([(-2, -2), (15, -4)]):  # corazones
        sprite(dib, d.PARTICULAS["corazon"][0], cx + dx * P, cy + (dy + k) * P, P // 2, d.ROSA)

    # Bit paseando con una galleta al lado
    Pb = 8 * escala // 4
    bit = [d.ARRIBA, "..XXXEXXXXEX..", d.BRAZOS, d.CUERPO, d.CUERPO] + d.PATAS_PASO
    bx = int(ancho * 0.56)
    sprite(dib, bit, bx, suelo - 7 * Pb, Pb, VERDE)
    galleta = {k: v for k, v in d.COLORES_GALLETA.items()}
    q = Pb // 2 + 1
    for f, fila in enumerate(d.GALLETA):
        for c, letra in enumerate(fila):
            if letra in galleta:
                x, y = bx + 17 * Pb + c * q, suelo - 8 * q + f * q
                dib.rectangle([x, y, x + q - 1, y + q - 1], fill=galleta[letra])

    # textos
    titulo = ImageFont.truetype(os.path.join(FUENTES, "seguibl.ttf"), 19 * escala)
    lema = ImageFont.truetype(os.path.join(FUENTES, "Inkfree.ttf"), 9 * escala)
    etiquetas = ImageFont.truetype(os.path.join(FUENTES, "segoeuib.ttf"), 5 * escala + 1)
    x, y = 17 * escala, int(alto * 0.22)
    dib.text((x + escala, y + escala), "Clawd", font=titulo, fill="#1B1F4A")  # sombrita
    dib.text((x, y), "Clawd", font=titulo, fill="#FFF4E6")
    y += 25 * escala
    dib.text((x, y), "de escritorio", font=lema, fill="#FAC775")
    y += 13 * escala
    dib.text((x, y), "Una mascota en píxeles que vive en tu Windows", font=etiquetas, fill="#FBEAF0")
    y += 9 * escala
    x_pastilla = x
    for texto in ("Telaraña", "Galletas", "Disfraces", "Recordatorios"):
        ancho_t = dib.textlength(texto, font=etiquetas)
        dib.rounded_rectangle([x_pastilla, y, x_pastilla + ancho_t + 6 * escala, y + 9 * escala],
                              radius=4 * escala // 2, fill=mezclar("#1B1F4A", "#000000", 0.2))
        dib.text((x_pastilla + 3 * escala, y + 1.2 * escala), texto, font=etiquetas, fill="#FFF4E6")
        x_pastilla += ancho_t + 9 * escala

    img.save(ruta)
    print("guardado", ruta)


if __name__ == "__main__":
    os.makedirs(DOCS, exist_ok=True)
    banner(1280, 400, 4, os.path.join(DOCS, "banner.png"))
    banner(1280, 640, 5, os.path.join(DOCS, "social.png"))  # la imagen que sale al compartir el enlace
