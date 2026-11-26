"""Prepara uma base ficticia isolada e abre a demonstracao do sistema."""

from calendar import monthrange
from contextlib import closing
from datetime import date, timedelta
import os
from pathlib import Path
import subprocess
import sys

from auth import cadastrar_usuario
from database import conectar, criar_tabela
from metas import criar_meta, registrar_economia
from services import cadastrar_transacao


PASTA_PROJETO = Path(__file__).resolve().parent
BANCO_DEMO = PASTA_PROJETO / "financeiro_demo.db"
USUARIO_DEMO = "demo"
SENHA_DEMO = "DemoFinanceiro2026!"


def _data_mes(meses_atras):
    hoje = date.today()
    indice = hoje.year * 12 + hoje.month - 1 - meses_atras
    ano, mes_zero = divmod(indice, 12)
    mes = mes_zero + 1
    return date(ano, mes, min(hoje.day, monthrange(ano, mes)[1]))


def preparar_demo(caminho=BANCO_DEMO):
    """Cria dados de exemplo uma unica vez sem tocar no banco real."""
    criar_tabela(caminho)
    with closing(conectar(caminho)) as conexao:
        usuario = conexao.execute(
            "SELECT id FROM usuarios WHERE nome_usuario = ?", (USUARIO_DEMO,)
        ).fetchone()
    usuario_id = (
        usuario["id"]
        if usuario
        else cadastrar_usuario(
            USUARIO_DEMO, "demo@example.com", SENHA_DEMO, caminho
        )
    )

    with closing(conectar(caminho)) as conexao:
        total_transacoes = conexao.execute(
            "SELECT COUNT(*) FROM transacoes WHERE usuario_id = ?", (usuario_id,)
        ).fetchone()[0]
        total_metas = conexao.execute(
            "SELECT COUNT(*) FROM metas WHERE usuario_id = ?", (usuario_id,)
        ).fetchone()[0]

    if total_transacoes == 0:
        for meses_atras in (2, 1, 0):
            data_transacao = _data_mes(meses_atras)
            cadastrar_transacao(
                usuario_id, "Salario mensal", 5200, "receita", caminho,
                data=data_transacao, categoria="Salario",
            )
            cadastrar_transacao(
                usuario_id, "Moradia", 1650, "despesa", caminho,
                data=data_transacao, categoria="Moradia",
            )
            cadastrar_transacao(
                usuario_id, "Mercado", 740, "despesa", caminho,
                data=data_transacao, categoria="Alimentacao",
            )

    if total_metas == 0:
        prazo = date.today() + timedelta(days=180)
        reserva = criar_meta(usuario_id, "Reserva de emergencia", 8000, prazo, caminho)
        registrar_economia(usuario_id, reserva, 3250, caminho)
        viagem = criar_meta(
            usuario_id, "Viagem", 5000, date.today() + timedelta(days=300), caminho
        )
        registrar_economia(usuario_id, viagem, 1800, caminho)

    return usuario_id


def main():
    preparar_demo()
    ambiente = os.environ.copy()
    ambiente["FINANCEIRO_DB_PATH"] = str(BANCO_DEMO)
    print("Demonstracao: http://localhost:8766")
    print(f"Usuario: {USUARIO_DEMO}")
    print(f"Senha: {SENHA_DEMO}")
    return subprocess.call(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(PASTA_PROJETO / "app.py"),
            "--server.headless",
            "true",
            "--server.port",
            "8766",
        ],
        cwd=PASTA_PROJETO,
        env=ambiente,
    )


if __name__ == "__main__":
    raise SystemExit(main())
