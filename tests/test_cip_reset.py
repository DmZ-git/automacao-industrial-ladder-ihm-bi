import unittest

from plc_data import PLCDataTable
from modules import auto, cip, saidas


class CipResetTests(unittest.TestCase):
    def test_cip_e7_zera_tanques_e_sensores(self):
        plc = PLCDataTable()
        plc.B3["EST_CIP"] = 1
        plc.B3["CIP_E7"] = 1
        plc.estado_cip_atual = "CIP_E7"

        plc.IA["LT101"] = 1200.0
        plc.IA["LT103"] = 1800.0
        plc.IA["TT102"] = 60.0
        plc.IA["FT101"] = 80.0
        plc.IA["FT201"] = 45.0
        plc.IA["PT101"] = 3.5
        plc.IA["AIT101"] = 11.0
        plc.IA["AIT102"] = 3000.0
        plc.IA["AIT103"] = 80.0
        plc.I["LS_TK101_H"] = 1
        plc.I["LS_TK101_L"] = 1
        plc.B3["ENVASE_VAZIO"] = 0
        plc.B3["ENVASE_PRODUTO_OK"] = 1
        plc.B3["PH_OK"] = 1
        plc.B3["CONDUTIVIDADE_OK"] = 1
        plc.B3["TURBIDEZ_OK"] = 1

        cip.executar(plc, dt=1.0)

        self.assertEqual(plc.B3["CIP_FEITO"], 1)
        self.assertEqual(plc.IA["LT101"], 0.0)
        self.assertEqual(plc.IA["LT103"], 0.0)
        self.assertEqual(plc.IA["TT102"], 25.0)
        self.assertEqual(plc.I["LS_TK101_H"], 0)
        self.assertEqual(plc.I["LS_TK101_L"], 0)
        self.assertEqual(plc.B3["ENVASE_VAZIO"], 1)
        self.assertEqual(plc.B3["ENVASE_PRODUTO_OK"], 0)
        self.assertEqual(plc.B3["PH_OK"], 0)
        self.assertEqual(plc.B3["CONDUTIVIDADE_OK"], 0)
        self.assertEqual(plc.B3["TURBIDEZ_OK"], 0)

    def test_auto_nao_permite_estados_simultaneos(self):
        plc = PLCDataTable()
        plc.B3["EST_PARADO"] = 0
        plc.B3["EST_RECEITA"] = 1
        plc.B3["PERMISSIVOS_OK"] = 1
        plc.B3["MODO_MANUAL"] = 0
        plc.I["PB_START"] = 0
        plc.B3["CIP_FEITO"] = 1

        auto.executar(plc, dt=1.0)

        estados_ativos = [tag for tag in ("EST_PARADO", "EST_RECEITA", "EST_CARGA", "EST_MISTURA",
                                          "EST_TRANSF", "EST_ENVASE", "EST_CIP", "EST_FINAL")
                          if plc.B3[tag]]
        self.assertEqual(len(estados_ativos), 1)

    def test_cip_finaliza_desliga_atuadores(self):
        plc = PLCDataTable()
        plc.B3["EST_CIP"] = 1
        plc.B3["CIP_E7"] = 1
        plc.B3["PERMISSIVOS_OK"] = 1
        plc.B3["MODO_MANUAL"] = 0
        plc.estado_cip_atual = "CIP_E7"
        plc.O["XV_DRENO"] = 1
        plc.O["P103_RUN"] = 1
        plc.O["XV_CIP_01"] = 1
        plc.O["P105_RUN"] = 1
        plc.O["XV_CIP_02"] = 1
        plc.O["P104_RUN"] = 1
        plc.O["HEAT101"] = 1
        plc.O["XV102"] = 1

        cip.executar(plc, dt=1.0)

        self.assertEqual(plc.O["XV_DRENO"], 0)
        self.assertEqual(plc.O["P103_RUN"], 0)
        self.assertEqual(plc.O["XV_CIP_01"], 0)
        self.assertEqual(plc.O["P105_RUN"], 0)
        self.assertEqual(plc.O["XV_CIP_02"], 0)
        self.assertEqual(plc.O["P104_RUN"], 0)
        self.assertEqual(plc.O["HEAT101"], 0)
        self.assertEqual(plc.O["XV102"], 0)

    def test_agitador_somente_com_nivel_minimo(self):
        plc = PLCDataTable()
        plc.B3["PERMISSIVOS_OK"] = 1
        plc.B3["MODO_MANUAL"] = 0
        plc.B3["EST_MISTURA"] = 1
        plc.I["LS_TK101_L"] = 0

        saidas.executar(plc)

        self.assertEqual(plc.O["AG101_RUN"], 0)


if __name__ == "__main__":
    unittest.main()
