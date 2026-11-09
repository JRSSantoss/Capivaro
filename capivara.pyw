"""
Capivara de Estimação 🐹 — versão animada
=========================================
A imagem ganha "ossos": cabeça, orelha, olho, nariz, patinhas e barriga se
movem separados, com física de mola (pula, amassa ao cair, inclina ao frear).

Para usar: dê dois cliques em "Iniciar Capivara.bat" (ele instala tudo sozinho).

  - Clique nela ........ carinho (ela pula de alegria)
  - Segurar e arrastar . pega ela no colo (ela balança igual pêndulo)
  - Clique direito ..... menu (trocar capivara, tamanho, balão, iniciar com o Windows)
  - Clicar em qualquer lugar da tela: ela se assusta e olha pra lá
  - Mouse parado por 15s: ela dorme

Quer outra capivara? Coloque um PNG de fundo transparente (virado para a DIREITA)
na pasta "imagens". Se quiser animação completa, crie um .json com o mesmo nome
(veja capivara_flores.json como exemplo).
"""

import glob
import json
import math
import os
import random
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA_IMAGENS = os.path.join(AQUI, "imagens")


def _garantir_dependencias():
    """Instala PySide6 e numpy sozinho na primeira execução."""
    try:
        import PySide6  # noqa: F401
        import numpy  # noqa: F401
        return
    except ImportError:
        pass

    import subprocess
    import tkinter as tk

    aviso = tk.Tk()
    aviso.title("Capivara")
    aviso.attributes("-topmost", True)
    aviso.resizable(False, False)
    tk.Label(
        aviso, padx=30, pady=22, font=("Segoe UI", 11),
        text="Instalando a capivara pela primeira vez...\n"
             "Isso leva 1 ou 2 minutos, só uma vez.\n\nNão feche esta janela.",
    ).pack()
    aviso.update()

    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    ok = False
    for cmd in (
        [sys.executable, "-m", "pip", "install", "PySide6", "numpy"],
        [sys.executable, "-m", "pip", "install", "--user", "PySide6", "numpy"],
    ):
        r = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, creationflags=flags)
        if r.returncode == 0:
            ok = True
            break
    aviso.destroy()

    if not ok:
        from tkinter import messagebox
        messagebox.showerror(
            "Capivara",
            "Não consegui instalar os componentes automaticamente.\n"
            "Verifique sua internet e abra o arquivo 'Iniciar Capivara.bat'.",
        )
        sys.exit(1)

    import importlib
    importlib.invalidate_caches()


_garantir_dependencias()

import numpy as np  # noqa: E402
from PySide6.QtCore import QPointF, QRect, QRectF, QSettings, Qt, QTimer  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QActionGroup, QColor, QCursor, QFont, QFontMetrics, QImage,
    QPainter, QPainterPath, QPen,
)
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QWidget  # noqa: E402

try:
    import winreg
except ImportError:
    winreg = None

try:
    import ctypes
    USER32 = ctypes.windll.user32
except Exception:
    USER32 = None

# ------------------------------------------------------------------ configurações
W, H = 420, 380            # janela transparente
GY = 366                   # "chão" dentro da janela
ALTURA = 190               # altura base da capivara (px)
DISTANCE = 78              # distância que ela mantém do cursor
SLEEP_AFTER = 15           # segundos de mouse parado até ela dormir
VMAX = 11                  # velocidade máxima (px por quadro a 60 fps)
APP_NAME = "CapivaraPet"

TAMANHOS = [("Pequena", 0.75), ("Média", 1.0), ("Grande", 1.3)]

OUT = QColor("#5b3217")
HEART_FILL = QColor("#ff8fab")
HEART_OUT = QColor("#c9506e")

FALAS_IDLE = [
    "oi!", "kyu~", "tô aqui!", "que dia bom!", "você é demais!",
    "me segue, eu te sigo", "hmm... pensando", "capivara feliz!",
    "bora trabalhar?", "bebe água!",
]
FALAS_SIP = ["slurp~", "tá geladinho!", "bubble tea é vida"]
FALAS_CARINHO = ["hihi!", "que gostoso!", "mais carinho!", "eu te adoro!"]
FALAS_ACORDA = ["ah, voltou!", "bom dia!", "hm? já acordei"]
FALAS_COLO = ["uiii!", "ei, me solta!", "eu voo!"]
FALAS_SUSTO = ["oh!", "hm?", "o que foi?"]

DEFAULT_RIG = {
    "head": {"pivot": [0.5, 0.45], "neck_y": 0.40, "band": 0.14, "x0": 0.10, "gain": 1.0},
    "ears": [], "eyes": [], "nose": None, "feet": [],
    "chest": {"pos": [0.5, 0.65], "r": [0.35, 0.28]},
    "sip": False,
}


