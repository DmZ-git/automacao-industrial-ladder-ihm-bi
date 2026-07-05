# Simulador de CLP — PROB_01_REFEITO_V4

Simulação em Python, **modular igual ao programa ladder** (`PROB_01_REFEITO_V4.RSS`),
construída a partir da lista de I/O (`Lista_IO_v4`). Roda em **loop contínuo**,
como a varredura (scan) de um CLP real: lê entradas, executa as sub-rotinas na
ordem certa, escreve saídas, grava CSV, aguarda o tempo de scan e volta ao início.

## Estrutura (1 arquivo = 1 sub-rotina, igual ao ladder)

```
main.py                  -> sub-rotina MAIN: o loop de varredura, chama as outras em ordem
plc_data.py               -> data table (equivalente a I:0, O:0, B3, T4, N7)
timer.py                  -> classe Timer (emula um TON do RSLogix)
plant_simulator.py        -> "planta física" (tanques/bombas) — não existe no ladder,
                              substitui o hardware real para a simulação poder rodar sozinha
operator_panel.py         -> lê painel_operador.json a cada scan (substitui a botoeira física)
csv_logger.py             -> grava os CSVs a cada scan

modules/
  inicializacao.py  -> INIT         (1a varredura: estado seguro, zera contadores)
  interlocks.py     -> INTERLOCKS   (prioridade MÁXIMA: emergência, permissivos, fail-safe)
  falhas.py         -> FALHAS       (térmica, feedback de bombas, sobrepressão)
  config.py         -> CONFIG       (carrega preset de receita: Sabão/Detergente)
  auto.py           -> AUTO         (máquina de estados E0..E7)
  cip.py            -> CIP          (sub-estados CIP_E1..E7 + validação)
  qualidade.py      -> QUALIDADE    (pH, condutividade, turbidez, níveis)
  manual.py         -> MANUAL       (operação manual com intertravamentos mantidos)
  saidas.py         -> SAIDAS       (única sub-rotina que escreve nas saídas físicas)
  eventos.py        -> EVENTOS      (contador de lotes e de alarmes)
```

A ordem de chamada em `main.py` segue exatamente a aba **"Subrotinas"** da planilha
(prioridade MÁXIMA → Alta → Média → Baixa).

## Como rodar

```bash
cd plc_sim
python3 main.py                    # roda indefinidamente (Ctrl+C para parar)
python3 main.py --ciclos 100       # roda só 100 scans (útil p/ teste)
python3 main.py --scan-time 0.5    # muda o tempo de scan (padrão 1.0 s = base dos timers)
```

Ao iniciar, o programa cria `painel_operador.json` na pasta atual (se não existir).
**Edite esse arquivo enquanto o programa está rodando** para operar o processo —
é lido a cada scan, então as mudanças entram em tempo real, exatamente como uma
botoeira/IHM conectada ao CLP:

```json
{
  "PB_START": true,          // pulso de partida (o programa zera sozinho após aplicar)
  "PB_STOP": false,
  "PB_EMG_ACIONADO": false,  // true = botão de emergência PRESSIONADO
  "PB_RESET": true,          // pulso de reset de falha/emergência
  "SEL_RECEITA": 0,          // 0 = Sabão | 1 = Detergente
  "HABILITA_MANUAL": false,
  "MAN_XV_CARGA": false, "MAN_XV101": false, "MAN_P101": false,
  "MAN_AG101": false, "MAN_XV_ENVASE": false, "MAN_P103": false,
  "forcar_falha_FL_P101": false,   // injeta falha de feedback para testar a sub-rotina FALHAS
  "forcar_falha_FL_P103": false,
  "forcar_falha_FL_P104": false,
  "forcar_falha_FL_P105": false
}
```

## Saída (CSV em tempo real)

- `output/estado_atual.csv` — 1 linha, **sobrescrita a cada scan**: é a "foto" atual
  do processo (todas as entradas, saídas, bits, timers, alarmes e contadores).
  Ideal para abrir num Excel com atualização automática ou ler de outro script.
- `output/historico_processo.csv` — 1 linha por scan, em **append**: histórico
  completo do lote, para gráficos/rastreabilidade (função da sub-rotina EVENTOS).

## O ciclo produtivo simulado

`E0 PARADO → E1 RECEITA → E2 CARGA → E3 MISTURA → E4 TRANSFERÊNCIA → E5 ENVASE
→ E6 CIP (CIP_E1..E7) → E7 FINALIZAÇÃO → volta a E0`

Emergência (`PB_EMG`, contato NF) ou falha (térmica/feedback/sobrepressão) interrompem
a sequência a qualquer momento e forçam saídas seguras (fail-safe), exigindo
`PB_RESET` para retomar — igual ao comportamento descrito na aba INTERLOCKS/FALHAS.

## Testando sem esperar o tempo real

`teste_offline.py` roda a lógica scan a scan **sem `time.sleep`**, útil para validar
rapidamente um lote inteiro (~1170 scans simulados) em segundos:

```bash
python3 teste_offline.py
```

## Extensões possíveis

- Trocar `plant_simulator.py` por leitura real de PLC (ex.: via `pycomm3`/Modbus)
  sem tocar nas sub-rotinas de lógica — é justamente para isso que a "planta" e a
  "lógica" ficam em módulos separados.
- Trocar `operator_panel.py` por uma IHM web (ex.: Flask + o mesmo JSON).
