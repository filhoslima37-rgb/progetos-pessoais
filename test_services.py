import sqlite3
from datetime import date
from io import BytesIO
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import pytest

from auth import autenticar_usuario, cadastrar_usuario
from database import conectar, criar_tabela
from services import (
    cadastrar_transacao,
    calcular_saldo,
    calcular_totais,
    editar_transacao,
    excluir_transacao,
    listar_transacoes,
)
from relatorios import gerar_excel, gerar_pdf, obter_relatorio
from metas import criar_meta, editar_meta, excluir_meta, listar_metas, registrar_economia


SENHA_TESTE = "Senha forte 123!"


@pytest.fixture
def banco(tmp_path):
    caminho = tmp_path / "financeiro_teste.db"
    criar_tabela(caminho)
    return caminho


@pytest.fixture
def usuario(banco):
    return cadastrar_usuario("testador", "testador@example.com", SENHA_TESTE, banco)


def test_conexao_e_tabela_existente(banco):
    with conectar(banco) as conexao:
        tabela = conexao.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            ("transacoes",),
        ).fetchone()
        chave_estrangeira = conexao.execute(
            "PRAGMA foreign_key_list(transacoes)"
        ).fetchall()
    assert tabela["name"] == "transacoes"
    assert any(
        chave["table"] == "usuarios" and chave["from"] == "usuario_id"
        for chave in chave_estrangeira
    )


def test_cadastrar_e_listar_transacao(banco, usuario):
    id_transacao = cadastrar_transacao(usuario, "Salário", 2500, "receita", banco)
    assert listar_transacoes(usuario, banco) == [{
        "id": id_transacao,
        "descricao": "Salário",
        "valor": 2500.0,
        "tipo": "receita",
        "data": date.today().isoformat(),
        "categoria": "Geral",
    }]


def test_editar_transacao(banco, usuario):
    id_transacao = cadastrar_transacao(usuario, "Compra", 30, "despesa", banco)
    assert editar_transacao(usuario, id_transacao, "Mercado", 45.5, "despesa", banco)
    assert listar_transacoes(usuario, banco)[0]["descricao"] == "Mercado"
    assert listar_transacoes(usuario, banco)[0]["valor"] == 45.5


def test_editar_tipo_atualiza_saldo_e_id_inexistente(banco, usuario):
    id_transacao = cadastrar_transacao(usuario, "Pagamento", 400, "despesa", banco)
    assert calcular_saldo(caminho=banco, usuario_id=usuario) == -400

    assert editar_transacao(usuario, id_transacao, "Reembolso", 400, "receita", banco)
    assert calcular_saldo(caminho=banco, usuario_id=usuario) == 400
    assert not editar_transacao(usuario, 99999, "Outra", 1, "receita", banco)


def test_excluir_transacao(banco, usuario):
    id_transacao = cadastrar_transacao(usuario, "Conta", 100, "despesa", banco)
    assert excluir_transacao(usuario, id_transacao, banco)
    assert listar_transacoes(usuario, banco) == []
    assert not excluir_transacao(usuario, id_transacao, banco)


def test_calcular_saldo_das_transacoes_no_banco(banco, usuario):
    cadastrar_transacao(usuario, "Salário", 2500, "receita", banco)
    cadastrar_transacao(usuario, "Aluguel", 900, "despesa", banco)
    cadastrar_transacao(usuario, "Mercado", 150, "despesa", banco)
    assert calcular_saldo(caminho=banco, usuario_id=usuario) == 1450


def test_calcular_saldo_sem_transacoes(banco, usuario):
    assert calcular_saldo(caminho=banco, usuario_id=usuario) == 0


def test_filtro_de_periodo_calcula_totais(banco, usuario):
    cadastrar_transacao(usuario, "Salário", 3000, "receita", banco, data="2025-04-01")
    cadastrar_transacao(usuario, "Aluguel", 1000, "despesa", banco, data="2025-04-05")
    cadastrar_transacao(usuario, "Extra", 500, "receita", banco, data="2025-05-01")

    assert calcular_totais(usuario, "2025-04-01", "2025-04-30", caminho=banco) == {
        "receitas": 3000.0,
        "despesas": 1000.0,
        "saldo": 2000.0,
    }
    assert calcular_totais(
        usuario, "2025-04-01", "2025-04-30", caminho=banco, tipo="despesa"
    ) == {"receitas": 0, "despesas": 1000.0, "saldo": -1000.0}


def test_migra_tabela_antiga_com_transacoes(tmp_path):
    caminho = tmp_path / "banco_antigo.db"
    conexao = sqlite3.connect(caminho)
    conexao.execute("""
        CREATE TABLE transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL,
            valor REAL NOT NULL,
            tipo TEXT NOT NULL
        )
    """)
    conexao.execute(
        "INSERT INTO transacoes (descricao, valor, tipo) VALUES (?, ?, ?)",
        ("Registro antigo", 25, "despesa"),
    )
    conexao.commit()
    conexao.close()

    criar_tabela(caminho)
    usuario_id = cadastrar_usuario("migrado", "migrado@example.com", SENHA_TESTE, caminho)
    transacoes = listar_transacoes(usuario_id, caminho)
    assert len(transacoes) == 1
    assert transacoes[0]["descricao"] == "Registro antigo"
    assert transacoes[0]["data"]
    assert transacoes[0]["categoria"] == "Geral"
    outro_usuario = cadastrar_usuario(
        "outro", "outro@example.com", SENHA_TESTE, caminho
    )
    assert listar_transacoes(outro_usuario, caminho) == []


