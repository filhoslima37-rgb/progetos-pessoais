"""Operacoes de metas financeiras com escopo por usuario autenticado."""

import math
from contextlib import closing

from database import conectar, criar_tabela
from services import _normalizar_data, exigir_usuario


def _validar_nome(nome):
    if not isinstance(nome, str) or not nome.strip():
        raise ValueError("O nome da meta e obrigatorio.")
    nome = nome.strip()
    if len(nome) > 100:
        raise ValueError("O nome da meta deve ter no maximo 100 caracteres.")
    return nome


def _validar_valor(valor):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor):
        raise ValueError("O valor deve ser numerico e finito.")
    if valor <= 0:
        raise ValueError("O valor deve ser positivo.")
    return float(valor)


def criar_meta(usuario_id, nome, valor_objetivo, prazo, caminho=None):
    """Cria uma meta financeira para o usuario autenticado."""
    nome = _validar_nome(nome)
    valor_objetivo = _validar_valor(valor_objetivo)
    prazo = _normalizar_data(prazo)
    criar_tabela(caminho)
    with closing(conectar(caminho)) as conexao:
        exigir_usuario(conexao, usuario_id)
        cursor = conexao.execute(
            """INSERT INTO metas (usuario_id, nome, valor_objetivo, prazo)
               VALUES (?, ?, ?, ?)""",
            (usuario_id, nome, valor_objetivo, prazo),
        )
        conexao.commit()
        return cursor.lastrowid


def listar_metas(usuario_id, caminho=None):
    """Lista metas do usuario com progresso e valor que falta."""
    criar_tabela(caminho)
    with closing(conectar(caminho)) as conexao:
        exigir_usuario(conexao, usuario_id)
        registros = conexao.execute(
            """SELECT id, nome, valor_objetivo, prazo, valor_economizado
               FROM metas WHERE usuario_id = ? ORDER BY prazo, id""",
            (usuario_id,),
        ).fetchall()
    metas = []
    for registro in registros:
        meta = dict(registro)
        meta["progresso"] = min(meta["valor_economizado"] / meta["valor_objetivo"], 1.0)
        meta["faltante"] = max(meta["valor_objetivo"] - meta["valor_economizado"], 0.0)
        metas.append(meta)
    return metas


def editar_meta(
    usuario_id, meta_id, nome, valor_objetivo, prazo, caminho=None
):
    """Edita nome, valor alvo e prazo somente da meta do proprio usuario."""
    nome = _validar_nome(nome)
    valor_objetivo = _validar_valor(valor_objetivo)
    prazo = _normalizar_data(prazo)
    criar_tabela(caminho)
    with closing(conectar(caminho)) as conexao:
        exigir_usuario(conexao, usuario_id)
        cursor = conexao.execute(
            """UPDATE metas SET nome = ?, valor_objetivo = ?, prazo = ?
               WHERE id = ? AND usuario_id = ?""",
            (nome, valor_objetivo, prazo, meta_id, usuario_id),
        )
        conexao.commit()
        return cursor.rowcount > 0


def excluir_meta(usuario_id, meta_id, caminho=None):
    """Exclui somente uma meta pertencente ao usuario."""
    criar_tabela(caminho)
    with closing(conectar(caminho)) as conexao:
        exigir_usuario(conexao, usuario_id)
        cursor = conexao.execute(
            "DELETE FROM metas WHERE id = ? AND usuario_id = ?",
            (meta_id, usuario_id),
        )
        conexao.commit()
        return cursor.rowcount > 0


def registrar_economia(usuario_id, meta_id, valor, caminho=None):
    """Adiciona um aporte ao valor economizado de uma meta do usuario."""
    valor = _validar_valor(valor)
    criar_tabela(caminho)
    with closing(conectar(caminho)) as conexao:
        exigir_usuario(conexao, usuario_id)
        cursor = conexao.execute(
            """UPDATE metas
               SET valor_economizado = valor_economizado + ?
               WHERE id = ? AND usuario_id = ?""",
            (valor, meta_id, usuario_id),
        )
        conexao.commit()
        return cursor.rowcount > 0
