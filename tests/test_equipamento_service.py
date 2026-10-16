"""Testes da camada de regras de negócio (EquipamentoService):
CRUD, validações e cache."""

from app.exceptions import EquipamentoNaoEncontradoError, ErroDeValidacao
from app.models.equipamento import Equipamento, Firewall, Servidor
from app.repositories.equipamento_repository import EquipamentoRepository
from app.services.equipamento_service import EquipamentoService
from tests.base import CasoDeTesteComBancoTemporario

NOME_DO_LOGGER = "app.services.equipamento_service"


class TestEquipamentoService(CasoDeTesteComBancoTemporario):
    """Testes das regras de negócio de equipamentos."""

    def setUp(self) -> None:
        super().setUp()
        self.servico = EquipamentoService(EquipamentoRepository(self.banco))

    # --- Create -----------------------------------------------------

    def test_cadastrar_com_dados_validos_retorna_equipamento_persistido(self):
        with self.assertLogs(NOME_DO_LOGGER, level="INFO"):
            equipamento = self.servico.cadastrar(
                nome="Servidor Um",
                responsavel="Fulano de Tal",
                setor="TI",
                classe=Servidor,
                descricao="servidor de testes",
            )

        self.assertIsNotNone(equipamento.id)
        self.assertEqual(self.servico.buscar_por_id(equipamento.id), equipamento)

    def test_cadastrar_com_nome_vazio_levanta_erro_de_validacao(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.cadastrar(
                nome="   ", responsavel="Fulano", setor="TI", classe=Servidor
            )

    def test_cadastrar_com_responsavel_vazio_levanta_erro_de_validacao(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.cadastrar(
                nome="Servidor Um", responsavel="", setor="TI", classe=Servidor
            )

    def test_cadastrar_com_setor_vazio_levanta_erro_de_validacao(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.cadastrar(
                nome="Servidor Um",
                responsavel="Fulano",
                setor="",
                classe=Servidor,
            )

    def test_cadastrar_com_tipo_invalido_levanta_erro_de_validacao(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.cadastrar(
                nome="Servidor Um", responsavel="Fulano", setor="TI", classe="Servidor"
            )

    def test_cadastrar_com_classe_base_equipamento_levanta_erro_de_validacao(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.cadastrar(
                nome="Servidor Um", responsavel="Fulano", setor="TI", classe=Equipamento
            )

    # --- Read ---------------------------------------------------------

    def test_buscar_por_id_de_equipamento_inexistente_levanta_erro(self):
        with self.assertRaises(EquipamentoNaoEncontradoError):
            self.servico.buscar_por_id(999)

    def test_buscar_por_nome_encontra_por_substring_sem_diferenciar_maiusculas(self):
        self.servico.cadastrar("Servidor Banco", "Fulano", "TI", Servidor)

        encontrados = self.servico.buscar_por_nome("servidor banco")

        self.assertEqual(len(encontrados), 1)
        self.assertEqual(encontrados[0].nome, "Servidor Banco")

    def test_buscar_por_nome_sem_correspondencia_retorna_lista_vazia(self):
        self.servico.cadastrar("Servidor Banco", "Fulano", "TI", Servidor)

        self.assertEqual(self.servico.buscar_por_nome("inexistente"), [])

    def test_buscar_por_nome_vazio_retorna_todos_os_equipamentos(self):
        self.servico.cadastrar("Servidor Um", "Fulano", "TI", Servidor)
        self.servico.cadastrar("Servidor Dois", "Fulano", "TI", Servidor)

        self.assertEqual(len(self.servico.buscar_por_nome("")), 2)

    def test_listar_todos_retorna_equipamentos_ordenados_por_id(self):
        primeiro_equipamento = self.servico.cadastrar(
            "Servidor Um", "Fulano", "TI", Servidor
        )
        segundo_equipamento = self.servico.cadastrar(
            "Servidor Dois", "Fulano", "TI", Servidor
        )

        equipamentos_cadastrados = self.servico.listar_todos()

        self.assertEqual(
            [equipamento.id for equipamento in equipamentos_cadastrados],
            [primeiro_equipamento.id, segundo_equipamento.id],
        )

    # --- Update ---------------------------------------------------------

    def test_atualizar_altera_os_campos_permitidos(self):
        equipamento = self.servico.cadastrar("Servidor Um", "Fulano", "TI", Servidor)

        with self.assertLogs(NOME_DO_LOGGER, level="INFO"):
            equipamento_atualizado = self.servico.atualizar(
                equipamento_id=equipamento.id,
                responsavel="Ciclana",
                setor="Financeiro",
                classe=Firewall,
                descricao="atualizado pelo teste",
            )

        self.assertEqual(equipamento_atualizado.responsavel, "Ciclana")
        self.assertEqual(equipamento_atualizado.setor, "Financeiro")
        self.assertIsInstance(equipamento_atualizado, Firewall)
        self.assertEqual(equipamento_atualizado.id, equipamento.id)
        self.assertIs(
            self.servico.buscar_por_id(equipamento.id), equipamento_atualizado
        )
        self.assertEqual(
            self.servico.buscar_por_id(equipamento.id).responsavel, "Ciclana"
        )

    def test_atualizar_equipamento_inexistente_levanta_erro(self):
        with self.assertRaises(EquipamentoNaoEncontradoError):
            self.servico.atualizar(999, "Fulano", "TI", Servidor)

    def test_atualizar_com_responsavel_vazio_levanta_erro_de_validacao(self):
        equipamento = self.servico.cadastrar("Servidor Um", "Fulano", "TI", Servidor)

        with self.assertRaises(ErroDeValidacao):
            self.servico.atualizar(equipamento.id, "", "TI", Servidor)

    # --- Delete ---------------------------------------------------------

    def test_excluir_remove_equipamento_do_cache_e_do_banco(self):
        equipamento = self.servico.cadastrar("Servidor Um", "Fulano", "TI", Servidor)

        with self.assertLogs(NOME_DO_LOGGER, level="INFO"):
            self.servico.excluir(equipamento.id)

        with self.assertRaises(EquipamentoNaoEncontradoError):
            self.servico.buscar_por_id(equipamento.id)

    def test_excluir_equipamento_inexistente_levanta_erro(self):
        with self.assertRaises(EquipamentoNaoEncontradoError):
            self.servico.excluir(999)

    # --- Cache (RF10 / RNF05) ----------------------------------------

    def test_nova_instancia_do_servico_recarrega_cache_a_partir_do_banco(self):
        self.servico.cadastrar("Servidor Um", "Fulano", "TI", Servidor)

        outro_servico_apontando_para_o_mesmo_banco = EquipamentoService(
            EquipamentoRepository(self.banco)
        )

        self.assertEqual(
            len(outro_servico_apontando_para_o_mesmo_banco.listar_todos()), 1
        )


class TestEquipamentoServiceApenasLetras(CasoDeTesteComBancoTemporario):
    """Testes da regra que proíbe números e caracteres especiais nos textos."""

    def setUp(self) -> None:
        super().setUp()
        self.servico = EquipamentoService(EquipamentoRepository(self.banco))

    def test_cadastrar_com_numeros_no_nome_levanta_erro_de_validacao(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.cadastrar(
                nome="Servidor 01", responsavel="Fulano", setor="TI", classe=Servidor
            )

    def test_cadastrar_com_caractere_especial_levanta_erro_de_validacao(self):
        with self.assertLogs(NOME_DO_LOGGER, level="WARNING"):
            with self.assertRaises(ErroDeValidacao):
                self.servico.cadastrar(
                    nome="Servidor", responsavel="Fulano", setor="T.I.", classe=Servidor
                )

    def test_cadastrar_com_descricao_com_numeros_levanta_erro_de_validacao(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.cadastrar(
                "Servidor", "Fulano", "TI", Servidor, descricao="Sala 3"
            )

    def test_cadastrar_aceita_letras_acentuadas_e_espacos(self):
        equipamento = self.servico.cadastrar(
            "Estação Financeiro", "João Antônio", "Gestão", Servidor, "Câmera ç"
        )

        self.assertIsNotNone(equipamento.id)

    def test_atualizar_com_numeros_no_setor_levanta_erro_de_validacao(self):
        equipamento = self.servico.cadastrar("Servidor Um", "Fulano", "TI", Servidor)

        with self.assertRaises(ErroDeValidacao):
            self.servico.atualizar(equipamento.id, "Fulano", "Sala 2", Servidor)
