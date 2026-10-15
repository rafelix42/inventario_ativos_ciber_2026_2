"""Testes da camada de regras de negócio (AtivoService): CRUD, validações e cache."""

from app.exceptions import AtivoNaoEncontradoError, ErroDeValidacao
from app.models.enums import TipoAtivo
from app.repositories.ativo_repository import AtivoRepository
from app.services.ativo_service import AtivoService
from tests.base import CasoDeTesteComBancoTemporario

NOME_DO_LOGGER = "app.services.ativo_service"


class TestAtivoService(CasoDeTesteComBancoTemporario):
    """Testes das regras de negócio de ativos."""

    def setUp(self) -> None:
        super().setUp()
        self.servico = AtivoService(AtivoRepository(self.banco))

    # --- Create -----------------------------------------------------

    def test_cadastrar_com_dados_validos_retorna_ativo_persistido(self):
        with self.assertLogs(NOME_DO_LOGGER, level="INFO"):
            ativo = self.servico.cadastrar(
                nome="Servidor-01",
                responsavel="Fulano de Tal",
                setor="TI",
                tipo=TipoAtivo.SERVIDOR,
                descricao="servidor de testes",
            )

        self.assertIsNotNone(ativo.id)
        self.assertEqual(self.servico.buscar_por_id(ativo.id), ativo)

    def test_cadastrar_com_nome_vazio_levanta_erro_de_validacao(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.cadastrar(
                nome="   ", responsavel="Fulano", setor="TI", tipo=TipoAtivo.SERVIDOR
            )

    def test_cadastrar_com_responsavel_vazio_levanta_erro_de_validacao(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.cadastrar(
                nome="Servidor-01", responsavel="", setor="TI", tipo=TipoAtivo.SERVIDOR
            )

    def test_cadastrar_com_setor_vazio_levanta_erro_de_validacao(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.cadastrar(
                nome="Servidor-01",
                responsavel="Fulano",
                setor="",
                tipo=TipoAtivo.SERVIDOR,
            )

    def test_cadastrar_com_tipo_invalido_levanta_erro_de_validacao(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.cadastrar(
                nome="Servidor-01", responsavel="Fulano", setor="TI", tipo="SERVIDOR"
            )

    # --- Read ---------------------------------------------------------

    def test_buscar_por_id_de_ativo_inexistente_levanta_erro(self):
        with self.assertRaises(AtivoNaoEncontradoError):
            self.servico.buscar_por_id(999)

    def test_buscar_por_nome_encontra_por_substring_sem_diferenciar_maiusculas(self):
        self.servico.cadastrar("DB-Server-01", "Fulano", "TI", TipoAtivo.SERVIDOR)

        encontrados = self.servico.buscar_por_nome("db-server")

        self.assertEqual(len(encontrados), 1)
        self.assertEqual(encontrados[0].nome, "DB-Server-01")

    def test_buscar_por_nome_sem_correspondencia_retorna_lista_vazia(self):
        self.servico.cadastrar("DB-Server-01", "Fulano", "TI", TipoAtivo.SERVIDOR)

        self.assertEqual(self.servico.buscar_por_nome("inexistente"), [])

    def test_buscar_por_nome_vazio_retorna_todos_os_ativos(self):
        self.servico.cadastrar("Servidor-01", "Fulano", "TI", TipoAtivo.SERVIDOR)
        self.servico.cadastrar("Servidor-02", "Fulano", "TI", TipoAtivo.SERVIDOR)

        self.assertEqual(len(self.servico.buscar_por_nome("")), 2)

    def test_listar_todos_retorna_ativos_ordenados_por_id(self):
        primeiro_ativo = self.servico.cadastrar(
            "Servidor-01", "Fulano", "TI", TipoAtivo.SERVIDOR
        )
        segundo_ativo = self.servico.cadastrar(
            "Servidor-02", "Fulano", "TI", TipoAtivo.SERVIDOR
        )

        ativos_cadastrados = self.servico.listar_todos()

        self.assertEqual(
            [ativo.id for ativo in ativos_cadastrados],
            [primeiro_ativo.id, segundo_ativo.id],
        )

    # --- Update ---------------------------------------------------------

    def test_atualizar_altera_os_campos_permitidos(self):
        ativo = self.servico.cadastrar(
            "Servidor-01", "Fulano", "TI", TipoAtivo.SERVIDOR
        )

        with self.assertLogs(NOME_DO_LOGGER, level="INFO"):
            ativo_atualizado = self.servico.atualizar(
                ativo_id=ativo.id,
                responsavel="Ciclana",
                setor="Financeiro",
                tipo=TipoAtivo.FIREWALL,
                descricao="atualizado pelo teste",
            )

        self.assertEqual(ativo_atualizado.responsavel, "Ciclana")
        self.assertEqual(ativo_atualizado.setor, "Financeiro")
        self.assertEqual(ativo_atualizado.tipo, TipoAtivo.FIREWALL)
        self.assertEqual(self.servico.buscar_por_id(ativo.id).responsavel, "Ciclana")

    def test_atualizar_ativo_inexistente_levanta_erro(self):
        with self.assertRaises(AtivoNaoEncontradoError):
            self.servico.atualizar(999, "Fulano", "TI", TipoAtivo.SERVIDOR)

    def test_atualizar_com_responsavel_vazio_levanta_erro_de_validacao(self):
        ativo = self.servico.cadastrar(
            "Servidor-01", "Fulano", "TI", TipoAtivo.SERVIDOR
        )

        with self.assertRaises(ErroDeValidacao):
            self.servico.atualizar(ativo.id, "", "TI", TipoAtivo.SERVIDOR)

    # --- Delete ---------------------------------------------------------

    def test_excluir_remove_ativo_do_cache_e_do_banco(self):
        ativo = self.servico.cadastrar(
            "Servidor-01", "Fulano", "TI", TipoAtivo.SERVIDOR
        )

        with self.assertLogs(NOME_DO_LOGGER, level="INFO"):
            self.servico.excluir(ativo.id)

        with self.assertRaises(AtivoNaoEncontradoError):
            self.servico.buscar_por_id(ativo.id)

    def test_excluir_ativo_inexistente_levanta_erro(self):
        with self.assertRaises(AtivoNaoEncontradoError):
            self.servico.excluir(999)

    # --- Cache (RF10 / RNF05) ----------------------------------------

    def test_nova_instancia_do_servico_recarrega_cache_a_partir_do_banco(self):
        self.servico.cadastrar("Servidor-01", "Fulano", "TI", TipoAtivo.SERVIDOR)

        outro_servico_apontando_para_o_mesmo_banco = AtivoService(
            AtivoRepository(self.banco)
        )

        self.assertEqual(
            len(outro_servico_apontando_para_o_mesmo_banco.listar_todos()), 1
        )
