import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime
import io

st.set_page_config(layout="wide")
st.title("🚛 Painel de Não Conformidades - Checklist Veicular")

st.sidebar.markdown("### 📂 Importar arquivos")

# Botão de upload mais compacto
with st.sidebar:
    file_checklist = st.file_uploader("Checklist preenchido", type=[".xlsx"], label_visibility="collapsed")
    file_manu = st.file_uploader("Planilha de frota (MANU.PREVENT)", type=[".xlsx"], label_visibility="collapsed")

if file_checklist and file_manu:
    df = pd.read_excel(file_checklist)
    frota = pd.read_excel(file_manu)

    df = df.rename(columns=lambda x: x.strip())

    # ✅ Ajuste fixo para a coluna "Placa do caminhão"
    if 'Placa do caminhão' not in df.columns:
        st.error("❌ A coluna 'Placa do caminhão' não foi encontrada. Verifique se está correta.")
        st.write("Colunas disponíveis:", df.columns.tolist())
        st.stop()
    
    df = df.rename(columns={'Placa do caminhão': 'Placa'})

    df['Data'] = pd.to_datetime(df['Data'], errors='coerce').dt.date
    df['Placa'] = df['Placa'].astype(str).str.strip().str.upper()

    resumo = df.groupby('Placa').agg(
        Checklists=('Data', 'count'),
        NCs=('Status', lambda x: (x == 'Problema').sum())
    ).reset_index()
    resumo['% Checklists com NC'] = 100 * resumo['NCs'] / resumo['Checklists']

    df_nc = df[df['Status'] == 'Problema']
    df_veic_nc = df_nc['Placa'].value_counts().reset_index()
    df_veic_nc.columns = ['Placa', 'Total NCs']

    veic_top = df_veic_nc.iloc[0]['Placa'] if not df_veic_nc.empty else '-'
    total_checklists = len(df['Data'])
    checklists_com_nc = df.groupby(['Data', 'Placa'])['Status'].apply(lambda x: (x == 'Problema').any()).sum()
    pct_checklists_com_nc = round((checklists_com_nc / total_checklists) * 100, 1) if total_checklists > 0 else 0
    media_nc_por_checklist = round(df_nc.shape[0] / total_checklists, 2) if total_checklists > 0 else 0
    total_itens_verificados = df.shape[0]
    media_pct_nc_por_checklist = round((df_nc.shape[0] / total_itens_verificados) * 100, 1) if total_itens_verificados > 0 else 0

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Visão Geral", "🚨 Itens Críticos", "📷 Fotos das Não Conformidades", "📑 Base de Dados"])

    with tab1:
        col1, col2, col3 = st.columns(3)
        col1.metric("🚛 Veículo com Mais NCs", veic_top)
        col2.metric("📋 Checklists no Período", total_checklists)
        col3.metric("📉 % de Checklists com NC", f"{pct_checklists_com_nc}%\n{checklists_com_nc} com NC")

        col4, col5, col6 = st.columns(3)
        col4.metric("⚠️ Média de NCs por Checklist", media_nc_por_checklist)
        col5.metric("🧾 Total de Itens Verificados", f"{total_itens_verificados:,}")
        col6.metric("🔧 % Médio de Itens NC por Checklist", f"{media_pct_nc_por_checklist}%")

        st.subheader("📍 Distribuição de NCs por Veículo")
        fig = px.bar(df_veic_nc, x='Placa', y='Total NCs', text='Total NCs')
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 📤 Exportar Indicadores")
        kpi_data = pd.DataFrame({
            "Indicador": [
                "Veículo com Mais NCs",
                "Checklists no Período",
                "% de Checklists com NC",
                "Média de NCs por Checklist",
                "Total de Itens Verificados",
                "% Médio de Itens NC por Checklist"
            ],
            "Valor": [
                veic_top,
                total_checklists,
                f"{pct_checklists_com_nc}% ({checklists_com_nc} com NC)",
                media_nc_por_checklist,
                f"{total_itens_verificados:,}",
                f"{media_pct_nc_por_checklist}%"
            ]
        })

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            kpi_data.to_excel(writer, sheet_name='Indicadores', index=False)
            resumo.to_excel(writer, sheet_name='Resumo NCs', index=False)
            df_veic_nc.to_excel(writer, sheet_name='Classificacao Veiculos', index=False)
            df_nc.groupby('Categoria')['Item'].value_counts().to_frame('Ocorrências').to_excel(writer, sheet_name='Itens Criticos')

        st.download_button(
            label="📁 Baixar Indicadores em Excel",
            data=buffer.getvalue(),
            file_name="indicadores_checklist.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with tab2:
        st.subheader("🚨 Itens Críticos por Categoria")
        df_cat_grouped = df_nc.groupby('Categoria')['Item'].value_counts().reset_index(name='Ocorrências')
        fig2 = px.bar(df_cat_grouped, x='Ocorrências', y='Item', color='Categoria', orientation='h')
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.subheader("📷 Fotos das Não Conformidades por Veículo")
        placas = df_nc['Placa'].dropna().unique().tolist()
        placas.insert(0, 'Todos')
        placa_selecionada = st.selectbox("Selecionar Placa", sorted(placas))

        if placa_selecionada == 'Todos':
            fotos_placa = df_nc.copy()
        else:
            fotos_placa = df_nc[df_nc['Placa'] == placa_selecionada]

        for _, row in fotos_placa.iterrows():
            st.markdown(f"**Data:** {row['Data']}  ")
            st.markdown(f"**Placa:** {row['Placa']}  ")
            st.markdown(f"**Item:** {row['Item']}  ")
            st.markdown(f"**Descrição:** {row['Descrição Problema']}")

            urls = re.split(r',\s*', str(row['foto'])) if pd.notna(row['foto']) else []
            for url in urls:
                st.image(url, use_container_width=True)

            st.markdown("---")

    with tab4:
        st.subheader("📑 Base Completa de Dados")
        st.dataframe(df)
