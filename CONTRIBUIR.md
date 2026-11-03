# Cómo contribuir

¡Gracias por querer mejorar a Clawd! No hace falta ser experto: muchas de las cosas más bonitas son solo dibujos.

## Ideas fáciles para empezar

- **Un disfraz nuevo.** En `dibujos.py`, añade un sombrero a `SOMBREROS` y su nombre a `DISFRACES`. Cada letra es un píxel (la tabla de colores está arriba del archivo). Las filas tienen que tener 14 caracteres.
- **Mensajes y frases.** En `cosas.py` están `MENSAJES` (lo que te trae), `FRASES` (lo que dice al hacerle clic) y `PAUSAS` (los carteles de descanso).
- **Una paleta de postal.** También en `cosas.py`, en `PALETAS_POSTAL`: cielo de arriba, cielo de abajo y sol.

## Algo más grande: un comportamiento nuevo

Clawd funciona con estados. En `clawd.py` cada uno tiene su función `estado_<nombre>()`, que se llama 30 veces por segundo:

1. Escribe `estado_lo_que_sea(self, ahora)` con lo que hace en cada fotograma.
2. Para empezarlo, llama a `self.cambiar("lo_que_sea", segundos)`.
3. Para que lo haga solo de vez en cuando, añádelo a la lista `opciones` de `decidir()`.
4. Si necesita una postura especial, añádela en `componer()`.

## Paso a paso, si es tu primera vez en GitHub

1. Pulsa **Fork**, arriba a la derecha, para tener tu propia copia.
2. Clónala y haz tus cambios.
3. Pruébalos con `py clawd_escritorio.py` (con `py`, no con `pyw`, así ves los errores).
4. Si cambiaste algo que se ve, regenera las imágenes:
   ```bash
   py herramientas/generar_imagenes.py
   py herramientas/generar_banner.py
   ```
5. Haz commit, súbelo y pulsa **Contribute → Open pull request**.

## Estilo del código

- Todo en español: nombres, comentarios y textos.
- Comentarios cortos que expliquen el *por qué*, pensando en alguien que está aprendiendo.
- Sin librerías nuevas si se puede: Clawd solo necesita Python, y Pillow es opcional.
