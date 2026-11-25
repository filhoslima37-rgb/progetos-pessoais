from datetime import date, timedelta

import pandas as pd
import streamlit as st

from auth import autenticar_usuario, cadastrar_usuario, obter_usuario
from database import criar_tabela
from services import (
    calcular_totais,
    cadastrar_transacao,
    editar_transacao,
    excluir_transacao,
    listar_transacoes,
)
from relatorios import gerar_excel, gerar_pdf, obter_relatorio
from metas import (
    criar_meta,
    editar_meta,
    excluir_meta,
    listar_metas,
    registrar_economia,
)


st.set_page_config(page_title="Controle financeiro", page_icon="💰", layout="wide")
criar_tabela()


def _login_callback():
    identificador = st.session_state.get("login_identificador", "")
    senha = st.session_state.get("login_senha", "")
    usuario_autenticado = autenticar_usuario(identificador, senha)
    st.session_state.pop("login_senha", None)
    st.session_state.pop("login_identificador", None)
    st.session_state.login_erro = None
    if usuario_autenticado is None:
        st.session_state.login_erro = "Usuário ou senha inválidos."
    else:
        st.session_state.usuario_id = usuario_autenticado["id"]


def _cadastro_callback():
    nome_usuario = st.session_state.get("cadastro_nome", "")
    email = st.session_state.get("cadastro_email", "")
    senha = st.session_state.get("cadastro_senha", "")
    confirmar = st.session_state.get("cadastro_confirmacao", "")
    st.session_state.pop("cadastro_senha", None)
    st.session_state.pop("cadastro_confirmacao", None)
    st.session_state.cadastro_erro = None
    if senha != confirmar:
        st.session_state.cadastro_erro = "As senhas não coincidem."
        return
    try:
        st.session_state.usuario_id = cadastrar_usuario(nome_usuario, email, senha)
    except ValueError as erro:
        st.session_state.cadastro_erro = str(erro)


def mostrar_autenticacao():
    st.title("💰 Controle financeiro")
    st.caption("Entre na sua conta ou crie um novo cadastro.")
    aba_login, aba_cadastro = st.tabs(["Entrar", "Criar conta"])

    with aba_login:
        with st.form("form_login"):
            st.text_input("Nome de usuário ou e-mail", key="login_identificador")
            st.text_input("Senha", type="password", key="login_senha")
            st.form_submit_button(
                "Entrar", type="primary", on_click=_login_callback
            )
        if st.session_state.get("login_erro"):
            st.error(st.session_state.login_erro)

    with aba_cadastro:
        with st.form("form_cadastro_usuario"):
            st.text_input("Nome de usuário", key="cadastro_nome")
            st.text_input("E-mail", key="cadastro_email")
            st.text_input("Senha", type="password", key="cadastro_senha")
            st.text_input(
                "Confirme a senha", type="password", key="cadastro_confirmacao"
            )
            st.form_submit_button(
                "Criar conta", type="primary", on_click=_cadastro_callback
            )
        if st.session_state.get("cadastro_erro"):
            st.error(st.session_state.cadastro_erro)


usuario_id_sessao = st.session_state.get("usuario_id")
usuario = obter_usuario(usuario_id_sessao) if usuario_id_sessao else None
if usuario is None:
    st.session_state.pop("usuario_id", None)
    mostrar_autenticacao()
    st.stop()

usuario_id = usuario["id"]
st.title("💰 Controle financeiro")
st.caption(f"Conta: {usuario['nome_usuario']}")

with st.sidebar:
    st.header("Nova transação")
    if st.button("Sair da conta", use_container_width=True):
        st.session_state.pop("usuario_id", None)
        st.rerun()

    with st.form("form_cadastro_transacao", clear_on_submit=True):
        tipo_nova = st.selectbox("Tipo", ["receita", "despesa"], format_func=str.title)
        descricao_nova = st.text_input("Descrição")
        categoria_nova = st.text_input("Categoria", value="Geral")
        valor_novo = st.number_input(
            "Valor (R$)", min_value=0.01, step=0.01, format="%.2f"
        )
        data_nova = st.date_input("Data", value=date.today(), format="DD/MM/YYYY")
        cadastrar = st.form_submit_button(
            "Cadastrar", type="primary", use_container_width=True
        )

    if cadastrar:
        try:
            cadastrar_transacao(
                usuario_id, descricao_nova, valor_novo, tipo_nova,
                data=data_nova, categoria=categoria_nova,
            )
            st.success("Transação cadastrada.")
        except ValueError as erro:
            st.error(str(erro))

st.subheader("Filtros")
todas = listar_transacoes(usuario_id)
categorias = sorted({item["categoria"] for item in todas})
col_filtro_tipo, col_filtro_data = st.columns([1, 2])
with col_filtro_tipo:
    tipo_filtro = st.selectbox(
        "Tipo de transação", ["Todas", "Receitas", "Despesas"], index=0
    )
