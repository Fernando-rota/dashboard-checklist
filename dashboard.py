import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import re

st.set_page_config(layout="wide")

st.title("✅ Painel de Não Conformidades - Checklist Veicular")

# Função para extrair links do campo de fotos
def extract_drive_links(text):
    return re.findall(r"https://drive.google.com/[^\s,]+", str(text))

# Upload do arquivo
uploaded_file = st.sidebar.file_uploader("📤 Envie o arquivo de checklist (.xlsx ou .xls)", type=["xlsx", "xls"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # Normaliza colunas e identifica colunas-chave
    df.columns = df.columns.str.strip()
    col_data = [col for col in df.columns if "data" in col.lower()][0]
    col_motorista = [col for col in df.columns if "motorista" in col.lower()][0]
    col_placa = [col for col in df.columns if "placa" in col.lower() and "caminh" in col.lower()][0]
    col_status = [col for col in df.columns if "status" in col.lower() and "nc" in col.lower()][0]
    col_fotos = [col for col in df.columns if "foto" in col.lower()][0]

    df[col_data] = pd.to_datetime(df[col_data], errors='coerce')
    df = df.dropna(subset=[col_data])

    # Itens de verificação = colunas entre "Motorista" e "Status NC"
    idx_motorista = df.columns.get_loc(col_motorista)
    idx_status = df.columns.get_loc(col_status)
    itens = df.columns[(idx_motorista + 1):idx_status]

    # Filtros
    with st.sidebar:
        st.markdown("### 🎯 Filtros")
        data_ini = st.date_input("Data inicial", value=df[col_data].min().date())
        data_fim = st.date_input("Data final", value=df[col_data].max().date())
        motoristas = sorted(df[col_motorista].dropna().unique())
        placas = sorted(df[col_placa].dropna().unique())
        status_nc = sorted(df[col_status].dropna().unique())

        sel_motorista = st.multiselect("Motorista", motoristas, default=motoristas)
        sel_placa = st.multiselect("Placa do Caminhão", placas, default=placas)
        sel_status = st.multiselect("Status NC", status_nc, default=status_nc)

    # Aplica filtros
    df_filtrado = df[
        (df[col_data] >= pd.to_datetime(data_ini)) &
        (df[col_data] <= pd.to_datetime(data_fim)) &
        (df[col_motorista].isin(sel_motorista)) &
        (df[col_placa].isin(sel_placa)) &
        (df[col_status].isin(sel_status))
    ]

    aba1, aba2, aba3, aba4, aba5 = st.tabs(["📊 Visão Geral", "📌 Itens Críticos", "📋 Checklist Completo", "📁 Checklist Filtrado", "📸 Fotos de NC"])

    with aba1:
        st.markdown("### 📊 Gráficos de Não Conformidades")

        # Total por veículo
        df_nc = df_filtrado.copy()
        df_nc["qtd_nc"] = df_nc[itens].apply(lambda row: sum(str(x).strip().lower() != "ok" for x in row), axis=1)
        nc_por_placa = df_nc.groupby(col_placa)["qtd_nc"].sum().reset_index().sort_values("qtd_nc", ascending=False)

        fig1 = px.bar(nc_por_placa, x="qtd_nc", y=col_placa, orientation="h", title="Total de Não Conformidades por Veículo")
        st.plotly_chart(fig1, use_container_width=True)

        # Tendência ao longo do tempo
        nc_por_data = df_nc.groupby(col_data)["qtd_nc"].sum().reset_index()
        fig2 = px.line(nc_por_data, x=col_data, y="qtd_nc", markers=True, title="Tendência de Não Conformidades ao longo do tempo")
        st.plotly_chart(fig2, use_container_width=True)

        # Pizza por status
        status_count = df_filtrado[col_status].value_counts().reset_index()
        status_count.columns = ["Status", "Quantidade"]
        fig3 = px.pie(status_count, names="Status", values="Quantidade", title="Distribuição por Status")
        st.plotly_chart(fig3, use_container_width=True)

        # Heatmap de frequência de NCs
        df_nc["dia_semana"] = df_nc[col_data].dt.day_name()
        heatmap_data = df_nc.groupby(["dia_semana", col_placa])["qtd_nc"].sum().reset_index()
        heatmap_pivot = heatmap_data.pivot(index="dia_semana", columns=col_placa, values="qtd_nc").fillna(0)
        fig4 = px.imshow(heatmap_pivot, text_auto=True, aspect="auto", title="Frequência de NCs por Dia e Veículo")
        st.plotly_chart(fig4, use_container_width=True)

    with aba2:
        st.markdown("### 📌 Itens com Mais Não Conformidades")
        item_counts = {}
        for item in itens:
            item_counts[item] = (df_filtrado[item].astype(str).str.lower() != "ok").sum()
        item_series = pd.Series(item_counts).sort_values(ascending=False)
        item_df = item_series.reset_index()
        item_df.columns = ["Item", "Não Conformidades"]

        fig5 = px.bar(item_df, x="Não Conformidades", y="Item", orientation="h", title="Frequência de NC por Item")
        st.plotly_chart(fig5, use_container_width=True)

        fig6 = px.treemap(item_df, path=["Item"], values="Não Conformidades", title="Treemap de Itens com NC")
        st.plotly_chart(fig6, use_container_width=True)

    with aba3:
        st.markdown("### 📋 Base Completa - Checklist (sem filtro)")
        st.dataframe(df)

    with aba4:
        st.markdown("### 📋 Checklist com Filtros Aplicados")
        st.dataframe(df_filtrado)

    with aba5:
        st.markdown("### 📸 Fotos de Não Conformidades")
        fotos_df = df[[col_data, col_motorista, col_placa, col_fotos, col_status] + list(itens)].dropna(subset=[col_fotos])
        placas_disp = sorted(fotos_df[col_placa].unique())
        sel_foto = st.selectbox("Filtrar por Placa", ["Todas"] + placas_disp)

        if sel_foto != "Todas":
            fotos_df = fotos_df[fotos_df[col_placa] == sel_foto]

        if fotos_df.empty:
            st.info("Nenhuma foto encontrada.")
        else:
            for _, row in fotos_df.iterrows():
                nc_itens = [col for col in itens if str(row[col]).strip().lower() != "ok"]
                links = extract_drive_links(row[col_fotos])

                st.markdown(f"""
**📅 {row[col_data].date()}**  
👨‍✈️ **Motorista:** {row[col_motorista]}  
🚚 **Placa:** {row[col_placa]}  
📍 **Status:** {row[col_status]}  
🔧 **Itens Não Conformes:** {', '.join(nc_itens)}
""")
                for i, link in enumerate(links, 1):
                    st.markdown(f"[🔗 Foto {i}]({link})")
                st.markdown("---")
else:
    st.info("Envie o arquivo de checklist no menu lateral para começar.")
