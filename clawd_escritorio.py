"""
Clawd de escritorio
-------------------
Una mascota en píxeles que vive en tu escritorio de Windows.

Para arrancarlo:   py clawd_escritorio.py
Sin ventana negra: pyw clawd_escritorio.py

Cómo está organizado el código:
  clawd_escritorio.py  el "mundo": arranca todo, el menú, la música, los avisos y la capa del hilo
  clawd.py             Clawd: sus estados (caminar, dormir, colgarse...) y cómo se dibuja
  dibujos.py           los dibujos en píxeles: Clawd, sombreros, galleta, corazones...
  cosas.py             lo que te trae (mensajes, postales, fotos, carteles), el globo y las galletas
  fisica.py            el hilo de telaraña
  ajustes.py           la ventana de ajustes y la de recordatorios (se guarda en clawd_datos.json)
  tiempo.py            mira qué tiempo hace en tu ciudad
  windows.py           lo que habla directamente con Windows

Cómo se usa:
  Clic: salta.   Arrastrar: te lo llevas colgando (y si lo sueltas en marcha, sale volando).
  Pasar el ratón por encima: mimos.   Clic derecho: menú con todo lo demás.
  Icono junto al reloj: clic para esconderlo o mostrarlo, clic derecho para el menú.
"""

import os
import random
import tempfile
import threading
import time
import tkinter as tk

import ajustes
import dibujos as d
import tiempo
import windows
from clawd import Clawd
from cosas import PAUSAS, Galleta
from fisica import COLOR_HILO

FPS = 30  # fotogramas por segundo


