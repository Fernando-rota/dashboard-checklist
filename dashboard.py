import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="📋 Checklist Veicular", layout="wide")
st.markdown("# 📋 Dashboard Checklist Veicular — Filtros por Botões")

# === Upload dos Arquivos ===
checklist_file = st.file_uploader("Selecione o arquivo Excel do checklist:", type="xlsx")
manut_file = st.file_uploader("Selecione o arquivo Excel MANU.PREVENT:", type="xlsx")

if checklist_file and manut_file:
    # === Carregar os dados ===
    df = pd.read_excel(checklist_file)
    manu = pd.read_excel(manut_file)

    # === Renomear colunas longas para índices ===
    colunas_problemas = df.columns[6:-1].tolist()
    col_map = {col: f"Item {i+1}" for i, col in enumerate(colunas_problemas)}
    df.rename(columns=col_map, inplace=True)

    # === Criar coluna de não conformidades por linha ===
    itens_nao_conformes = list(col_map.values())
    df["Qtd_Não_Conforme"] = df[itens_nao_conformes].apply(lambda x: (x == "Não Conforme").sum(), axis=1)

    # === Sidebar com filtros ===
    st.sidebar.markdown("## 🚦 Filtrar por Motorista")
    motoristas = sorted(df["Motorista"].dropna().unique())
    motorista_selecionado = st.sidebar.multiselect("Motoristas:", motoristas, default=motoristas)

    st.sidebar.markdown("## 🚦 Filtrar por Placa")
    placas = sorted(df["Placa do Caminhão"].dropna().unique())
    placa_selecionada = st.sidebar.multiselect("Placas:", placas, default=placas)

    # === Aplicar Filtros ===
    df_filtrado = df[df["Motorista"].isin(motorista_selecionado) & df["Placa do Caminhão"].isin(placa_selecionado)]

    # === KPIs ===
    col1, col2 = st.columns(2)
    col1.metric("📄 Total de Checklists", len(df_filtrado))
    col2.metric("❌ Total de Não Conformidades", int(df_filtrado["Qtd_Não_Conforme"].sum()))

    # === Gráfico de reincidências por placa ===
    st.markdown("## 🚨 Reincidências por Veículo")
    reinc = df_filtrado[itens_nao_conformes + ["Placa do Caminhão"]].copy()
    reinc = reinc.melt(id_vars=["Placa do Caminhão"], value_vars=itens_nao_conformes)
    reinc = reinc[reinc["value"] == "Não Conforme"]
    reincidencias = reinc.groupby("Placa do Caminhão").size().reset_index(name="Reincidências")

    fig_reinc = px.bar(reincidencias, x="Placa do Caminhão", y="Reincidências", text="Reincidências",
                       color_discrete_sequence=["indianred"])
    fig_reinc.update_traces(textposition="outside")
    fig_reinc.update_layout(xaxis_title="Placa", yaxis_title="Nº de Não Conformidades")
    st.plotly_chart(fig_reinc, use_container_width=True)

    # === Gráfico de Não Conformidade por Item (resumido) ===
    st.markdown("## 🔧 Não Conformidades por Item")
    problemas_por_item = df_filtrado[itens_nao_conformes].apply(lambda col: (col == "Não Conforme").sum())
    problemas_df = pd.DataFrame({"Item": problemas_por_item.index, "Qtd": problemas_por_item.values})
    fig_problemas = px.bar(problemas_df, x="Item", y="Qtd", text="Qtd", color_discrete_sequence=["darkorange"])
    fig_problemas.update_traces(textposition="outside")
    fig_problemas.update_layout(xaxis_title="Item", yaxis_title="Quantidade de Não Conformidades")
    st.plotly_chart(fig_problemas, use_container_width=True)

    # === Tabela de Legenda dos Itens ===
    st.markdown("### 📌 Legenda dos Itens de Verificação")
    legenda_df = pd.DataFrame({"Índice": list(col_map.values()), "Descrição": list(col_map.keys())})
    st.dataframe(legenda_df, use_container_width=True, hide_index=True)

    # === Indicador cruzado com manutenção programada ===
    st.markdown("## 🔧 Indicador Cruzado: Manutenção Programada x Reincidências")
    cruzado = pd.merge(reincidencias, manu, left_on="Placa do Caminhão", right_on="PLACA", how="left")
    cruzado["MANUT. PROGRAMADA"] = pd.to_datetime(cruzado[" MANUT. PROGRAMADA"], errors='coerce')

    fig_manu = px.scatter(cruzado, x="MANUT. PROGRAMADA", y="Reincidências", color="PLACA",
                          hover_data=["MODELO", "ANO/MODELO"],
                          labels={"MANUT. PROGRAMADA": "Data da Manutenção"},
                          color_discrete_sequence=px.colors.qualitative.Set1)
    st.plotly_chart(fig_manu, use_container_width=True)

    # === Expansor com dados brutos ===
    with st.expander("📊 Ver dados brutos (checklist)"):
        st.dataframe(df_filtrado, use_container_width=True)

else:
    st.info("🔄 Aguarde o envio dos dois arquivos para visualizar o dashboard.")
