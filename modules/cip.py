# -*- coding: utf-8 -*-
"""
modules/cip.py  (sub-rotina CIP)
Responsabilidade: limpeza automática.
Conteúdo: sub-estados CIP_E1..E7; validação condutividade + pH + turbidez.
Só roda quando o AUTO está em E6 (EST_CIP).
"""

_SUBESTADOS = ("CIP_E1", "CIP_E2", "CIP_E3", "CIP_E4", "CIP_E5", "CIP_E6", "CIP_E7")


def _ir_para(plc, sub_alvo):
    for e in _SUBESTADOS:
        plc.B3[e] = 1 if e == sub_alvo else 0
    plc.estado_cip_atual = sub_alvo
    plc.registrar_etapa(f"CIP::{sub_alvo}", receita=plc.receita_nome)


def _desligar_atuadores_cip(plc):
    for tag in ("XV_DRENO", "P103_RUN", "XV_CIP_01", "P105_RUN",
                "XV_CIP_02", "P104_RUN", "HEAT101", "XV102"):
        plc.O[tag] = 0


def _resetar_tanques_e_sensores(plc):
    """Deixa a planta pronta para a próxima receita após o CIP."""
    plc.IA["LT101"] = 0.0
    plc.IA["LT103"] = 0.0
    plc.IA["TT102"] = 25.0
    plc.IA["FT101"] = 0.0
    plc.IA["FT201"] = 0.0
    plc.IA["PT101"] = 0.0
    plc.IA["AIT101"] = 7.0
    plc.IA["AIT102"] = 0.0
    plc.IA["AIT103"] = 0.0

    plc.I["LS_TK101_H"] = 0
    plc.I["LS_TK101_L"] = 0

    plc.B3["ENVASE_VAZIO"] = 1
    plc.B3["ENVASE_PRODUTO_OK"] = 0
    plc.B3["PH_OK"] = 0
    plc.B3["CONDUTIVIDADE_OK"] = 0
    plc.B3["TURBIDEZ_OK"] = 0


def executar(plc, dt=None):
    dt = plc.scan_time if dt is None else dt
    B3, T = plc.B3, plc.T

    if not B3["EST_CIP"]:
        return  # AUTO não está em E6; nada a fazer

    if plc.estado_cip_atual is None:
        B3["CIP_FEITO"] = 0  # inicia limpeza: lote só pode reiniciar após concluir
        _ir_para(plc, "CIP_E1")

    # ---- CIP_E1: drenagem inicial (XV_DRENO + P103), 30s ----
    if B3["CIP_E1"]:
        if T["T_CIP_E1"].tick(True, dt):
            T["T_CIP_E1"].reset()
            _ir_para(plc, "CIP_E2")
        return

    # ---- CIP_E2: enxágue primário (P105 + XV_CIP_01), 60s ----
    if B3["CIP_E2"]:
        if T["T_CIP_E2"].tick(True, dt):
            T["T_CIP_E2"].reset()
            _ir_para(plc, "CIP_E3")
        return

    # ---- CIP_E3: circulação alcalina (P104 + XV_CIP_02), 180s ----
    if B3["CIP_E3"]:
        if T["T_CIP_E3"].tick(True, dt):
            T["T_CIP_E3"].reset()
            _ir_para(plc, "CIP_E4")
        return

    # ---- CIP_E4: recirculação quente (P105 + HEAT101), 120s ----
    if B3["CIP_E4"]:
        if T["T_CIP_E4"].tick(True, dt):
            T["T_CIP_E4"].reset()
            _ir_para(plc, "CIP_E5")
        return

    # ---- CIP_E5: enxágue final (P105), 90s ----
    if B3["CIP_E5"]:
        if T["T_CIP_E5"].tick(True, dt):
            T["T_CIP_E5"].reset()
            _ir_para(plc, "CIP_E6")
        return

    # ---- CIP_E6: validação química (cond + pH + turbidez), estabiliza 20s ----
    if B3["CIP_E6"]:
        validado = B3["PH_OK"] and B3["CONDUTIVIDADE_OK"] and B3["TURBIDEZ_OK"]
        if T["T_CIP_E6"].tick(validado, dt):
            T["T_CIP_E6"].reset()
            _ir_para(plc, "CIP_E7")
        return

    # ---- CIP_E7: liberação ----
    if B3["CIP_E7"]:
        B3["CIP_FEITO"] = 1
        for e in _SUBESTADOS:
            B3[e] = 0
        _desligar_atuadores_cip(plc)
        _resetar_tanques_e_sensores(plc)
        plc.estado_cip_atual = None
        return
