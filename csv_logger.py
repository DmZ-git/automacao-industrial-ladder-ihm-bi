# -*- coding: utf-8 -*-
"""
csv_logger.py
Gera dois CSVs a cada scan:
  - estado_atual.csv   : 1 linha, sempre sobrescrita -> "foto" em tempo real
  - historico_processo.csv : 1 linha por scan, em append -> trace completo
"""

import csv
import os
import datetime

_COLUNAS_BASE = ["scan", "timestamp", "estado_auto", "estado_cip"]


def _linha(plc, colunas_extra):
    B3 = plc.B3
    estado_auto = next(
        (e.replace("EST_", "") for e in
         ("EST_PARADO", "EST_RECEITA", "EST_CARGA", "EST_MISTURA", "EST_TRANSF",
          "EST_ENVASE", "EST_CIP", "EST_FINAL") if B3[e]),
        "FALHA" if B3["EST_FALHA"] else ("EMG" if B3["EST_EMG"] else "?")
    )
    linha = {
        "scan": plc.scan_count,
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "estado_auto": estado_auto,
        "estado_cip": plc.estado_cip_atual or "",
        "lote_id": plc.lote_atual,
        "receita": plc.receita_nome,
        "etapa": plc.etapa_atual or estado_auto,
        "etapa_inicio_ts": datetime.datetime.fromtimestamp(plc.etapa_inicio_ts).isoformat(timespec="seconds") if plc.etapa_inicio_ts else "",
        "etapa_fim_ts": datetime.datetime.fromtimestamp(plc.etapa_fim_ts).isoformat(timespec="seconds") if plc.etapa_fim_ts else "",
        "duracao_lote_s": round(plc.lote_duracao_s, 3),
        "duracao_etapa_s": round(plc.etapa_duracao_s, 3),
    }
    for prefixo, dic in (("I_", plc.I), ("IA_", plc.IA), ("O_", plc.O),
                         ("OA_", plc.OA), ("B3_", plc.B3), ("N_", plc.N),
                         ("ALM_", plc.ALM)):
        for k, v in dic.items():
            linha[prefixo + k] = round(v, 2) if isinstance(v, float) else v
    for tag, t in plc.T.items():
        linha[f"T_{tag}_ACC"] = round(t.ACC, 1)
        linha[f"T_{tag}_DN"] = int(t.DN)
    return linha


def _colunas(linha):
    return list(linha.keys())


def grava_estado_atual(plc, caminho="output/estado_atual.csv"):
    linha = _linha(plc, None)
    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_colunas(linha))
        w.writeheader()
        w.writerow(linha)


def grava_historico(plc, caminho="output/historico_processo.csv"):
    linha = _linha(plc, None)
    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    existe = os.path.exists(caminho)
    with open(caminho, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_colunas(linha))
        if not existe:
            w.writeheader()
        w.writerow(linha)
