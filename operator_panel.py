# -*- coding: utf-8 -*-
"""
operator_panel.py
Substitui a botoeira física: um arquivo JSON que o usuário pode editar
enquanto a simulação está rodando ("tempo real"). É lido a cada scan.
Botões de pulso (START/RESET) são auto-resetados após aplicados, como
uma botoeira normal-aberta que só fica pressionada por um instante.
"""

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CAMINHO_PADRAO = ROOT / "painel_operador.json"

_PADRAO = {
    "PB_START": False,
    "PB_STOP": False,
    "PB_EMG_ACIONADO": False,   # true = botão de emergência PRESSIONADO
    "PB_RESET": False,
    "SEL_RECEITA": 0,           # 0 = Sabao | 1 = Detergente
    "HABILITA_MANUAL": False,
    "MAN_XV_CARGA": False,
    "MAN_XV101": False,
    "MAN_P101": False,
    "MAN_AG101": False,
    "MAN_XV_ENVASE": False,
    "MAN_P103": False,
    "forcar_falha_FL_P101": False,
    "forcar_falha_FL_P103": False,
    "forcar_falha_FL_P104": False,
    "forcar_falha_FL_P105": False,
}

# Botões de pulso: aplicam por 1 scan e o painel os zera sozinho
# O STOP também é tratado como pulso para não travar a sequência em parada.
_BOTOES_PULSO = ("PB_START", "PB_RESET", "PB_STOP")


class OperatorPanel:
    def __init__(self, plc, plant, caminho=CAMINHO_PADRAO):
        self.plc = plc
        self.plant = plant
        self.caminho = Path(caminho) if caminho is not None else CAMINHO_PADRAO
        if not self.caminho.is_absolute():
            self.caminho = ROOT / self.caminho
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        if not os.path.exists(self.caminho):
            self._escreve(_PADRAO)

    def _le(self):
        try:
            with open(self.caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            dados = dict(_PADRAO)
        # garante todas as chaves, mesmo se o usuário editou e apagou alguma
        for k, v in _PADRAO.items():
            dados.setdefault(k, v)
        return dados

    def _escreve(self, dados):
        with open(self.caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)

    def aplicar_comandos(self):
        dados = self._le()
        I, B3 = self.plc.I, self.plc.B3

        I["PB_START"] = 1 if dados["PB_START"] else 0
        I["PB_STOP"] = 1 if dados["PB_STOP"] else 0
        I["PB_EMG"] = 0 if dados["PB_EMG_ACIONADO"] else 1  # contato NF
        I["PB_RESET"] = 1 if dados["PB_RESET"] else 0
        I["SEL_RECEITA"] = 1 if int(dados.get("SEL_RECEITA", 0)) else 0

        B3["HABILITA_MANUAL"] = 1 if dados["HABILITA_MANUAL"] else 0
        B3["MAN_XV_CARGA"] = 1 if dados["MAN_XV_CARGA"] else 0
        B3["MAN_XV101"] = 1 if dados["MAN_XV101"] else 0
        B3["MAN_P101"] = 1 if dados["MAN_P101"] else 0
        B3["MAN_AG101"] = 1 if dados["MAN_AG101"] else 0
        B3["MAN_XV_ENVASE"] = 1 if dados["MAN_XV_ENVASE"] else 0
        B3["MAN_P103"] = 1 if dados["MAN_P103"] else 0

        for tag in ("FL_P101", "FL_P103", "FL_P104", "FL_P105"):
            self.plant.forcar_falha[tag] = bool(dados.get(f"forcar_falha_{tag}", False))

        # zera os botões de pulso no arquivo, para não ficar START permanente
        alterou = False
        for botao in _BOTOES_PULSO:
            if dados.get(botao):
                dados[botao] = False
                alterou = True
        if alterou:
            self._escreve(dados)
