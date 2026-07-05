#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teste offline: roda a logica scan a scan sem sleep, para validar rapidamente."""
import json
from plc_data import PLCDataTable
from plant_simulator import PlantSimulator
from operator_panel import OperatorPanel
import csv_logger
from modules import (inicializacao, interlocks, falhas, config, auto, cip,
                      qualidade, manual, saidas, eventos)

with open("painel_operador.json", "w") as f:
    json.dump({
        "PB_START": True, "PB_STOP": False, "PB_EMG_ACIONADO": False, "PB_RESET": False,
        "SEL_RECEITA": 1, "HABILITA_MANUAL": False,
        "MAN_XV_CARGA": False, "MAN_XV101": False, "MAN_P101": False, "MAN_AG101": False,
        "MAN_XV_ENVASE": False, "MAN_P103": False,
        "forcar_falha_FL_P101": False, "forcar_falha_FL_P103": False,
        "forcar_falha_FL_P104": False, "forcar_falha_FL_P105": False
    }, f)

plc = PLCDataTable()
plc.scan_time = 1.0
planta = PlantSimulator(plc)
painel = OperatorPanel(plc, planta)

estados_vistos = []
max_scans = 1400
for i in range(max_scans):
    planta.atualizar_entradas(plc.scan_time)
    painel.aplicar_comandos()
    inicializacao.executar(plc)
    interlocks.executar(plc)
    falhas.executar(plc)
    config.executar(plc)
    auto.executar(plc)
    cip.executar(plc)
    qualidade.executar(plc)
    manual.executar(plc)
    saidas.executar(plc)
    eventos.executar(plc)
    planta.aplicar_saidas(plc.scan_time)
    plc.scan_count += 1

    estado = next((e for e in ("EST_PARADO","EST_RECEITA","EST_CARGA","EST_MISTURA",
                                "EST_TRANSF","EST_ENVASE","EST_CIP","EST_FINAL")
                   if plc.B3[e]), "?")
    sub = plc.estado_cip_atual or ""
    tag = f"{estado}/{sub}"
    if not estados_vistos or estados_vistos[-1][0] != tag:
        estados_vistos.append((tag, i))

    csv_logger.grava_estado_atual(plc, "output/estado_atual.csv")
    csv_logger.grava_historico(plc, "output/historico_processo.csv")

    if plc.N["N_LOTE_CTR"] >= 1:
        print(f"Lote concluido no scan {i}")
        break

print("\nTransicoes de estado (estado/sub-estado, scan em que entrou):")
for tag, scan in estados_vistos:
    print(f"  scan {scan:5d}  ->  {tag}")

print("\nContadores finais:", plc.N)
print("Alarmes finais:", {k: v for k, v in plc.ALM.items() if v})
