"""
Todo lo que habla directamente con Windows (con ctypes).

Aquí está lo "difícil": saber dónde están las ventanas, si suena música,
si hay algo a pantalla completa, el icono junto al reloj y el arranque automático.
Si estás aprendiendo, no hace falta entender este archivo para jugar con los demás.
"""

import ctypes
import os
import sys
import winreg
from ctypes import wintypes

user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32
dwmapi = ctypes.windll.dwmapi
ole32 = ctypes.windll.ole32
kernel32 = ctypes.windll.kernel32

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # para que las medidas cuadren con pantallas escaladas
except Exception:
    pass
try:
    # Por defecto el reloj de Windows solo "despierta" cada 15,6 ms, así que una espera de 33 ms
    # acaba durando 47 ms y la animación va a saltos. Con esto despierta cada 1 ms.
    ctypes.windll.winmm.timeBeginPeriod(1)
except Exception:
    pass

# Le decimos a Python qué tipos usa cada función de Windows (importante en 64 bits)
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetParent.argtypes = [wintypes.HWND]
user32.GetParent.restype = wintypes.HWND
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsIconic.argtypes = [wintypes.HWND]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
user32.MonitorFromWindow.restype = wintypes.HMONITOR
user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.c_void_p]
dwmapi.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]


# ---------- Pantalla y teclado ----------

def area_de_trabajo():
    """Devuelve (izquierda, arriba, derecha, abajo) de la pantalla sin la barra de tareas."""
    r = wintypes.RECT()
    user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(r), 0)  # SPI_GETWORKAREA
    return r.left, r.top, r.right, r.bottom


# Letras, números, espacio, enter, borrar y signos de puntuación
TECLAS = [0x08, 0x0D, 0x20] + list(range(0x30, 0x5B)) + list(range(0xBA, 0xC1)) + list(range(0xDB, 0xDF))


def se_pulso_alguna_tecla():
    """Solo mira SI se pulsó alguna tecla. No guarda cuál ni lo que escribes."""
    pulsada = False
    for vk in TECLAS:
        if user32.GetAsyncKeyState(vk) & 0x8001:
            pulsada = True
    return pulsada


def boton_izquierdo_pulsado():
    return bool(user32.GetAsyncKeyState(0x01) & 0x8000)


def hacer_atravesable(win):
    """Hace que los clics atraviesen la ventana entera, como si no existiera."""
    win.update_idletasks()
    hwnd = user32.GetParent(win.winfo_id())
    estilo = user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
    user32.SetWindowLongW(hwnd, -20, estilo | 0x80000 | 0x20 | 0x80)  # LAYERED | TRANSPARENT | TOOLWINDOW


# ---------- Las ventanas de los demás programas ----------

def clase_de(hwnd):
    buf = ctypes.create_unicode_buffer(64)
    user32.GetClassNameW(hwnd, buf, 64)
    return buf.value


def rect_ventana(hwnd):
    """Rectángulo (izq, arriba, der, abajo) de una ventana, o None si ya no se ve."""
    if not (user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd)) or user32.IsIconic(hwnd):
        return None
    r = wintypes.RECT()
    # DWMWA_EXTENDED_FRAME_BOUNDS: el borde que se ve de verdad (sin la sombra invisible)
    if dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(r), ctypes.sizeof(r)) != 0:
        user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom


def _es_de_este_programa(hwnd):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value == os.getpid()


def _esta_oculta(hwnd):
    valor = ctypes.c_int(0)
    dwmapi.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(valor), 4)  # DWMWA_CLOAKED
    return valor.value != 0


WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]


def ventanas_visibles():
    """Lista de (hwnd, rect) de las ventanas normales que se ven, de la de delante a la de atrás."""
    lista = []

    def cada_una(hwnd, _):
        if (user32.GetWindowTextLengthW(hwnd) > 0 and not _es_de_este_programa(hwnd)
                and not _esta_oculta(hwnd) and not (user32.GetWindowLongW(hwnd, -20) & 0x80)
                and clase_de(hwnd) not in ("Progman", "WorkerW", "Shell_TrayWnd")):
            r = rect_ventana(hwnd)
            if r and r[2] - r[0] >= 250 and r[3] - r[1] >= 120:
                lista.append((hwnd, r))
        return True

    user32.EnumWindows(WNDENUMPROC(cada_una), 0)
    return lista


