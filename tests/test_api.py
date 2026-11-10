"""Testes da API REST (camada HTTP).

As regras de negócio já são testadas nos testes de serviço. Aqui verificamos
o que é próprio da API: rotas, formato do JSON, códigos de status HTTP e o
formato único das mensagens de erro ({"detail": "..."}).

Cada teste sobe a API com um banco SQLite temporário, usando o TestClient do
FastAPI (que faz as requisições sem precisar abrir uma porta de rede).
"""

import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.aplicacao import criar_aplicacao
from app.models.dependencia import Dependencia
from app.repositories.database import ConexaoBancoDeDados
from app.repositories.dependencia_repository import DependenciaRepository

ORIGEM_DO_FRONTEND = "http://localhost:5173"


class CasoDeTesteDaApi(unittest.TestCase):
    """Sobe a API sobre um banco temporário e oferece atalhos de cadastro."""

    def setUp(self) -> None:
        self._recursos = ExitStack()
        diretorio = self._recursos.enter_context(tempfile.TemporaryDirectory())
        self.caminho_do_banco = Path(diretorio) / "teste.db"
        aplicacao = criar_aplicacao(self.caminho_do_banco, [ORIGEM_DO_FRONTEND])
        # Usar o TestClient com 'with' executa o início e o fim da API
        # (abre e fecha o banco de dados).
        self.cliente = self._recursos.enter_context(TestClient(aplicacao))

    def tearDown(self) -> None:
        self._recursos.close()

    def _cadastrar_equipamento(self, nome="Servidor Web", classe="Servidor") -> dict:
        resposta = self.cliente.post(
            "/api/equipamentos",
            json={
                "nome": nome,
                "responsavel": "Fulano",
                "setor": "TI",
                "classe": classe,
            },
        )
        self.assertEqual(resposta.status_code, 201, resposta.text)
        return resposta.json()

    def _cadastrar_vulnerabilidade(self, descricao="Senha fraca", nota_cvss=8.0):
        resposta = self.cliente.post(
            "/api/vulnerabilidades",
            json={
                "descricao": descricao,
                "categoria": "Autenticação",
                "nota_cvss": nota_cvss,
                "status": "ABERTA",
            },
        )
        self.assertEqual(resposta.status_code, 201, resposta.text)
        return resposta.json()

    def _atribuir(self, equipamento_id: int, vulnerabilidade_id: int) -> None:
        resposta = self.cliente.post(
            f"/api/equipamentos/{equipamento_id}/vulnerabilidades/{vulnerabilidade_id}"
        )
        self.assertEqual(resposta.status_code, 204, resposta.text)

    def _verificar_erro(self, resposta, status_esperado: int) -> None:
        """Verifica o status e o formato padrão de erro: {"detail": "texto"}."""
        self.assertEqual(resposta.status_code, status_esperado, resposta.text)
        self.assertIsInstance(resposta.json()["detail"], str)


class TestOpcoesESaude(CasoDeTesteDaApi):
    """Rotas de valores fixos e de saúde."""

    def test_saude(self):
        resposta = self.cliente.get("/api/saude")

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json(), {"status": "ok"})

    def test_tipos_de_equipamento_trazem_classe_rotulo_e_fator(self):
        tipos = self.cliente.get("/api/tipos-de-equipamento").json()

        firewall = next(tipo for tipo in tipos if tipo["classe"] == "Firewall")
        self.assertEqual(firewall["rotulo"], "Firewall")
        self.assertEqual(firewall["fator_de_exposicao"], 1.5)

    def test_status_de_vulnerabilidade(self):
        status = self.cliente.get("/api/status-de-vulnerabilidade").json()

        self.assertIn({"valor": "EM_TRATAMENTO", "rotulo": "Em Tratamento"}, status)

    def test_cors_permite_a_origem_do_frontend(self):
        resposta = self.cliente.options(
            "/api/equipamentos",
            headers={
                "Origin": ORIGEM_DO_FRONTEND,
                "Access-Control-Request-Method": "POST",
            },
        )

        self.assertEqual(
            resposta.headers["access-control-allow-origin"], ORIGEM_DO_FRONTEND
        )


