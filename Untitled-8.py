test/financeiro/test_financeiro.py
import pytest

from services.financeiro import (
    calcular_saldo,
    adicionar_transacao
)


def test_calcular_saldo():
    assert calcular_saldo(2000, 500) == 1500


def test_adicionar_receita():
    transacoes = []

    adicionar_transacao(
        transacoes,
        "Salário",
        2000,
        "receita"
    )

    assert len(transacoes) == 1
    assert transacoes[0]["valor"] == 2000


def test_impedir_valor_negativo():
    transacoes = []

    with pytest.raises(ValueError):
        adicionar_transacao(
            transacoes,
            "Compra",
            -100,
            "despesa"
        )
