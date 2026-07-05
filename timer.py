# -*- coding: utf-8 -*-
"""
timer.py
Emula um temporizador TON (Timer On-Delay) do RSLogix 500 (arquivo T4:x).
Cada scan chama .tick(habilita, dt) -> equivalente a uma rung com o TON.
"""


class Timer:
    def __init__(self, pre=0.0, base=1.0, tag=""):
        self.tag = tag
        self.PRE = float(pre)   # preset, em segundos (já convertido pela base)
        self.base = base        # base de tempo (informativo, igual a Base do ladder)
        self.ACC = 0.0          # acumulado
        self.EN = False         # enable
        self.TT = False         # timer timing (contando)
        self.DN = False         # done

    def tick(self, habilita: bool, dt: float):
        """Equivale a uma rung: XIC(condicao) TON(self)"""
        self.EN = bool(habilita)
        if self.EN:
            self.ACC = min(self.ACC + dt, self.PRE)
            self.DN = self.ACC >= self.PRE
            self.TT = not self.DN
        else:
            # TON reseta ACC quando a condição de habilitação cai (sem retenção)
            self.ACC = 0.0
            self.TT = False
            self.DN = False
        return self.DN

    def reset(self):
        self.ACC = 0.0
        self.EN = False
        self.TT = False
        self.DN = False

    def __repr__(self):
        return f"<T {self.tag} ACC={self.ACC:.1f}/{self.PRE:.1f} DN={self.DN}>"