class TestEquipamentos(CasoDeTesteDaApi):
    """CRUD de equipamentos pela API."""

    def test_cadastrar_retorna_201_com_o_equipamento(self):
        equipamento = self._cadastrar_equipamento("Servidor Web", "Servidor")

        self.assertEqual(equipamento["nome"], "Servidor Web")
        self.assertEqual(equipamento["classe"], "Servidor")
        self.assertEqual(equipamento["tipo"], "Servidor")
        self.assertEqual(equipamento["quantidade_de_vulnerabilidades"], 0)

    def test_cadastrar_com_tipo_inexistente_retorna_422(self):
        resposta = self.cliente.post(
            "/api/equipamentos",
            json={"nome": "X", "responsavel": "Ana", "setor": "TI", "classe": "Nave"},
        )

        self._verificar_erro(resposta, 422)
        self.assertIn("classe", resposta.json()["detail"])

    def test_cadastrar_sem_campo_obrigatorio_retorna_422_em_portugues(self):
        resposta = self.cliente.post(
            "/api/equipamentos",
            json={"nome": "X", "setor": "TI", "classe": "Servidor"},
        )

        self._verificar_erro(resposta, 422)
        self.assertEqual(
            resposta.json()["detail"],
            "Campo 'responsavel': campo obrigatório não informado.",
        )

    def test_regra_de_negocio_do_servico_retorna_422(self):
        resposta = self.cliente.post(
            "/api/equipamentos",
            json={
                "nome": "Servidor",
                "responsavel": "Fulano 2",
                "setor": "TI",
                "classe": "Servidor",
            },
        )

        self._verificar_erro(resposta, 422)

    def test_buscar_por_id(self):
        cadastrado = self._cadastrar_equipamento()

        resposta = self.cliente.get(f"/api/equipamentos/{cadastrado['id']}")

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json(), cadastrado)

    def test_buscar_id_inexistente_retorna_404(self):
        self._verificar_erro(self.cliente.get("/api/equipamentos/999"), 404)

    def test_listar_e_filtrar_por_nome(self):
        self._cadastrar_equipamento("Servidor Web")
        self._cadastrar_equipamento("Roteador Borda", "Roteador")

        todos = self.cliente.get("/api/equipamentos").json()
        filtrados = self.cliente.get("/api/equipamentos", params={"nome": "rot"}).json()

        self.assertEqual(len(todos), 2)
        self.assertEqual([e["nome"] for e in filtrados], ["Roteador Borda"])

    def test_atualizar(self):
        cadastrado = self._cadastrar_equipamento()

        resposta = self.cliente.put(
            f"/api/equipamentos/{cadastrado['id']}",
            json={"responsavel": "Beltrano", "setor": "Rede", "classe": "Firewall"},
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["responsavel"], "Beltrano")
        self.assertEqual(resposta.json()["classe"], "Firewall")
        self.assertEqual(resposta.json()["nome"], cadastrado["nome"])

    def test_excluir_informa_as_vulnerabilidades_excluidas_junto(self):
        equipamento = self._cadastrar_equipamento()
        vulnerabilidade = self._cadastrar_vulnerabilidade()
        self._atribuir(equipamento["id"], vulnerabilidade["id"])

        exclusivas = self.cliente.get(
            f"/api/equipamentos/{equipamento['id']}/vulnerabilidades-exclusivas"
        ).json()
        resposta = self.cliente.delete(f"/api/equipamentos/{equipamento['id']}")

        self.assertEqual([v["id"] for v in exclusivas], [vulnerabilidade["id"]])
        self.assertEqual(
            resposta.json(),
            {"ids_das_vulnerabilidades_excluidas": [vulnerabilidade["id"]]},
        )
        self._verificar_erro(
            self.cliente.get(f"/api/equipamentos/{equipamento['id']}"), 404
        )
        self._verificar_erro(
            self.cliente.get(f"/api/vulnerabilidades/{vulnerabilidade['id']}"), 404
        )