def ventana_de_delante():
    return user32.GetForegroundWindow()


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]


def hay_pantalla_completa():
    """True si estás jugando, viendo un vídeo o presentando a pantalla completa."""
    estado = ctypes.c_int(0)
    try:
        # 2 = app a pantalla completa, 3 = juego, 4 = modo presentación
        if shell32.SHQueryUserNotificationState(ctypes.byref(estado)) == 0 and estado.value in (2, 3, 4):
            return True
    except Exception:
        pass
    hwnd = user32.GetForegroundWindow()
    if not hwnd or clase_de(hwnd) in ("Progman", "WorkerW") or _es_de_este_programa(hwnd):
        return False
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(MONITORINFO)
    user32.GetMonitorInfoW(user32.MonitorFromWindow(hwnd, 2), ctypes.byref(info))
    m = info.rcMonitor
    return r.left <= m.left and r.top <= m.top and r.right >= m.right and r.bottom >= m.bottom


# ---------- ¿Suena algo? (el medidor de volumen de Windows) ----------

class GUID(ctypes.Structure):
    _fields_ = [("d1", ctypes.c_ulong), ("d2", ctypes.c_ushort), ("d3", ctypes.c_ushort), ("d4", ctypes.c_ubyte * 8)]


def _guid(texto):
    g = GUID()
    ole32.CLSIDFromString(ctypes.c_wchar_p(texto), ctypes.byref(g))
    return g


def _metodo(objeto, indice, *argumentos):
    """Saca la función número `indice` de un objeto COM (así se usan las piezas de Windows por dentro)."""
    tabla = ctypes.cast(objeto, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
    return ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *argumentos)(tabla[indice])


class MedidorAudio:
    """Lee el nivel de sonido que sale por los altavoces (0 = silencio, 1 = a tope)."""

    def __init__(self):
        self.medidor = None
        try:
            ole32.CoInitialize(None)
            self._conectar()
        except Exception:
            self.medidor = None

    def _conectar(self):
        enumerador = ctypes.c_void_p()
        if ole32.CoCreateInstance(ctypes.byref(_guid("{BCDE0395-E52F-467C-8E3D-C4579291692E}")), None, 1,
                                  ctypes.byref(_guid("{A95664D2-9614-4F35-A746-DE8DB63617E6}")),
                                  ctypes.byref(enumerador)) != 0:
            return
        dispositivo = ctypes.c_void_p()
        _metodo(enumerador, 4, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p))(
            enumerador, 0, 1, ctypes.byref(dispositivo))  # altavoces por defecto
        _metodo(enumerador, 2)(enumerador)  # Release
        if not dispositivo:
            return
        medidor = ctypes.c_void_p()
        _metodo(dispositivo, 3, ctypes.POINTER(GUID), ctypes.c_ulong, ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_void_p))(
            dispositivo, ctypes.byref(_guid("{C02216F6-8C67-4B5B-9D00-D008E73E0064}")), 23, None,
            ctypes.byref(medidor))
        _metodo(dispositivo, 2)(dispositivo)
        self.medidor = medidor if medidor else None

    def reconectar(self):
        """Por si cambiaste de altavoces a auriculares."""
        try:
            if self.medidor:
                _metodo(self.medidor, 2)(self.medidor)
            self.medidor = None
            self._conectar()
        except Exception:
            self.medidor = None

    def pico(self):
        if not self.medidor:
            return 0.0
        valor = ctypes.c_float()
        try:
            if _metodo(self.medidor, 3, ctypes.POINTER(ctypes.c_float))(self.medidor, ctypes.byref(valor)) != 0:
                return 0.0
        except Exception:
            return 0.0
        return valor.value


