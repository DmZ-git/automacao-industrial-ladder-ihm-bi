import json
from plc_data import PLCDataTable
from plant_simulator import PlantSimulator
from operator_panel import OperatorPanel
import modules.inicializacao as inicializacao
import modules.interlocks as interlocks
import modules.falhas as falhas
import modules.config as config
import modules.auto as auto
import modules.cip as cip
import modules.qualidade as qualidade
import modules.manual as manual
import modules.saidas as saidas
import modules.eventos as eventos
import csv_logger

plc = PLCDataTable()
planta = PlantSimulator(plc)
painel = OperatorPanel(plc, planta)

with open('painel_operador.json','w',encoding='utf-8') as f:
    json.dump({
        'PB_START': True,
        'PB_STOP': False,
        'PB_EMG_ACIONADO': False,
        'PB_RESET': False,
        'SEL_RECEITA': 0,
        'HABILITA_MANUAL': False,
        'MAN_XV_CARGA': False,
        'MAN_XV101': False,
        'MAN_P101': False,
        'MAN_AG101': False,
        'MAN_XV_ENVASE': False,
        'MAN_P103': False,
        'forcar_falha_FL_P101': False,
        'forcar_falha_FL_P103': False,
        'forcar_falha_FL_P104': False,
        'forcar_falha_FL_P105': False,
    }, f)

for i in range(20):
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
    csv_logger.grava_estado_atual(plc,'output/estado_atual.csv')
    plc.scan_count += 1
    print(i, 'EST_PARADO', plc.B3['EST_PARADO'], 'EST_CARGA', plc.B3['EST_CARGA'], 'EST_MISTURA', plc.B3['EST_MISTURA'], 'EST_TRANSF', plc.B3['EST_TRANSF'], 'EST_ENVASE', plc.B3['EST_ENVASE'], 'EST_CIP', plc.B3['EST_CIP'], 'EST_FINAL', plc.B3['EST_FINAL'])
