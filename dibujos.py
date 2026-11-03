"""
Los dibujos de Clawd: cada letra de estos textos es un píxel.

  .  nada (transparente)      X  el cuerpo (su color)       E  ojo
  N  negro    R  rojo    W  blanco    M  morado    Y  amarillo
  B  azul     K  gris oscuro    L  gris claro    O  gris muy claro    P  rosa

Ojos especiales (los pinta clawd.py encima de un píxel del cuerpo):
  c  cerrado    a  aburrido (medio cerrado)    f  feliz    h  corazón    m  mareado
"""

TRANSPARENTE = "#FF00FE"  # este color se vuelve invisible (y los clics lo atraviesan)
OJO = "#2C2C2A"
ROSA = "#D4537E"

COLORES = {
    "E": OJO, "N": "#2C2C2A", "R": "#E24B4A", "W": "#F1EFE8", "M": "#534AB7", "Y": "#EF9F27",
    "B": "#378ADD", "K": "#5F5E5A", "L": "#A8A8A8", "O": "#EDEDED", "P": ROSA,
}

# ---------- Clawd ----------

ARRIBA = "..XXXXXXXXXX.."   # la cabeza (también es la base de la fila de los ojos)
BRAZOS = "XXXXXXXXXXXXXX"   # fila con los bracitos a los lados
CUERPO = "..XXXXXXXXXX.."
SENTADO = "..XX......XX.."  # patitas dobladas al sentarse

PATAS_QUIETO = ["...X.X..X.X...", "...X.X..X.X..."]
PATAS_PASO = ["...X.X..X.X...", "..X.X....X.X.."]
PATAS_SALTO = ["..X.X....X.X..", ".X..X....X..X."]
PATAS_COLGANDO = {  # según hacia dónde se balancea
    -1: ["..X.X..X.X....", "..X.X..X.X...."],
    0: ["...X.X..X.X...", "...X.X..X.X..."],
    1: ["....X.X..X.X..", "....X.X..X.X.."],
}
MANOS_RATON = ["......XX......", ".....X..X.....", "....X....X...."]  # manos juntas arriba
MANOS_ARRIBA = [  # dos posiciones para avanzar mano tras mano (y para estirarse)
    ["X............X", "X............X", ".X..........X."],
    ["X.............", "X............X", ".X..........X."],
]

# ---------- Disfraces ----------

DISFRACES = {  # clave: nombre que se ve en los menús
    "auto": "Automático (según la fecha, la hora y el tiempo)",
    "ninguno": "Ninguno",
    "copa": "Sombrero de copa",
    "navidad": "Gorro de Navidad",
    "bruja": "Sombrero de bruja",
    "corona": "Corona",
    "gafas": "Gafas de sol",
    "capa": "Capa de héroe",
    "dormir": "Gorro de dormir",
    "lana": "Gorro de lana",
}

# Los sombreros se pintan justo encima de la cabeza (la última fila toca la cabeza)
SOMBREROS = {
    "copa": [
        "....NNNNNN....",
        "....NNNNNN....",
        "....RRRRRR....",
        "..NNNNNNNNNN..",
    ],
    "navidad": [
        "..........WW..",
        "........RR....",
        "......RRRR....",
        "....RRRRRRR...",
        "..WWWWWWWWWW..",
    ],
    "bruja": [
        ".......M......",
        "......MM......",
        ".....MMMM.....",
        "....YYYYYY....",
        ".MMMMMMMMMMMM.",
    ],
    "corona": [
        "...Y..YY..Y...",
        "...YYYYYYYY...",
    ],
    "dormir": [
        "...........W..",
        ".........BB...",
        "......BBBBB...",
        "....BBBBBBBB..",
        "..WWWWWWWWWW..",
    ],
    "lana": [
        "......WW......",
        "....RRRRRR....",
        "...WWWWWWWW...",
        "..RRRRRRRRRR..",
    ],
}
GAFAS = "...NNNNNNNN..."  # se pinta encima de la fila de los ojos
PARAGUAS = [              # sale cuando llueve en tu ciudad
    "....BBBBBB....",
    "..BBBBBBBBBB..",
    ".BBBBBBBBBBBB.",
    ".......K......",
    ".......K......",
]
COLOR_CAPA = "#E24B4A"

# ---------- Particulitas (corazones, zetas...) ----------

PARTICULAS = {  # (dibujo, color); se pintan con píxeles más pequeños
    "corazon": ([".X.X.", "XXXXX", ".XXX.", "..X.."], ROSA),
    "zeta": (["XXXX", "..X.", ".X..", "XXXX"], "#378ADD"),
    "estrella": ([".X.", "XXX", ".X."], "#EF9F27"),
    "nota": (["..XX", "..X.", "..X.", "XXX.", "XX.."], "#7F77DD"),
    "miga": (["XX", "XX"], "#C98A4B"),
}

# ---------- Galleta ----------

GALLETA = [
    "..CCCC..",
    ".CCDCCC.",
    "CCCCCDCC",
    "CDCCCCCC",
    "CCCCDCCC",
    "CCDCCCDC",
    ".CCCCCC.",
    "..CCCC..",
]
COLORES_GALLETA = {"C": "#C98A4B", "D": "#5A3A1E"}


def crear_icono(ruta, color):
    """Guarda un icono .ico con la cara de Clawd (para el icono junto al reloj)."""
    from PIL import Image
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    filas = [ARRIBA, "..XXEXXXXEXX..", BRAZOS, CUERPO, CUERPO] + PATAS_QUIETO
    rgb = {"X": color, "E": OJO}
    escala, ox, oy = 4, 4, 18
    for f, fila in enumerate(filas):
        for c, letra in enumerate(fila):
            if letra in rgb:
                hexa = rgb[letra]
                pixel = tuple(int(hexa[i:i + 2], 16) for i in (1, 3, 5)) + (255,)
                for dx in range(escala):
                    for dy in range(escala):
                        img.putpixel((ox + c * escala + dx, oy + f * escala + dy), pixel)
    img.save(ruta, sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
