# -*- coding: utf-8 -*-
"""
modules/config.py  (sub-rotina CONFIG)
Responsabilidade: receitas e parâmetros.
Conteúdo: carrega N7:0..4 (e presets dos timers) conforme SEL_RECEITA.
Executa continuamente em E1 (EST_RECEITA), como um MOV em rung condicionado.
"""

_TIMER_POR_N = {
    "N_T_CARGA": "T_CARGA",
    "N_T_MIX": "T_MISTURA",
    "N_T_TRANSF": "T_TRANSF",
    "N_T_ENV": "T_ENVASE",
}


def executar(plc):
    B3, I, N = plc.B3, plc.I, plc.N

    # Espelha a chave seletora de receita no bit de memória
    B3["SEL_RECEITA_BIT"] = 1 if I["SEL_RECEITA"] else 0

    if not B3["EST_RECEITA"]:
        return

    receita = plc.receita_atual()  # 0 = Sabão | 1 = Detergente
    for tag_n, (sabao, detergente) in plc._presets_receita.items():
        valor = detergente if receita == 1 else sabao
        N[tag_n] = valor
        if tag_n in _TIMER_POR_N:
            plc.T[_TIMER_POR_N[tag_n]].PRE = float(valor)
