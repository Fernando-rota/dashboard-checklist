import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Dashboard Checklist Veicular", layout="wide")

@st.cache_data

def load_excel(file):
    df = pd.read_excel(file)
    df.columns = df.columns.str.strip().str.replace('\s+', ' ', regex=True)
    return df

st.title("📋 Dashboard Checklist Veicular")

col_upload1, col_upload2 = st.columns(2)

with col_upload1:
    uploaded_file = st.file_uploader("📤 Faça upload do checklist (.xlsx)", type="xlsx", key="file1")

if uploaded_file is None:
    st.warning("Por favor, envie o arquivo do checklist.")
    st.stop()

df = load_excel(uploaded_file)

aba1, aba2, aba3, aba4, aba5 = st.tabs([
    "📊 Resumo Geral",
    "🚛 Por Veículo",
    "👷 Por Motorista",
    "🧾 Manutenção",
    "📷 Fotos das Não Conformidades"
])

with aba1:
    st.subheader("📊 Resumo Geral")
    st.write("Adicione seus indicadores aqui...")

with aba2:
    st.subheader("🚛 Dados por Veículo")
    st.write("Gráficos e tabelas filtradas por placa...")

with aba3:
    st.subheader("👷 Dados por Motorista")
    st.write("Gráficos e tabelas filtradas por motorista...")

with aba4:
    st.subheader("🧾 Manutenção Preventiva")
    st.write("Relatório de manutenção programada...")

with aba5:
    st.markdown("## 📷 Galeria de Fotos das Não Conformidades")

    col_descricoes = [col for col in df.columns if 'descri' in col.lower() or 'problema' in col.lower()]
    col_fotos = [col for col in df.columns if 'foto' in col.lower() or 'file_id' in col.lower()]
    col_placa = [col for col in df.columns if 'placa' in col.lower()][0]
    col_motorista = [col for col in df.columns if 'motorista' in col.lower()][0]
    col_data = [col for col in df.columns if 'carimbo' in col.lower() or 'data' in col.lower()][0]

    if not col_descricoes or not col_fotos:
        st.warning("⚠️ Colunas de descrição ou foto não foram encontradas.")
        st.stop()

    df_fotos = df.copy()
    df_fotos = df_fotos.dropna(subset=col_descricoes + col_fotos, how='all')

    if df_fotos.empty:
        st.info("Nenhuma não conformidade com foto foi encontrada.")
    else:
        cols = st.columns(3)

        for idx, (_, row) in enumerate(df_fotos.iterrows()):
            descricao = ""
            for c in col_descricoes:
                if pd.notna(row[c]) and str(row[c]).strip():
                    descricao += f"🔸 {c}: {row[c]}\n"

            for c in col_fotos:
                valor = str(row[c]).strip()
                if not valor or valor.lower() == "nan":
                    continue

                with cols[idx % 3]:
                    st.markdown(f"**🗓 {pd.to_datetime(row[col_data]).strftime('%d/%m/%Y')}**")
                    st.markdown(f"**🚛 {row[col_placa]}**")
                    st.markdown(f"**👷 {row[col_motorista]}**")
                    if valor.startswith("http"):
                        st.image(valor, use_column_width=True, caption=row[col_placa])
                    else:
                        st.markdown(f"📎 *file_id:* `{valor}`")

                    st.markdown(f"📝 {descricao}")
                    st.markdown("---")