class TestVulnerabilidades(CasoDeTesteDaApi):
    """Catálogo de vulnerabilidades e associação com equipamentos."""

    def test_cadastrar_calcula_a_severidade(self):
        vulnerabilidade = self._cadastrar_vulnerabilidade(nota_cvss=9.8)

        self.assertEqual(vulnerabilidade["severidade"], "CRITICA")
        self.assertEqual(vulnerabilidade["ids_dos_equipamentos_afetados"], [])

    def test_status_inexistente_retorna_422(self):
        resposta = self.cliente.post(
            "/api/vulnerabilidades",
            json={
                "descricao": "Senha fraca",
                "categoria": "Rede",
                "nota_cvss": 5,
                "status": "RESOLVIDA",
            },
        )

        self._verificar_erro(resposta, 422)

    def test_nota_cvss_fora_da_faixa_retorna_422(self):
        resposta = self.cliente.post(
            "/api/vulnerabilidades",
            json={
                "descricao": "Senha fraca",
                "categoria": "Rede",
                "nota_cvss": 11,
                "status": "ABERTA",
            },
        )

        self._verificar_erro(resposta, 422)

    def test_atualizar(self):
        vulnerabilidade = self._cadastrar_vulnerabilidade(nota_cvss=8.0)

        resposta = self.cliente.put(
            f"/api/vulnerabilidades/{vulnerabilidade['id']}",
            json={
                "descricao": "Senha fraca",
                "categoria": "Rede",
                "nota_cvss": 2.0,
                "status": "CORRIGIDA",
            },
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["severidade"], "BAIXA")
        self.assertEqual(resposta.json()["status"], "CORRIGIDA")

    def test_excluir_retorna_204(self):
        vulnerabilidade = self._cadastrar_vulnerabilidade()

        resposta = self.cliente.delete(f"/api/vulnerabilidades/{vulnerabilidade['id']}")

        self.assertEqual(resposta.status_code, 204)
        self.assertEqual(self.cliente.get("/api/vulnerabilidades").json(), [])

    def test_atribuir_e_remover_de_um_equipamento(self):
        equipamento = self._cadastrar_equipamento()
        vulnerabilidade = self._cadastrar_vulnerabilidade()
        caminho = (
            f"/api/equipamentos/{equipamento['id']}"
            f"/vulnerabilidades/{vulnerabilidade['id']}"
        )

        self._atribuir(equipamento["id"], vulnerabilidade["id"])
        do_equipamento = self.cliente.get(
            f"/api/equipamentos/{equipamento['id']}/vulnerabilidades"
        ).json()
        afetados = self.cliente.get(
            f"/api/vulnerabilidades/{vulnerabilidade['id']}/equipamentos"
        ).json()
        remocao = self.cliente.delete(caminho)

        self.assertEqual([v["id"] for v in do_equipamento], [vulnerabilidade["id"]])
        self.assertEqual([e["id"] for e in afetados], [equipamento["id"]])
        self.assertEqual(remocao.status_code, 204)

    def test_atribuir_duas_vezes_retorna_422(self):
        equipamento = self._cadastrar_equipamento()
        vulnerabilidade = self._cadastrar_vulnerabilidade()
        self._atribuir(equipamento["id"], vulnerabilidade["id"])

        resposta = self.cliente.post(
            f"/api/equipamentos/{equipamento['id']}"
            f"/vulnerabilidades/{vulnerabilidade['id']}"
        )

        self._verificar_erro(resposta, 422)

    def test_atribuir_vulnerabilidade_inexistente_retorna_404(self):
        equipamento = self._cadastrar_equipamento()

        resposta = self.cliente.post(
            f"/api/equipamentos/{equipamento['id']}/vulnerabilidades/999"
        )

        self._verificar_erro(resposta, 404)


class TestDependencias(CasoDeTesteDaApi):
    """Dependências entre equipamentos."""

    def test_salvar_listar_e_excluir(self):
        web = self._cadastrar_equipamento("Web")
        banco = self._cadastrar_equipamento("Banco", "BancoDeDados")
        caminho = f"/api/dependencias/{web['id']}/{banco['id']}"

        salva = self.cliente.put(caminho, json={"fator": 0.4})
        listadas = self.cliente.get(
            "/api/dependencias", params={"equipamento_id": web["id"]}
        ).json()
        excluida = self.cliente.delete(caminho)

        esperada = {
            "equipamento_id": web["id"],
            "depende_de_id": banco["id"],
            "fator": 0.4,
        }
        self.assertEqual(salva.json(), esperada)
        self.assertEqual(listadas, [esperada])
        self.assertEqual(excluida.status_code, 204)
        self.assertEqual(self.cliente.get("/api/dependencias").json(), [])

    def test_soma_dos_fatores_maior_ou_igual_a_um_retorna_422(self):
        web = self._cadastrar_equipamento("Web")
        banco = self._cadastrar_equipamento("Banco")
        firewall = self._cadastrar_equipamento("Firewall")
        self.cliente.put(
            f"/api/dependencias/{web['id']}/{banco['id']}", json={"fator": 0.6}
        )

        resposta = self.cliente.put(
            f"/api/dependencias/{web['id']}/{firewall['id']}", json={"fator": 0.4}
        )

        self._verificar_erro(resposta, 422)

    def test_equipamento_inexistente_retorna_404(self):
        web = self._cadastrar_equipamento("Web")

        resposta = self.cliente.put(
            f"/api/dependencias/{web['id']}/999", json={"fator": 0.4}
        )

        self._verificar_erro(resposta, 404)


