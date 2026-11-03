"""
Clawd, la mascota: cómo decide qué hacer, cómo se mueve y cómo se dibuja.

Funciona con "estados": en cada momento Clawd está en uno (quieto, caminar, dormir...)
y cada estado tiene su función estado_<nombre>() que se llama unas 30 veces por segundo.
"""

import io
import math
import random
import threading
import time
import tkinter as tk
import urllib.request
from datetime import datetime

import dibujos as d
import windows
from cosas import FRASES, MENSAJES, Burbuja, Objeto
from fisica import LARGO_HILO, LARGO_HILO_ARRASTRE, Hilo

try:
    from PIL import Image, ImageTk
    HAY_PILLOW = True
except ImportError:
    HAY_PILLOW = False

COLS, FILAS = 20, 16  # el lienzo de Clawd mide 20 x 16 píxeles
GRAVEDAD = 0.8
# Estados en los que está de pie en el suelo (ahí puede llevar paraguas o capa)
DE_PIE = ("quieto", "caminar", "traer", "cazar", "mareado", "ir_comer", "pillar", "huir", "irse", "en_ventana")


def es_de_noche():
    hora = datetime.now().hour
    return hora >= 22 or hora < 7


class Clawd:
    def __init__(self, mundo, principal=True):
        self.mundo = mundo
        self.principal = principal  # el principal trae cosas; Bit, el amigo, solo juega
        self.nombre = "Clawd" if principal else "Bit"
        m = mundo

        self.win = tk.Toplevel(m.raiz)
        self.win.overrideredirect(True)  # sin bordes ni barra de título
        self.win.wm_attributes("-topmost", True)  # siempre encima de todo
        self.win.wm_attributes("-transparentcolor", d.TRANSPARENTE)
        self.win.config(bg=d.TRANSPARENTE)
        self.lienzo = tk.Canvas(self.win, bg=d.TRANSPARENTE, highlightthickness=0)
        self.lienzo.pack()
        self.aplicar_ajustes()

        # Posición: x es el centro de Clawd, y es el borde de abajo de su ventana
        self.x = (m.izq + m.der) / 2 if principal else random.uniform(m.izq + 200, m.der - 200)
        self.y = m.arr + self.H  # empieza arriba y cae
        self.vx = self.vy = 0.0
        self.dir = 1
        self.mirar = 0
        self.moviendo = False
        self.t = random.randint(0, 100)
        self.parpadeo = 0
        self.fila_arriba = self.fila_abajo = 0
        self.fila_cabeza = FILAS - 7

        self.burbuja = Burbuja(m.raiz)
        self.cargando = None  # lo que va arrastrando ahora mismo
        self.objetos = []     # lo que ya dejó en la pantalla
        self.tipo_viaje = self.contenido_viaje = self.foto = None
        self.proximo_viaje = time.time() + random.uniform(20, 40)

        self.laptop = 0.0  # 0 = guardada, 1 = abierta del todo
        self.hilo = None
        self.vel_balanceo = 0.0
        self.pulsado = None
        self.mareo = 0
        self.mareo_pendiente = False
        self.caricia = 0.0
        self.raton_x_antes = 0

        self.ultima_interaccion = time.time()
        self.emocion_hasta = 0.0
        self.ojos_corazon_hasta = 0.0
        self.particulas = []
        self.proxima_particula = 0.0
        self.comandos, self.dibujado = [], None
        self.pos_ventana = None

        self.galleta = None
        self.amigo_juego = None
        self.espera_hasta = 0.0
        self.ventana = self.rect_v = None
        self.pausa_hasta = 0.0
        self.salto = self.luego = None
        self.salto_i = self.salto_n = 0
        self.salto_alto = 0
        self.seguir_cazando = 0.0
        self.proximo_salto = 0.0
        self.objetivo = self.x
        self.cerrado = False

        self.estado, self.fase, self.hasta = None, "", 0.0
        self.cambiar("caer")

        self.lienzo.bind("<ButtonPress-1>", self.al_pulsar)
        self.lienzo.bind("<B1-Motion>", self.al_mover)
        self.lienzo.bind("<ButtonRelease-1>", self.al_soltar)
        self.lienzo.bind("<Button-3>", self.mostrar_menu)
        self.menu = m.crear_menu(self)

    def aplicar_ajustes(self):
        aj = self.mundo.aj
        self.P = int(aj["tamano"])
        self.color = aj["color"] if self.principal else aj["color_amigo"]
        self.W, self.H = COLS * self.P, FILAS * self.P
        self.lienzo.config(width=self.W, height=self.H)
        self.margen = self.W / 2 - 3 * self.P  # así su cuerpo toca justo el borde de la pantalla

    # ----- el bucle principal (lo llama el Mundo unas 30 veces por segundo) -----

    def paso(self, ahora):
        self.t += 1
        self.reaccionar(ahora)
        getattr(self, "estado_" + self.estado)(ahora)  # p. ej. llama a estado_caminar()
        if self.cerrado:  # Bit acaba de irse
            return

        if self.parpadeo > 0:
            self.parpadeo -= 1
        elif random.random() < 0.01:
            self.parpadeo = 6

        self.comprobar_caricias(ahora)
        self.mover_particulas()
        self.dibujar()
        self.colocar()
        for o in self.objetos[:]:
            if o.caducado(ahora):
                o.cerrar()
                self.objetos.remove(o)

    def reaccionar(self, ahora):
        """Cosas que le hacen dejar lo que está haciendo: galletas, avisos, teclear, música."""
        m = self.mundo
        tecleo = ahora - m.ultima_tecla < 1
        libre = self.estado in ("quieto", "caminar")
        galleta = m.galleta_libre() if self.estado in ("quieto", "caminar", "dormir", "bailar") else None
        if galleta:
            galleta.duena = self
            self.galleta = galleta
            self.decir("¡Una galleta!", 2)
            self.cambiar("ir_comer")
        elif self.principal and m.cola_carteles and self.estado in ("quieto", "caminar", "dormir", "bailar"):
            self.empezar_viaje("cartel", m.cola_carteles.pop(0))
        elif tecleo and self.estado in ("quieto", "caminar", "bailar"):
            self.cambiar("escribir", fase="sacar")
        elif tecleo and self.estado == "dormir":
            self.despertar()
        elif m.hay_musica and m.aj["bailar"] and libre:
            self.cambiar("bailar", 3)
            self.decir("♪ ¡Me encanta esta canción! ♪", 2)

    def cambiar(self, estado, segundos=0, fase=""):
        if self.cargando and estado != "traer":  # si lo interrumpen, suelta lo que llevaba
            self.objetos.append(self.cargando)
            self.cargando = None
        if estado != "escribir":
            self.laptop = 0.0
        if estado not in ("colgado_raton", "arrastrado"):
            self.hilo = None
        if estado not in ("ir_comer", "comer") and self.galleta:
            self.galleta.duena = None
            self.galleta = None
        self.estado = estado
        self.fase = fase
        self.hasta = time.time() + segundos

    def decidir(self, ahora):
        """Elige qué hacer a continuación."""
        m = self.mundo
        sueno = 150 if es_de_noche() else 420  # segundos sin hacerle caso antes de dormirse
        if ahora - self.ultima_interaccion > sueno and random.random() < 0.4:
            self.dormir()
            return
        if self.principal and ahora >= self.proximo_viaje:
            self.empezar_viaje()
            return

        t = m.aj["travesuras"]
        otro = m.amigo_de(self)
        opciones = [
            (0.05 * t, lambda: self.cambiar("perseguir", 6)),
            (0.04 * t, self.ir_a_trepar),
            (0.07 * t, self.ir_a_ventana),
            (0.05 * t, self.cazar),
        ]
        if otro and otro.estado in ("quieto", "caminar"):
            opciones.append((0.12 * t, lambda: self.jugar_con(otro)))
        r = random.random()
        for prob, accion in opciones:
            if r < prob:
                if accion() is not False:  # ir_a_ventana devuelve False si no hay ventanas
                    return
                break
            r -= prob

        if self.animo(ahora) == "aburrido" and random.random() < 0.15:
            self.decir(random.choice(["Qué aburrimiento...", "¿Jugamos?", "Hmm..."]), 2.5)
        if random.random() < 0.55:
            self.cambiar("caminar")
            self.objetivo = random.uniform(m.izq + self.margen, m.der - self.margen)
        else:
            self.cambiar("quieto", random.uniform(2, 6))

    # ----- ánimo -----

    def animo(self, ahora):
        if self.estado == "dormir":
            return "dormido"
        if ahora < self.emocion_hasta:
            return "emocionado"
        if ahora - self.ultima_interaccion > 180:
            return "aburrido"
        return "contento"

    def interaccion(self):
        """Le hiciste caso: ya no se aburre."""
        self.ultima_interaccion = time.time()

    def emocionar(self, segundos):
        self.emocion_hasta = time.time() + segundos
        self.interaccion()

    def velocidad(self):
        return self.mundo.aj["velocidad"] * (0.6 if self.animo(time.time()) == "aburrido" else 1)

    # ----- ayudas para moverse -----

    def andar_hacia(self, objetivo, vel=None):
        """Da un pasito hacia objetivo. Devuelve True cuando ya llegó."""
        vel = vel or self.velocidad()
        dif = objetivo - self.x
        if abs(dif) <= vel:
            self.x = objetivo
            self.moviendo = False
            return True
        self.dir = 1 if dif > 0 else -1
        self.mirar = self.dir
        self.x += self.dir * vel
        self.moviendo = True
        return False

    def saltar_hacia(self, x1, y1, luego):
        """Salta en curva (parábola) hasta (x1, y1) y luego llama a `luego`."""
        dist = math.hypot(x1 - self.x, y1 - self.y)
        self.salto = (self.x, self.y, x1, y1)
        self.salto_n = max(18, int(dist / 10))
        self.salto_i = 0
        self.salto_alto = 50 + max(0, self.y - y1) * 0.4
        self.luego = luego
        self.mirar = 1 if x1 > self.x else -1
        self.cambiar("saltar_a")

    def limites(self):
        m = self.mundo
        return m.izq + self.margen, m.der - self.margen

    def decir(self, texto, segundos=3):
        self.burbuja.decir(texto, segundos)

    def colocar(self):
        pos = (int(self.x - self.W / 2), int(self.y - self.H))
        if pos != self.pos_ventana:  # mover una ventana cuesta: solo si de verdad se movió
            self.win.geometry(f"+{pos[0]}+{pos[1]}")
            self.pos_ventana = pos
        arriba = self.y - self.H
        self.burbuja.seguir(self.x, arriba + self.fila_arriba * self.P - 4,
                            arriba + self.fila_abajo * self.P + 4, self.mundo.arr)

    # ----- estados: lo que hace Clawd en cada momento -----

    def estado_quieto(self, ahora):
        self.y = self.mundo.suelo
        if ahora < self.emocion_hasta:  # contento: da saltitos
            self.y -= abs(math.sin(self.t / 4)) * 8
        self.mirar = 0
        if ahora >= self.hasta:
            self.decidir(ahora)

    def estado_caminar(self, ahora):
        self.y = self.mundo.suelo
        if self.andar_hacia(self.objetivo):
            self.cambiar("quieto", random.uniform(1, 4))

    def estado_caer(self, ahora):
        m = self.mundo
        self.vy += GRAVEDAD
        self.y += self.vy
        self.x += self.vx
        self.vx *= 0.99
        izq, der = self.limites()
        if self.x < izq or self.x > der:  # rebota en las paredes
            self.x = max(izq, min(der, self.x))
            self.vx = -self.vx * 0.6
        if self.y - self.H < m.arr:  # y en el techo
            self.y = m.arr + self.H
            self.vy = abs(self.vy) * 0.3
        if self.y >= m.suelo:
            self.y = m.suelo
            if self.vy > 18:
                self.mareo_pendiente = True  # ¡menudo golpe!
            if self.vy > 6:
                self.vy = -self.vy * 0.4  # rebote
                self.vx *= 0.7
            elif abs(self.vx) > 1.5:
                self.vy = 0  # sigue resbalando por el suelo
                self.vx *= 0.85
            else:
                self.aterrizar(ahora)

    def aterrizar(self, ahora):
        self.vx = self.vy = 0
        if self.seguir_cazando > ahora:
            self.cambiar("cazar", self.seguir_cazando - ahora)
        elif self.mareo_pendiente:
            self.mareo_pendiente = False
            self.cambiar("mareado", 3)
            self.decir("Todo da vueltas...", 2.5)
        else:
            self.cambiar("quieto", 1.5)

    def estado_saltar_a(self, ahora):
        self.salto_i += 1
        s = min(1.0, self.salto_i / self.salto_n)
        x0, y0, x1, y1 = self.salto
        self.x = x0 + (x1 - x0) * s
        self.y = y0 + (y1 - y0) * s - self.salto_alto * 4 * s * (1 - s)
        if s >= 1:
            self.luego()

    def estado_mareado(self, ahora):
        self.y = self.mundo.suelo
        izq, der = self.limites()
        self.x = max(izq, min(der, self.x + math.sin(self.t / 3) * 1.2))  # se tambalea
        if ahora >= self.hasta:
            self.cambiar("quieto", 1)

    # Traer cosas

    def estado_traer(self, ahora):
        m = self.mundo
        self.y = m.suelo
        rapido = 2.5 if self.tipo_viaje == "cartel" else 1.5  # los avisos van con prisa
        if self.fase == "salir":  # se va por el borde de la pantalla
            if self.andar_hacia(self.objetivo, self.velocidad() * rapido):
                self.fase = "esperar"
                self.hasta = ahora + 10
        elif self.fase == "esperar":  # fuera de la pantalla, espera a que llegue la foto
            if self.tipo_viaje == "foto" and self.foto is None and ahora < self.hasta:
                return
            self.cargando = self.crear_objeto()
            self.win.lift()
            self.objetivo = random.uniform(m.izq + 250, m.der - 250)
            self.fase = "volver"
        elif self.fase == "volver":  # vuelve arrastrando el objeto detrás de él
            llego = self.andar_hacia(self.objetivo, self.velocidad() * (1.5 if rapido > 2 else 1))
            o = self.cargando
            borde = self.x - self.dir * 7 * self.P
            o.mover(borde - o.ancho if self.dir > 0 else borde, m.suelo - o.alto - abs(math.sin(self.t / 4)) * 3)
            if llego:
                self.objetos.append(o)
                self.cargando = None
                if self.tipo_viaje == "cartel":
                    self.decir("¡Esto es importante!", 3)
                else:
                    self.decir(random.choice(["¡Mira lo que encontré!", "Te traje esto", "Para ti"]))
                self.cambiar("quieto", 3)

    def empezar_viaje(self, tipo=None, contenido=None):
        self.proximo_viaje = time.time() + random.uniform(0.6, 1.4) * self.mundo.aj["minutos_viaje"] * 60
        if tipo is None:
            tipo = random.choice(["mensaje", "postal"] + (["foto", "foto"] if HAY_PILLOW else []))
        if tipo == "foto" and not HAY_PILLOW:
            self.decir("Para fotos instala Pillow. ¡Te traigo una postal!", 4)
            tipo = "postal"
        if tipo == "foto":
            self.foto = None
            threading.Thread(target=self.descargar_foto, daemon=True).start()
        self.tipo_viaje, self.contenido_viaje = tipo, contenido
        self.cambiar("traer", fase="salir")  # suelta lo que llevara antes
        m = self.mundo
        self.objetivo = m.izq - self.W if self.x < (m.izq + m.der) / 2 else m.der + self.W

    def descargar_foto(self):
        """Se ejecuta en segundo plano para que Clawd no se congele mientras descarga."""
        try:
            url = f"https://picsum.photos/260/170?random={random.randint(1, 10**6)}"
            with urllib.request.urlopen(url, timeout=10) as respuesta:
                self.foto = respuesta.read()
        except Exception:
            self.foto = b""

    def crear_objeto(self):
        raiz = self.mundo.raiz
        if self.tipo_viaje == "cartel":
            return Objeto(raiz, "cartel", self.contenido_viaje)
        if self.tipo_viaje == "foto":
            try:
                imagen = ImageTk.PhotoImage(Image.open(io.BytesIO(self.foto)))
                return Objeto(raiz, "foto", imagen)
            except Exception:
                pass  # si no hubo internet, trae una postal
        if self.tipo_viaje == "mensaje":
            return Objeto(raiz, "mensaje", random.choice(MENSAJES))
        return Objeto(raiz, "postal")

    def cerrar_objetos(self):
        for o in self.objetos:
            o.cerrar()
        self.objetos.clear()

    # Colgarse del ratón (con hilo de telaraña)

    def estado_perseguir(self, ahora):
        m = self.mundo
        mx, my = m.raton
        # va a un punto debajo del ratón, a la distancia del largo del hilo
        dx, dy = mx - self.x, min(my + LARGO_HILO + self.H, m.suelo) - self.y
        dist = math.hypot(dx, dy)
        if dist < 14:
            self.hilo = Hilo((mx, my + 3), (self.x, self.y - self.H), LARGO_HILO, (self.vx, self.vy))
            self.vx = self.vy = 0
            self.mareo = 0
            self.cambiar("colgado_raton", random.uniform(6, 10))
            self.decir("¡Te tengo!", 2)
        elif ahora >= self.hasta:
            self.vx = self.vy = 0
            self.cambiar("caer")
        else:
            vel = min(9, dist)
            self.vx, self.vy = dx / dist * vel, dy / dist * vel
            self.x += self.vx
            self.y += self.vy
            self.mirar = 1 if dx > 0 else -1

    def colgar_del_raton(self):
        """Mueve el hilo con el ratón y coloca a Clawd agarrado a la punta."""
        mx, my = self.mundo.raton
        izq, der = self.limites()
        # +3: el hilo empieza justo debajo de la punta del ratón, así puedes seguir haciendo clic
        self.hilo.paso((mx, my + 3), izq, der, self.mundo.suelo - 10 * self.P)
        hx, hy = self.hilo.punta()
        vx, vy = self.hilo.velocidad()
        if math.hypot(vx, vy) > 22:
            self.mareo += 1  # ¡lo estás zarandeando!
        self.vel_balanceo = vx
        self.x, self.y = hx, hy + self.H  # sus manos están arriba del todo de su ventana

    def soltar_hilo(self):
        """Se suelta conservando el impulso, como Spider-Man al final del columpio."""
        self.vx, self.vy = self.hilo.velocidad()
        self.mareo_pendiente = self.mareo > 12
        self.mareo = 0
        self.cambiar("caer")

    def estado_colgado_raton(self, ahora):
        self.colgar_del_raton()
        if ahora >= self.hasta:
            self.soltar_hilo()

    def estado_arrastrado(self, ahora):
        self.colgar_del_raton()

    # Trepar y colgarse arriba

    def ir_a_trepar(self):
        m = self.mundo
        self.cambiar("trepar", fase="ir")
        izq, der = self.limites()
        self.objetivo = izq if self.x < (m.izq + m.der) / 2 else der

    def estado_trepar(self, ahora):
        m = self.mundo
        if self.fase == "ir":  # camina hasta la pared
            self.y = m.suelo
            if self.andar_hacia(self.objetivo):
                self.fase = "subir"
        else:  # sube por la pared
            self.moviendo = True
            self.y -= 3
            if self.y - self.H <= m.arr:
                self.y = m.arr + self.H
                self.cambiar("colgado_arriba", random.uniform(6, 12))
                self.objetivo = random.uniform(*self.limites())

    def estado_colgado_arriba(self, ahora):
        self.y = self.mundo.arr + self.H
        if self.andar_hacia(self.objetivo, 1.2):
            self.objetivo = random.uniform(*self.limites())
        if ahora >= self.hasta:
            self.vy = 0
            self.cambiar("caer")
            self.decir("¡Aaaah!", 1.5)

    # Subirse encima de una ventana

    def ir_a_ventana(self):
        m = self.mundo
        delante = windows.ventana_de_delante()
        candidatas = [(h, r) for h, r in windows.ventanas_visibles()
                      if r[1] >= m.arr + 80 and r[0] < m.der - 150 and r[2] > m.izq + 150]
        if not candidatas:
            return False
        hwnd, r = next(((h, r) for h, r in candidatas if h == delante), random.choice(candidatas[:3]))
        izq_v = max(r[0], m.izq) + self.margen
        der_v = min(r[2], m.der) - self.margen
        if izq_v >= der_v:
            return False
        self.ventana, self.rect_v = hwnd, r
        self.saltar_hacia(random.uniform(izq_v, der_v), r[1], self.llegar_a_ventana)

    def llegar_a_ventana(self):
        self.cambiar("en_ventana", random.uniform(10, 25))
        self.objetivo = self.x
        self.pausa_hasta = 0

    def estado_en_ventana(self, ahora):
        m = self.mundo
        r = windows.rect_ventana(self.ventana)
        if r is None or abs(r[0] - self.rect_v[0]) > 3 or abs(r[1] - self.rect_v[1]) > 3:
            # ¡movieron (o cerraron) la ventana!
            self.vx = self.vy = 0
            self.cambiar("caer")
            self.decir("¡Eeeeh!", 1.5)
            return
        self.rect_v = r
        self.y = r[1]
        if ahora >= self.pausa_hasta and self.andar_hacia(self.objetivo, self.velocidad() * 0.8):
            self.pausa_hasta = ahora + random.uniform(0.5, 3)
            self.objetivo = random.uniform(max(r[0], m.izq) + self.margen, min(r[2], m.der) - self.margen)
        if ahora >= self.hasta:  # se aburre y salta al suelo
            self.vx, self.vy = self.dir * 2, -6
            self.cambiar("caer")

    # Cazar el ratón como un gato con un puntero láser

    def cazar(self):
        self.cambiar("cazar", random.uniform(8, 12))
        self.decir("¡Ese puntito es mío!", 2)

    def estado_cazar(self, ahora):
        m = self.mundo
        mx, my = m.raton
        if ahora >= self.hasta:
            self.seguir_cazando = 0
            self.cambiar("quieto", 2)
            self.decir("Uf, se escapó", 2)
            return
        if abs(mx - self.x) < 60 and m.suelo - 280 < my < m.suelo - 20 and ahora > self.proximo_salto:
            self.proximo_salto = ahora + 1.2
            self.seguir_cazando = self.hasta  # después del salto sigue cazando
            self.saltar_hacia(mx, min(m.suelo, my + 7 * self.P), lambda: self.cambiar("caer"))
            return
        izq, der = self.limites()
        llego = self.andar_hacia(max(izq, min(der, mx)), self.velocidad() * 1.9)
        self.y = m.suelo - (0 if llego else abs(math.sin(self.t / 3)) * 10)  # corre a saltitos

    # Dormir

    def dormir(self):
        self.cambiar("dormir", random.uniform(120, 300))
        self.decir("Qué sueño... (bostezo)", 2.5)

    def despertar(self):
        self.cambiar("despertar", 2)
        self.decir("¡Buenos días!", 2)
        self.interaccion()

    def estado_dormir(self, ahora):
        self.y = self.mundo.suelo
        self.mirar = 0
        if ahora > self.proxima_particula:
            self.emitir("zeta")
            self.proxima_particula = ahora + 1.3
        if ahora >= self.hasta:
            self.despertar()

    def estado_despertar(self, ahora):
        self.y = self.mundo.suelo
        if ahora >= self.hasta:
            self.cambiar("quieto", 1)

    # Bailar con la música

    def estado_bailar(self, ahora):
        self.y = self.mundo.suelo - abs(math.sin(self.t / 4)) * 4
        if self.mundo.hay_musica:
            self.hasta = max(self.hasta, ahora + 3)  # sigue mientras suene algo
        if ahora > self.proxima_particula:
            self.emitir("nota")
            self.proxima_particula = ahora + 0.7
        if ahora >= self.hasta:
            self.cambiar("quieto", 1)

    # Comer galletas

    def estado_ir_comer(self, ahora):
        g = self.galleta
        if g is None or g not in self.mundo.galletas:
            self.cambiar("quieto", 1)
            return
        self.y = self.mundo.suelo
        lado = -1 if self.x < g.x else 1  # se pone al lado de la galleta
        izq, der = self.limites()
        objetivo = max(izq, min(der, g.x + lado * (7 * self.P + 18)))
        if self.andar_hacia(objetivo, self.velocidad() * 1.8) and g.en_suelo:
            self.cambiar("comer", 2.4)

    def estado_comer(self, ahora):
        g = self.galleta
        self.y = self.mundo.suelo
        self.mirar = 1 if g.x > self.x else -1
        mordiscos = min(3, int((2.4 - (self.hasta - ahora)) / 0.8) + 1)
        if mordiscos > g.mordiscos:
            g.mordiscos = mordiscos
            self.emitir("miga", 3)
        if ahora >= self.hasta:
            if g in self.mundo.galletas:
                self.mundo.galletas.remove(g)
            self.galleta = None
            self.emocionar(6)
            self.emitir("corazon", 3)
            self.decir("¡Ñam! ¡Gracias!", 2.5)
            self.cambiar("quieto", 3)

    # Jugar al pilla-pilla con Bit

    def jugar_con(self, otro):
        self.amigo_juego, otro.amigo_juego = otro, self
        self.cambiar("pillar", 15)
        otro.cambiar("huir", 15)
        self.decir("¡Te pillo!", 2)
        otro.decir("¡No me pillas!", 2)

    def fin_juego(self):
        otro = self.amigo_juego
        self.amigo_juego = None
        self.cambiar("quieto", 2)
        self.emitir("corazon", 2)
        if otro and otro.estado in ("pillar", "huir"):
            otro.amigo_juego = None
            otro.cambiar("quieto", 2)
            otro.decir("¡Otra vez!", 2)

    def estado_pillar(self, ahora):
        o = self.amigo_juego
        if o is None or o.estado != "huir" or ahora >= self.hasta:
            self.fin_juego()
            return
        self.y = self.mundo.suelo
        if ahora < self.espera_hasta:  # cuenta hasta tres antes de correr
            return
        self.andar_hacia(o.x, self.velocidad() * 1.65)
        if abs(o.x - self.x) < 50:  # ¡pillado! cambian los papeles
            restante = self.hasta - ahora
            o.cambiar("pillar", restante)
            o.espera_hasta = ahora + 1
            self.cambiar("huir", restante)
            o.decir("¡Me pillaste!", 1.5)

    def estado_huir(self, ahora):
        o = self.amigo_juego
        if o is None or o.estado != "pillar" or ahora >= self.hasta:
            self.fin_juego()
            return
        self.y = self.mundo.suelo
        izq, der = self.limites()
        lejos = 1 if self.x > o.x else -1
        destino = self.x + lejos * 100
        if destino < izq or destino > der:  # acorralado contra la pared: se escapa por el otro lado
            destino = self.x - lejos * 100
        self.andar_hacia(max(izq, min(der, destino)), self.velocidad() * 1.45)

    def irse(self):
        """Bit se despide y se va por un lado de la pantalla."""
        m = self.mundo
        self.cambiar("irse")
        self.decir("¡Adiós!", 2)
        self.objetivo = m.izq - self.W if self.x < (m.izq + m.der) / 2 else m.der + self.W

    def estado_irse(self, ahora):
        self.y = self.mundo.suelo
        if self.andar_hacia(self.objetivo, self.velocidad() * 1.5):
            self.mundo.quitar(self)

    # Escribir con la laptop

    def sacar_laptop(self):
        self.mundo.ultima_tecla = time.time()
        self.cambiar("escribir", fase="sacar")

    def estado_escribir(self, ahora):
        self.y = self.mundo.suelo
        self.mirar = 0
        ultima = self.mundo.ultima_tecla
        if self.fase == "sacar":
            self.laptop = min(1.0, self.laptop + 0.07)
            if self.laptop >= 1:
                self.fase = "teclear"
        elif self.fase == "teclear":
            if ahora - ultima > 3:
                self.fase = "guardar"
        else:  # guardar
            if ahora - ultima < 1:
                self.fase = "sacar"
                return
            self.laptop = max(0.0, self.laptop - 0.07)
            if self.laptop <= 0:
                self.cambiar("quieto", 1.5)

    def saltar(self):
        self.vy = -11
        self.cambiar("caer")

    # ----- ratón -----

    def comprobar_caricias(self, ahora):
        """Si pasas el ratón por encima sin hacer clic, le haces mimos."""
        if self.estado not in ("quieto", "caminar", "dormir", "bailar"):
            self.caricia = 0
            return
        mx, my = self.mundo.raton
        dentro = abs(mx - self.x) < 7 * self.P and self.y - 9 * self.P < my < self.y
        if dentro and not windows.boton_izquierdo_pulsado():
            self.caricia += abs(mx - self.raton_x_antes)
        self.raton_x_antes = mx
        self.caricia *= 0.96
        if self.caricia > 250:
            self.caricia = 0
            self.emitir("corazon", 3)
            self.ojos_corazon_hasta = ahora + 2
            self.emocionar(4)
            if self.estado == "dormir":
                self.despertar()
            else:
                if self.estado == "caminar":
                    self.cambiar("quieto", 3)
                if not self.burbuja.visible:
                    self.decir(random.choice(["¡Me encanta!", "Jiji", "Más, más", "Mimos"]), 1.5)

    def al_pulsar(self, e):
        self.pulsado = (e.x_root, e.y_root)
        self.interaccion()

    def al_mover(self, e):
        if self.pulsado and self.estado != "arrastrado":
            x0, y0 = self.pulsado
            if abs(e.x_root - x0) + abs(e.y_root - y0) > 6:
                self.hilo = Hilo((e.x_root, e.y_root + 3), (self.x, self.y - self.H), LARGO_HILO_ARRASTRE)
                self.mareo = 0
                self.cambiar("arrastrado")

    def al_soltar(self, e):
        if self.estado == "arrastrado":
            self.soltar_hilo()
        elif self.pulsado:
            if self.estado == "dormir":
                self.despertar()
            else:
                self.saltar()
                self.decir(random.choice(FRASES), 2)
        self.pulsado = None

    def mostrar_menu(self, e):
        self.interaccion()
        self.var_disfraz.set(self.mundo.aj["disfraz" if self.principal else "disfraz_amigo"])
        self.menu.tk_popup(e.x_root, e.y_root)

    # ----- mostrar, esconder y cerrar -----

    def mostrar(self, visible):
        if visible:
            self.win.deiconify()
            self.win.lift()
        else:
            self.win.withdraw()
            self.burbuja.esconder()
        for o in self.objetos + ([self.cargando] if self.cargando else []):
            o.mostrar(visible)

    def cerrar(self):
        self.cerrado = True
        self.cerrar_objetos()
        if self.cargando:
            self.cargando.cerrar()
        self.burbuja.win.destroy()
        self.win.destroy()

    # ----- particulitas -----

    def emitir(self, tipo, n=1):
        P = self.P
        for _ in range(n):
            if tipo == "miga":  # salen de la boca y caen
                x = self.W / 2 + self.mirar * 5 * P + random.uniform(-P, P)
                y = (self.fila_cabeza + 3) * P
                vx, vy = self.mirar * random.uniform(0.5, 1.5), random.uniform(-1.5, 0)
            else:  # suben flotando desde la cabeza
                x = self.W / 2 + random.uniform(-3 * P, 3 * P)
                y = (self.fila_cabeza - 1) * P
                vx = random.uniform(0.2, 0.5) if tipo == "zeta" else random.uniform(-0.3, 0.3)
                vy = -random.uniform(0.6, 1.0)
            self.particulas.append({"tipo": tipo, "x": x, "y": y, "vx": vx, "vy": vy, "vida": 50})

    def mover_particulas(self):
        for p in self.particulas[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            if p["tipo"] == "miga":
                p["vy"] += 0.3
            p["vida"] -= 1
            if p["vida"] <= 0 or p["y"] < -10 or p["y"] > self.H:
                self.particulas.remove(p)

    def dibujar_particula(self, tipo, x, y):
        filas, color = d.PARTICULAS[tipo]
        q = max(2, self.P // 2)
        for f, fila in enumerate(filas):
            for c, letra in enumerate(fila):
                if letra == "X":
                    self.rect(x + c * q, y + f * q, q, q, color)

    # ----- dibujo -----
    #
    # Para que vaya fluido, no dibuja directamente: primero apunta los rectángulos en una lista
    # (juntando los píxeles seguidos del mismo color en uno solo) y al final, solo si el dibujo
    # cambió respecto al fotograma anterior, borra el lienzo y lo pinta de nuevo.

    def rect(self, x, y, w, h, color):
        if self.comandos:
            px, py, pw, ph, pcolor = self.comandos[-1]
            if py == y and ph == h and pcolor == color and px + pw == x:  # sigue la fila: alárgalo
                self.comandos[-1] = (px, py, pw + w, ph, pcolor)
                return
        self.comandos.append((x, y, w, h, color))

    def volcar(self):
        if self.comandos == self.dibujado:
            return  # igual que antes: no hace falta tocar nada
        L = self.lienzo
        L.delete("all")
        for x, y, w, h, color in self.comandos:
            L.create_rectangle(x, y, x + w, y + h, fill=color, outline="")
        self.dibujado = self.comandos

    def pintar(self, filas, col0, fila0):
        """Dibuja una lista de filas de letras empezando en la casilla (col0, fila0)."""
        self.fila_arriba = min(self.fila_arriba, fila0)
        self.fila_abajo = max(self.fila_abajo, fila0 + len(filas))
        for f, fila in enumerate(filas):
            for c, letra in enumerate(fila):
                if letra != ".":
                    self.pintar_letra(letra, col0 + c, fila0 + f)

    def pintar_letra(self, letra, c, f):
        P = self.P
        x, y = c * P, f * P
        if letra == "X":
            self.rect(x, y, P, P, self.color)
        elif letra in d.COLORES:
            self.rect(x, y, P, P, d.COLORES[letra])
        else:  # ojos especiales: un píxel del cuerpo con algo encima
            self.rect(x, y, P, P, self.color)
            g = max(1, P // 3)
            if letra == "c":    # cerrado: una rayita
                self.rect(x, y + P // 2, P, g, d.OJO)
            elif letra == "a":  # aburrido: medio cerrado
                self.rect(x, y + P // 2, P, P - P // 2, d.OJO)
            elif letra == "f":  # feliz: rayita arriba, como un ^
                self.rect(x, y + P // 4, P, g, d.OJO)
            elif letra == "h":  # corazón
                self.rect(x, y, P, P, d.ROSA)
            elif letra == "m":  # mareado: el ojo se mueve solo
                ox, oy = random.choice((-1, 0, 1)) * g, random.choice((-1, 0, 1)) * g
                self.rect(x + g + ox, y + g + oy, P - 2 * g, P - 2 * g, d.OJO)

    def fila_ojos(self):
        ahora, e = time.time(), self.estado
        if e == "mareado":
            ojo = "m"
        elif e == "dormir":
            ojo = "c"
        elif ahora < self.ojos_corazon_hasta:
            ojo = "h"
        elif self.parpadeo > 0:
            ojo = "c"
        elif e == "comer" or ahora < self.emocion_hasta:
            ojo = "f"
        elif self.animo(ahora) == "aburrido":
            ojo = "a"
        else:
            ojo = "E"
        fila = list(d.ARRIBA)
        mirar = max(-1, min(1, self.mirar))
        fila[4 + mirar] = ojo
        fila[9 + mirar] = ojo
        return "".join(fila)

    def disfraz_actual(self):
        elegido = self.mundo.aj["disfraz" if self.principal else "disfraz_amigo"]
        if elegido != "auto":
            return elegido
        hoy = datetime.now()
        tiempo = self.mundo.tiempo
        if hoy.month == 10:
            return "bruja"
        if hoy.month == 12:
            return "navidad"
        if es_de_noche():
            return "dormir"
        if tiempo and tiempo["nieve"]:
            return "lana"
        if tiempo and tiempo["temp"] >= 28 and tiempo["codigo"] <= 1:
            return "gafas"
        return "ninguno"

    def dibujar(self):
        self.comandos = []
        self.componer()
        self.volcar()

    def componer(self):
        self.fila_arriba, self.fila_abajo = FILAS, 0
        e, f = self.estado, self.fase
        ojos = self.fila_ojos()
        alterno = (self.t // 6) % 2 == 1
        cuerpo_colgado = [d.ARRIBA, ojos, d.CUERPO, d.CUERPO, d.CUERPO]
        col0, de_pie = 3, False

        # 1) elige la postura: (filas, columna, fila de arriba, cuántas filas hay encima de la cabeza)
        if e == "escribir":
            self.dibujar_laptop(ojos)
            self.dibujar_extras(3, 8)
            return
        if e in ("colgado_raton", "arrastrado", "perseguir"):
            if e == "perseguir":
                patas = d.PATAS_SALTO
            else:  # las patitas se quedan atrás: si va hacia la derecha, apuntan a la izquierda
                lado = 0 if abs(self.vel_balanceo) < 1 else (-1 if self.vel_balanceo > 0 else 1)
                patas = d.PATAS_COLGANDO[lado]
            filas, fila0, cabeza = d.MANOS_RATON + cuerpo_colgado + patas, 0, 3
        elif e == "colgado_arriba" or (e == "trepar" and f == "subir"):
            manos = d.MANOS_ARRIBA[1 if self.moviendo and alterno else 0]
            patas = d.PATAS_PASO if self.moviendo and alterno else d.PATAS_COLGANDO[0]
            filas, fila0, cabeza = manos + cuerpo_colgado + patas, 0, 3
        elif e == "dormir":
            filas = [d.ARRIBA, ojos, d.CUERPO, d.CUERPO, d.CUERPO, d.SENTADO]
            fila0, cabeza = FILAS - len(filas), 0
        elif (e == "despertar" and (self.t // 10) % 2) or (e == "bailar" and (self.t // 8) % 2):
            # se estira (o baila) con los brazos arriba
            filas = d.MANOS_ARRIBA[0] + cuerpo_colgado + (d.PATAS_PASO if e == "bailar" else d.PATAS_QUIETO)
            fila0, cabeza = FILAS - len(filas), 3
            if e == "bailar":
                col0 = 3 + round(math.sin(self.t / 6))
        else:
            if e in ("caer", "saltar_a"):
                patas = d.PATAS_SALTO
            elif e in ("caminar", "traer", "trepar", "cazar", "ir_comer", "pillar", "huir", "irse", "bailar") \
                    or (e == "en_ventana" and self.moviendo):
                patas = d.PATAS_PASO if alterno else d.PATAS_QUIETO
            else:
                patas = d.PATAS_QUIETO
            filas = [d.ARRIBA, ojos, d.BRAZOS, d.CUERPO, d.CUERPO]
            if e == "comer" and (self.t // 6) % 2:
                filas = filas[:4]  # se agacha para morder
            elif e == "quieto" and (self.t // 25) % 2:
                filas.append(d.CUERPO)  # respira: se estira un píxel
            filas += patas
            fila0, cabeza = FILAS - len(filas), 0
            if e == "bailar":
                col0 = 3 + round(math.sin(self.t / 6))
            de_pie = True

        # 2) píntalo todo en orden: capa detrás, sombrero, cuerpo, gafas y particulitas delante
        disfraz = self.disfraz_actual()
        if disfraz == "capa" and de_pie:
            self.dibujar_capa(col0, fila0)
        self.fila_cabeza = fila0 + cabeza
        self.dibujar_sombrero(col0, self.fila_cabeza, disfraz, de_pie)
        self.pintar(filas, col0, fila0)
        self.dibujar_extras(col0, self.fila_cabeza, sombrero=False)

    def dibujar_sombrero(self, col0, fila_cabeza, disfraz, de_pie):
        tiempo = self.mundo.tiempo
        if tiempo and tiempo["lluvia"] and de_pie and self.estado in DE_PIE:
            self.pintar(d.PARAGUAS, col0, fila_cabeza - len(d.PARAGUAS))
        elif disfraz in d.SOMBREROS:
            sombrero = d.SOMBREROS[disfraz]
            self.pintar(sombrero, col0, fila_cabeza - len(sombrero))

    def dibujar_extras(self, col0, fila_cabeza, sombrero=True):
        disfraz = self.disfraz_actual()
        if sombrero:
            self.dibujar_sombrero(col0, fila_cabeza, disfraz, False)
        if disfraz == "gafas" and self.estado != "dormir":
            self.pintar([d.GAFAS], col0 + max(-1, min(1, self.mirar)), fila_cabeza + 1)
        if self.estado == "mareado":  # estrellitas dando vueltas alrededor de la cabeza
            P = self.P
            for k in range(3):
                a = self.t / 5 + k * 2.09
                self.dibujar_particula("estrella", self.W / 2 + math.cos(a) * 5 * P - P,
                                       (fila_cabeza - 1) * P + math.sin(a) * P)
        for p in self.particulas:
            self.dibujar_particula(p["tipo"], p["x"], p["y"])

    def dibujar_capa(self, col0, fila0):
        """La capa asoma por los lados y ondea hacia atrás al caminar."""
        for fila in range(fila0 + 3, fila0 + 7):
            for col in (col0 + 1, col0 + 12):
                self.pintar_letra("R", col, fila)
        if self.moviendo:
            detras = col0 + (0 if self.dir > 0 else 13)
            for fila in range(fila0 + 4 + (self.t // 4) % 2, fila0 + 7):
                self.pintar_letra("R", detras, fila)

    def dibujar_laptop(self, ojos):
        p = self.laptop
        abierta = p >= 1
        tecleando = abierta and time.time() - self.mundo.ultima_tecla < 0.4
        self.fila_cabeza = 8
        self.pintar([d.ARRIBA, ojos, d.CUERPO if abierta else d.BRAZOS, d.CUERPO, d.CUERPO], 3, 8)
        if p > 0.05:
            self.pintar(["KKKKKKKKKKKK"], 4, 15)  # la base del teclado
        alto = round(4 * p)  # la tapa se va abriendo
        if alto:
            tapa = ["LLLLLLLL"] * alto
            if alto >= 3:
                tapa[1] = "LLLOOLLL"  # el logo
            self.pintar(tapa, 6, 15 - alto)
        if abierta:  # bracitos sobre el teclado; con cada tecla baja una mano
            izq_abajo = tecleando and (self.t // 3) % 2 == 0
            der_abajo = tecleando and not izq_abajo
            for c, f in [(4, 10), (4, 11), (5, 12), (6, 14 if izq_abajo else 13),
                         (15, 10), (15, 11), (14, 12), (13, 14 if der_abajo else 13)]:
                self.pintar_letra("X", c, f)
