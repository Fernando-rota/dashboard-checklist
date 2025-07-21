import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Dashboard Checklist Veicular", layout="wide")

# Função para carregar dados
@st.cache_data
def load_excel(file):
    df = pd.read_excel(file)
    df.columns = df.columns.str.strip().str.replace('\s+', ' ', regex=True)
    return df

# Título
st.title("🛠️ Checklist Veicular - Dashboard de Análise")

# Layout com 2 colunas para upload lado a lado e botões menores
col1, col2 = st.columns(2)
with col1:
    uploaded_file_checklist = st.file_uploader("📥 Upload do Checklist", type=["xlsx"], label_visibility="collapsed", key="checklist")
    st.caption("📄 Checklist")

with col2:
    uploaded_file_manut = st.file_uploader("📥 Upload da Planilha de Manutenção", type=["xlsx"], label_visibility="collapsed", key="manut")
    st.caption("🧾 Manutenção")

# Validar uploads
if uploaded_file_checklist is None or uploaded_file_manut is None:
    st.warning("Por favor, envie as duas planilhas para visualizar o dashboard.")
    st.stop()

# Carregar dados
df = load_excel(uploaded_file_checklist)
df_manut = load_excel(uploaded_file_manut)

# Padronizar nomes de colunas
df.columns = df.columns.str.lower().str.strip()
df_manut.columns = df_manut.columns.str.lower().str.strip()

# Ajustar nome da coluna de status, se existir
col_status = next((col for col in df.columns if "status" in col), None)
if col_status is None:
    st.error("Coluna de status de não conformidade não encontrada.")
    st.stop()

# Filtros laterais
st.sidebar.header("🔎 Filtros")
df["Carimbo de data/hora"] = pd.to_datetime(df["carimbo de data/hora"])
min_date, max_date = df["Carimbo de data/hora"].min(), df["Carimbo de data/hora"].max()

start_date = st.sidebar.date_input("Data inicial", min_date.date())
end_date = st.sidebar.date_input("Data final", max_date.date())
if start_date > end_date:
    st.sidebar.error("Data inicial não pode ser maior que a final.")
    st.stop()

df = df[(df["Carimbo de data/hora"] >= pd.Timestamp(start_date)) & 
        (df["Carimbo de data/hora"] <= pd.Timestamp(end_date) + pd.Timedelta(days=1))]

# Filtros com checkboxes
motoristas = sorted(df["motorista"].dropna().unique())
todos_motoristas = st.sidebar.checkbox("Selecionar todos os motoristas", value=True)
sel_motorista = motoristas if todos_motoristas else st.sidebar.multiselect("Motoristas", motoristas)

placas = sorted(df["placa do caminhão"].dropna().unique())
todos_placas = st.sidebar.checkbox("Selecionar todas as placas", value=True)
sel_placa = placas if todos_placas else st.sidebar.multiselect("Placas", placas)

df = df[df["motorista"].isin(sel_motorista)]
df = df[df["placa do caminhão"].isin(sel_placa)]

status_opcoes = ["Todos", "Aberto / Em andamento", "Concluído"]
status_sel = st.sidebar.selectbox("Status da NC", status_opcoes)

if status_sel == "Aberto / Em andamento":
    df = df[df[col_status].isin(["aberto", "em andamento"])]
elif status_sel == "Concluído":
    df = df[df[col_status] == "concluído"]

# Indicadores
st.subheader("📊 Indicadores Gerais")
col1, col2, col3 = st.columns(3)
col1.metric("Registros Totais", len(df))
col2.metric("Não Conformidades", df[col_status].isin(["aberto", "em andamento", "concluído"]).sum())
col3.metric("Motoristas únicos", df["motorista"].nunique())

# Gráficos
st.markdown("### 🚛 Ocorrências por Veículo")
ocorrencias_placa = df["placa do caminhão"].value_counts().reset_index()
ocorrencias_placa.columns = ["Placa", "Ocorrências"]
fig1 = px.bar(ocorrencias_placa, x="Placa", y="Ocorrências", color="Ocorrências", text_auto=True)
st.plotly_chart(fig1, use_container_width=True)

st.markdown("### 👷 Ocorrências por Motorista")
ocorrencias_motorista = df["motorista"].value_counts().reset_index()
ocorrencias_motorista.columns = ["Motorista", "Ocorrências"]
fig2 = px.bar(ocorrencias_motorista, x="Motorista", y="Ocorrências", color="Ocorrências", text_auto=True)
st.plotly_chart(fig2, use_container_width=True)

# Tabela com problemas abertos e em andamento
st.markdown("### 📋 Lista de Não Conformidades (Abertas e Em Andamento)")
df_ncs = df[df[col_status].isin(["aberto", "em andamento"])]
st.dataframe(df_ncs[["carimbo de data/hora", "motorista", "placa do caminhão", col_status]].sort_values(by="carimbo de data/hora", ascending=False), use_container_width=True)

# Relacionar com a planilha de manutenção
st.markdown("### 🔧 Veículos com Não Conformidades e Dados de Manutenção")
veiculos_com_problemas = df["placa do caminhão"].unique()
df_manut_filtered = df_manut[df_manut["placa"].isin(veiculos_com_problemas)]
st.dataframe(df_manut_filtered, use_container_width=True)
