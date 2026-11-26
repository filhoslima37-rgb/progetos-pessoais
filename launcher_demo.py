"""Launcher empacotavel para a demonstracao do Sistema Financeiro."""

import os
from pathlib import Path
import sys

import pandas  # Garante que o PyInstaller inclua o suporte a tabelas/gráficos.

from demo import SENHA_DEMO, USUARIO_DEMO, preparar_demo


def main():
    """Prepara uma base isolada e inicia o servidor Streamlit empacotado."""
    pasta_dados = Path(
        os.environ.get(
            "FINANCEIRO_DEMO_DATA_DIR",
            str(Path(os.environ.get("LOCALAPPDATA", Path.home())) / "FinanceiroDemo"),
        )
    )
    pasta_dados.mkdir(parents=True, exist_ok=True)
    banco_demo = pasta_dados / "financeiro_demo.db"
    preparar_demo(banco_demo)
    os.environ["FINANCEIRO_DB_PATH"] = str(banco_demo)

    pasta_app = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    caminho_app = pasta_app / "app.py"
    if not caminho_app.is_file():
        raise FileNotFoundError(f"Arquivo da aplicacao nao encontrado: {caminho_app}")

    print("Sistema Financeiro - demonstracao")
    porta = os.environ.get("FINANCEIRO_DEMO_PORT", "8766")
    print(f"O navegador abrira em http://localhost:{porta}")
    print(f"Usuario: {USUARIO_DEMO} | Senha: {SENHA_DEMO}")

    from streamlit.web import cli as streamlit_cli

    sys.argv = [
        "streamlit", "run", str(caminho_app),
        "--global.developmentMode=false",
        "--server.headless=false", f"--server.port={porta}",
        "--browser.gatherUsageStats=false",
    ]
    streamlit_cli.main()


if __name__ == "__main__":
    main()
