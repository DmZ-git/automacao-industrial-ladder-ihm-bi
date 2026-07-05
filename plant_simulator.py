# -*- coding: utf-8 -*-
"""
plant_simulator.py
Não faz parte do ladder original — é o "processo físico" que substitui o
hardware real (tanques, bombas, sensores) para a simulação poder rodar
sem CLP/campo de verdade. Traduz o estado das saídas do scan anterior em
novas entradas digitais/analógicas para o próximo scan.
"""

import random


class PlantSimulator:
    def __init__(self, plc):
        self.plc = plc
        # capacidades/parâmetros físicos simplificados
        self.vazao_carga_l_s = 15.0     # L/s enchendo TK-101
        self.vazao_transf_l_s = 8.0     # L/s TK-101 -> TK-102/TK-103
        self.vazao_envase_l_s = 3.0     # L/s esvaziando TK-103
        self.forcar_falha = {           # injeção de falha manual (via painel do operador)
            "FL_P101": False, "FL_P103": False, "FL_P104": False, "FL_P105": False,
        }

    def atualizar_entradas(self, dt):
        """Lê o estado atual das saídas (scan anterior) e atualiza sensores/feedbacks."""
        O, I, IA = self.plc.O, self.plc.I, self.plc.IA

        # --- Nível TK-101 (LT101) ---
        if O["XV_CARGA"]:
            IA["LT101"] = min(1500.0, IA["LT101"] + self.vazao_carga_l_s * dt)
        if O["P101_RUN"] and O["XV101"]:
            IA["LT101"] = max(0.0, IA["LT101"] - self.vazao_transf_l_s * dt)
            IA["FT101"] = 60.0  # L/min nominal enquanto transferindo
        else:
            IA["FT101"] = 0.0

        I["LS_TK101_H"] = 1 if IA["LT101"] >= 1400.0 else 0
        I["LS_TK101_L"] = 1 if IA["LT101"] >= 100.0 else 0

        # --- Nível TK-103 / envase (LT103) ---
        if O["P101_RUN"] and O["XV101"]:
            IA["LT103"] = min(2500.0, IA["LT103"] + self.vazao_transf_l_s * dt)
        if O["P103_RUN"] and O["XV_ENVASE"]:
            IA["LT103"] = max(0.0, IA["LT103"] - self.vazao_envase_l_s * dt)
            IA["FT201"] = 40.0
        else:
            IA["FT201"] = 0.0

        # --- Feedback das bombas: espelha o comando, salvo falha forçada ---
        I["FL_P101"] = 0 if self.forcar_falha["FL_P101"] else O["P101_RUN"]
        I["FL_P103"] = 0 if self.forcar_falha["FL_P103"] else O["P103_RUN"]
        I["FL_P104"] = 0 if self.forcar_falha["FL_P104"] else O["P104_RUN"]
        I["FL_P105"] = 0 if self.forcar_falha["FL_P105"] else O["P105_RUN"]

        # --- CIP: pressão, pH, condutividade, turbidez evoluindo em direção ao alvo ---
        alvo_pressao = 2.5 if (O["P104_RUN"] or O["P105_RUN"]) else 0.0
        IA["PT101"] += (alvo_pressao - IA["PT101"]) * min(1.0, dt / 5.0)

        if self.plc.B3.get("CIP_E5") or self.plc.B3.get("CIP_E6"):
            IA["AIT101"] += (7.0 - IA["AIT101"]) * min(1.0, dt / 15.0)
            IA["AIT102"] += (100.0 - IA["AIT102"]) * min(1.0, dt / 15.0)
            IA["AIT103"] += (5.0 - IA["AIT103"]) * min(1.0, dt / 15.0)
        elif self.plc.B3.get("CIP_E3"):
            IA["AIT101"] = 11.0  # solução alcalina em circulação
            IA["AIT102"] = 3000.0
            IA["AIT103"] = 80.0

        # --- Temperatura TK-102 sobe levemente durante recirculação quente (CIP_E4) ---
        if O["HEAT101"]:
            IA["TT102"] = min(80.0, IA["TT102"] + 5.0 * dt)
        else:
            IA["TT102"] += (25.0 - IA["TT102"]) * min(1.0, dt / 30.0)

        # ruído de instrumentação, só para não ficar "morto" no CSV
        for tag in ("PT101", "AIT101", "AIT102", "AIT103", "TT102"):
            IA[tag] = max(0.0, IA[tag] + random.uniform(-0.01, 0.01))

    def aplicar_saidas(self, dt):
        """Ponto de extensão para efeitos que dependam das saídas já calculadas neste scan."""
        pass
