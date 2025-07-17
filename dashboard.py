import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Checklist Veicular", layout="wide")

st.title("📋 Dashboard - Checklist Veicular")

uploaded_file = st.file_uploader("Faça upload do arquivo Excel com os dados do checklist", type=["xlsx"])
if not uploaded_file:
    st.warning("Por favor, envie um arquivo para visualizar o dashboard.")
    st.stop()

df = pd.read_excel(uploaded_file)
df.columns = df.columns.str.strip()
df["Carimbo de data/hora"] = pd.to_datetime(df["Carimbo de data/hora"], errors="coerce")
df["Data"] = df["Carimbo de data/hora"].dt.strftime("%d/%m/%Y")

col_fotos = next((c for c in df.columns if "foto" in c.lower()), None)
col_status = next((c for c in df.columns if "status" in c.lower()), None)
itens = [c for c in df.columns if c.startswith("Item")]

# Filtros no sidebar
st.sidebar.markdown("### 📅 Filtros")
min_date, max_date = df["Carimbo de data/hora"].min(), df["Carimbo de data/hora"].max()
start_date = st.sidebar.date_input("Data inicial", min_date.date())
end_date = st.sidebar.date_input("Data final", max_date.date())

if start_date > end_date:
    st.sidebar.error("Data inicial não pode ser maior que a final.")
    st.stop()

df = df[(df["Carimbo de data/hora"] >= pd.Timestamp(start_date)) & (df["Carimbo de data/hora"] <= pd.Timestamp(end_date) + pd.Timedelta(days=1))]

# Filtro motorista
motoristas = sorted(df["Motorista"].dropna().unique())
motoristas_opcoes = ["Todos"] + motoristas
sel_motorista = st.sidebar.selectbox("Motoristas", motoristas_opcoes)
if sel_motorista != "Todos":
    df = df[df["Motorista"] == sel_motorista]

# Filtro placa
placas = sorted(df["Placa do Caminhão"].dropna().unique())
placas_opcoes = ["Todos"] + placas
sel_placa = st.sidebar.selectbox("Placas", placas_opcoes)
if sel_placa != "Todos":
    df = df[df["Placa do Caminhão"] == sel_placa]

# Filtro status
status_opcoes = ["Todos", "Aberto / Em andamento", "Concluído"]
status_sel = st.sidebar.selectbox("Status da NC", status_opcoes)
if status_sel == "Aberto / Em andamento":
    df = df[df[col_status].isin(["aberto", "em andamento"])]
elif status_sel == "Concluído":
    df = df[df[col_status] == "concluído"]

def extract_drive_links(texto):
    if pd.isna(texto):
        return []
    return [part for part in texto.split() if "http" in part]

# KPIs
total_checklists = len(df)
total_nc = df[itens].apply(lambda x: (x.str.strip().str.lower() != "ok").sum(), axis=1).sum()
porcentagem_nc = round((total_nc / (len(df) * len(itens))) * 100, 1) if len(df) > 0 else 0

col1, col2, col3 = st.columns(3)
col1.metric("✅ Checklists Realizados", total_checklists)
col2.metric("❌ Não Conformidades", int(total_nc))
col3.metric("📊 % de NC", f"{porcentagem_nc}%")

# Abas
aba1, aba2, aba3, aba4, aba5 = st.tabs(["📄 Tabela Geral", "🚫 Não Conformidades", "📈 Visão Geral", "📊 NC por Item", "📸 Fotos"])

with aba1:
    st.markdown("### 📄 Tabela Geral")
    st.dataframe(df[["Data", "Motorista", "Placa do Caminhão"] + itens + [col_status]])

with aba2:
    st.markdown("### 🚫 Registros com Não Conformidades")
    nc_df = df.copy()
    nc_df["Total NC"] = nc_df[itens].apply(lambda x: (x.str.strip().str.lower() != "ok").sum(), axis=1)
    nc_df = nc_df[nc_df["Total NC"] > 0]
    if nc_df.empty:
        st.success("Nenhuma não conformidade registrada no período.")
    else:
        st.dataframe(nc_df[["Data", "Motorista", "Placa do Caminhão", "Total NC", col_status]])

with aba3:
    st.markdown("### 📈 Visão Geral de Não Conformidades por Placa")
    nc_por_placa = df.copy()
    nc_por_placa["NCs"] = nc_por_placa[itens].apply(lambda x: (x.str.strip().str.lower() != "ok").sum(), axis=1)
    agrupado = nc_por_placa.groupby("Placa do Caminhão")["NCs"].sum().reset_index()
    fig = px.bar(agrupado, x="Placa do Caminhão", y="NCs", color="NCs",
                 title="Total de NCs por Placa", labels={"NCs": "Não Conformidades"},
                 height=400)
    st.plotly_chart(fig, use_container_width=True)

with aba4:
    st.markdown("### 📊 Frequência de NC por Item")
    frequencia = {}
    for item in itens:
        ncs = df[item].str.strip().str.lower() != "ok"
        frequencia[item] = ncs.sum()
    freq_df = pd.DataFrame(list(frequencia.items()), columns=["Item", "Total NC"]).sort_values(by="Total NC", ascending=False)
    fig2 = px.bar(freq_df, x="Item", y="Total NC", color="Total NC", title="Frequência de NC por Item", height=500)
    st.plotly_chart(fig2, use_container_width=True)

with aba5:
    st.markdown("### 📸 Fotos de Não Conformidades")
    fotos_df = df[["Data", "Motorista", "Placa do Caminhão", col_fotos, col_status] + itens].dropna(subset=[col_fotos])
    placas_disp = sorted(fotos_df["Placa do Caminhão"].unique())
    sel_foto = st.selectbox("Filtrar por Placa", ["Todas"] + placas_disp)

    if sel_foto != "Todas":
        fotos_df = fotos_df[fotos_df["Placa do Caminhão"] == sel_foto]

    if fotos_df.empty:
        st.info("Nenhuma foto encontrada.")
    else:
        for _, row in fotos_df.iterrows():
            nc_itens = [col for col in itens if row[col].strip().lower() != "ok"]
            links = extract_drive_links(row[col_fotos])
            st.markdown(f"""
**📅 {row['Data']}**  
👨‍✈️ **Motorista:** {row['Motorista']}  
🚚 **Placa:** {row['Placa do Caminhão']}  
📍 **Status:** {row[col_status]}  
🔧 **Itens Não Conformes:** {", ".join(nc_itens)}
""")
            for i, link in enumerate(links, 1):
                st.markdown(f"[🔗 Foto {i}]({link})")
            st.markdown("---")
