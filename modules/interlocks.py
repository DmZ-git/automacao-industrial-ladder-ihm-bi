# -*- coding: utf-8 -*-
"""
modules/interlocks.py  (sub-rotina INTERLOCKS)
Prioridade MÁXIMA. Executa antes de tudo, exceto INIT.
Conteúdo: Emergência (contato NF), permissivos, fail-safe.
"""


def executar(plc):
    I, B3, ALM = plc.I, plc.B3, plc.ALM

    # PB_EMG é NF: 1 = normal (repousado), 0 = emergência acionada (abriu)
    B3["EST_EMG"] = 1 if I["PB_EMG"] == 0 else 0
    ALM["ALM_EMG"] = B3["EST_EMG"]

    # PERMISSIVOS_OK: sem emergência e sem falha (trava ou não) -> habilita avanço da sequência
    B3["PERMISSIVOS_OK"] = 1 if (B3["EST_EMG"] == 0 and B3["EST_FALHA"] == 0
                                  and B3["FALHA_LATCHED"] == 0) else 0

    # PB_RESET: só reseta falha/travas se emergência já não está mais presente.
    # Como o operador_panel.py zera o pulso após 1 scan, este bloco usa o estado atual
    # do bit para limpar a falha e também força o retorno a E0 se a máquina estiver travada.
    if I["PB_RESET"] and B3["EST_EMG"] == 0:
        B3["EST_FALHA"] = 0
        B3["FALHA_LATCHED"] = 0
        B3["EST_PARADO"] = 1
        for e in ("EST_RECEITA", "EST_CARGA", "EST_MISTURA", "EST_TRANSF",
                  "EST_ENVASE", "EST_CIP", "EST_FINAL"):
            B3[e] = 0
        for tag in ("T_FALHA_P101", "T_FALHA_P103", "T_FALHA_P104", "T_FALHA_P105"):
            plc.T[tag].reset()
        for tag in ("ALM_FALHA_P101", "ALM_FALHA_P103", "ALM_FALHA_P104",
                    "ALM_FALHA_P105", "ALM_FALHA_AG", "ALM_SOBREPRESSAO"):
            ALM[tag] = 0

    # PB_STOP ou emergência: fail-safe -> força retorno a E0 (sem apagar CIP_FEITO)
    if I["PB_STOP"] or B3["EST_EMG"]:
        for e in ("EST_RECEITA", "EST_CARGA", "EST_MISTURA", "EST_TRANSF",
                  "EST_ENVASE", "EST_CIP", "EST_FINAL"):
            B3[e] = 0
        B3["EST_PARADO"] = 1
        for tag in ("CIP_E1", "CIP_E2", "CIP_E3", "CIP_E4", "CIP_E5", "CIP_E6", "CIP_E7"):
            B3[tag] = 0
        plc.estado_cip_atual = None
