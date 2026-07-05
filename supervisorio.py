# -*- coding: utf-8 -*-
"""
supervisorio.py
Supervisório visual (estilo P&ID reduzido) para o CLP simulado do PROB_01.

Em vez de um formulário de botões/checkboxes, desenha o fluxograma do processo
(TK-101 -> TK-102 -> TK-103 + skid de CIP) num Canvas, com tanques, válvulas,
bombas e lâmpadas que mudam de cor/nível/valor em tempo real, lendo
`output/estado_atual.csv` (gerado pelo main.py a cada scan).

Os comandos continuam escrevendo no MESMO `painel_operador.json` lido por
`operator_panel.py` — nenhuma mudança é necessária no simulador (main.py,
plc_data.py, modules/...) para usar este supervisório.
"""

import argparse
import csv
import json
import tkinter as tk
from pathlib import Path

import customtkinter as ctk

ROOT = Path(__file__).resolve().parent
PAINEL_PADRAO = ROOT / "painel_operador.json"
CSV_PADRAO = ROOT / "output" / "estado_atual.csv"


def resolver_caminhos(caminho_json=None, caminho_csv=None, saida="output"):
    """Resolve os caminhos do painel e do CSV de forma compatível com o main.py."""
    def resolver_path(caminho, padrao):
        if caminho is None:
            return padrao
        caminho_path = Path(caminho)
        if caminho_path.is_absolute():
            return caminho_path
        candidatos = [Path.cwd() / caminho_path, ROOT / caminho_path]
        for candidato in candidatos:
            if candidato.exists() or candidato.parent.exists():
                return candidato.resolve()
        return (ROOT / caminho_path).resolve()

    caminho_json = resolver_path(caminho_json, PAINEL_PADRAO)
    if caminho_csv is None:
        caminho_csv = (ROOT / saida / "estado_atual.csv").resolve()
    else:
        caminho_csv = resolver_path(caminho_csv, ROOT / saida / "estado_atual.csv")

    return caminho_json, caminho_csv

_PADRAO = {
    "PB_START": False,
    "PB_STOP": False,
    "PB_EMG_ACIONADO": False,
    "PB_RESET": False,
    "SEL_RECEITA": 0,
    "HABILITA_MANUAL": False,
    "MAN_XV_CARGA": False,
    "MAN_XV101": False,
    "MAN_P101": False,
    "MAN_AG101": False,
    "MAN_XV_ENVASE": False,
    "MAN_P103": False,
    "forcar_falha_FL_P101": False,
    "forcar_falha_FL_P103": False,
    "forcar_falha_FL_P104": False,
    "forcar_falha_FL_P105": False,
}

# ---------------------------------------------------------------- cores ----
COR_FUNDO = "#10141a"
COR_TUBO = "#5a6472"
COR_TUBO_ATIVO = "#3fa9f5"
COR_ON = "#2fa572"
COR_OFF = "#3a3f47"
COR_ALARME = "#d9483d"
COR_CONTORNO = "#8a93a2"
COR_TEXTO = "#e7ebf0"
COR_TEXTO_FRACO = "#9aa3b0"
COR_LIQUIDO = "#3fa9f5"


# ------------------------------------------------------------ persistência ----
def carregar_painel(caminho=PAINEL_PADRAO) -> dict:
    caminho = Path(caminho)
    if not caminho.exists():
        salvar_painel(dict(_PADRAO), caminho)
        return dict(_PADRAO)
    try:
        with caminho.open("r", encoding="utf-8") as f:
            dados = json.load(f)
    except (json.JSONDecodeError, OSError):
        dados = {}
    for chave, valor in _PADRAO.items():
        dados.setdefault(chave, valor)
    return dados


def salvar_painel(dados: dict, caminho=PAINEL_PADRAO) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)


def ler_status_csv(caminho=CSV_PADRAO) -> dict:
    caminho = Path(caminho)
    if not caminho.exists():
        return {}
    try:
        with caminho.open("r", encoding="utf-8", newline="") as f:
            linhas = list(csv.DictReader(f))
    except (OSError, csv.Error):
        return {}
    return linhas[-1] if linhas else {}


def _num(status: dict, chave: str, default: float = 0.0) -> float:
    try:
        return float(status.get(chave, default))
    except (TypeError, ValueError):
        return default


def _bit(status: dict, chave: str) -> bool:
    try:
        return int(float(status.get(chave, 0))) != 0
    except (TypeError, ValueError):
        return False