class Mundo:
    def __init__(self):
        self.raiz = tk.Tk()
        self.raiz.withdraw()  # la ventana principal de Tkinter no se ve; cada Clawd tiene la suya
        self.aj = ajustes.cargar()
        self.izq, self.arr, self.der, self.suelo = windows.area_de_trabajo()

        # Capa invisible del tamaño de la pantalla donde se dibujan los hilos y las galletas
        self.capa = tk.Toplevel(self.raiz)
        self.capa.overrideredirect(True)
        self.capa.wm_attributes("-topmost", True)
        self.capa.wm_attributes("-transparentcolor", d.TRANSPARENTE)
        ancho, alto = self.der - self.izq, self.suelo - self.arr - 1  # -1: que Windows no crea que es pantalla completa
        self.capa.geometry(f"{ancho}x{alto}+{self.izq}+{self.arr}")
        self.lienzo_capa = tk.Canvas(self.capa, width=ancho, height=alto, bg=d.TRANSPARENTE, highlightthickness=0)
        self.lienzo_capa.pack()
        windows.hacer_atravesable(self.capa)

        self.galletas = []
        self.cola_carteles = []  # avisos que Clawd tiene que traerte
        self.tiempo = None
        self.proximo_tiempo = 0.0
        self.tiempo_nuevo = None
        self.al_terminar_tiempo = None

        self.medidor = windows.MedidorAudio()
        self.ultimo_sonido = 0.0
        self.musica_desde = None
        self.hay_musica = False
        self.fotograma = 0

        self.ultima_tecla = 0.0
        self.ultima_actividad = time.time()
        self.tiempo_activo = 0
        self.raton = self.raton_antes = self.raiz.winfo_pointerxy()  # se lee una vez por fotograma
        self.capa_con_algo = False
        self.oculto = self.oculto_pantalla = self.pausado = False
        self.proxima_revision = 0.0

        self.clawds = [Clawd(self, principal=True)]
        self.aplicar_ajustes(guardar=False)  # si Bit estaba invitado, viene

        self.icono = None
        try:
            ruta = os.path.join(tempfile.gettempdir(), "clawd_bandeja.ico")
            try:
                d.crear_icono(ruta, self.aj["color"])
            except Exception:
                ruta = None
            self.icono = windows.IconoBandeja("Clawd", ruta, lambda: self.raiz.after(0, self.alternar_escondido),
                                              lambda: self.raiz.after(0, self.menu_bandeja))
        except Exception:
            self.icono = None
        self.clawds[0].decir("¡Hola! Clic derecho para ver todo lo que sé hacer", 5)

    def empezar(self):
        self.siguiente = time.perf_counter()
        self.paso()
        self.raiz.mainloop()

    # ----- el bucle principal -----

    def paso(self):
        try:
            self.raton = self.raiz.winfo_pointerxy()
            ahora = time.time()
            self.fotograma += 1
            if ahora >= self.proxima_revision:
                self.revisar_cada_segundo(ahora)
            if self.tiempo_nuevo is not None:  # llegó el tiempo desde internet
                resultado, self.tiempo_nuevo = self.tiempo_nuevo[0], None
                if resultado:
                    self.tiempo = resultado
                if self.al_terminar_tiempo:
                    self.al_terminar_tiempo(resultado)
                    self.al_terminar_tiempo = None
            if not (self.oculto or self.oculto_pantalla or self.pausado):
                if windows.se_pulso_alguna_tecla():
                    self.ultima_tecla = self.ultima_actividad = ahora
                if self.raton != self.raton_antes:
                    self.raton_antes = self.raton
                    self.ultima_actividad = ahora
                if self.fotograma % 3 == 0:
                    self.escuchar_musica(ahora)
                for g in self.galletas:
                    g.caer(self.suelo)
                for c in list(self.clawds):
                    c.paso(ahora)
                self.dibujar_capa()
        finally:
            # Apunta a 30 fotogramas por segundo exactos: si este fotograma tardó, el siguiente espera menos
            self.siguiente += 1 / FPS
            espera = self.siguiente - time.perf_counter()
            if espera < -0.1:  # se quedó muy atrás (p. ej. arrastrando un menú): vuelve a empezar la cuenta
                self.siguiente, espera = time.perf_counter(), 0
            self.raiz.after(max(1, int(espera * 1000)), self.paso)

    def revisar_cada_segundo(self, ahora):
        self.proxima_revision = ahora + 1
        tapado = self.aj["esconder_pantalla_completa"] and windows.hay_pantalla_completa()
        if tapado != self.oculto_pantalla:
            self.oculto_pantalla = tapado
            self.actualizar_visibilidad()
        if self.oculto or self.oculto_pantalla:
            return
        self.revisar_recordatorios(ahora)
        self.revisar_pausas(ahora)
        if self.aj["ciudad"] and ahora >= self.proximo_tiempo:
            self.pedir_tiempo()
        if self.fotograma % 3600 < 30:  # cada ~2 minutos, por si cambiaste de altavoces
            self.medidor.reconectar()

    def escuchar_musica(self, ahora):
        """Si lleva sonando algo más de 2 segundos seguidos, es música: ¡a bailar!"""
        if self.medidor.pico() > 0.015:
            self.ultimo_sonido = ahora
            if self.musica_desde is None:
                self.musica_desde = ahora
        elif ahora - self.ultimo_sonido > 2.5:
            self.musica_desde = None
        self.hay_musica = self.musica_desde is not None and ahora - self.musica_desde > 2

    def dibujar_capa(self):
        hay_algo = bool(self.galletas) or any(c.hilo for c in self.clawds)
        if not hay_algo and not self.capa_con_algo:
            return  # la capa ya está vacía: no gastes en borrarla otra vez
        self.capa_con_algo = hay_algo
        L = self.lienzo_capa
        L.delete("all")
        for c in self.clawds:
            if c.hilo:
                puntos = []
                for x, y in c.hilo.puntos:
                    puntos += [x - self.izq, y - self.arr]
                # un borde oscuro y el hilo claro encima, para que se vea en fondos claros y oscuros
                L.create_line(*puntos, fill=d.OJO, width=4, smooth=True)
                L.create_line(*puntos, fill=COLOR_HILO, width=2, smooth=True)
        for g in self.galletas:
            g.dibujar(L, self.izq, self.arr)

    # ----- tiempo, avisos y pausas -----

    def pedir_tiempo(self, al_terminar=None):
        self.proximo_tiempo = time.time() + 1800  # cada media hora
        self.al_terminar_tiempo = al_terminar
        ciudad = self.aj["ciudad"]

        def trabajo():  # en segundo plano; el resultado lo recoge paso()
            self.tiempo_nuevo = (tiempo.consultar(ciudad),)

        threading.Thread(target=trabajo, daemon=True).start()

    def decir_tiempo(self, c):
        if not self.aj["ciudad"]:
            c.decir("Dime tu ciudad en Ajustes y te lo cuento", 3)
        elif not self.tiempo:
            c.decir("Déjame mirar por la ventana...", 2)
            self.pedir_tiempo(al_terminar=lambda t: self.decir_tiempo(c) if t else c.decir("No pude mirarlo", 2))
        else:
            t = self.tiempo
            extra = " ¡Saco el paraguas!" if t["lluvia"] else ""
            c.decir(f"En {t['ciudad']}: {t['temp']:.0f}° y {t['descripcion']}.{extra}", 4)

    def agregar_recordatorio(self, texto, cuando):
        self.aj["recordatorios"].append({"texto": texto, "cuando": cuando})
        ajustes.guardar(self.aj)
        self.clawds[0].decir(f"¡Vale! Te lo recuerdo a las {time.strftime('%H:%M', time.localtime(cuando))}", 3)

    def revisar_recordatorios(self, ahora):
        vencidos = [r for r in self.aj["recordatorios"] if r["cuando"] <= ahora]
        if vencidos:
            for r in vencidos:
                self.cola_carteles.append(("¡No lo olvides!", r["texto"], "Clawd · " + time.strftime("%H:%M"), None))
            self.aj["recordatorios"] = [r for r in self.aj["recordatorios"] if r["cuando"] > ahora]
            ajustes.guardar(self.aj)

    def revisar_pausas(self, ahora):
        """Cuenta el tiempo que llevas usando el ordenador; si te alejas, no cuenta."""
        if not self.aj["pausas"]:
            return
        if ahora - self.ultima_actividad < 60:
            self.tiempo_activo += 1
        if self.tiempo_activo >= self.aj["minutos_pausa"] * 60:
            self.tiempo_activo = 0
            self.cola_carteles.append(("Hora de una pausa", random.choice(PAUSAS), "Clawd te cuida", 300))

    # ----- galletas y amigos -----

    def dar_galleta(self):
        self.galletas.append(Galleta(random.uniform(self.izq + 150, self.der - 150), self.arr + 40))

    def galleta_libre(self):
        return next((g for g in self.galletas if g.duena is None), None)

    def amigo_de(self, c):
        return next((o for o in self.clawds if o is not c and o.estado != "irse"), None)

    def jugar(self, c):
        otro = self.amigo_de(c)
        if otro:
            c.jugar_con(otro)
        else:
            c.decir("No tengo con quién jugar... ¡invita a Bit!", 3)

    def invitar_amigo(self):
        bit = Clawd(self, principal=False)
        self.clawds.append(bit)
        bit.decir("¡Hola! Soy Bit", 3)
        self.clawds[0].decir("¡Vino Bit!", 2)

    def quitar(self, c):
        if c in self.clawds and not c.principal:
            self.clawds.remove(c)
            c.cerrar()

    def alternar_amigo(self):
        self.aj["amigo"] = not self.aj["amigo"]
        self.aplicar_ajustes()

    # ----- ajustes, menú, esconder y salir -----

    def aplicar_ajustes(self, guardar=True):
        for c in self.clawds:
            c.aplicar_ajustes()
        bit = next((c for c in self.clawds if not c.principal and c.estado != "irse"), None)
        if self.aj["amigo"] and not bit:
            self.invitar_amigo()
        elif not self.aj["amigo"] and bit:
            bit.irse()
        if guardar:
            ajustes.guardar(self.aj)

    def poner_ajuste(self, clave, valor):
        self.aj[clave] = valor
        self.aplicar_ajustes()

    def abrir_ajustes(self):
        ajustes.VentanaAjustes(self)

    def abrir_recordatorios(self):
        ajustes.VentanaRecordatorios(self)

    def actualizar_visibilidad(self):
        visible = not (self.oculto or self.oculto_pantalla)
        self.capa.deiconify() if visible else self.capa.withdraw()
        for c in self.clawds:
            c.mostrar(visible)

    def alternar_escondido(self):
        if not self.oculto and not (self.icono and self.icono.activo):
            self.clawds[0].decir("Sin icono junto al reloj no podría volver. ¡Me quedo!", 3)
            return
        self.oculto = not self.oculto
        self.actualizar_visibilidad()

    def menu_bandeja(self):
        x, y = self.raiz.winfo_pointerxy()
        c = self.clawds[0]
        c.var_disfraz.set(self.aj["disfraz"])
        c.menu.tk_popup(x, y)

    def crear_menu(self, c):
        menu = tk.Menu(self.raiz, tearoff=0)

        def hacer(accion):  # cualquier cosa del menú cuenta como hacerle caso
            return lambda: (c.interaccion(), accion())

        menu.add_command(label="Saltar", command=hacer(c.saltar))
        if c.principal:
            traer = tk.Menu(menu, tearoff=0)
            for etiqueta, tipo in (("Una foto", "foto"), ("Una postal", "postal"), ("Un mensaje", "mensaje")):
                traer.add_command(label=etiqueta, command=hacer(lambda t=tipo: c.empezar_viaje(t)))
            menu.add_cascade(label="Tráeme...", menu=traer)

        travesuras = tk.Menu(menu, tearoff=0)
        travesuras.add_command(label="Cuélgate arriba", command=hacer(c.ir_a_trepar))
        travesuras.add_command(label="Cuélgate del ratón", command=hacer(lambda: c.cambiar("perseguir", 6)))
        travesuras.add_command(label="Súbete a una ventana",
                               command=hacer(lambda: c.ir_a_ventana() is False and c.decir("No veo ninguna ventana", 2)))
        travesuras.add_command(label="Caza el ratón", command=hacer(c.cazar))
        travesuras.add_command(label="Baila", command=hacer(lambda: c.cambiar("bailar", 6)))
        travesuras.add_command(label="Saca la laptop", command=hacer(c.sacar_laptop))
        travesuras.add_command(label="Juega con tu amigo", command=hacer(lambda: self.jugar(c)))
        travesuras.add_command(label="Duérmete", command=c.dormir)
        menu.add_cascade(label="Travesuras", menu=travesuras)
        menu.add_command(label="Dale una galleta", command=hacer(self.dar_galleta))

        clave = "disfraz" if c.principal else "disfraz_amigo"
        c.var_disfraz = tk.StringVar(value=self.aj[clave])
        disfraces = tk.Menu(menu, tearoff=0)
        for valor, nombre in d.DISFRACES.items():
            disfraces.add_radiobutton(label=nombre, value=valor, variable=c.var_disfraz,
                                      command=lambda: self.poner_ajuste(clave, c.var_disfraz.get()))
        menu.add_cascade(label="Disfraz", menu=disfraces)
        menu.add_separator()

        if c.principal:
            menu.add_command(label="Recuérdame algo...", command=self.abrir_recordatorios)
            menu.add_command(label="¿Qué tiempo hace?", command=hacer(lambda: self.decir_tiempo(c)))
            menu.add_command(label="Invitar o despedir a Bit", command=self.alternar_amigo)
            menu.add_separator()
            self.var_pausa = tk.BooleanVar(value=False)
            menu.add_checkbutton(label="Pausar", variable=self.var_pausa,
                                 command=lambda: setattr(self, "pausado", self.var_pausa.get()))
            menu.add_command(label="Esconder (vuelve con el icono junto al reloj)", command=self.alternar_escondido)
            menu.add_command(label="Ajustes...", command=self.abrir_ajustes)
            menu.add_command(label="Cerrar lo que trajo", command=c.cerrar_objetos)
            menu.add_command(label="Salir", command=self.salir)
        else:
            menu.add_command(label="Despedir a Bit", command=self.alternar_amigo)
        return menu

    def salir(self):
        if self.icono:
            self.icono.quitar()
        ajustes.guardar(self.aj)
        self.raiz.destroy()


if __name__ == "__main__":
    Mundo().empezar()
