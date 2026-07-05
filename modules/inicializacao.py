# -*- coding: utf-8 -*-
"""
modules/inicializacao.py  (sub-rotina INIT)
Responsabilidade: inicialização segura.
Conteúdo: 1a varredura -> força E0, CIP_FEITO=1, zera contadores.
"""


def executar(plc):
    if not plc.primeira_varredura:
        return

    plc.B3["EST_PARADO"] = 1
    for e in ("EST_RECEITA", "EST_CARGA", "EST_MISTURA", "EST_TRANSF",
              "EST_ENVASE", "EST_CIP", "EST_FINAL", "EST_EMG", "EST_FALHA"):
        plc.B3[e] = 0

    plc.B3["CIP_FEITO"] = 1
    plc.B3["FALHA_LATCHED"] = 0
    plc.N["N_LOTE_CTR"] = 0
    plc.N["N_ALM_CTR"] = 0

    for t in plc.T.values():
        t.reset()

    plc.estado_cip_atual = None
    plc.primeira_varredura = False
