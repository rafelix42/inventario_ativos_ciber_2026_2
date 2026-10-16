"""Testes da classificação de severidade a partir da nota CVSS."""

import unittest

from app.models.enums import Severidade


class TestSeveridadeAPartirDaNotaCvss(unittest.TestCase):
    """Testes da conversão de nota CVSS em severidade."""

    def test_nota_zero_e_classificada_como_nenhuma(self):
        self.assertEqual(Severidade.a_partir_da_nota_cvss(0.0), Severidade.NENHUMA)

    def test_notas_no_limite_inferior_e_superior_da_faixa_baixa(self):
        self.assertEqual(Severidade.a_partir_da_nota_cvss(0.1), Severidade.BAIXA)
        self.assertEqual(Severidade.a_partir_da_nota_cvss(3.9), Severidade.BAIXA)

    def test_notas_no_limite_inferior_e_superior_da_faixa_media(self):
        self.assertEqual(Severidade.a_partir_da_nota_cvss(4.0), Severidade.MEDIA)
        self.assertEqual(Severidade.a_partir_da_nota_cvss(6.9), Severidade.MEDIA)

    def test_notas_no_limite_inferior_e_superior_da_faixa_alta(self):
        self.assertEqual(Severidade.a_partir_da_nota_cvss(7.0), Severidade.ALTA)
        self.assertEqual(Severidade.a_partir_da_nota_cvss(8.9), Severidade.ALTA)

    def test_notas_no_limite_inferior_e_superior_da_faixa_critica(self):
        self.assertEqual(Severidade.a_partir_da_nota_cvss(9.0), Severidade.CRITICA)
        self.assertEqual(Severidade.a_partir_da_nota_cvss(10.0), Severidade.CRITICA)