# ---------- Icono junto al reloj ----------

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int), ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND), ("uID", wintypes.UINT),
                ("uFlags", wintypes.UINT), ("uCallbackMessage", wintypes.UINT), ("hIcon", wintypes.HICON),
                ("szTip", wintypes.WCHAR * 128), ("dwState", wintypes.DWORD), ("dwStateMask", wintypes.DWORD),
                ("szInfo", wintypes.WCHAR * 256), ("uVersion", wintypes.UINT),
                ("szInfoTitle", wintypes.WCHAR * 64), ("dwInfoFlags", wintypes.DWORD),
                ("guidItem", GUID), ("hBalloonIcon", wintypes.HICON)]


user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = ctypes.c_ssize_t
user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HWND,
                                   wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
user32.CreateWindowExW.restype = wintypes.HWND
user32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT, ctypes.c_int, ctypes.c_int,
                              wintypes.UINT]
user32.LoadImageW.restype = wintypes.HANDLE
user32.LoadIconW.argtypes = [wintypes.HINSTANCE, ctypes.c_void_p]
user32.LoadIconW.restype = wintypes.HICON
shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE


class IconoBandeja:
    """El iconito de Clawd junto al reloj de Windows."""

    def __init__(self, texto, ruta_icono, al_clic, al_clic_derecho):
        self.al_clic, self.al_clic_derecho = al_clic, al_clic_derecho
        self._proc = WNDPROC(self._mensaje)  # hay que guardarlo o Python lo borra
        instancia = kernel32.GetModuleHandleW(None)
        clase = WNDCLASSW()
        clase.lpfnWndProc = self._proc
        clase.hInstance = instancia
        clase.lpszClassName = "ClawdBandeja"
        user32.RegisterClassW(ctypes.byref(clase))
        self.hwnd = user32.CreateWindowExW(0, "ClawdBandeja", "Clawd", 0, 0, 0, 0, 0, None, None, instancia, None)
        icono = user32.LoadImageW(None, ruta_icono, 1, 0, 0, 0x10 | 0x40) if ruta_icono else None
        if not icono:
            icono = user32.LoadIconW(None, ctypes.c_void_p(32512))  # icono normal de Windows
        d = self.datos = NOTIFYICONDATAW()
        d.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        d.hWnd = self.hwnd
        d.uID = 1
        d.uFlags = 1 | 2 | 4  # mensajes, icono y texto al pasar el ratón
        d.uCallbackMessage = 0x8001
        d.hIcon = icono
        d.szTip = texto
        self.activo = bool(shell32.Shell_NotifyIconW(0, ctypes.byref(d)))

    def _mensaje(self, hwnd, msg, wparam, lparam):
        if msg == 0x8001:
            evento = lparam & 0xFFFF
            if evento == 0x0202:    # clic izquierdo
                self.al_clic()
            elif evento == 0x0205:  # clic derecho
                self.al_clic_derecho()
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def quitar(self):
        if self.activo:
            shell32.Shell_NotifyIconW(2, ctypes.byref(self.datos))
            self.activo = False


# ---------- Arrancar con Windows ----------

CLAVE_ARRANQUE = r"Software\Microsoft\Windows\CurrentVersion\Run"
NOMBRE_ARRANQUE = "ClawdEscritorio"


def arranque_activado():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CLAVE_ARRANQUE) as clave:
            winreg.QueryValueEx(clave, NOMBRE_ARRANQUE)
            return True
    except OSError:
        return False


def poner_arranque(activar, ruta_script):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CLAVE_ARRANQUE, 0, winreg.KEY_SET_VALUE) as clave:
        if activar:
            if getattr(sys, "frozen", False):  # es Clawd.exe: se arranca él mismo
                orden = f'"{sys.executable}"'
            else:  # es el código en Python: hace falta pythonw + el script
                pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
                orden = f'"{pythonw}" "{ruta_script}"'
            winreg.SetValueEx(clave, NOMBRE_ARRANQUE, 0, winreg.REG_SZ, orden)
        else:
            try:
                winreg.DeleteValue(clave, NOMBRE_ARRANQUE)
            except OSError:
                pass