# ==================================================================== ====
class DiagramaProcesso(tk.Canvas):
    """Fluxograma do processo (P&ID reduzido) desenhado uma vez;
    a cada refresh só reconfiguramos cor/posição/texto dos itens (por tag)."""

    LARGURA, ALTURA = 900, 560

    def __init__(self, master):
        super().__init__(master, width=self.LARGURA, height=self.ALTURA,
                          bg=COR_FUNDO, highlightthickness=0)
        self.itens = {}
        self._montar()

    # -- primitivas ---------------------------------------------------
    def _tubo(self, x1, y1, x2, y2, tag):
        item = self.create_line(x1, y1, x2, y2, fill=COR_TUBO, width=6,
                                 capstyle=tk.ROUND)
        self.itens[tag] = item

    def _tanque(self, x, y, w, h, tag, titulo, capacidade):
        self.create_rectangle(x, y, x + w, y + h, outline=COR_CONTORNO, width=2)
        nivel = self.create_rectangle(x + 2, y + h - 2, x + w - 2, y + h - 2,
                                       fill=COR_LIQUIDO, outline="")
        titulo_linhas = titulo.split("\n")
        titulo_y = y - 42
        for idx, linha in enumerate(titulo_linhas):
            self.create_text(x + w / 2, titulo_y + idx * 14, text=linha, fill=COR_TEXTO,
                              font=("Segoe UI", 9, "bold"))
        self.create_text(x + w / 2, y - 6, text=f"cap. {capacidade:,.0f} L".replace(",", "."),
                          fill=COR_TEXTO_FRACO, font=("Segoe UI", 8))
        valor = self.create_text(x + w / 2, y + h / 2, text="0 L",
                                  fill=COR_TEXTO, font=("Segoe UI", 12, "bold"), anchor="center")
        self.create_text(x + w / 2, y + h + 14, text="Nível", fill=COR_TEXTO_FRACO,
                          font=("Segoe UI", 8))
        self.itens[f"{tag}_nivel"] = nivel
        self.itens[f"{tag}_valor"] = valor
        self.itens[f"{tag}_geom"] = (x, y, w, h, capacidade)

    def _valvula(self, x, y, tag, label, orient="h"):
        s = 10
        if orient == "h":
            pontos = (x - s, y - s, x, y, x - s, y + s, x + s, y + s, x, y, x + s, y - s)
        else:
            pontos = (x - s, y - s, x, y, x + s, y - s, x + s, y + s, x, y, x - s, y + s)
        poly = self.create_polygon(*pontos, fill=COR_OFF, outline=COR_CONTORNO, width=1)
        # menor fonte e posicionado com mais folga para evitar sobreposição
        txt = self.create_text(x, y + (24 if orient == "h" else 0),
                                text=label, fill=COR_TEXTO_FRACO, font=("Segoe UI", 7))
        if orient == "h":
            self.coords(txt, x, y + 24)
        else:
            # desloca rótulo vertical para a direita, com âncora à esquerda
            self.coords(txt, x + 36, y)
            self.itemconfig(txt, anchor="w")
        self.itens[tag] = poly

    def _bomba(self, x, y, tag, label):
        r = 15
        circ = self.create_oval(x - r, y - r, x + r, y + r, fill=COR_OFF,
                                 outline=COR_CONTORNO, width=2)
        tri = self.create_polygon(x - 6, y - 8, x - 6, y + 8, x + 9, y,
                                   fill=COR_TEXTO, outline="")
        self.create_text(x, y + r + 12, text=label, fill=COR_TEXTO_FRACO,
                          font=("Segoe UI", 8))
        self.itens[tag] = circ
        self.itens[f"{tag}_tri"] = tri

    def _icone(self, x, y, tag, label, forma="circulo"):
        r = 13
        if forma == "circulo":
            item = self.create_oval(x - r, y - r, x + r, y + r, fill=COR_OFF,
                                     outline=COR_CONTORNO, width=2)
        else:
            item = self.create_rectangle(x - r, y - r, x + r, y + r, fill=COR_OFF,
                                          outline=COR_CONTORNO, width=2)
        # texto do ícone menor para reduzir poluição visual
        self.create_text(x, y + r + 10, text=label, fill=COR_TEXTO_FRACO,
                          font=("Segoe UI", 7))
        self.itens[tag] = item

    def _lampada(self, x, y, tag, label):
        r = 11
        item = self.create_oval(x - r, y - r, x + r, y + r, fill=COR_OFF, outline=COR_CONTORNO)
        # posição e tamanho reduzidos para evitar encavalamento
        self.create_text(x + 26, y, text=label, fill=COR_TEXTO_FRACO, anchor="w",
                          font=("Segoe UI", 8))
        self.itens[tag] = item

    def _leitura(self, x, y, tag, label, unidade=""):
        # etiquetas de leitura com fonte reduzida
        self.create_text(x, y - 12, text=label, fill=COR_TEXTO_FRACO, font=("Segoe UI", 7))
        txt = self.create_text(x, y + 4, text=f"---{unidade}", fill=COR_TEXTO,
                                font=("Segoe UI", 10, "bold"))
        self.itens[tag] = txt

    # -- montagem -------------------------------------------------------
    def _montar(self):
        self.create_text(16, 16, text="Supervisório", fill=COR_TEXTO,
                          anchor="w", font=("Segoe UI", 12, "bold"))

        # ---- Linha de matéria-prima / carga -> TK-101 ----
        self._tubo(90, 60, 90, 90, "tubo_carga")
        self._valvula(90, 60, "v_xv_carga", "XV_CARGA\nEntrada", orient="v")
        self.create_text(90, 32, text="Matéria-prima", fill=COR_TEXTO_FRACO, font=("Segoe UI", 8))

        # ---- TK-101 (pré-mistura / carregamento) ----
        self._tanque(45, 90, 90, 170, "tk101", "TK-101", 1500)
        self._icone(112, 115, "ag101", "AG101", forma="circulo")
        # sensores de nível ficam FORA do corpo do tanque (à direita), para não
        # encavalar com a legenda "Nível" nem com a borda do tanque
        self._lampada(152, 108, "ls_h", "LS_TK101_H (alto)")
        self._lampada(152, 240, "ls_l", "LS_TK101_L (baixo)")

        # ---- Saída TK-101 -> P-101 -> XV101 -> TK-102 ----
        self._tubo(90, 260, 90, 310, "tubo_p101_in")
        self._bomba(90, 320, "p101", "P-101")
        self._tubo(90, 335, 90, 360, "tubo_p101_out")
        self._tubo(90, 360, 205, 360, "tubo_p101_h")
        self._valvula(225, 360, "v_xv101", "XV101\nTransfer", orient="h")
        self._tubo(245, 360, 315, 360, "tubo_xv101_tk102")

        # ---- TK-102 (mistura, sem sensor de nível na Lista_IO) ----
        self.create_rectangle(315, 300, 415, 400, outline=COR_CONTORNO, width=2)
        self.create_text(365, 279, text="TK-102\nMistura", fill=COR_TEXTO, font=("Segoe UI", 11, "bold"))
        self._icone(365, 318, "heat101", "HEAT101", forma="quadrado")
        tt = self.create_text(365, 362, text="TT102\n---°C", fill=COR_TEXTO,
                               font=("Segoe UI", 11, "bold"), justify="center")
        self.create_text(365, 388, text="Temperatura", fill=COR_TEXTO_FRACO,
                          font=("Segoe UI", 8))
        self.itens["tt102"] = tt

        # ---- TK-102 -> TK-103 ----
        self._tubo(415, 350, 475, 350, "tubo_tk102_tk103")
        self._tubo(475, 350, 475, 200, "tubo_tk102_tk103_v")

        # ---- TK-103 (armazenamento / envase) ----
        self._tanque(475, 90, 90, 170, "tk103", "TK-103\nEnvase", 2500)

        # ---- TK-103 -> XV_ENVASE -> P-103 -> linha de envase ----
        self._tubo(520, 260, 520, 300, "tubo_env_in")
        self._valvula(520, 310, "v_xv_envase", "XV_ENVASE\nEnvase", orient="v")
        self._tubo(520, 325, 520, 350, "tubo_env_mid")
        self._bomba(520, 365, "p103", "P-103")
        self._tubo(520, 380, 520, 410, "tubo_env_out")
        self.create_text(520, 425, text="Linha de Envase", fill=COR_TEXTO_FRACO, font=("Segoe UI", 9))

        # ---- Skid de CIP ----
        self.create_text(45, 445, text="CIP", fill=COR_TEXTO, anchor="w",
                          font=("Segoe UI", 12, "bold"))
        self._tubo(45, 470, 700, 470, "tubo_cip_main")

        # orient="h" pois estas válvulas ficam sobre a tubulação HORIZONTAL do
        # coletor de CIP; com orient="v" o rótulo era desenhado ao lado, na
        # mesma altura do tubo, e ficava encavalado em cima da linha
        self._valvula(110, 470, "v_xv_dreno", "XV_DRENO\nDreno", orient="h")
        self._bomba(190, 505, "p105", "P-105\nÁgua")
        self._valvula(270, 470, "v_xv_cip01", "XV_CIP_01\nAlcalino", orient="h")
        self._bomba(350, 505, "p104", "P-104\nÁlcali")
        self._valvula(430, 470, "v_xv_cip02", "XV_CIP_02\nÁgua", orient="h")
        self._valvula(500, 470, "v_xv102", "XV102\nCIP Geral", orient="h")

        self._tubo(110, 470, 110, 410, "tubo_dreno_up")
        self.create_text(110, 398, text="Dreno TK-101/103", fill=COR_TEXTO_FRACO, font=("Segoe UI", 8))

        # ---- Instrumentação de qualidade / pressão CIP ----
        self._leitura(590, 505, "pt101", "PT101 (bar)")
        self._leitura(660, 505, "ait101", "AIT101 pH")
        self._leitura(730, 505, "ait102", "AIT102 µS/cm")
        self._leitura(810, 505, "ait103", "AIT103 NTU")
        self.create_text(590, 530, text="Pressão", fill=COR_TEXTO_FRACO, font=("Segoe UI", 8))
        self.create_text(660, 530, text="pH", fill=COR_TEXTO_FRACO, font=("Segoe UI", 8))
        self.create_text(730, 530, text="Cond.", fill=COR_TEXTO_FRACO, font=("Segoe UI", 8))
        self.create_text(810, 530, text="Turbidez", fill=COR_TEXTO_FRACO, font=("Segoe UI", 8))

        # ---- Lâmpadas de sinalização geral (canto superior direito) ----
        self._lampada(680, 40, "pl_auto", "PL_AUTO")
        self._lampada(680, 65, "pl_cip", "PL_CIP")
        self._lampada(680, 90, "pl_falha", "PL_FALHA")
        self._lampada(680, 115, "alm_horn", "ALM_HORN (sirene)")

        # ---- Estado da máquina (destaque) ----
        self.create_rectangle(600, 150, 850, 220, outline=COR_CONTORNO, width=1)
        self.create_text(725, 165, text="ESTADO", fill=COR_TEXTO_FRACO, font=("Segoe UI", 9))
        est = self.create_text(725, 188, text="—", fill=COR_TEXTO, font=("Segoe UI", 16, "bold"))
        sub = self.create_text(725, 208, text="", fill=COR_TEXTO_FRACO, font=("Segoe UI", 10))
        self.itens["estado_txt"] = est
        self.itens["subestado_txt"] = sub

    # -- atualização ------------------------------------------------------
    def _cor(self, ligado, alarme=False):
        if alarme:
            return COR_ALARME
        return COR_ON if ligado else COR_OFF

    def _cor_atuador(self, status, campo_run_prefixado, campo_run_cru, campo_falha=None):
        """Cor de bombas/agitador: vermelho se a falha (real ou forçada pelo
        painel) estiver ativa — antes disso o LED só mostrava rodando/parado
        e escondia a falha, deixando o botão de 'forçar falha' parecendo que
        não fazia nada."""
        ligado = _bit(status, campo_run_prefixado) or _bit(status, campo_run_cru)
        falha = _bit(status, campo_falha) if campo_falha else False
        return self._cor(ligado, alarme=falha)

    def _set_nivel(self, tag, valor):
        x, y, w, h, cap = self.itens[f"{tag}_geom"]
        frac = max(0.0, min(1.0, valor / cap if cap else 0.0))
        y_topo = y + h - (h - 4) * frac - 2
        self.coords(self.itens[f"{tag}_nivel"], x + 2, y_topo, x + w - 2, y + h - 2)
        self.itemconfig(self.itens[f"{tag}_valor"], text=f"{valor:,.0f} L".replace(",", "."))

    def atualizar(self, status: dict):
        # --- tanques ---
        self._set_nivel("tk101", _num(status, "IA_LT101", _num(status, "LT101", 0.0)))
        self._set_nivel("tk103", _num(status, "IA_LT103", _num(status, "LT103", 0.0)))
        self.itemconfig(self.itens["tt102"], text=f"TT102\n{_num(status,'IA_TT102', _num(status,'TT102', 25.0)):.1f}°C")

        # --- lâmpadas de nível ---
        self.itemconfig(self.itens["ls_h"], fill=self._cor(_bit(status, "I_LS_TK101_H") or _bit(status, "LS_TK101_H")))
        self.itemconfig(self.itens["ls_l"], fill=self._cor(_bit(status, "I_LS_TK101_L") or _bit(status, "LS_TK101_L")))

        # --- válvulas ---
        self.itemconfig(self.itens["v_xv_carga"], fill=self._cor(_bit(status, "O_XV_CARGA") or _bit(status, "XV_CARGA")))
        self.itemconfig(self.itens["v_xv101"], fill=self._cor(_bit(status, "O_XV101") or _bit(status, "XV101")))
        self.itemconfig(self.itens["v_xv_envase"], fill=self._cor(_bit(status, "O_XV_ENVASE") or _bit(status, "XV_ENVASE")))
        self.itemconfig(self.itens["v_xv_dreno"], fill=self._cor(_bit(status, "O_XV_DRENO") or _bit(status, "XV_DRENO")))
        self.itemconfig(self.itens["v_xv_cip01"], fill=self._cor(_bit(status, "O_XV_CIP_01") or _bit(status, "XV_CIP_01")))
        self.itemconfig(self.itens["v_xv_cip02"], fill=self._cor(_bit(status, "O_XV_CIP_02") or _bit(status, "XV_CIP_02")))
        self.itemconfig(self.itens["v_xv102"], fill=self._cor(_bit(status, "O_XV102") or _bit(status, "XV102")))

        # --- bombas / agitador / aquecimento ---
        # cada bomba considera também seu alarme de falha de feedback (real ou
        # injetado pelo painel de "forçar falha"), para o LED realmente
        # mostrar a falha em vez de continuar verde como se nada tivesse ocorrido
        for tag, campo, campo_falha in (
            ("p101", "O_P101_RUN", "ALM_ALM_FALHA_P101"),
            ("p103", "O_P103_RUN", "ALM_ALM_FALHA_P103"),
            ("p104", "O_P104_RUN", "ALM_ALM_FALHA_P104"),
            ("p105", "O_P105_RUN", "ALM_ALM_FALHA_P105"),
        ):
            cor = self._cor_atuador(status, campo, campo.replace("O_", ""), campo_falha)
            self.itemconfig(self.itens[tag], fill=cor)
        self.itemconfig(self.itens["ag101"], fill=self._cor_atuador(
            status, "O_AG101_RUN", "AG101_RUN", "ALM_ALM_FALHA_AG"))
        self.itemconfig(self.itens["heat101"], fill=self._cor(_bit(status, "O_HEAT101") or _bit(status, "HEAT101")))

        # --- tubulação principal de transferência "acende" quando há fluxo ---
        transferindo = (_bit(status, "O_P101_RUN") or _bit(status, "P101_RUN")) and (_bit(status, "O_XV101") or _bit(status, "XV101"))
        for tag in ("tubo_p101_h", "tubo_xv101_tk102", "tubo_tk102_tk103", "tubo_tk102_tk103_v"):
            self.itemconfig(self.itens[tag], fill=COR_TUBO_ATIVO if transferindo else COR_TUBO)
        envasando = (_bit(status, "O_P103_RUN") or _bit(status, "P103_RUN")) and (_bit(status, "O_XV_ENVASE") or _bit(status, "XV_ENVASE"))
        for tag in ("tubo_env_mid", "tubo_env_out"):
            self.itemconfig(self.itens[tag], fill=COR_TUBO_ATIVO if envasando else COR_TUBO)

        # --- lâmpadas gerais ---
        self.itemconfig(self.itens["pl_auto"], fill=self._cor(_bit(status, "O_PL_AUTO") or _bit(status, "PL_AUTO")))
        self.itemconfig(self.itens["pl_cip"], fill=self._cor(_bit(status, "O_PL_CIP") or _bit(status, "PL_CIP")))
        self.itemconfig(self.itens["pl_falha"], fill=self._cor(False, alarme=_bit(status, "O_PL_FALHA") or _bit(status, "PL_FALHA")))
        self.itemconfig(self.itens["alm_horn"], fill=self._cor(False, alarme=_bit(status, "O_ALM_HORN") or _bit(status, "ALM_HORN")))

        # --- instrumentação CIP / qualidade ---
        self.itemconfig(self.itens["pt101"], text=f"{_num(status,'IA_PT101', _num(status,'PT101',0.0)):.2f}")
        self.itemconfig(self.itens["ait101"], text=f"{_num(status,'IA_AIT101', _num(status,'AIT101',0.0)):.2f}")
        self.itemconfig(self.itens["ait102"], text=f"{_num(status,'IA_AIT102', _num(status,'AIT102',0.0)):.0f}")
        self.itemconfig(self.itens["ait103"], text=f"{_num(status,'IA_AIT103', _num(status,'AIT103',0.0)):.1f}")

        # --- estado da máquina ---
        estado = status.get("estado_auto", "—") or "—"
        subestado = status.get("estado_cip", "") or ""
        self.itemconfig(self.itens["estado_txt"], text=estado,
                         fill=COR_ALARME if estado in ("FALHA", "EMG") else COR_TEXTO)
        self.itemconfig(self.itens["subestado_txt"], text=subestado)