class TestAnaliseDeRisco(CasoDeTesteDaApi):
    """Análise de risco pela API, com o cenário resolvido à mão descrito em
    tests/test_analise_de_risco.py: x = [13, 11.5, 7.75]."""

    def _montar_cenario_resolvido_a_mao(self):
        e1, e2, e3 = (
            self._cadastrar_equipamento(nome, "EstacaoDeTrabalho")
            for nome in ("Estacao Um", "Estacao Dois", "Estacao Tres")
        )
        v1 = self._cadastrar_vulnerabilidade("Vulnerabilidade Um", 8.0)
        v2 = self._cadastrar_vulnerabilidade("Vulnerabilidade Dois", 5.0)
        v3 = self._cadastrar_vulnerabilidade("Vulnerabilidade Tres", 2.0)
        self._atribuir(e1["id"], v1["id"])
        self._atribuir(e1["id"], v2["id"])
        self._atribuir(e2["id"], v2["id"])
        self._atribuir(e3["id"], v3["id"])
        self.cliente.put(
            f"/api/dependencias/{e2['id']}/{e1['id']}", json={"fator": 0.5}
        )
        self.cliente.put(
            f"/api/dependencias/{e3['id']}/{e2['id']}", json={"fator": 0.5}
        )
        return e1, e2, e3

    def test_riscos_do_cenario_resolvido_a_mao_ordenados_pelo_efetivo(self):
        self._montar_cenario_resolvido_a_mao()

        analise = self.cliente.get("/api/analise-de-risco").json()

        self.assertAlmostEqual(analise["determinante"], 1.0)
        efetivos = [risco["risco_efetivo"] for risco in analise["riscos"]]
        proprios = [risco["risco_proprio"] for risco in analise["riscos"]]
        self.assertEqual(efetivos, [13.0, 11.5, 7.75])
        self.assertEqual(proprios, [13.0, 5.0, 2.0])

    def test_risco_de_um_equipamento(self):
        _, e2, _ = self._montar_cenario_resolvido_a_mao()

        risco = self.cliente.get(
            f"/api/analise-de-risco/equipamentos/{e2['id']}"
        ).json()

        self.assertEqual(risco["risco_proprio"], 5.0)
        self.assertEqual(risco["risco_herdado"], 6.5)
        self.assertEqual(risco["risco_efetivo"], 11.5)

    def test_risco_de_equipamento_inexistente_retorna_404(self):
        self._verificar_erro(
            self.cliente.get("/api/analise-de-risco/equipamentos/999"), 404
        )

    def test_matrizes_do_modelo(self):
        self._montar_cenario_resolvido_a_mao()

        matrizes = self.cliente.get("/api/analise-de-risco/matrizes").json()

        self.assertEqual(
            matrizes["matriz_de_incidencia"], [[1, 1, 0], [0, 1, 0], [0, 0, 1]]
        )
        self.assertEqual(matrizes["vetor_de_severidade"], [8.0, 5.0, 2.0])
        self.assertEqual(
            matrizes["matriz_de_dependencias"],
            [[0, 0, 0], [0.5, 0, 0], [0, 0.5, 0]],
        )

    def test_sistema_nao_invertivel_retorna_409(self):
        # Grava direto no banco, sem as validações do serviço, dependências
        # que deixam a soma de cada linha de A igual a 1.
        ids = [
            self._cadastrar_equipamento(nome)["id"] for nome in ("Um", "Dois", "Tres")
        ]
        banco_de_dados = ConexaoBancoDeDados(self.caminho_do_banco)
        repositorio = DependenciaRepository(banco_de_dados)
        for equipamento_id in ids:
            for outro_id in ids:
                if outro_id != equipamento_id:
                    repositorio.salvar(Dependencia(equipamento_id, outro_id, 0.5))
        banco_de_dados.fechar()

        self._verificar_erro(self.cliente.get("/api/analise-de-risco"), 409)
