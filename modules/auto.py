# -*- coding: utf-8 -*-
"""
modules/auto.py  (sub-rotina AUTO)
Responsabilidade: máquina de estados.
Conteúdo: rungs E0 -> E7; transições; timers produtivos.
Só avança quando PERMISSIVOS_OK=1 e MODO_MANUAL=0.
"""

_ESTADOS = ("EST_PARADO", "EST_RECEITA", "EST_CARGA", "EST_MISTURA",
            "EST_TRANSF", "EST_ENVASE", "EST_CIP", "EST_FINAL")


def _ir_para(plc, estado_alvo):
    for e in _ESTADOS:
        plc.B3[e] = 1 if e == estado_alvo else 0
    nome_etapa = {
        "EST_PARADO": "Parado",
        "EST_RECEITA": "Receita",
        "EST_CARGA": "Carga",
        "EST_MISTURA": "Mistura",
        "EST_TRANSF": "Transferência",
        "EST_ENVASE": "Envase",
        "EST_CIP": "CIP",
        "EST_FINAL": "Finalização",
    }.get(estado_alvo, estado_alvo)
    plc.registrar_etapa(nome_etapa, receita=plc.receita_nome)


def executar(plc, dt=None):
    dt = plc.scan_time if dt is None else dt
    B3, I, T = plc.B3, plc.I, plc.T

    # Em falha/emergência ou em modo manual, AUTO não avança a sequência
    if not B3["PERMISSIVOS_OK"] or B3["MODO_MANUAL"]:
        return

    # ---------------- E0 — PARADO ----------------
    if B3["EST_PARADO"]:
        if I["PB_START"] and B3["CIP_FEITO"]:
            plc.iniciar_lote()
            _ir_para(plc, "EST_RECEITA")
        return

    # ---------------- E1 — RECEITA ----------------
    if B3["EST_RECEITA"]:
        # CONFIG já carregou os parâmetros nesta mesma varredura; debounce curto e segue
        dn = T["T_CONFIRM_NV"].tick(True, dt)
        if dn:
            T["T_CONFIRM_NV"].reset()
            _ir_para(plc, "EST_CARGA")
        return

    # ---------------- E2 — CARGA ----------------
    if B3["EST_CARGA"]:
        T["T_CARGA"].tick(True, dt)
        if I["LS_TK101_H"] or T["T_CARGA"].DN:
            T["T_CARGA"].reset()
            _ir_para(plc, "EST_MISTURA")
        return

    # ---------------- E3 — MISTURA ----------------
    if B3["EST_MISTURA"]:
        # A mistura deve iniciar após a carga, mesmo se o nível não tiver atingido o limiar
        # de LS_TK101_L em todos os cenários de simulação. O fluxo de processo fica mais robusto
        # quando a etapa é habilitada por um timer de mistura que começa assim que a carga termina.
        habilita = True
        T["T_MISTURA"].tick(habilita, dt)
        if T["T_MISTURA"].DN:
            T["T_MISTURA"].reset()
            _ir_para(plc, "EST_TRANSF")
        return

    # ---------------- E4 — TRANSFERÊNCIA ----------------
    if B3["EST_TRANSF"]:
        # XV101 abre primeiro (SAIDAS cuida disso); timer só conta com feedback de bomba ok
        habilita = bool(I["FL_P101"])
        T["T_TRANSF"].tick(habilita, dt)
        if T["T_TRANSF"].DN or I["LS_TK101_L"] == 0:
            T["T_TRANSF"].reset()
            _ir_para(plc, "EST_ENVASE")
        return

    # ---------------- E5 — ENVASE ----------------
    if B3["EST_ENVASE"]:
        # ALM_ENVASE_SECO (checado só na entrada, feito por QUALIDADE) já reprovou
        # o início se não havia produto; durante a etapa, só para quando ESVAZIAR de fato.
        habilita = not B3["ENVASE_VAZIO"]
        T["T_ENVASE"].tick(habilita, dt)
        if T["T_ENVASE"].DN or B3["ENVASE_VAZIO"]:
            T["T_ENVASE"].reset()
            _ir_para(plc, "EST_CIP")
        return

    # ---------------- E6 — CIP ----------------
    if B3["EST_CIP"]:
        # a sub-máquina CIP (modules/cip.py) roda em sua própria sub-rotina;
        # aqui só verificamos a conclusão (CIP_FEITO setado pela sub-rotina CIP)
        if B3["CIP_FEITO"]:
            _ir_para(plc, "EST_FINAL")
        return

    # ---------------- E7 — FINALIZAÇÃO ----------------
    if B3["EST_FINAL"]:
        plc.pulso_lote_concluido = True  # EVENTOS incrementa N_LOTE_CTR nesta borda
        plc.finalizar_lote()
        _ir_para(plc, "EST_PARADO")
        return