@pytest.mark.parametrize(
    "descricao,valor,tipo",
    [("", 10, "receita"), ("Compra", 0, "despesa"), ("Compra", -1, "despesa"),
     ("Compra", 10, "outro")],
)
def test_rejeita_transacao_invalida(banco, usuario, descricao, valor, tipo):
    with pytest.raises(ValueError):
        cadastrar_transacao(usuario, descricao, valor, tipo, banco)
    assert listar_transacoes(usuario, banco) == []


def test_cadastrar_usuario_guarda_hash_e_permite_login(banco):
    usuario_id = cadastrar_usuario("alice", "Alice@example.com", SENHA_TESTE, banco)
    with conectar(banco) as conexao:
        registro = conexao.execute(
            "SELECT senha_hash FROM usuarios WHERE id = ?", (usuario_id,)
        ).fetchone()

    assert registro["senha_hash"] != SENHA_TESTE
    assert registro["senha_hash"].startswith("pbkdf2_sha256$")
    outro_id = cadastrar_usuario(
        "alice2", "alice2@example.com", SENHA_TESTE, banco
    )
    with conectar(banco) as conexao:
        outro_hash = conexao.execute(
            "SELECT senha_hash FROM usuarios WHERE id = ?", (outro_id,)
        ).fetchone()["senha_hash"]
    assert outro_hash != registro["senha_hash"]
    assert autenticar_usuario("alice", SENHA_TESTE, banco)["id"] == usuario_id
    assert autenticar_usuario("alice@example.com", SENHA_TESTE, banco)["id"] == usuario_id


def test_login_com_senha_incorreta_falha(banco):
    cadastrar_usuario("alice", "alice@example.com", SENHA_TESTE, banco)
    assert autenticar_usuario("alice", "senha errada", banco) is None
    assert autenticar_usuario("naoexiste", "senha errada", banco) is None


def test_impede_nome_de_usuario_ou_email_duplicado(banco):
    cadastrar_usuario("alice", "alice@example.com", SENHA_TESTE, banco)
    with pytest.raises(ValueError, match="já cadastrado"):
        cadastrar_usuario("ALICE", "outra@example.com", SENHA_TESTE, banco)
    with pytest.raises(ValueError, match="já cadastrado"):
        cadastrar_usuario("outra", "ALICE@example.com", SENHA_TESTE, banco)


def test_valida_campos_de_cadastro(banco):
    with pytest.raises(ValueError):
        cadastrar_usuario("ab", "alice@example.com", SENHA_TESTE, banco)
    with pytest.raises(ValueError):
        cadastrar_usuario("alice", "email-invalido", SENHA_TESTE, banco)
    with pytest.raises(ValueError):
        cadastrar_usuario("alice", "alice@example.com", "curta", banco)


def test_transacoes_isoladas_e_operacoes_de_outro_usuario_bloqueadas(banco):
    alice = cadastrar_usuario("alice", "alice@example.com", SENHA_TESTE, banco)
    bob = cadastrar_usuario("bob", "bob@example.com", SENHA_TESTE, banco)
    id_alice = cadastrar_transacao(alice, "Salário", 3000, "receita", banco)

    assert len(listar_transacoes(alice, banco)) == 1
    assert listar_transacoes(bob, banco) == []
    assert not editar_transacao(bob, id_alice, "Alterada", 1, "despesa", banco)
    assert not excluir_transacao(bob, id_alice, banco)
    assert listar_transacoes(alice, banco)[0]["descricao"] == "Salário"
    assert calcular_totais(bob, caminho=banco)["saldo"] == 0


def test_operacoes_exigem_usuario_existente(banco):
    with pytest.raises(PermissionError):
        listar_transacoes(98765, banco)
    with pytest.raises(PermissionError):
        cadastrar_transacao(98765, "Sem dono", 10, "receita", banco)


def test_relatorio_mensal_resumo_e_filtro_de_categoria(banco):
    alice = cadastrar_usuario("alice", "alice@example.com", SENHA_TESTE, banco)
    bob = cadastrar_usuario("bob", "bob@example.com", SENHA_TESTE, banco)
    cadastrar_transacao(
        alice, "Pagamento", 5000, "receita", banco,
        data="2025-06-01", categoria="Salario",
    )
    cadastrar_transacao(
        alice, "Aluguel", 1500, "despesa", banco,
        data="2025-06-03", categoria="Moradia",
    )
    cadastrar_transacao(
        bob, "Privado de Bob", 9000, "receita", banco,
        data="2025-06-02", categoria="Salario",
    )

    relatorio = obter_relatorio(
        alice, "2025-06-01", "2025-06-30", caminho=banco
    )
    assert relatorio["resumo"] == {
        "receitas": 5000.0,
        "despesas": 1500.0,
        "saldo": 3500.0,
    }
    assert relatorio["mensal"] == [{
        "mes": "2025-06",
        "receitas": 5000.0,
        "despesas": 1500.0,
        "saldo": 3500.0,
    }]
    assert {item["descricao"] for item in relatorio["transacoes"]} == {
        "Pagamento", "Aluguel"
    }

    filtrado = obter_relatorio(
        alice, "2025-06-01", "2025-06-30", categoria="Moradia", caminho=banco
    )
    assert filtrado["resumo"] == {
        "receitas": 0,
        "despesas": 1500.0,
        "saldo": -1500.0,
    }
    assert [item["descricao"] for item in filtrado["transacoes"]] == ["Aluguel"]


