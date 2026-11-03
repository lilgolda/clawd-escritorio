"""El hilo de telaraña del que cuelga Clawd."""

import math

LARGO_HILO = 160          # largo del hilo cuando se cuelga del ratón
LARGO_HILO_ARRASTRE = 45  # largo del hilo cuando lo arrastras tú
TROZOS_HILO = 10          # en cuántos trocitos se divide el hilo (más = más flexible)
GRAVEDAD_HILO = 0.35      # cuánto tira Clawd del hilo hacia abajo
AMORTIGUACION = 0.995     # 1 = se balancea para siempre; menos = se frena antes
COLOR_HILO = "#F5F5F5"


class Hilo:
    """Un hilo de telaraña hecho de puntitos unidos entre sí (física "Verlet").

    Cada puntito recuerda dónde estaba antes; la diferencia es su velocidad.
    El primero va pegado al ratón y del último cuelga Clawd, que pesa más.
    Como los puntitos de en medio tardan en enterarse de que moviste el ratón,
    un tirón brusco recorre el hilo como una onda: el latigazo.
    """

    def __init__(self, desde, hasta, largo, vel=(0, 0)):
        n = TROZOS_HILO
        self.tramo = largo / n
        self.puntos = [[desde[0] + (hasta[0] - desde[0]) * i / n,
                        desde[1] + (hasta[1] - desde[1]) * i / n] for i in range(n + 1)]
        # "antes" un poco por detrás = el hilo nace ya moviéndose a la velocidad de Clawd
        self.antes = [[x - vel[0] * i / n / 2, y - vel[1] * i / n / 2] for i, (x, y) in enumerate(self.puntos)]
        self.ligereza = [0] + [1] * (n - 1) + [0.25]  # 0 = no se mueve; Clawd pesa 4 veces un trocito

    def paso(self, ancla, izq, der, suelo):
        self.puntos[0] = list(ancla)
        self.antes[0] = list(ancla)
        for _ in range(2):  # dos pasitos por fotograma: más suave y estable
            for p, a in zip(self.puntos[1:], self.antes[1:]):
                vx, vy = (p[0] - a[0]) * AMORTIGUACION, (p[1] - a[1]) * AMORTIGUACION
                a[0], a[1] = p[0], p[1]
                p[0] += vx
                p[1] += vy + GRAVEDAD_HILO
            for _ in range(8):  # corrige varias veces para que cada trozo mantenga su largo
                for i in range(len(self.puntos) - 1):
                    p, q = self.puntos[i], self.puntos[i + 1]
                    dx, dy = q[0] - p[0], q[1] - p[1]
                    d = math.hypot(dx, dy) or 0.001
                    w1, w2 = self.ligereza[i], self.ligereza[i + 1]
                    k = (d - self.tramo) / d / (w1 + w2)
                    p[0] += dx * k * w1
                    p[1] += dy * k * w1
                    q[0] -= dx * k * w2
                    q[1] -= dy * k * w2
                punta = self.puntos[-1]  # que Clawd no se salga de la pantalla
                punta[0] = max(izq, min(der, punta[0]))
                punta[1] = min(suelo, punta[1])

    def punta(self):
        return self.puntos[-1]

    def velocidad(self):
        """Velocidad de Clawd por fotograma (por eso el * 2: hay dos pasitos por fotograma)."""
        p, a = self.puntos[-1], self.antes[-1]
        return (p[0] - a[0]) * 2, (p[1] - a[1]) * 2
