# -*- coding: utf-8 -*-
"""
modules/qualidade.py  (sub-rotina QUALIDADE)
Responsabilidade: validação analógica.
Conteúdo: pH, condutividade, turbidez, LT103 (antes/depois do envase).
"""

_LIMITE_TURBIDEZ_NTU = 20.0
_LIMITE_COND_US_CM = 200.0
_LT103_MIN_PRODUTO_L = 200.0   # acima disso considera "produto disponível"
_LT103_BAIXO_L = 50.0          # abaixo disso considera tanque esvaziado


def executar(plc):
    IA, B3, ALM = plc.IA, plc.B3, plc.ALM

    B3["PH_OK"] = 1 if 6.5 <= IA["AIT101"] <= 8.0 else 0
    B3["CONDUTIVIDADE_OK"] = 1 if IA["AIT102"] < _LIMITE_COND_US_CM else 0
    B3["TURBIDEZ_OK"] = 1 if IA["AIT103"] < _LIMITE_TURBIDEZ_NTU else 0

    B3["ENVASE_PRODUTO_OK"] = 1 if IA["LT103"] > _LT103_MIN_PRODUTO_L else 0
    B3["ENVASE_VAZIO"] = 1 if IA["LT103"] < _LT103_BAIXO_L else 0

    # Alarmes médios de qualidade, só monitorados durante a etapa relevante (CIP_E6)
    if B3.get("CIP_E6"):
        ALM["ALM_PH_FORA"] = 0 if B3["PH_OK"] else 1
        ALM["ALM_COND_ALTA"] = 0 if B3["CONDUTIVIDADE_OK"] else 1
        ALM["ALM_TURB_ALTA"] = 0 if B3["TURBIDEZ_OK"] else 1
    else:
        ALM["ALM_PH_FORA"] = 0
        ALM["ALM_COND_ALTA"] = 0
        ALM["ALM_TURB_ALTA"] = 0

    if B3["EST_ENVASE"] and B3["ENVASE_VAZIO"]:
        ALM["ALM_ENVASE_SECO"] = 1
    elif not B3["EST_ENVASE"]:
        ALM["ALM_ENVASE_SECO"] = 0

    if B3["EST_CARGA"] and plc.I["LS_TK101_H"]:
        ALM["ALM_NIVEL_H"] = 1
    else:
        ALM["ALM_NIVEL_H"] = 0

    if B3["EST_MISTURA"] and not plc.I["LS_TK101_L"]:
        ALM["ALM_NIVEL_L"] = 1
    else:
        ALM["ALM_NIVEL_L"] = 0

    ALM["ALM_CIP_PEND"] = 0 if B3["CIP_FEITO"] else 1
