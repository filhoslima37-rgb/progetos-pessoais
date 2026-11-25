import sqlite3
from contextlib import closing
from pathlib import Path


DB_PATH = Path(__file__).resolve().with_name("financeiro.db")


def conectar(caminho=None):
    """Abre uma conexão SQLite com chaves estrangeiras habilitadas."""
    conexao = sqlite3.connect(DB_PATH if caminho is None else caminho)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def criar_tabela(caminho=None):
    """Cria o esquema atual e migra bancos legados sem descartar transações."""
    with closing(conectar(caminho)) as conexao:
        conexao.execute("BEGIN IMMEDIATE")
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_usuario TEXT NOT NULL COLLATE NOCASE UNIQUE,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                senha_hash TEXT NOT NULL,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS transacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descricao TEXT NOT NULL,
                valor REAL NOT NULL,
                tipo TEXT NOT NULL,
                data TEXT NOT NULL DEFAULT '',
                categoria TEXT NOT NULL DEFAULT 'Geral',
                usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE
            )
        """)
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS metas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
                nome TEXT NOT NULL,
                valor_objetivo REAL NOT NULL CHECK (valor_objetivo > 0),
                prazo TEXT NOT NULL,
                valor_economizado REAL NOT NULL DEFAULT 0
                    CHECK (valor_economizado >= 0),
                criada_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        colunas = {
            coluna["name"]
            for coluna in conexao.execute("PRAGMA table_info(transacoes)")
        }
        if "data" not in colunas:
            conexao.execute(
                "ALTER TABLE transacoes ADD COLUMN data TEXT NOT NULL DEFAULT ''"
            )
        if "categoria" not in colunas:
            conexao.execute(
                "ALTER TABLE transacoes ADD COLUMN categoria TEXT NOT NULL DEFAULT 'Geral'"
            )
        if "usuario_id" not in colunas:
            conexao.execute(
                "ALTER TABLE transacoes ADD COLUMN usuario_id INTEGER "
                "REFERENCES usuarios(id) ON DELETE CASCADE"
            )

        conexao.execute(
            "UPDATE transacoes SET data = DATE('now') WHERE data IS NULL OR data = ''"
        )
        conexao.execute("""
            CREATE TRIGGER IF NOT EXISTS transacoes_usuario_obrigatorio_insert
            BEFORE INSERT ON transacoes
            WHEN NEW.usuario_id IS NULL
            BEGIN
                SELECT RAISE(ABORT, 'usuario_id obrigatorio');
            END
        """)
        conexao.execute("""
            CREATE TRIGGER IF NOT EXISTS transacoes_usuario_obrigatorio_update
            BEFORE UPDATE OF usuario_id ON transacoes
            WHEN NEW.usuario_id IS NULL
            BEGIN
                SELECT RAISE(ABORT, 'usuario_id obrigatorio');
            END
        """)
        conexao.commit()


if __name__ == "__main__":
    criar_tabela()
    print("Banco de dados pronto!")