# ==================================================================== ====
class SupervisorApp(ctk.CTk):
    def __init__(self, caminho_json=PAINEL_PADRAO, caminho_csv=CSV_PADRAO):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title("Supervisório — Simulador CLP (PROB_01)")
        self.geometry("1180x700")
        self.minsize(1080, 640)

        self.caminho_json, self.caminho_csv = resolver_caminhos(caminho_json, caminho_csv)
        self.dados = carregar_painel(self.caminho_json)

        self._vars = {}
        self._montar_layout()
        self._sincronizar_controles()
        self.after(400, self._refresh_loop)

    # ---------------------------------------------------------------- UI --
    def _montar_layout(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        self.configure(fg_color=COR_FUNDO)

        # ------ Diagrama (esquerda, ocupa a maior parte da tela) ------
        frame_diagrama = ctk.CTkFrame(self, fg_color=COR_FUNDO)
        frame_diagrama.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(12, 6), pady=12)
        self.diagrama = DiagramaProcesso(frame_diagrama)
        self.diagrama.pack(padx=8, pady=8, fill="both", expand=True)

        # ------ Painel de controle (direita) ------
        painel = ctk.CTkScrollableFrame(self, width=360, fg_color="#1a1f25")
        painel.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(6, 12), pady=12)
        painel.grid_columnconfigure(0, weight=1)
        painel.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(painel, text="Comandos do operador", font=ctk.CTkFont(size=16, weight="bold"), text_color=COR_TEXTO).grid(
            row=0, column=0, columnspan=2, padx=12, pady=(12, 8), sticky="w")

        ctk.CTkButton(painel, text="▶  Iniciar (START)", fg_color="#2fa572", hover_color="#248a5d",
                      command=lambda: self._pulso("PB_START")).grid(row=1, column=0, columnspan=2, padx=12, pady=5, sticky="ew")
        ctk.CTkButton(painel, text="■  Parar (STOP)", fg_color="#c95f3b", hover_color="#a54a2f",
                      command=lambda: self._pulso("PB_STOP")).grid(row=2, column=0, columnspan=2, padx=12, pady=5, sticky="ew")
        ctk.CTkButton(painel, text="⟲  Rearmar falha (RESET)", fg_color="#4a6ea9", hover_color="#355b86",
                      command=lambda: self._pulso("PB_RESET")).grid(row=3, column=0, columnspan=2, padx=12, pady=5, sticky="ew")

        self._vars["PB_EMG_ACIONADO"] = tk.BooleanVar(value=bool(self.dados.get("PB_EMG_ACIONADO", False)))
        self._vars["HABILITA_MANUAL"] = tk.BooleanVar(value=bool(self.dados.get("HABILITA_MANUAL", False)))
        ctk.CTkSwitch(painel, text="Botão de emergência (parada total)", variable=self._vars["PB_EMG_ACIONADO"],
                      progress_color="#c94b4b",
                      command=lambda: self._salvar_variavel("PB_EMG_ACIONADO")).grid(
            row=4, column=0, columnspan=2, padx=12, pady=(10, 4), sticky="w")
        ctk.CTkSwitch(painel, text="Modo manual (libera os comandos abaixo)", variable=self._vars["HABILITA_MANUAL"],
                      command=lambda: self._salvar_variavel("HABILITA_MANUAL")).grid(
            row=5, column=0, columnspan=2, padx=12, pady=4, sticky="w")

        ctk.CTkLabel(painel, text="Receita do lote", font=ctk.CTkFont(size=14, weight="bold"), text_color=COR_TEXTO).grid(
            row=6, column=0, columnspan=2, padx=12, pady=(14, 4), sticky="w")
        self.receita_var = tk.StringVar(value=self._receita_label(self.dados.get("SEL_RECEITA", 0)))
        ctk.CTkSegmentedButton(painel, values=["Sabão", "Detergente"],
                               variable=self.receita_var, command=self._salvar_receita).grid(
            row=7, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="ew")

        ctk.CTkLabel(painel, text="Comandos manuais", font=ctk.CTkFont(size=14, weight="bold"), text_color=COR_TEXTO).grid(
            row=8, column=0, columnspan=2, padx=12, pady=(6, 0), sticky="w")
        ctk.CTkLabel(painel, text="(só têm efeito com o modo manual ligado)", font=ctk.CTkFont(size=10),
                     text_color=COR_TEXTO_FRACO).grid(row=9, column=0, columnspan=2, padx=12, pady=(0, 4), sticky="w")
        # nomes completos, um comando por linha, para não truncar/confundir
        manual_keys = [
            ("MAN_XV_CARGA", "Válvula de carga (XV_CARGA)"),
            ("MAN_XV101", "Válvula de transferência (XV101)"),
            ("MAN_P101", "Bomba de transferência (P-101)"),
            ("MAN_AG101", "Agitador (AG-101)"),
            ("MAN_XV_ENVASE", "Válvula de envase (XV_ENVASE)"),
            ("MAN_P103", "Bomba de envase (P-103)"),
        ]
        for idx, (key, label) in enumerate(manual_keys):
            var = tk.BooleanVar(value=bool(self.dados.get(key, False)))
            self._vars[key] = var
            row = 10 + idx
            ctk.CTkCheckBox(painel, text=label, variable=var,
                             command=lambda k=key: self._salvar_variavel(k)).grid(
                row=row, column=0, columnspan=2, padx=12, pady=6, sticky="w")

        ctk.CTkLabel(painel, text="Simular falha de sensor (bancada de teste)",
                     font=ctk.CTkFont(size=13, weight="bold"), text_color=COR_TEXTO).grid(
            row=16, column=0, columnspan=2, padx=12, pady=(14, 0), sticky="w")
        ctk.CTkLabel(painel, text="Remove o sinal de retorno da bomba, para testar a lógica de FALHAS",
                     font=ctk.CTkFont(size=10), text_color=COR_TEXTO_FRACO, wraplength=320, justify="left").grid(
            row=17, column=0, columnspan=2, padx=12, pady=(0, 4), sticky="w")
        falha_keys = [
            ("forcar_falha_FL_P101", "Bomba P-101 sem sinal de retorno"),
            ("forcar_falha_FL_P103", "Bomba P-103 sem sinal de retorno"),
            ("forcar_falha_FL_P104", "Bomba P-104 sem sinal de retorno"),
            ("forcar_falha_FL_P105", "Bomba P-105 sem sinal de retorno"),
        ]
        for idx, (key, label) in enumerate(falha_keys):
            var = tk.BooleanVar(value=bool(self.dados.get(key, False)))
            self._vars[key] = var
            row = 18 + idx
            ctk.CTkCheckBox(painel, text=label, fg_color="#c95f3b", hover_color="#a54a2f",
                             variable=var, command=lambda k=key: self._salvar_variavel(k)).grid(
                row=row, column=0, columnspan=2, padx=12, pady=6, sticky="w")

        ctk.CTkLabel(painel, text="Status", font=ctk.CTkFont(size=14, weight="bold"), text_color=COR_TEXTO).grid(
            row=23, column=0, columnspan=2, padx=12, pady=(16, 4), sticky="w")
        self.status_var = tk.StringVar(value="Aguardando dados do CSV...")
        self.receita_status_var = tk.StringVar(value="Receita: --")
        self.seguranca_var = tk.StringVar(value="Segurança: OK")
        self.etapa_var = tk.StringVar(value="Etapa: --")
        self.tempo_restante_var = tk.StringVar(value="Tempo restante: --")
        ctk.CTkLabel(painel, textvariable=self.status_var, justify="left", anchor="w",
                     wraplength=320).grid(row=24, column=0, columnspan=2, padx=12, pady=(0, 6), sticky="w")
        ctk.CTkLabel(painel, textvariable=self.etapa_var, justify="left", anchor="w",
                     wraplength=320).grid(row=25, column=0, columnspan=2, padx=12, pady=(0, 4), sticky="w")
        ctk.CTkLabel(painel, textvariable=self.receita_status_var, justify="left", anchor="w",
                     wraplength=320).grid(row=26, column=0, columnspan=2, padx=12, pady=(0, 4), sticky="w")
        ctk.CTkLabel(painel, textvariable=self.tempo_restante_var, justify="left", anchor="w",
                     wraplength=320).grid(row=27, column=0, columnspan=2, padx=12, pady=(0, 4), sticky="w")
        ctk.CTkLabel(painel, textvariable=self.seguranca_var, justify="left", anchor="w",
                     wraplength=320).grid(row=28, column=0, columnspan=2, padx=12, pady=(0, 8), sticky="w")
        self.alarmes_var = tk.StringVar(value="Sem alarmes")
        self.timer_var = tk.StringVar(value="Mistura: --")
        self.progress_var = tk.DoubleVar(value=0.0)

        ctk.CTkLabel(painel, text="Timer de mistura", font=ctk.CTkFont(size=13, weight="bold"), text_color=COR_TEXTO).grid(
            row=29, column=0, columnspan=2, padx=12, pady=(8, 4), sticky="w")
        ctk.CTkLabel(painel, textvariable=self.timer_var, text_color=COR_TEXTO).grid(
            row=30, column=0, columnspan=2, padx=12, pady=(0, 4), sticky="w")
        self.progress_bar = ctk.CTkProgressBar(painel, variable=self.progress_var, width=320)
        self.progress_bar.grid(row=31, column=0, columnspan=2, padx=12, pady=(0, 10), sticky="ew")
        ctk.CTkLabel(painel, textvariable=self.alarmes_var, justify="left", anchor="w",
                     text_color="#d9483d", wraplength=320).grid(
            row=32, column=0, columnspan=2, padx=12, pady=(0, 10), sticky="w")

    # ---------------------------------------------------------- ações ----
    def _salvar_variavel(self, chave):
        self.dados[chave] = bool(self._vars[chave].get())
        salvar_painel(self.dados, self.caminho_json)

    def _receita_label(self, valor):
        return "Sabão" if int(valor) == 0 else "Detergente"

    def _salvar_receita(self, valor):
        self.dados["SEL_RECEITA"] = 0 if valor.strip() == "Sabão" else 1
        salvar_painel(self.dados, self.caminho_json)

    def _pulso(self, chave):
        self.dados[chave] = True
        salvar_painel(self.dados, self.caminho_json)
        self.after(200, self._sincronizar_controles)

    def _timer_mistura(self, status: dict) -> dict:
        acc = _num(status, "T_T_MISTURA_ACC", 0.0)
        pre = _num(status, "N_N_T_MIX", _num(status, "N_T_MIX", 300.0))
        pre = pre if pre > 0 else 300.0
        progresso = max(0.0, min(1.0, acc / pre if pre else 0.0))
        return {"acc": acc, "pre": pre, "progresso": progresso}

    def _sincronizar_controles(self):
        self.dados = carregar_painel(self.caminho_json)
        for chave, var in self._vars.items():
            var.set(bool(self.dados.get(chave, False)))
        self.receita_var.set(self._receita_label(self.dados.get("SEL_RECEITA", 0)))

    # ------------------------------------------------------ atualização --
    def _refresh_loop(self):
        self._sincronizar_controles()
        status = ler_status_csv(self.caminho_csv)
        if status:
            self.diagrama.atualizar(status)
            scan = status.get("scan", "?")
            lote = status.get("N_N_LOTE_CTR", status.get("N_LOTE_CTR", "?"))
            self.status_var.set(
                f"scan={scan}  |  lotes concluídos={lote}\n"
                f"estado={status.get('estado_auto','?')}  cip={status.get('estado_cip','') or '-'}"
            )
            self.etapa_var.set(f"Etapa: {status.get('etapa', status.get('estado_auto','-'))}")
            self.receita_status_var.set(f"Receita: {status.get('receita', '-')}  |  Lote: {status.get('lote_id', '-')}" )
            self.seguranca_var.set(
                "Segurança: OK" if not any(_bit(status, k) for k in ("B3_EST_FALHA", "B3_EST_EMG")) else "Segurança: TRAVADO"
            )
            restante = _num(status, "T_T_MISTURA_ACC", 0.0)
            pre = _num(status, "N_N_T_MIX", _num(status, "N_T_MIX", 300.0))
            if pre > 0:
                restante = max(0.0, pre - restante)
                self.tempo_restante_var.set(f"Tempo restante: {restante:.1f}s")
            else:
                self.tempo_restante_var.set("Tempo restante: --")

            if status.get("estado_auto") == "MISTURA" or status.get("estado_auto") == "EST_MISTURA":
                timer = self._timer_mistura(status)
                self.timer_var.set(f"Mistura: {timer['acc']:.1f}s / {timer['pre']:.1f}s")
                self.progress_var.set(timer['progresso'])
            else:
                self.timer_var.set("Mistura: aguardando etapa")
                self.progress_var.set(0.0)
            ativos = [k.replace("ALM_", "") for k in status
                      if k.startswith("ALM_") and _bit(status, k)]
            self.alarmes_var.set("Alarmes: " + (", ".join(ativos) if ativos else "nenhum"))
        else:
            self.status_var.set("output/estado_atual.csv ainda não foi criado.\nInicie main.py.")
        self.after(400, self._refresh_loop)


def main():
    ap = argparse.ArgumentParser(description="Supervisório visual (P&ID) do simulador de CLP")
    ap.add_argument("--caminho-json", default=None)
    ap.add_argument("--caminho-csv", default=None)
    ap.add_argument("--saida", default="output", help="Pasta de saída usada pelo main.py")
    args = ap.parse_args()
    caminho_json, caminho_csv = resolver_caminhos(args.caminho_json, args.caminho_csv, args.saida)
    app = SupervisorApp(caminho_json, caminho_csv)
    app.mainloop()


if __name__ == "__main__":
    main()