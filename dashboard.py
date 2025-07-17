import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide")

st.title("📋 Dashboard de Não Conformidades")

st.markdown("Este painel exibe as não conformidades registradas nos checklists por veículo.")

# Upload dos arquivos
col1, col2 = st.columns([4, 1])
with col1:
    uploaded_file = st.file_uploader("Importar checklist (.xlsx)", type=["xlsx"])
with col2:
    st.write("")

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # Renomeando colunas para facilitar a leitura
    df.rename(columns={
        "Placa do Caminhão": "Placa",
        "Status NC": "Status",
        "Anexe as fotos das não conformidades:": "foto",
        "Observações:": "Descrição"
    }, inplace=True)

    # Filtro apenas das linhas com não conformidades
    df_nc = df[df['Status'] == 'Não Conforme']

    if df_nc.empty:
        st.warning("✅ Nenhuma não conformidade registrada.")
    else:
        placas = df_nc["Placa"].dropna().unique().tolist()
        placas.sort()

        # Filtro de placa com "Todos"
        placas_opcoes = ["Todos"] + placas
        placa_selecionada = st.selectbox("Filtrar por placa", placas_opcoes)

        if placa_selecionada != "Todos":
            df_filtrado = df_nc[df_nc["Placa"] == placa_selecionada]
        else:
            df_filtrado = df_nc.copy()

        st.subheader("🔎 Não Conformidades Registradas")
        for i, row in df_filtrado.iterrows():
            with st.container():
                st.markdown(f"**📍 Placa:** {row['Placa']}  \n"
                            f"🕒 **Data:** {row['Data']}  \n"
                            f"📝 **Descrição:** {row['Descrição'] if pd.notna(row['Descrição']) else 'Não informada'}")
                if pd.notna(row["foto"]):
                    st.image(row["foto"], caption="📷 Evidência", use_container_width=True)
                st.markdown("---")

else:
    st.info("📂 Importe um arquivo Excel com os dados do checklist.")
