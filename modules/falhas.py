# -*- coding: utf-8 -*-
"""
modules/falhas.py  (sub-rotina FALHAS)
Responsabilidade: tratamento de alarmes.
Conteúdo: térmica + feedback (P101/103/104/105) + sobrepressão.
"""


def _checa_feedback(plc, tag_run, tag_fb, tag_timer, tag_alm):
    dt = plc.scan_time
    run = plc.O[tag_run]
    fb = plc.I[tag_fb]
    # habilita o timer de falha somente quando o motor está comandado a rodar
    # e o feedback não confirma (falha de feedback)
    sem_feedback = bool(run) and not fb
    dn = plc.T[tag_timer].tick(sem_feedback, dt)
    if dn:
        plc.ALM[tag_alm] = 1
    return dn


def executar(plc, dt=None):
    I, O, B3, ALM = plc.I, plc.O, plc.B3, plc.ALM

    falha_termica = any([
        I["AL_MOTOR_P101"], I["AL_MOTOR_P103"],
        I["AL_MOTOR_P104"], I["AL_MOTOR_P105"], I["AL_MOTOR_AG"],
    ])
    if I["AL_MOTOR_P101"]:
        ALM["ALM_FALHA_P101"] = 1
    if I["AL_MOTOR_P103"]:
        ALM["ALM_FALHA_P103"] = 1
    if I["AL_MOTOR_P104"]:
        ALM["ALM_FALHA_P104"] = 1
    if I["AL_MOTOR_P105"]:
        ALM["ALM_FALHA_P105"] = 1
    if I["AL_MOTOR_AG"]:
        ALM["ALM_FALHA_AG"] = 1

    falha_fb_p101 = _checa_feedback(plc, "P101_RUN", "FL_P101", "T_FALHA_P101", "ALM_FALHA_P101")
    falha_fb_p103 = _checa_feedback(plc, "P103_RUN", "FL_P103", "T_FALHA_P103", "ALM_FALHA_P103")
    falha_fb_p104 = _checa_feedback(plc, "P104_RUN", "FL_P104", "T_FALHA_P104", "ALM_FALHA_P104")
    falha_fb_p105 = _checa_feedback(plc, "P105_RUN", "FL_P105", "T_FALHA_P105", "ALM_FALHA_P105")

    # Sobrepressão na linha CIP, só relevante durante CIP (E6)
    if B3["EST_CIP"] and plc.IA["PT101"] > 5.0:
        ALM["ALM_SOBREPRESSAO"] = 1

    houve_falha = any([
        falha_termica, falha_fb_p101, falha_fb_p103, falha_fb_p104, falha_fb_p105,
        ALM["ALM_SOBREPRESSAO"],
    ])

    if houve_falha:
        B3["EST_FALHA"] = 1
        B3["FALHA_LATCHED"] = 1  # crítico: exige PB_RESET manual (INTERLOCKS trata o reset)
