import math
from contextlib import closing
from datetime import date

from database import conectar, criar_tabela


def calcular_saldo(receitas=None, despesas=None, caminho=None, usuario_id=None):
    """Calcula o saldo do usuario ou, por compatibilidade, de dois valores."""
    if receitas is not None and despesas is not None:
        return receitas - despesas
    if receitas is not None or despesas is not None:
        raise TypeError("Informe receitas e despesas juntos ou nenhum dos dois.")
    if usuario_id is None:
        raise PermissionError("Autentique-se para consultar o saldo do banco.")
    return calcular_totais(usuario_id, caminho=caminho)["saldo"]


def adicionar_transacao(transacoes, descricao, valor, tipo):
    """Mantem a API em memoria ja usada pelo projeto."""
    _validar_transacao(descricao, valor, tipo)
    transacoes.append({"descricao": descricao.strip(), "valor": valor, "tipo": tipo})


def _validar_transacao(descricao, valor, tipo):
    if not isinstance(descricao, str) or not descricao.strip():
        raise ValueError("A descricao e obrigatoria.")
    if (
        isinstance(valor, bool)
        or not isinstance(valor, (int, float))
        or not math.isfinite(valor)
        or valor <= 0
    ):
        raise ValueError("O valor deve ser positivo e finito.")
    if tipo not in ("receita", "despesa"):
        raise ValueError("Tipo invalido.")


def _validar_categoria(categoria):
    if not isinstance(categoria, str) or not categoria.strip():
        raise ValueError("A categoria e obrigatoria.")
    categoria = categoria.strip()
    if len(categoria) > 50:
        raise ValueError("A categoria deve ter no maximo 50 caracteres.")
    return categoria


def _validar_usuario_id(usuario_id):
    if isinstance(usuario_id, bool) or not isinstance(usuario_id, int) or usuario_id <= 0:
        raise PermissionError("Usuario autenticado invalido.")


def _normalizar_data(data_transacao):
    if data_transacao is None:
        return date.today().isoformat()
    if isinstance(data_transacao, date):
        return data_transacao.isoformat()
    if not isinstance(data_transacao, str):
        raise ValueError("A data deve estar no formato AAAA-MM-DD.")
    try:
        return date.fromisoformat(data_transacao).isoformat()
    except ValueError as erro:
        raise ValueError("A data deve estar no formato AAAA-MM-DD.") from erro


def exigir_usuario(conexao, usuario_id):
    _validar_usuario_id(usuario_id)
    existe = conexao.execute(
        "SELECT 1 FROM usuarios WHERE id = ?", (usuario_id,)
    ).fetchone()
    if existe is None:
        raise PermissionError("Usuario autenticado nao existe.")


def cadastrar_transacao(
    usuario_id, descricao, valor, tipo, caminho=None, data=None, categoria="Geral"
):
    """Cadastra uma transacao vinculada ao usuario autenticado."""
    _validar_transacao(descricao, valor, tipo)
    data = _normalizar_data(data)
    categoria = _validar_categoria(categoria)
    criar_tabela(caminho)
    with closing(conectar(caminho)) as conexao:
        exigir_usuario(conexao, usuario_id)
        cursor = conexao.execute(
            """INSERT INTO transacoes
               (descricao, valor, tipo, data, categoria, usuario_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (descricao.strip(), valor, tipo, data, categoria, usuario_id),
        )
        conexao.commit()
        return cursor.lastrowid


def listar_transacoes(
    usuario_id, caminho=None, data_inicio=None, data_fim=None, categoria=None
):
    """Lista apenas transacoes do usuario, com filtros opcionais."""
    criar_tabela(caminho)
    with closing(conectar(caminho)) as conexao:
        exigir_usuario(conexao, usuario_id)
        condicoes = ["usuario_id = ?"]
        parametros = [usuario_id]
        if data_inicio is not None:
            condicoes.append("data >= ?")
            parametros.append(_normalizar_data(data_inicio))
        if data_fim is not None:
            condicoes.append("data <= ?")
            parametros.append(_normalizar_data(data_fim))
        if categoria is not None:
            condicoes.append("categoria = ?")
            parametros.append(_validar_categoria(categoria))
        registros = conexao.execute(
            f"""SELECT id, descricao, valor, tipo, data, categoria
                FROM transacoes WHERE {' AND '.join(condicoes)}
                ORDER BY data DESC, id DESC""",
            parametros,
        ).fetchall()
        return [dict(registro) for registro in registros]


def editar_transacao(
    usuario_id, id_transacao, descricao, valor, tipo, caminho=None, data=None,
    categoria="Geral",
):
    """Edita uma transacao somente se pertencer ao usuario."""
    _validar_transacao(descricao, valor, tipo)
    data = _normalizar_data(data)
    categoria = _validar_categoria(categoria)
    criar_tabela(caminho)
    with closing(conectar(caminho)) as conexao:
        exigir_usuario(conexao, usuario_id)
        cursor = conexao.execute(
            """UPDATE transacoes
               SET descricao = ?, valor = ?, tipo = ?, data = ?, categoria = ?
               WHERE id = ? AND usuario_id = ?""",
            (descricao.strip(), valor, tipo, data, categoria, id_transacao, usuario_id),
        )
        conexao.commit()
        return cursor.rowcount > 0


def excluir_transacao(usuario_id, id_transacao, caminho=None):
    """Exclui uma transacao somente se pertencer ao usuario."""
    criar_tabela(caminho)
    with closing(conectar(caminho)) as conexao:
        exigir_usuario(conexao, usuario_id)
        cursor = conexao.execute(
            "DELETE FROM transacoes WHERE id = ? AND usuario_id = ?",
            (id_transacao, usuario_id),
        )
        conexao.commit()
        return cursor.rowcount > 0


def calcular_totais(
    usuario_id, data_inicio=None, data_fim=None, caminho=None, tipo=None,
    categoria=None,
):
    """Calcula os totais de um usuario com filtros opcionais."""
    criar_tabela(caminho)
    condicoes = ["usuario_id = ?"]
    parametros = [usuario_id]
    if data_inicio is not None:
        condicoes.append("data >= ?")
        parametros.append(_normalizar_data(data_inicio))
    if data_fim is not None:
        condicoes.append("data <= ?")
        parametros.append(_normalizar_data(data_fim))
    if tipo is not None:
        if tipo not in ("receita", "despesa"):
            raise ValueError("Tipo invalido.")
        condicoes.append("tipo = ?")
        parametros.append(tipo)
    if categoria is not None:
        condicoes.append("categoria = ?")
        parametros.append(_validar_categoria(categoria))

    where = " AND ".join(condicoes)
    with closing(conectar(caminho)) as conexao:
        exigir_usuario(conexao, usuario_id)
        totais = conexao.execute(f"""
            SELECT
                COALESCE(SUM(CASE WHEN tipo = 'receita' THEN valor ELSE 0 END), 0) AS receitas,
                COALESCE(SUM(CASE WHEN tipo = 'despesa' THEN valor ELSE 0 END), 0) AS despesas
            FROM transacoes
            WHERE {where}
        """, parametros).fetchone()
    receitas = totais["receitas"]
    despesas = totais["despesas"]
    return {"receitas": receitas, "despesas": despesas, "saldo": receitas - despesas}
