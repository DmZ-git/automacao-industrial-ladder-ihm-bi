# -*- coding: utf-8 -*-
"""
modules/saidas.py  (sub-rotina SAIDAS)
Responsabilidade: acionamento de atuadores.
Conteúdo: todas as saídas com fail-safe (XIO EMG/FALHA).
É a ÚLTIMA sub-rotina lógica antes de aplicar na planta: nenhuma outra
sub-rotina deve escrever diretamente em plc.O — só esta.
"""


def executar(plc):
    I, O, OA, B3 = plc.I, plc.O, plc.OA, plc.B3

    seguro = bool(B3["PERMISSIVOS_OK"])  # XIO(EMG) . XIO(FALHA) equivalente

    if not seguro:
        for k in O:
            O[k] = 0
        for k in OA:
            OA[k] = 0.0
        O["ALM_HORN"] = 1  # sirene continua podendo soar mesmo sem permissivos
        O["PL_FALHA"] = 1 if B3["EST_FALHA"] else 0
        return

    manual = B3["MODO_MANUAL"]

    # -------- Processo --------
    O["XV_CARGA"] = 1 if (manual and B3["MAN_XV_CARGA"]) or (not manual and B3["EST_CARGA"]) else 0

    O["XV101"] = 1 if (manual and B3["MAN_XV101"]) or (not manual and B3["EST_TRANSF"]) else 0
    O["P101_RUN"] = 1 if O["XV101"] and (
        (manual and B3["MAN_P101"]) or (not manual and B3["EST_TRANSF"])
    ) else 0

    O["AG101_RUN"] = 1 if I["LS_TK101_L"] and (
        (manual and B3["MAN_AG101"]) or (not manual and B3["EST_MISTURA"])
    ) else 0
    receita = plc.receita_atual()
    OA["AG101_SPD"] = (80.0 if receita == 0 else 50.0) if O["AG101_RUN"] else 0.0

    O["XV_ENVASE"] = 1 if (manual and B3["MAN_XV_ENVASE"]) or (not manual and B3["EST_ENVASE"]) else 0
    O["P103_RUN"] = 1 if O["XV_ENVASE"] and (
        (manual and B3["MAN_P103"]) or (not manual and B3["EST_ENVASE"] and not B3["ENVASE_VAZIO"])
    ) else 0

    # -------- CIP --------
    O["XV_DRENO"] = 1 if B3["CIP_E1"] else 0
    O["P103_RUN"] = 1 if (O["P103_RUN"] or B3["CIP_E1"]) else 0  # CIP E1 também usa P103 (dreno)
    O["XV_CIP_01"] = 1 if B3["CIP_E2"] else 0
    O["P105_RUN"] = 1 if (B3["CIP_E2"] or B3["CIP_E4"] or B3["CIP_E5"]) else 0
    O["XV_CIP_02"] = 1 if B3["CIP_E3"] else 0
    O["P104_RUN"] = 1 if B3["CIP_E3"] else 0
    O["HEAT101"] = 1 if B3["CIP_E4"] else 0
    O["XV102"] = 1 if B3["EST_CIP"] else 0  # isola linha de produto durante todo o CIP

    # -------- Sinalização --------
    O["ALM_HORN"] = 1 if (B3["EST_EMG"] or B3["EST_FALHA"]) else 0
    O["PL_FALHA"] = 1 if B3["EST_FALHA"] else 0
    O["PL_CIP"] = 1 if B3["EST_CIP"] else 0
    O["PL_AUTO"] = 1 if (not manual and not B3["EST_PARADO"]) else 0
