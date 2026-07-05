# -*- coding: utf-8 -*-
"""
modules/eventos.py  (sub-rotina EVENTOS)
Responsabilidade: rastreabilidade.
Conteúdo: contadores de lote e de alarmes (borda de subida).
Prioridade Baixa -> roda por último.
"""

import time


def executar(plc):
    if plc.pulso_lote_concluido:
        plc.N["N_LOTE_CTR"] += 1
        plc.pulso_lote_concluido = False
        plc.historico_etapas.append({
            "etapa": "Lote concluído",
            "inicio": plc.lote_inicio_ts,
            "fim": time.time(),
            "duracao_s": round(plc.lote_duracao_s, 3),
            "scan_inicio": 0,
            "scan_fim": plc.scan_count,
            "receita": plc.receita_nome,
        })

    for tag, valor in plc.ALM.items():
        anterior = plc._alm_prev.get(tag, 0)
        if valor and not anterior:
            plc.N["N_ALM_CTR"] += 1
        plc._alm_prev[tag] = valor