# ------------------------------------------------------------------ iniciar com Windows
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _startup_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    exe = sys.executable
    if exe.lower().endswith("python.exe"):
        exe = exe[:-10] + "pythonw.exe"
    return f'"{exe}" "{os.path.abspath(__file__)}"'


def startup_enabled():
    if not winreg:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as k:
            winreg.QueryValueEx(k, APP_NAME)
            return True
    except OSError:
        return False


def set_startup(enable):
    if not winreg:
        return
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as k:
            if enable:
                winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, _startup_command())
            else:
                try:
                    winreg.DeleteValue(k, APP_NAME)
                except OSError:
                    pass
    except OSError:
        pass


# ------------------------------------------------------------------ helpers
def pen(w=2.6, color=OUT):
    p = QPen(color, w)
    p.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return p


def heart_path(x, y, s):
    path = QPainterPath()
    for i in range(41):
        t = i / 40 * 2 * math.pi
        hx = 16 * math.sin(t) ** 3
        hy = -(13 * math.cos(t) - 5 * math.cos(2 * t)
               - 2 * math.cos(3 * t) - math.cos(4 * t))
        pt = QPointF(x + hx * s / 16, y + hy * s / 16)
        if i == 0:
            path.moveTo(pt)
        else:
            path.lineTo(pt)
    path.closeSubpath()
    return path


def nome_bonito(arquivo):
    base = os.path.splitext(os.path.basename(arquivo))[0]
    return base.replace("_", " ").replace("-", " ").capitalize()


def clamp(v, a, b):
    return a if v < a else b if v > b else v


def _smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def carregar_rig(caminho_png):
    rig = json.loads(json.dumps(DEFAULT_RIG))
    jp = os.path.splitext(caminho_png)[0] + ".json"
    if os.path.exists(jp):
        try:
            with open(jp, encoding="utf-8") as f:
                dados = json.load(f)
            for k, v in dados.items():
                if isinstance(v, dict) and isinstance(rig.get(k), dict):
                    rig[k].update(v)
                else:
                    rig[k] = v
        except (OSError, ValueError):
            pass
    return rig


class Mola:
    """Mola amortecida: dá aquele balanço natural (overshoot) aos movimentos."""

    def __init__(self, k=0.18, c=0.16, x=0.0):
        self.k, self.c, self.x, self.v = k, c, x, 0.0

    def step(self, alvo, d):
        a = (alvo - self.x) * self.k - self.v * self.c
        self.v += a * d
        self.x += self.v * d
        return self.x

    def impulso(self, dv):
        self.v += dv