def test_exportacoes_excel_e_pdf_contem_apenas_dados_do_usuario(banco):
    alice = cadastrar_usuario("alice", "alice@example.com", SENHA_TESTE, banco)
    bob = cadastrar_usuario("bob", "bob@example.com", SENHA_TESTE, banco)
    cadastrar_transacao(
        alice, "Dado de Alice", 25, "despesa", banco, categoria="Lazer"
    )
    cadastrar_transacao(
        bob, "Dado privado de Bob", 700, "receita", banco, categoria="Trabalho"
    )

    arquivo_excel = gerar_excel(alice, caminho=banco)
    with ZipFile(BytesIO(arquivo_excel)) as arquivo:
        assert arquivo.testzip() is None
        transacoes_xml = arquivo.read("xl/worksheets/sheet1.xml").decode("utf-8")
        workbook = ET.fromstring(arquivo.read("xl/workbook.xml"))
        nomes_abas = {
            aba.attrib["name"]
            for aba in workbook.findall(
                ".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet"
            )
        }
        for nome in (
            "[Content_Types].xml",
            "_rels/.rels",
            "xl/_rels/workbook.xml.rels",
            "xl/worksheets/sheet1.xml",
            "xl/worksheets/sheet2.xml",
            "xl/worksheets/sheet3.xml",
        ):
            if nome.endswith(".xml"):
                ET.fromstring(arquivo.read(nome))
    assert nomes_abas == {"Transacoes", "Resumo", "Mensal"}
    assert "Dado de Alice" in transacoes_xml
    assert "Dado privado de Bob" not in transacoes_xml
    arquivo_pdf = gerar_pdf(alice, caminho=banco)
    assert arquivo_pdf.startswith(b"%PDF-1.4")
    assert b"Dado de Alice" in arquivo_pdf
    assert b"Dado privado de Bob" not in arquivo_pdf
    posicao_xref = int(arquivo_pdf.split(b"startxref\n", 1)[1].splitlines()[0])
    assert arquivo_pdf[posicao_xref:posicao_xref + 4] == b"xref"


def test_criar_meta_registrar_economia_e_calcular_progresso(banco, usuario):
    meta_id = criar_meta(usuario, "Reserva de emergencia", 2000, "2027-12-31", banco)
    assert registrar_economia(usuario, meta_id, 500, banco)
    meta = listar_metas(usuario, banco)[0]
    assert meta["id"] == meta_id
    assert meta["valor_economizado"] == 500
    assert meta["progresso"] == 0.25
    assert meta["faltante"] == 1500

    assert registrar_economia(usuario, meta_id, 1800, banco)
    meta = listar_metas(usuario, banco)[0]
    assert meta["progresso"] == 1
    assert meta["faltante"] == 0


def test_editar_excluir_e_isolar_metas_por_usuario(banco):
    alice = cadastrar_usuario("alice", "alice@example.com", SENHA_TESTE, banco)
    bob = cadastrar_usuario("bob", "bob@example.com", SENHA_TESTE, banco)
    meta_id = criar_meta(alice, "Viagem", 4000, "2027-06-01", banco)

    assert listar_metas(bob, banco) == []
    assert not editar_meta(bob, meta_id, "Alterada", 1, "2027-01-01", banco)
    assert not excluir_meta(bob, meta_id, banco)
    assert not registrar_economia(bob, meta_id, 100, banco)
    assert listar_metas(alice, banco)[0]["nome"] == "Viagem"

    assert editar_meta(alice, meta_id, "Viagem longa", 5000, "2027-08-01", banco)
    assert listar_metas(alice, banco)[0]["valor_objetivo"] == 5000
    assert excluir_meta(alice, meta_id, banco)
    assert listar_metas(alice, banco) == []


@pytest.mark.parametrize(
    "nome,valor,prazo",
    [("", 100, "2027-01-01"), ("Meta", 0, "2027-01-01"),
     ("Meta", -1, "2027-01-01"), ("Meta", 100, "data-invalida")],
)
def test_rejeita_dados_invalidos_de_meta(banco, usuario, nome, valor, prazo):
    with pytest.raises(ValueError):
        criar_meta(usuario, nome, valor, prazo, banco)


def test_operacoes_de_meta_exigem_usuario_existente(banco):
    with pytest.raises(PermissionError):
        listar_metas(123456, banco)
