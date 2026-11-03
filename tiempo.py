"""Mira qué tiempo hace en tu ciudad (con Open-Meteo, que es gratis y no pide registro)."""

import json
import urllib.parse
import urllib.request

LLUVIA = set(range(51, 68)) | {80, 81, 82, 95, 96, 99}
NIEVE = set(range(71, 78)) | {85, 86}


def describir(codigo):
    if codigo == 0:
        return "despejado"
    if codigo <= 3:
        return "con nubes"
    if codigo in (45, 48):
        return "con niebla"
    if codigo in NIEVE:
        return "nevando"
    if codigo >= 95:
        return "con tormenta"
    if codigo in LLUVIA:
        return "lloviendo"
    return "raro"


def _leer(url):
    with urllib.request.urlopen(url, timeout=10) as respuesta:
        return json.load(respuesta)


def consultar(ciudad):
    """Devuelve un diccionario con el tiempo, o None si no se pudo (sin internet, ciudad rara...)."""
    try:
        geo = _leer("https://geocoding-api.open-meteo.com/v1/search?count=1&language=es&format=json&name="
                    + urllib.parse.quote(ciudad))
        lugar = geo["results"][0]
        datos = _leer("https://api.open-meteo.com/v1/forecast?current=temperature_2m,weather_code"
                      "&hourly=precipitation_probability&forecast_hours=3&timezone=auto"
                      f"&latitude={lugar['latitude']}&longitude={lugar['longitude']}")
        codigo = datos["current"]["weather_code"]
        prob = max([p or 0 for p in datos["hourly"]["precipitation_probability"]] or [0])
        return {
            "ciudad": lugar["name"],
            "temp": datos["current"]["temperature_2m"],
            "codigo": codigo,
            "descripcion": describir(codigo),
            "lluvia": codigo in LLUVIA or prob >= 60,  # llueve o va a llover pronto
            "nieve": codigo in NIEVE,
        }
    except Exception:
        return None
