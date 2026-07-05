#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py  (sub-rotina MAIN)
Responsabilidade: coordenação geral.
Conteúdo: JSR para as sub-rotinas na ordem correta de prioridade (aba "Subrotinas").

Assim como o CLP real, este programa roda em loop infinito ("varredura"/scan):
  1) lê entradas (planta simulada + painel do operador)
  2) executa a lógica (sub-rotinas, na ordem certa)
  3) aplica saídas
  4) grava o CSV
  5) aguarda o tempo de scan e volta para o passo 1

Uso:
    python3 main.py                      # roda indefinidamente (Ctrl+C para parar)
    python3 main.py --ciclos 50           # roda só 50 scans (útil p/ teste/CI)
    python3 main.py --scan-time 0.2       # muda o tempo de scan (s)
"""

import argparse
import sys
import time
from pathlib import Path

from plc_data import PLCDataTable
from plant_simulator import PlantSimulator
from operator_panel import OperatorPanel
import csv_logger

ROOT = Path(__file__).resolve().parent

from modules import (
    inicializacao, interlocks, falhas, config, auto, cip,
    qualidade, manual, saidas, eventos,
)


def main():
    ap = argparse.ArgumentParser(description="Simulador de CLP - PROB_01")
    ap.add_argument("--ciclos", type=int, default=None,
                     help="numero de scans a executar (padrao: infinito)")
    ap.add_argument("--scan-time", type=float, default=1.0,
                     help="tempo de scan em segundos (padrao 1.0s = base dos timers)")
    ap.add_argument("--saida", type=str, default="output",
                     help="pasta de saida dos CSVs")
    args = ap.parse_args()

    plc = PLCDataTable()
    plc.scan_time = args.scan_time
    planta = PlantSimulator(plc)
    painel = OperatorPanel(plc, planta)

    saida = Path(args.saida)
    if not saida.is_absolute():
        saida = ROOT / saida
    saida.mkdir(parents=True, exist_ok=True)

    caminho_estado = str(saida / "estado_atual.csv")
    caminho_historico = str(saida / "historico_processo.csv")

    print("=== Simulador de CLP - PROB_01_REFEITO_V4 ===")
    print(f"Scan time: {plc.scan_time}s | CSV tempo real: {caminho_estado}")
    print("Edite 'painel_operador.json' enquanto o programa roda para operar o processo.")
    print("Ctrl+C para encerrar.\n")

    try:
        while True:
            t0 = time.time()

            # 1) ENTRADAS: planta física simulada + painel do operador
            planta.atualizar_entradas(plc.scan_time)
            painel.aplicar_comandos()

            # 2) LÓGICA — MAIN chama as sub-rotinas na ordem de prioridade
            inicializacao.executar(plc)          # INIT       (1a varredura)
            interlocks.executar(plc)             # INTERLOCKS (MÁXIMA)
            falhas.executar(plc)                 # FALHAS     (Alta)
            config.executar(plc)                 # CONFIG     (Média)
            auto.executar(plc)                   # AUTO       (Alta)
            cip.executar(plc)                    # CIP        (Alta)
            qualidade.executar(plc)              # QUALIDADE  (Média)
            manual.executar(plc)                 # MANUAL     (Média)
            saidas.executar(plc)                 # SAIDAS     (Alta) - sempre por último antes de EVENTOS
            eventos.executar(plc)                # EVENTOS    (Baixa)

            # 3) Efeitos de saída que dependam do scan já concluído
            planta.aplicar_saidas(plc.scan_time)

            # 4) CSV em tempo real (sobrescrito) + histórico (append)
            csv_logger.grava_estado_atual(plc, caminho_estado)
            csv_logger.grava_historico(plc, caminho_historico)

            plc.scan_count += 1

            # 5) aguarda o tempo de scan e volta ao passo 1 (loop do CLP)
            if args.ciclos is not None and plc.scan_count >= args.ciclos:
                break
            dt_exec = time.time() - t0
            time.sleep(max(0.0, plc.scan_time - dt_exec))

    except KeyboardInterrupt:
        print("\nSimulação encerrada pelo usuário.")
        sys.exit(0)


if __name__ == "__main__":
    main()
