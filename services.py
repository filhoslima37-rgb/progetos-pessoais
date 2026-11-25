def calcular_saldo(receitas, despesas):
    return receitas - despesas


def adicionar_transacao(transacoes, descricao, valor, tipo):
    if valor <= 0:
        raise ValueError("O valor deve ser positivo.")

    if tipo not in ("receita", "despesa"):
        raise ValueError("Tipo inválido.")

    transacao = {
        "descricao": descricao,
        "valor": valor,
        "tipo": tipo
    }

    transacoes.append(transacao)