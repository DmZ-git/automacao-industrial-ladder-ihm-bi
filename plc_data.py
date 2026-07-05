# -*- coding: utf-8 -*-
"""
plc_data.py
Data table central do CLP simulado — equivalente aos arquivos de dados do RSLogix 500
(I:0, O:0, I:1/O:1 analógicos, B3, T4, N7), montado a partir da Lista_IO_v4.

Todas as sub-rotinas recebem esta mesma instância (PLCDataTable) e leem/escrevem
nela, exatamente como rungs de ladder leem/escrevem no mesmo data table físico do CLP.
"""

import time
from timer import Timer


class PLCDataTable:
    def __init__(self):
        # ------------------------------------------------------------------
        # ENTRADAS DIGITAIS (I:0) — ver aba "Entradas Digitais"
        # ------------------------------------------------------------------
        self.I = {
            "PB_START": 0,
            "PB_STOP": 0,
            "PB_EMG": 1,        # contato NF -> 1 = normal (não pressionado), 0 = emergência
            "PB_RESET": 0,
            "SEL_RECEITA": 0,   # 0 = Sabão | 1 = Detergente
            "LS_TK101_H": 0,
            "LS_TK101_L": 0,
            "FL_P101": 0,
            "FL_P103": 0,
            "FL_P104": 0,
            "FL_P105": 0,
            "AL_MOTOR_P101": 0,
            "AL_MOTOR_P103": 0,
            "AL_MOTOR_P104": 0,
            "AL_MOTOR_P105": 0,
            "AL_MOTOR_AG": 0,
        }

        # ------------------------------------------------------------------
        # ENTRADAS ANALÓGICAS (I:1 / I:2) — engenharia já convertida
        # ------------------------------------------------------------------
        self.IA = {
            "LT101": 0.0,   # Nível TK-101, 0-1500 L
            "TT102": 25.0,  # Temperatura TK-102, 0-120 C
            "FT101": 0.0,   # Vazão de transferência, 0-200 L/min
            "FT201": 0.0,   # Vazão de envase, 0-120 L/min
            "PT101": 0.0,   # Pressão linha CIP, 0-6 bar
            "AIT101": 7.0,  # pH do produto, 0-14
            "AIT102": 0.0,  # Condutividade retorno CIP, uS/cm
            "AIT103": 0.0,  # Turbidez retorno CIP, NTU
            "LT103": 0.0,   # Nível TK-103 (envase), 0-2500 L
        }

        # ------------------------------------------------------------------
        # SAÍDAS DIGITAIS (O:0 / O:2)
        # ------------------------------------------------------------------
        self.O = {
            "P101_RUN": 0,
            "P103_RUN": 0,
            "AG101_RUN": 0,
            "XV_CARGA": 0,
            "XV101": 0,
            "HEAT101": 0,
            "ALM_HORN": 0,
            "PL_AUTO": 0,
            "PL_CIP": 0,
            "PL_FALHA": 0,
            "P104_RUN": 0,
            "P105_RUN": 0,
            "XV_DRENO": 0,
            "XV_CIP_01": 0,
            "XV_CIP_02": 0,
            "XV102": 0,
            "XV_ENVASE": 0,
        }

        # ------------------------------------------------------------------
        # SAÍDAS ANALÓGICAS (O:1) — 0 a 100 %
        # ------------------------------------------------------------------
        self.OA = {
            "TV101": 0.0,
            "FV101": 0.0,
            "AG101_SPD": 0.0,
        }

        # ------------------------------------------------------------------
        # MEMÓRIAS INTERNAS (B3) — bits de estado/controle
        # ------------------------------------------------------------------
        self.B3 = {
            # ciclo produtivo E0..E7
            "EST_PARADO": 1,
            "EST_RECEITA": 0,
            "EST_CARGA": 0,
            "EST_MISTURA": 0,
            "EST_TRANSF": 0,
            "EST_ENVASE": 0,
            "EST_CIP": 0,
            "EST_FINAL": 0,
            # segurança
            "EST_EMG": 0,
            "EST_FALHA": 0,
            # sub-estados CIP
            "CIP_E1": 0, "CIP_E2": 0, "CIP_E3": 0, "CIP_E4": 0,
            "CIP_E5": 0, "CIP_E6": 0, "CIP_E7": 0,
            # controle/monitoramento
            "SEL_RECEITA_BIT": 0,
            "CIP_FEITO": 1,
            "FALHA_LATCHED": 0,
            "PERMISSIVOS_OK": 1,
            "PH_OK": 0,
            "CONDUTIVIDADE_OK": 0,
            "ENVASE_PRODUTO_OK": 0,
            "ENVASE_VAZIO": 1,
            "TURBIDEZ_OK": 0,
            "MODO_MANUAL": 0,
            # manual (B3:3)
            "HABILITA_MANUAL": 0,
            "MAN_P101": 0,
            "MAN_AG101": 0,
            "MAN_XV101": 0,
            "MAN_P103": 0,
            "MAN_XV_ENVASE": 0,
            "MAN_XV_CARGA": 0,
        }

        # ------------------------------------------------------------------
        # INTEIROS (N7)
        # ------------------------------------------------------------------
        self.N = {
            "N_T_CARGA": 120,
            "N_T_MIX": 300,
            "N_T_TRANSF": 90,
            "N_T_ENV": 180,
            "N_VEL_AGIT": 16384,
            "N_LOTE_CTR": 0,
            "N_ALM_CTR": 0,
        }

        # Presets por receita (0 = Sabão, 1 = Detergente), conforme aba "Inteiros"
        # tupla = (Sabão, Detergente)
        self._presets_receita = {
            "N_T_CARGA": (150, 120),
            "N_T_MIX": (420, 300),
            "N_T_TRANSF": (120, 90),
            "N_T_ENV": (210, 180),
            "N_VEL_AGIT": (26214, 16384),  # Sabão=80%, Detergente=50%
        }

        # ------------------------------------------------------------------
        # TEMPORIZADORES (T4) — base 1.0 s
        # ------------------------------------------------------------------
        self.T = {
            "T_CARGA": Timer(pre=120, tag="T4:0"),
            "T_MISTURA": Timer(pre=300, tag="T4:1"),
            "T_TRANSF": Timer(pre=90, tag="T4:2"),
            "T_ENVASE": Timer(pre=180, tag="T4:3"),
            "T_CIP_E1": Timer(pre=30, tag="T4:4"),
            "T_CIP_E2": Timer(pre=60, tag="T4:5"),
            "T_CIP_E3": Timer(pre=180, tag="T4:6"),
            "T_CIP_E4": Timer(pre=120, tag="T4:7"),
            "T_CIP_E5": Timer(pre=90, tag="T4:8"),
            "T_CIP_E6": Timer(pre=20, tag="T4:9"),
            "T_ANTIREARME": Timer(pre=5, tag="T4:10"),
            "T_CONFIRM_NV": Timer(pre=3, tag="T4:11"),
            "T_FALHA_P101": Timer(pre=3, tag="T4:12"),
            "T_FALHA_P103": Timer(pre=3, tag="T4:13"),
            "T_FALHA_P104": Timer(pre=3, tag="T4:14"),
            "T_FALHA_P105": Timer(pre=3, tag="T4:15"),
        }

        # ------------------------------------------------------------------
        # ALARMES (aba "Alarmes")
        # ------------------------------------------------------------------
        self.ALM = {
            "ALM_EMG": 0,
            "ALM_SOBREPRESSAO": 0,
            "ALM_FALHA_P101": 0,
            "ALM_FALHA_P103": 0,
            "ALM_FALHA_P104": 0,
            "ALM_FALHA_P105": 0,
            "ALM_FALHA_AG": 0,
            "ALM_NIVEL_H": 0,
            "ALM_NIVEL_L": 0,
            "ALM_ENVASE_SECO": 0,
            "ALM_PH_FORA": 0,
            "ALM_COND_ALTA": 0,
            "ALM_TURB_ALTA": 0,
            "ALM_CIP_PEND": 0,
        }
        self._alm_prev = dict(self.ALM)  # para detectar borda de subida (EVENTOS)

        # ------------------------------------------------------------------
        # Controle de varredura / rastreabilidade
        # ------------------------------------------------------------------
        self.primeira_varredura = True
        self.scan_count = 0
        self.scan_time = 1.0          # s, igual à base dos timers (1.0 s)
        self.timestamp = time.time()
        self.estado_cip_atual = None  # 'CIP_E1'..'CIP_E7' ou None
        self.pulso_lote_concluido = False  # setado por AUTO, consumido por EVENTOS
        self.lote_atual = 0
        self.lote_inicio_ts = None
        self.lote_duracao_s = 0.0
        self.receita_nome = "Sabão"
        self.etapa_atual = "Parado"
        self.etapa_inicio_ts = None
        self.etapa_inicio_scan = 0
        self.etapa_duracao_s = 0.0
        self.etapa_fim_ts = None
        self.historico_etapas = []

    def definir_receita_nome(self):
        self.receita_nome = "Detergente" if self.receita_atual() else "Sabão"

    def iniciar_lote(self):
        self.lote_atual += 1
        self.lote_inicio_ts = time.time()
        self.lote_duracao_s = 0.0
        self.etapa_atual = "Parado"
        self.etapa_inicio_ts = None
        self.etapa_inicio_scan = self.scan_count
        self.etapa_duracao_s = 0.0
        self.etapa_fim_ts = None
        self.historico_etapas = []
        self.definir_receita_nome()

    def registrar_etapa(self, etapa, receita=None):
        agora = time.time()
        if receita is not None:
            self.receita_nome = receita
        if self.etapa_atual != etapa:
            if self.etapa_atual and self.etapa_inicio_ts is not None:
                self.historico_etapas.append({
                    "etapa": self.etapa_atual,
                    "inicio": self.etapa_inicio_ts,
                    "fim": agora,
                    "duracao_s": round(agora - self.etapa_inicio_ts, 3),
                    "scan_inicio": self.etapa_inicio_scan,
                    "scan_fim": self.scan_count,
                    "receita": self.receita_nome,
                })
            self.etapa_atual = etapa
            self.etapa_inicio_ts = agora
            self.etapa_inicio_scan = self.scan_count
            self.etapa_duracao_s = 0.0
            self.etapa_fim_ts = None
        else:
            self.etapa_duracao_s = agora - self.etapa_inicio_ts if self.etapa_inicio_ts else 0.0
        return self.etapa_atual

    def finalizar_lote(self):
        agora = time.time()
        if self.lote_inicio_ts is not None:
            self.lote_duracao_s = agora - self.lote_inicio_ts
        self.etapa_fim_ts = agora
        self.etapa_duracao_s = agora - self.etapa_inicio_ts if self.etapa_inicio_ts else 0.0

    def receita_atual(self):
        """0 = Sabão | 1 = Detergente"""
        return 1 if self.B3["SEL_RECEITA_BIT"] else 0