with col_filtro_data:
    hoje = date.today()
    intervalo = st.date_input(
        "Período",
        value=(hoje.replace(day=1), hoje),
        min_value=date(1900, 1, 1),
        max_value=date(2200, 12, 31),
        format="DD/MM/YYYY",
    )

if isinstance(intervalo, (tuple, list)) and len(intervalo) == 2:
    data_inicio, data_fim = intervalo
else:
    data_inicio, data_fim = None, None

tipo_sql = {"Todas": None, "Receitas": "receita", "Despesas": "despesa"}[tipo_filtro]
categoria_filtro = st.selectbox("Categoria", ["Todas", *categorias])
categoria_sql = None if categoria_filtro == "Todas" else categoria_filtro
totais = calcular_totais(
    usuario_id, data_inicio, data_fim, tipo=tipo_sql, categoria=categoria_sql
)


def moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


col_saldo, col_receitas, col_despesas = st.columns(3)
col_saldo.metric("Saldo no período", moeda(totais["saldo"]))
col_receitas.metric("Total de receitas", moeda(totais["receitas"]))
col_despesas.metric("Total de despesas", moeda(totais["despesas"]))

transacoes = listar_transacoes(
    usuario_id,
    data_inicio=data_inicio,
    data_fim=data_fim,
    categoria=categoria_sql,
)
if tipo_sql is not None:
    transacoes = [item for item in transacoes if item["tipo"] == tipo_sql]

st.subheader("Transações")
if transacoes:
    tabela = pd.DataFrame(transacoes).rename(
        columns={
            "id": "ID",
            "descricao": "Descrição",
            "tipo": "Tipo",
            "categoria": "Categoria",
            "data": "Data",
            "valor": "Valor (R$)",
        }
    )
    st.dataframe(
        tabela[["ID", "Data", "Descrição", "Tipo", "Categoria", "Valor (R$)"]],
        hide_index=True,
        use_container_width=True,
        column_config={"Valor (R$)": st.column_config.NumberColumn(format="R$ %.2f")},
    )
else:
    st.info("Nenhuma transação encontrada para os filtros selecionados.")

st.subheader("Receitas e despesas por mês")
if transacoes:
    dados_grafico = pd.DataFrame(transacoes)
    dados_grafico["Mês"] = pd.to_datetime(dados_grafico["data"]).dt.strftime("%Y-%m")
    grafico = dados_grafico.pivot_table(
        index="Mês", columns="tipo", values="valor", aggfunc="sum", fill_value=0
    ).reindex(columns=["receita", "despesa"], fill_value=0)
    grafico.columns = ["Receitas", "Despesas"]
    st.bar_chart(grafico.reset_index(), x="Mês", y=["Receitas", "Despesas"])
else:
    st.info("Cadastre transações para visualizar o gráfico.")

st.subheader("Relatório financeiro mensal")
relatorio = obter_relatorio(
    usuario_id, data_inicio, data_fim, categoria=categoria_sql
)
if relatorio["mensal"]:
    tabela_mensal = pd.DataFrame(relatorio["mensal"]).rename(
        columns={
            "mes": "Mês",
            "receitas": "Receitas (R$)",
            "despesas": "Despesas (R$)",
            "saldo": "Saldo (R$)",
        }
    )
    st.dataframe(tabela_mensal, hide_index=True, use_container_width=True)
    st.line_chart(tabela_mensal.set_index("Mês")[["Saldo (R$)"]])
else:
    st.info("Não há dados para gerar o relatório no período selecionado.")

