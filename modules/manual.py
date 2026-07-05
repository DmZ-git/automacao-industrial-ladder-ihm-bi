# -*- coding: utf-8 -*-
"""
modules/manual.py  (sub-rotina MANUAL)
Responsabilidade: operação manual.
Conteúdo: acionamento individual com intertravamentos mantidos.
MODO_MANUAL só é permitido em E0 (parado), sem emergência/falha.
Os comandos MAN_* em si vêm do painel do operador (operator_panel.py).
"""


def executar(plc):
    I, B3 = plc.I, plc.B3

    B3["MODO_MANUAL"] = 1 if (
        B3["HABILITA_MANUAL"] and B3["EST_PARADO"] and B3["PERMISSIVOS_OK"]
    ) else 0

    if not B3["MODO_MANUAL"]:
        # fora do modo manual, nenhum comando manual deve ficar retido
        for tag in ("MAN_P101", "MAN_AG101", "MAN_XV101",
                    "MAN_P103", "MAN_XV_ENVASE", "MAN_XV_CARGA"):
            B3[tag] = 0
        return

    # Intertravamentos mantidos mesmo em manual (aba "Memórias Internas"):
    # MAN_P101 exige XV101 aberta; MAN_P103 exige XV_ENVASE aberta;
    # MAN_XV_CARGA exige nível abaixo do máximo; MAN_AG101 exige nível mínimo.
    if B3["MAN_P101"] and not B3["MAN_XV101"]:
        B3["MAN_P101"] = 0
    if B3["MAN_P103"] and not B3["MAN_XV_ENVASE"]:
        B3["MAN_P103"] = 0
    if B3["MAN_XV_CARGA"] and I["LS_TK101_H"]:
        B3["MAN_XV_CARGA"] = 0
    if B3["MAN_AG101"] and not I["LS_TK101_L"]:
        B3["MAN_AG101"] = 0
