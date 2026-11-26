# Sistema financeiro

Aplicacao em Python com Streamlit e SQLite, com autenticacao, isolamento de
transacoes por usuario e relatorios financeiros.

O sistema permite controlar receitas e despesas, acompanhar metas de economia e
consultar relatorios mensais. Os dados ficam no SQLite e cada conta acessa
somente suas proprias transacoes e metas.

## Recursos

- Dashboard autenticado com saldo, receitas, despesas e evolucao mensal.
- Cadastro, edicao e exclusao de transacoes por usuario.
- Categoria, tipo e intervalo de datas como filtros.
- Relatorio mensal com receitas, despesas e saldo.
- Metas financeiras por usuario, com prazo, aportes, progresso, edicao e exclusao.
- Exportacao das transacoes e dos resumos para Excel (`.xlsx`) e PDF (`.pdf`).
- Hash de senha PBKDF2-SHA256; senhas nao sao armazenadas em texto puro.

O modulo `services.py` centraliza as consultas financeiras com escopo de dono.
`relatorios.py` reutiliza esses servicos para montar os relatorios e arquivos.
`metas.py` gerencia metas e valores economizados, sempre vinculados ao usuario.
`database.py` cria e migra o esquema, incluindo a categoria `Geral` para os
registros antigos.

## Instalar e executar

No terminal, dentro da pasta do projeto:

```bash
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

No Windows, depois de instalar as dependencias, tambem e possivel iniciar com
duplo clique em `iniciar_sistema.bat`.

Crie uma conta ou entre na tela inicial. Os downloads respeitam o periodo e a
categoria selecionados e incluem somente transacoes da conta autenticada.
Os arquivos XLSX e PDF sao gerados em memoria, sem gravar copias no projeto.

## Testes

```bash
py -m pytest test.py test_services.py
```

Os testes usam bancos temporarios e nao alteram `financeiro.db`.