col_excel, col_pdf = st.columns(2)
with col_excel:
    st.download_button(
        "Exportar para Excel",
        data=gerar_excel(usuario_id, data_inicio, data_fim, categoria_sql),
        file_name="relatorio_financeiro.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
with col_pdf:
    st.download_button(
        "Baixar relatorio PDF",
        data=gerar_pdf(usuario_id, data_inicio, data_fim, categoria_sql),
        file_name="relatorio_financeiro.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

st.subheader("Editar ou excluir transação")
if todas:
    transacao_por_id = {transacao["id"]: transacao for transacao in todas}
    id_selecionado = st.selectbox(
        "Selecione pelo ID",
        list(transacao_por_id),
        format_func=lambda item_id: (
            f"#{item_id} — {transacao_por_id[item_id]['descricao']} "
            f"({transacao_por_id[item_id]['data']})"
        ),
    )
    selecionada = transacao_por_id[id_selecionado]

    with st.form("form_edicao_transacao"):
        descricao_edicao = st.text_input("Descrição", value=selecionada["descricao"])
        categoria_edicao = st.text_input(
            "Categoria", value=selecionada["categoria"]
        )
        col_tipo_edicao, col_valor_edicao, col_data_edicao = st.columns(3)
        with col_tipo_edicao:
            tipo_edicao = st.selectbox(
                "Tipo",
                ["receita", "despesa"],
                index=["receita", "despesa"].index(selecionada["tipo"]),
            )
        with col_valor_edicao:
            valor_edicao = st.number_input(
                "Valor (R$)",
                min_value=0.01,
                value=float(selecionada["valor"]),
                step=0.01,
                format="%.2f",
            )
        with col_data_edicao:
            data_edicao = st.date_input(
                "Data",
                value=date.fromisoformat(selecionada["data"]),
                format="DD/MM/YYYY",
            )
        salvar_edicao = st.form_submit_button("Salvar alterações")

    if salvar_edicao:
        try:
            editar_transacao(
                usuario_id,
                id_selecionado,
                descricao_edicao,
                valor_edicao,
                tipo_edicao,
                data=data_edicao,
                categoria=categoria_edicao,
            )
            st.success("Transação atualizada.")
            st.rerun()
        except ValueError as erro:
            st.error(str(erro))

    confirmar_exclusao = st.checkbox(
        f"Confirmo a exclusão de #{id_selecionado} — {selecionada['descricao']}"
    )
    if st.button("Excluir transação", disabled=not confirmar_exclusao):
        excluir_transacao(usuario_id, id_selecionado)
        st.success("Transação excluída.")
        st.rerun()
else:
    st.info("Não há transações para editar ou excluir.")

st.subheader("Metas financeiras")
with st.expander("Criar nova meta"):
    with st.form("form_criar_meta"):
        nome_meta = st.text_input("Nome da meta")
        valor_meta = st.number_input(
            "Valor desejado (R$)", min_value=0.01, step=50.0, format="%.2f"
        )
        prazo_meta = st.date_input(
            "Prazo", value=date.today() + timedelta(days=90), format="DD/MM/YYYY"
        )
        salvar_meta = st.form_submit_button("Criar meta", type="primary")
    if salvar_meta:
        try:
            criar_meta(usuario_id, nome_meta, valor_meta, prazo_meta)
            st.success("Meta criada.")
            st.rerun()
        except ValueError as erro:
            st.error(str(erro))

metas_usuario = listar_metas(usuario_id)
if not metas_usuario:
    st.info("Voce ainda nao tem metas financeiras cadastradas.")

for meta in metas_usuario:
    with st.container(border=True):
        col_meta, col_progresso = st.columns([2, 1])
        col_meta.markdown(f"#### {meta['nome']}")
        col_meta.caption(f"Prazo: {meta['prazo']}")
        col_progresso.metric("Progresso", f"{meta['progresso']:.0%}")
        st.progress(meta["progresso"])
        st.write(
            f"Economizado: **{moeda(meta['valor_economizado'])}** de "
            f"**{moeda(meta['valor_objetivo'])}** · Falta "
            f"**{moeda(meta['faltante'])}**"
        )

        with st.form(f"form_economia_meta_{meta['id']}"):
            aporte = st.number_input(
                "Adicionar valor economizado (R$)",
                min_value=0.01,
                step=10.0,
                format="%.2f",
                key=f"aporte_meta_{meta['id']}",
            )
            registrar_aporte = st.form_submit_button("Registrar economia")
        if registrar_aporte:
            registrar_economia(usuario_id, meta["id"], aporte)
            st.success("Valor registrado na meta.")
            st.rerun()

        with st.expander(f"Editar meta: {meta['nome']}"):
            with st.form(f"form_editar_meta_{meta['id']}"):
                nome_editado = st.text_input(
                    "Nome", value=meta["nome"], key=f"nome_meta_{meta['id']}"
                )
                valor_editado = st.number_input(
                    "Valor desejado (R$)",
                    min_value=0.01,
                    value=float(meta["valor_objetivo"]),
                    step=50.0,
                    format="%.2f",
                    key=f"valor_meta_{meta['id']}",
                )
                prazo_editado = st.date_input(
                    "Prazo",
                    value=date.fromisoformat(meta["prazo"]),
                    format="DD/MM/YYYY",
                    key=f"prazo_meta_{meta['id']}",
                )
                salvar_edicao_meta = st.form_submit_button("Salvar meta")
            if salvar_edicao_meta:
                try:
                    editar_meta(
                        usuario_id,
                        meta["id"],
                        nome_editado,
                        valor_editado,
                        prazo_editado,
                    )
                    st.success("Meta atualizada.")
                    st.rerun()
                except ValueError as erro:
                    st.error(str(erro))

        confirmar_exclusao_meta = st.checkbox(
            f"Confirmo excluir a meta {meta['nome']}",
            key=f"confirmar_exclusao_meta_{meta['id']}",
        )
        if st.button(
            "Excluir meta",
            key=f"excluir_meta_{meta['id']}",
            disabled=not confirmar_exclusao_meta,
        ):
            excluir_meta(usuario_id, meta["id"])
            st.success("Meta excluida.")
            st.rerun()
