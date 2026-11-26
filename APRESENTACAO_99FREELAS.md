# Apresentação para 99Freelas — Controle Financeiro Pessoal

## Descrição curta

Aplicação web demonstrativa para controle de receitas e despesas, acompanhamento de metas financeiras e geração de relatórios em Excel e PDF.

## Texto para apresentar o projeto

Desenvolvi um sistema de controle financeiro pessoal com dashboard interativo para acompanhar receitas, despesas e saldo por período. A aplicação permite cadastrar e organizar transações por categoria, aplicar filtros, acompanhar metas de economia e exportar relatórios mensais em Excel e PDF.

O projeto foi desenvolvido em Python com Streamlit e SQLite. Inclui autenticação de usuários, hash de senhas e consultas financeiras vinculadas à conta. A demonstração pode ser executada localmente com dados fictícios, sem usar o banco de dados pessoal.

## Principais recursos

- Dashboard com indicadores e gráfico mensal.
- Cadastro, edição e exclusão de receitas e despesas.
- Filtros por tipo, categoria e período.
- Metas financeiras com prazo, aportes e progresso.
- Relatórios mensais com exportação em Excel e PDF.
- Demonstração local usando banco de dados separado.

## Tecnologias

Python, Streamlit, SQLite e Pandas.

## Como demonstrar

Instale as dependências com `py -m pip install -r requirements.txt`, execute `py demo.py` e acesse `http://localhost:8766`. Use a conta fictícia `demo` / `DemoFinanceiro2026!`. A demonstração é local e não deve receber dados reais nem ser publicada como serviço compartilhado sem uma etapa própria de implantação e revisão de segurança.

## Observação de escopo

Este repositório apresenta um projeto demonstrativo local. A publicação em ambiente de produção, integração com serviços externos, implantação em nuvem, suporte e novos recursos devem ser definidos como escopo separado conforme a necessidade do cliente.