# ------------------------------------------------------------------ o boneco (sprite deformável)
class Boneco:
    """Imagem com deformação por regiões, feita em tempo real com numpy."""

    MARGEM = 14      # folga (px lógicos) ao redor para a cabeça/orelha poderem sair
    PAD = 6          # borda transparente para amostragem

    def __init__(self, caminho, altura, dpr, largura_max, qualidade=1.0):
        self.rig = carregar_rig(caminho)
        img = QImage(caminho).convertToFormat(QImage.Format.Format_RGBA8888_Premultiplied)
        alvo_h = float(altura)
        alvo_w = img.width() * alvo_h / max(1, img.height())
        if alvo_w > largura_max:
            alvo_h *= largura_max / alvo_w
            alvo_w = largura_max
        self.ws = max(0.6, min(dpr, 1.5) * qualidade)       # resolução da deformação
        w = max(8, int(round(alvo_w * self.ws)))
        h = max(8, int(round(alvo_h * self.ws)))
        img = img.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)
        bpl = img.bytesPerLine()
        arr = np.frombuffer(img.constBits(), np.uint8).reshape(h, bpl // 4, 4)[:, :w]
        M = int(round(self.MARGEM * self.ws))
        P = self.PAD
        canvas = np.zeros((h + 2 * M + 2 * P, w + 2 * M + 2 * P, 4), np.float32)
        canvas[P + M:P + M + h, P + M:P + M + w] = arr
        self.flat = canvas.reshape(-1, 4)
        self.wp = w + 2 * M + 2 * P
        self.w, self.h, self.M = w, h, M
        self.cw, self.ch = w + 2 * M, h + 2 * M
        self.X = np.arange(self.cw, dtype=np.float32)[None, :]
        self.Y = np.arange(self.ch, dtype=np.float32)[:, None]
        self.pw, self.ph = w / self.ws, h / self.ws
        self.m = M / self.ws
        self.qimg = None
        self.warp(self.params_neutros())

    @staticmethod
    def params_neutros():
        return {"head_rot": 0.0, "head_bob": 0.0, "breath": 0.0, "ear": 0.0,
                "blink": 0.0, "sniff": 0.0, "lifts": [0.0, 0.0]}

    # coordenadas normalizadas do rig -> pixels do buffer
    def _bx(self, v):
        return self.M + v * self.w

    def _by(self, v):
        return self.M + v * self.h

    def _janela(self, cx, cy, rx, ry, k):
        x0 = max(0, int(cx - rx * k))
        x1 = min(self.cw, int(cx + rx * k) + 1)
        y0 = max(0, int(cy - ry * k))
        y1 = min(self.ch, int(cy + ry * k) + 1)
        return slice(y0, max(y0, y1)), slice(x0, max(x0, x1))

    def warp(self, P):
        ws, X, Y, w, h = self.ws, self.X, self.Y, self.w, self.h
        R = self.rig
        mx = np.zeros((self.ch, self.cw), np.float32)
        my = np.zeros((self.ch, self.cw), np.float32)

        # ---- cabeça (rotação em torno do pescoço + sobe/desce)
        hd = R["head"]
        th = math.radians(P["head_rot"]) * hd["gain"]
        bob = P["head_bob"] * ws * hd["gain"]
        if abs(th) > 1e-4 or abs(bob) > 1e-3:
            py = self._by(hd["neck_y"])
            band = max(2.0, hd["band"] * h)
            r1 = min(self.ch, int(py + band / 2) + 2)
            wy = _smooth((py - Y[:r1]) / band + 0.5)
            wx = _smooth((X - self._bx(hd["x0"])) / (0.12 * w))
            g = wy * wx
            ppx, ppy = self._bx(hd["pivot"][0]), self._by(hd["pivot"][1])
            mx[:r1] += -th * (Y[:r1] - ppy) * g
            my[:r1] += (th * (X - ppx) + bob) * g

        # ---- barriga respirando
        b = P["breath"]
        if abs(b) > 1e-4:
            c = R["chest"]
            cx, cy = self._bx(c["pos"][0]), self._by(c["pos"][1])
            rx, ry = c["r"][0] * w, c["r"][1] * h
            sy_, sx_ = self._janela(cx, cy, rx, ry, 1.7)
            gx = np.exp(-((X[:, sx_] - cx) / rx) ** 2)
            gy = np.exp(-((Y[sy_] - cy) / ry) ** 2)
            g = gy * gx
            mx[sy_, sx_] += (X[:, sx_] - cx) * b * g
            my[sy_, sx_] += (Y[sy_] - cy) * b * g

        # ---- orelhas
        te = math.radians(P["ear"])
        if abs(te) > 1e-3:
            for e in R["ears"]:
                cx, cy = self._bx(e["pos"][0]), self._by(e["pos"][1])
                rx, ry = e["r"][0] * w, e["r"][1] * h
                sy_, sx_ = self._janela(cx, cy, rx, ry, 2.0)
                g = (np.exp(-((Y[sy_] - cy) / ry) ** 2)
                     * np.exp(-((X[:, sx_] - cx) / rx) ** 2))
                ppx, ppy = self._bx(e["pivot"][0]), self._by(e["pivot"][1])
                mx[sy_, sx_] += -te * (Y[sy_] - ppy) * g
                my[sy_, sx_] += te * (X[:, sx_] - ppx) * g

        # ---- olhos (piscar: achata; susto: arregala)
        bl = P["blink"]
        if abs(bl) > 0.02 and R["eyes"]:
            if bl > 0:
                s_ = 1 - 0.88 * bl
                k = 1.0 / max(s_, 0.1)
            else:
                k = 1.0 / (1 - 0.35 * bl)
            for e in R["eyes"]:
                cx, cy = self._bx(e["pos"][0]), self._by(e["pos"][1])
                rx, ry = e["r"][0] * w, e["r"][1] * h
                sy_, sx_ = self._janela(cx, cy, rx * 1.1, ry, 4.0 if bl > 0 else 2.6)
                d_ = Y[sy_] - cy
                gx = np.exp(-(np.abs(X[:, sx_] - cx) / (rx * 2.2)) ** 4)
                if bl > 0:
                    # a pele ao redor é lisa: só amostramos dentro de 1.2*ry do olho
                    L = 1.2 * ry
                    gy = np.exp(-(np.abs(d_) / (ry * 1.3)) ** 6)
                    off = np.clip(d_ * (1 + (k - 1) * gy), -L, L)
                    fade = 1 - _smooth((np.abs(d_) - L) / (0.5 * L))
                    fin = d_ + (off - d_) * fade
                    my[sy_, sx_] += (d_ - fin) * gx
                else:
                    gy = np.exp(-(np.abs(d_) / (ry * 1.7)) ** 4)
                    g = gy * gx
                    my[sy_, sx_] += -d_ * (k - 1) * g
                    mx[sy_, sx_] += -(X[:, sx_] - cx) * (k - 1) * g

        # ---- nariz farejando
        a = P["sniff"]
        nz = R.get("nose")
        if nz and abs(a) > 1e-3:
            cx, cy = self._bx(nz["pos"][0]), self._by(nz["pos"][1])
            r = nz["r"] * w
            sy_, sx_ = self._janela(cx, cy, r, r, 2.0)
            g = (np.exp(-((Y[sy_] - cy) / r) ** 2)
                 * np.exp(-((X[:, sx_] - cx) / r) ** 2))
            mx[sy_, sx_] += -(X[:, sx_] - cx) * a * g
            my[sy_, sx_] += -(Y[sy_] - cy) * a * g

        # ---- patinhas levantando
        for f in R["feet"]:
            lift = P["lifts"][min(1, int(f.get("group", 0)))] * ws
            if lift > 0.05:
                cx, cy = self._bx(f["pos"][0]), self._by(f["pos"][1])
                rx, ry = f["r"][0] * w, f["r"][1] * h
                sy_, sx_ = self._janela(cx, cy, rx, ry, 2.2)
                g = (np.exp(-((Y[sy_] - cy) / (ry * 1.5)) ** 2)
                     * np.exp(-((X[:, sx_] - cx) / rx) ** 2))
                my[sy_, sx_] += -lift * g

        # ---- amostragem bilinear (alpha pré-multiplicado)
        PD = self.PAD
        sx = np.clip(X - mx, -PD + 0.01, self.cw + PD - 2.01)
        sy = np.clip(Y - my, -PD + 0.01, self.ch + PD - 2.01)
        x0 = np.floor(sx).astype(np.int32)
        y0 = np.floor(sy).astype(np.int32)
        fx = (sx - x0)[..., None]
        fy = (sy - y0)[..., None]
        idx = (y0 + PD) * self.wp + (x0 + PD)
        fl, wp = self.flat, self.wp
        out = (fl[idx] * ((1 - fx) * (1 - fy)) + fl[idx + 1] * (fx * (1 - fy))
               + fl[idx + wp] * ((1 - fx) * fy) + fl[idx + wp + 1] * (fx * fy))
        out = np.clip(out, 0, 255)
        out[..., :3] = np.minimum(out[..., :3], out[..., 3:4])
        out = (out + 0.5).astype(np.uint8)
        self._buf = out
        self.qimg = QImage(out.data, self.cw, self.ch, self.cw * 4,
                           QImage.Format.Format_RGBA8888_Premultiplied).copy()
        return self.qimg


# ------------------------------------------------------------------ a capivara
class Capivara(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(W, H)

        self.settings = QSettings("CapivaraPet", "Capivara3")
        self.speech_on = self.settings.value("speech", True, type=bool)
        self.escala = float(self.settings.value("escala", 1.0))

        self.arquivos = sorted(glob.glob(os.path.join(PASTA_IMAGENS, "*.png")))
        if not self.arquivos:
            QMessageBox.critical(
                None, "Capivara",
                "Não encontrei imagens na pasta 'imagens'.\n"
                "Mantenha a pasta 'imagens' junto do arquivo capivara.pyw.")
            sys.exit(1)
        salvo = str(self.settings.value("sprite", ""))
        self.sprite_path = next((a for a in self.arquivos
                                 if os.path.basename(a) == salvo), self.arquivos[0])
        self.dpr = QApplication.primaryScreen().devicePixelRatio()
        self.qualidade = 1.0
        self.tempos = []
        self.clock = time.time
        self.cursor_pos = QCursor.pos
        self.bo = None
        self.carregar_sprite()

        geo = QApplication.primaryScreen().availableGeometry()
        self.wx = geo.center().x() - W / 2
        self.wy = geo.center().y() - H / 2
        self.prev_wx = self.wx
        self.facing = 1
        self.fv = 1.0
        self.phase = 0.0
        self.prev_sin = 0.0
        self.walking = False
        self.sleeping = False
        self.dragging = False
        self.press_pos = None
        self.grab_off = (0, 0)
        self.hearts = []
        self.frame = 0
        self.bubble = ("", 0)

        # física
        self.vx = self.vy = 0.0
        self.z = self.vz = 0.0
        self.hops = 0
        self.antic_until = 0.0
        self.prev_dvx = 0.0
        self.sq = Mola(0.22, 0.14)
        self.lean = Mola(0.12, 0.16)
        self.head = Mola(0.16, 0.22)
        self.ear = Mola(0.30, 0.10)
        self.blinkm = Mola(0.50, 0.35)
        self.pend = Mola(0.05, 0.06)

        now = self.clock()
        self.now = now
        self.t_prev = now
        pos = self.cursor_pos()
        self.last_mouse = (pos.x(), pos.y())
        self.mouse = self.last_mouse
        self.look_pos = self.last_mouse
        self.last_move = now
        self.happy_until = 0
        self.startle_until = 0
        self.look_until = 0
        self.blink_until = 0
        self.blink_again = False
        self.next_blink = now + 2
        self.next_ear = now + 4
        self.next_sniff = now + 6
        self.sniff_until = 0
        self.next_look = now + 5
        self.glance_until = 0
        self.glance_angle = 0.0
        self.next_wiggle = now + 9
        self.wiggle_until = 0
        self.next_sip = now + 5
        self.sip_until = 0
        self.next_stretch = now + 14
        self.next_joy = now + 14
        self.next_speak = now + 20
        self.prev_down = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(16)
        self.move(int(self.wx), int(self.wy))

    # -------------------------------------------------------------- sprite
    def carregar_sprite(self):
        self.bo = Boneco(self.sprite_path, ALTURA * self.escala, self.dpr,
                         W - 50, self.qualidade)

    def trocar_sprite(self, caminho):
        self.sprite_path = caminho
        self.settings.setValue("sprite", os.path.basename(caminho))
        self.carregar_sprite()
        self.make_happy(1.2, falar=False)

    def trocar_tamanho(self, escala):
        self.escala = escala
        self.settings.setValue("escala", escala)
        self.carregar_sprite()

    # -------------------------------------------------------------- falas / eventos
    def say(self, lines, seconds=2.8):
        if not self.speech_on:
            return
        text = random.choice(lines) if isinstance(lines, list) else lines
        self.bubble = (text, self.clock() + seconds)

    def make_happy(self, seconds=1.7, falar=True):
        now = self.clock()
        was_sleeping = self.sleeping
        self.happy_until = now + seconds
        self.sleeping = False
        self.last_move = now
        if self.z <= 0.01:
            self.hops = 2
            self.antic_until = now + 0.14
        if falar:
            self.say(FALAS_ACORDA if was_sleeping else FALAS_CARINHO)

    # -------------------------------------------------------------- mouse
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.RightButton:
            self.show_menu(e.globalPosition().toPoint())
            return
        g = e.globalPosition()
        self.press_pos = (g.x(), g.y())
        self.grab_off = (g.x() - self.wx, g.y() - self.wy)
        self.dragging = False

    def mouseMoveEvent(self, e):
        if self.press_pos is None:
            return
        g = e.globalPosition()
        if not self.dragging and math.hypot(
                g.x() - self.press_pos[0], g.y() - self.press_pos[1]) > 5:
            self.dragging = True
            self.sleeping = False
            self.hops = 0
            self.say(FALAS_COLO)
        if self.dragging:
            self.wx = g.x() - self.grab_off[0]
            self.wy = g.y() - self.grab_off[1]

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        if self.press_pos is not None and not self.dragging:
            self.make_happy()
        elif self.dragging:
            self.sq.impulso(-0.05)
        self.dragging = False
        self.press_pos = None
        self.last_move = self.clock()

    def show_menu(self, pos):
        m = QMenu(self)
        m.addAction("Fazer carinho", self.make_happy)

        sub = m.addMenu("Trocar capivara")
        grp = QActionGroup(sub)
        grp.setExclusive(True)
        for arq in self.arquivos:
            a = sub.addAction(nome_bonito(arq))
            a.setCheckable(True)
            a.setChecked(arq == self.sprite_path)
            grp.addAction(a)
            a.triggered.connect(lambda _=False, ar=arq: self.trocar_sprite(ar))

        sub2 = m.addMenu("Tamanho")
        grp2 = QActionGroup(sub2)
        grp2.setExclusive(True)
        for nome, esc in TAMANHOS:
            a = sub2.addAction(nome)
            a.setCheckable(True)
            a.setChecked(abs(self.escala - esc) < 0.01)
            grp2.addAction(a)
            a.triggered.connect(lambda _=False, e=esc: self.trocar_tamanho(e))

        a = m.addAction("Balão de fala")
        a.setCheckable(True)
        a.setChecked(self.speech_on)
        a.toggled.connect(self.set_speech)
        if winreg:
            a2 = m.addAction("Iniciar com o Windows")
            a2.setCheckable(True)
            a2.setChecked(startup_enabled())
            a2.toggled.connect(set_startup)
        m.addSeparator()
        m.addAction("Sair", QApplication.quit)
        m.exec(pos)

    def set_speech(self, on):
        self.speech_on = on
        self.settings.setValue("speech", on)

    # -------------------------------------------------------------- lógica
    def poll_global_click(self, now, pos):
        if not USER32:
            return
        down = bool(USER32.GetAsyncKeyState(0x01) & 0x8000)
        if down and not self.prev_down and not self.dragging:
            bo = self.bo
            rect = QRect(int(self.wx + W / 2 - bo.pw / 2 - 10),
                         int(self.wy + GY - bo.ph - 10),
                         int(bo.pw + 20), int(bo.ph + 20))
            if not rect.contains(pos):
                self.susto(now, (pos.x(), pos.y()))
        self.prev_down = down

    def susto(self, now, ponto):
        was_sleeping = self.sleeping
        self.startle_until = now + 0.7
        self.look_until = now + 1.4
        self.look_pos = ponto
        self.last_move = now
        self.sleeping = False
        if self.z <= 0.01 and self.hops == 0:
            self.vz = 3.4
        self.ear.impulso(-6)
        self.say(FALAS_ACORDA if was_sleeping else FALAS_SUSTO, 2)

    def tick(self):
        t0 = time.perf_counter()
        now = self.clock()
        self.now = now
        dt = min(0.05, max(0.001, now - self.t_prev))
        self.t_prev = now
        d = dt * 60.0
        self.frame += 1
        bo = self.bo
        pos = self.cursor_pos()
        mx, my = pos.x(), pos.y()
        self.mouse = (mx, my)

        if (mx, my) != self.last_mouse:
            if self.sleeping:
                self.say(FALAS_ACORDA)
            self.last_mouse = (mx, my)
            self.last_move = now
            self.sleeping = False
        self.poll_global_click(now, pos)

        # ---------------- movimento (com aceleração suave)
        if not self.dragging:
            dx = mx - (self.wx + W / 2)
            if abs(dx) > 110:
                novo = 1 if dx > 0 else -1
                if novo != self.facing:
                    self.facing = novo
                    self.sq.impulso(0.04)
            tx = mx - self.facing * DISTANCE - W / 2
            ty = my - GY + 12
            ddx, ddy = tx - self.wx, ty - self.wy
            dist = math.hypot(ddx, ddy)
            if self.sleeping or dist <= 3:
                tvx = tvy = 0.0
            else:
                want = min(dist * 0.06, VMAX)
                tvx, tvy = ddx / dist * want, ddy / dist * want
            k = min(1.0, 0.12 * d)
            self.vx += (tvx - self.vx) * k
            self.vy += (tvy - self.vy) * k
            self.wx += self.vx * d
            self.wy += self.vy * d
            self.prev_dvx = 0.0
        else:
            dvx = (self.wx - self.prev_wx) / max(d, 0.5)
            self.pend.impulso(-(dvx - self.prev_dvx) * 1.3)
            self.prev_dvx = dvx
            self.vx = self.vy = 0.0
        self.prev_wx = self.wx
        speed = math.hypot(self.vx, self.vy)
        self.walking = speed > (0.5 if self.walking else 0.9)
        sv = min(speed, 9.0) / 9.0

        if not self.walking and not self.dragging and now - self.last_move > SLEEP_AFTER:
            self.sleeping = True

        happy = now < self.happy_until
        startle = now < self.startle_until
        held = self.dragging
        sleeping = self.sleeping

        if (not self.walking and not sleeping and not held and not happy
                and now > self.next_joy and math.hypot(
                    mx - (self.wx + W / 2), my - (self.wy + GY)) < 180):
            self.make_happy(1.5, falar=False)
            self.next_joy = now + random.uniform(12, 24)

        # ---------------- passos
        if self.walking:
            self.phase += speed * 0.035 * d
        s_now = math.sin(self.phase)
        if self.walking and (s_now > 0) != (self.prev_sin > 0):
            self.sq.impulso(-0.011 * min(speed, 9))       # impacto do passo
        self.prev_sin = s_now

        # ---------------- pulo (física de verdade)
        if (self.hops > 0 and self.z <= 0.01 and self.vz == 0 and now >= self.antic_until
                and not held):
            self.vz = 5.2
            self.hops -= 1
        if self.z > 0 or self.vz != 0:
            self.vz -= 0.42 * d
            self.z += self.vz * d
            if self.z <= 0:
                if self.vz < -1:
                    self.sq.impulso(-0.022 * abs(self.vz))   # amassa ao cair
                self.z = 0.0
                self.vz = 0.0
                if self.hops > 0:
                    self.antic_until = now + 0.05
        if held:
            self.z = self.vz = 0.0
        antic = self.hops > 0 and self.z <= 0.01 and now < self.antic_until

        # ---------------- comportamentos espontâneos
        livre = not (self.walking or sleeping or held or happy or startle)
        if livre:
            if now > self.next_ear:
                self.ear.impulso(random.choice((-9, 9)))
                self.next_ear = now + random.uniform(3.5, 9)
            if now > self.next_sniff:
                self.sniff_until = now + 0.8
                self.next_sniff = now + random.uniform(7, 15)
            if now > self.next_look:
                self.glance_until = now + random.uniform(1.2, 2.2)
                self.glance_angle = random.choice((-5, -3, 3, 5))
                self.next_look = now + random.uniform(6, 13)
            if now > self.next_wiggle:
                self.wiggle_until = now + 0.8
                self.next_wiggle = now + random.uniform(10, 20)
            if now > self.next_stretch:
                self.sq.impulso(0.035)
                self.next_stretch = now + random.uniform(14, 26)
            if self.bo.rig.get("sip") and now > self.next_sip:
                self.sip_until = now + 1.5
                self.next_sip = now + random.uniform(6, 11)
                if random.random() < 0.35:
                    self.say(FALAS_SIP, 2)
            if now > self.next_speak:
                self.say(FALAS_IDLE)
                self.next_speak = now + random.uniform(25, 45)
        if now > self.next_blink and not sleeping:
            self.blink_until = now + 0.11
            if random.random() < 0.25 and not self.blink_again:
                self.blink_again = True
                self.next_blink = now + 0.28
            else:
                self.blink_again = False
                self.next_blink = now + random.uniform(2.2, 5.5)

        # ---------------- molas
        sq_t = 0.0
        if antic:
            sq_t = -0.13
        elif self.z > 0.5:
            sq_t = 0.07 * min(1.0, abs(self.vz) / 5.0)
        elif held:
            sq_t = 0.07
        elif sleeping:
            sq_t = -0.05
        self.sq.step(sq_t, d)

        lean_t = 0.0
        if not held:
            lean_t = clamp(self.vx * 0.55, -7, 7) + math.sin(self.phase) * 3.5 * sv
            if now < self.wiggle_until:
                lean_t += math.sin(now * 14) * 3.5
        self.lean.step(lean_t, d)
        self.pend.step(0.0, d)
        self.pend.x = clamp(self.pend.x, -30, 30)

        # cabeça: olha o cursor, balança com atraso e faz mesuras
        tx_, ty_ = self.look_pos if now < self.look_until else self.mouse
        hx = self.wx + W / 2 + self.facing * bo.pw * 0.2
        hy = self.wy + GY - bo.ph * 0.7
        up = clamp(-(ty_ - hy) / 140.0, -1, 1)
        head_t = -up * 6.0
        head_bob = math.sin(now * 2.2 - 0.5) * 0.6
        sip_env = 0.0
        if now < self.sip_until:
            sip_env = math.sin(math.pi * (1 - (self.sip_until - now) / 1.5))
        if sleeping:
            head_t = 9 + 1.5 * math.sin(now * 0.9)
        elif held:
            head_t = -7
        else:
            if now < self.glance_until:
                head_t = self.glance_angle
            head_t += -self.lean.x * 0.55 + math.sin(self.phase - 0.9) * 2.4 * sv
            head_bob += math.sin(self.phase * 2 - 1.0) * 1.3 * sv
            head_t += sip_env * 4.0
            head_bob += sip_env * 2.2
        self.head.step(head_t, d)

        ear_t = 0.0
        if happy:
            ear_t = math.sin(now * 26) * 14
        elif startle:
            ear_t = -12
        elif self.walking:
            ear_t = math.sin(self.phase * 2) * 5 * sv
        self.ear.step(ear_t, d)

        if sleeping:
            bl_t = 1.0
        elif happy:
            bl_t = 0.6
        elif startle or held:
            bl_t = -0.9
        else:
            bl_t = 1.0 if now < self.blink_until else 0.0
        self.blinkm.step(bl_t, d)

        rate, amp = (1.5, 0.04) if sleeping else (2.2, 0.022)
        breath = amp * math.sin(now * rate) + 0.03 * sip_env
        if happy:
            breath += 0.012 * math.sin(now * 18)
        sniff = 0.0
        if now < self.sniff_until:
            env = math.sin(math.pi * (1 - (self.sniff_until - now) / 0.8))
            sniff = 0.14 * env * math.sin(now * 38)

        # pés
        if held:
            lifts = [4 + 3 * math.sin(now * 7), 4 + 3 * math.sin(now * 7 + 2)]
        elif self.z > 0.5:
            tuck = clamp(self.z * 0.22, 0, 5)
            lifts = [tuck, tuck]
        elif self.walking:
            lifts = [max(0.0, s_now) * 7 * sv, max(0.0, -s_now) * 7 * sv]
        else:
            lifts = [0.0, 0.0]

        self.fv += (self.facing - self.fv) * min(1.0, 0.25 * d)
        params = {"head_rot": self.head.x, "head_bob": head_bob, "breath": breath,
                  "ear": self.ear.x, "blink": self.blinkm.x, "sniff": sniff,
                  "lifts": lifts}
        bo.warp(params)

        # quicar durante a caminhada
        self.walk_z = abs(s_now) * 6.0 * sv if self.walking else 0.0

        # corações
        if happy and self.frame % 9 == 0:
            self.hearts.append([W / 2 + self.facing * bo.pw * random.uniform(0.05, 0.3),
                                GY - bo.ph * random.uniform(1.0, 1.12) - self.z - 6,
                                random.uniform(0, 6.28), random.randint(7, 11)])
        for h in self.hearts:
            h[1] -= 1.0 * d
            h[2] += 0.1 * d
        self.hearts = [h for h in self.hearts if h[1] > 6]

        self.move(int(self.wx), int(self.wy))
        self.update()

        # se o computador estiver lento, baixa a resolução da animação sozinho
        self.tempos.append(time.perf_counter() - t0)
        if len(self.tempos) >= 90:
            media = sum(self.tempos) / len(self.tempos)
            self.tempos = []
            if media > 0.016 and self.qualidade > 0.65:
                self.qualidade *= 0.8
                self.carregar_sprite()

    # -------------------------------------------------------------- desenho
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHints(QPainter.RenderHint.Antialiasing
                         | QPainter.RenderHint.TextAntialiasing
                         | QPainter.RenderHint.SmoothPixmapTransform)
        now = self.now
        bo = self.bo
        f = self.fv
        if abs(f) < 0.07:
            f = 0.07 if f >= 0 else -0.07

        # pendulo quando está no colo
        if self.dragging:
            gx, gy = self.grab_off
            p.translate(gx, gy)
            p.rotate(self.pend.x)
            p.translate(-gx, -gy)

        p.translate(W / 2, GY)

        altura = self.z + getattr(self, "walk_z", 0.0)
        sh = max(0.45, 1 - altura / 90)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(60, 30, 10, 55))
        p.drawEllipse(QPointF(0, -2), bo.pw * 0.42 * sh, 8 * sh)

        p.translate(0, -altura)
        p.rotate(self.lean.x)
        sy = clamp(1 + self.sq.x, 0.8, 1.25)
        sx = 1.0 / sy
        p.scale(f * sx, sy)
        if self.sleeping:
            p.setOpacity(0.94)
        p.drawImage(QRectF(-bo.pw / 2 - bo.m, -bo.ph - bo.m,
                           bo.cw / bo.ws, bo.ch / bo.ws), bo.qimg)
        p.setOpacity(1)

        p.resetTransform()

        if self.sleeping:
            for i in range(3):
                t = (now * 0.5 + i / 3) % 1
                p.setFont(QFont("Segoe UI", int(11 + i * 3), QFont.Weight.Bold))
                p.setPen(QColor("#5b7fa6"))
                p.setOpacity(1 - t * 0.7)
                p.drawText(QPointF(W / 2 + self.facing * bo.pw * (0.2 + t * 0.2),
                                   GY - bo.ph * 0.85 - t * 55), "z")
            p.setOpacity(1)

        for hx, hy, ph, s in self.hearts:
            p.setBrush(HEART_FILL)
            p.setPen(pen(2, HEART_OUT))
            p.drawPath(heart_path(hx + math.sin(ph) * 6, hy, s))

        text, until = self.bubble
        if text and now < until:
            font = QFont("Segoe UI", 10, QFont.Weight.Bold)
            p.setFont(font)
            tw = QFontMetrics(font).horizontalAdvance(text)
            bw, bh = tw + 26, 30
            hx = W / 2 + self.facing * bo.pw * 0.15
            bx = max(4, min(W - bw - 4, hx - bw / 2))
            by = max(4, GY - bo.ph - 52 - altura * 0.5)
            shape = QPainterPath()
            shape.addRoundedRect(QRectF(bx, by, bw, bh), 13, 13)
            tail = QPainterPath()
            tail.moveTo(hx - 7, by + bh - 1)
            tail.lineTo(hx + 7, by + bh - 1)
            tail.lineTo(hx + self.facing * 3, by + bh + 11)
            tail.closeSubpath()
            shape = shape.united(tail)
            p.setBrush(QColor(255, 255, 255, 245))
            p.setPen(pen(2.6))
            p.drawPath(shape)
            p.setPen(OUT)
            p.drawText(QRectF(bx, by, bw, bh), Qt.AlignmentFlag.AlignCenter, text)

        p.end()


def main():
    app = QApplication(sys.argv)
    pet = Capivara()
    pet.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
