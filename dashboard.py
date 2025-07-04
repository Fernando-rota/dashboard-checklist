import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime
import locale

# Definir localidade para pt_BR
locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')

st.set_page_config(page_title="Dashboard Checklist Veicular", layout="wide")

@st.cache_data
def load_excel(file):
    df = pd.read_excel(file)
    df.columns = df.columns.str.strip()
    return df

def extract_drive_links(urls_string):
    if not urls_string or pd.isna(urls_string):
        return []
    urls = re.split(r'[,\s\n]+', str(urls_string).strip())
    links = []
    for url in urls:
        match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
        if not match:
            match = re.search(r'id=([a-zA-Z0-9_-]+)', url)
        if match:
            file_id = match.group(1)
            links.append(f"https://drive.google.com/uc?export=view&id={file_id}")
        else:
            links.append(url)
    return links

def severity_color(value, thresholds=(0.1, 0.3)):
    if value <= thresholds[0]:
        return "green"
    elif value <= thresholds[1]:
        return "yellow"
    else:
        return "red"

def main():
    st.title("🚛 Dashboard Checklist Veicular")

    uploaded_checklist = st.file_uploader("📁 Selecione o arquivo Excel do checklist:", type=["xlsx"])
    uploaded_manut = st.file_uploader("📁 Selecione o arquivo Excel MANU. PREVENT:", type=["xlsx"])

    if not uploaded_checklist or not uploaded_manut:
        st.info("📌 Por favor, faça upload dos dois arquivos para continuar.")
        return

    with st.spinner("Carregando dados..."):
        df = load_excel(uploaded_checklist)
        manut = load_excel(uploaded_manut)

    col_fotos = "Anexe as fotos das não conformidades:"
    col_obs = "Observações:"
    col_status = "Status NC"

    checklist_required = [
        "Carimbo de data/hora", "Motorista", "Placa do Caminhão",
        "Pontuação", col_fotos, col_obs, col_status
    ]

    missing = [col for col in checklist_required if col not in df.columns]
    if missing:
        st.error(f"Colunas faltantes no checklist: {missing}")
        return

    df["Carimbo de data/hora"] = pd.to_datetime(df["Carimbo de data/hora"], errors='coerce')
    df["Data"] = df["Carimbo de data/hora"].dt.strftime('%d/%m/%Y')

    df = df.dropna(subset=["Carimbo de data/hora"])

    col_filtros, col_data = st.columns(2)
    with col_data:
        min_date = df["Carimbo de data/hora"].min()
        max_date = df["Carimbo de data/hora"].max()
        start_date = st.date_input("Data inicial", min_date.date())
        end_date = st.date_input("Data final", max_date.date())
        df = df[(df["Carimbo de data/hora"] >= pd.Timestamp(start_date)) & (df["Carimbo de data/hora"] <= pd.Timestamp(end_date))]

    motoristas = sorted(df["Motorista"].dropna().unique())
    placas = sorted(df["Placa do Caminhão"].dropna().unique())

    with col_filtros:
        motorista_sel = st.multiselect("Filtrar Motorista(s)", options=motoristas, default=motoristas)
        placa_sel = st.multiselect("Filtrar Placa(s)", options=placas, default=placas)
        status_options = ["Todos", "Aberto / Em andamento", "Concluído"]
        status_sel = st.selectbox("Filtrar Status da Não Conformidade", options=status_options, index=0)

    df = df[df["Motorista"].isin(motorista_sel)]
    df = df[df["Placa do Caminhão"].isin(placa_sel)]

    if status_sel == "Aberto / Em andamento":
        df = df[df[col_status].str.lower().isin(["aberto", "em andamento"])]
    elif status_sel == "Concluído":
        df = df[df[col_status].str.lower() == "concluído"]

    cols_itens = [col for col in df.columns if col not in checklist_required + ["Data", "Km atual"]]
    df_itens = df[cols_itens].astype(str).applymap(lambda x: x.strip().lower())
    df["Reincidencias"] = df_itens.apply(lambda row: sum(v != "ok" and v != "" for v in row), axis=1)

    aba1, aba2, aba3, aba4 = st.tabs(["📊 Visão Geral", "🛠 Manutenção", "📌 Por Item", "📷 Fotos"])

    with aba1:
        st.subheader("Veículo com Mais Não Conformidades")
        reincid_por_placa = df.groupby("Placa do Caminhão")["Reincidencias"].sum().reset_index()
        reincid_por_placa = reincid_por_placa.sort_values(by="Reincidencias", ascending=False)
        if not reincid_por_placa.empty:
            st.metric("Veículo", reincid_por_placa.iloc[0]['Placa do Caminhão'], f"{int(reincid_por_placa.iloc[0]['Reincidencias'])} ocorrências")

        st.plotly_chart(px.bar(
            reincid_por_placa,
            y="Placa do Caminhão", x="Reincidencias",
            orientation="h", color="Reincidencias",
            color_continuous_scale=["green", "yellow", "red"],
            title="Não Conformidades por Veículo"
        ), use_container_width=True)

    with aba2:
        manut = manut.rename(columns=lambda x: x.strip())
        cruzado = pd.merge(reincid_por_placa, manut, how="left", left_on="Placa do Caminhão", right_on="PLACA")
        cruzado = cruzado.dropna(subset=["MANUT. PROGRAMADA"])
        cruzado["Índice de Severidade"] = (cruzado["Reincidencias"] / len(cols_itens)).round(3)
        st.write(cruzado[["PLACA", "MODELO", "MANUT. PROGRAMADA", "Reincidencias", "Índice de Severidade"]])

    with aba3:
        df_nc_item = pd.DataFrame({
            "Item": cols_itens,
            "Não Conformidades": [df_itens[col].ne("ok").sum() for col in cols_itens]
        })
        df_nc_item = df_nc_item[df_nc_item["Não Conformidades"] > 0].sort_values(by="Não Conformidades", ascending=False)
        st.plotly_chart(px.bar(
            df_nc_item, y="Item", x="Não Conformidades", orientation="h",
            color="Não Conformidades", color_continuous_scale=["green", "yellow", "red"]
        ), use_container_width=True)
        st.dataframe(df_nc_item)

    with aba4:
        st.subheader("Links das Fotos por Veículo e Itens Não Conformes")
        fotos_df = df.dropna(subset=[col_fotos])
        for placa in fotos_df["Placa do Caminhão"].unique():
            st.markdown(f"### Veículo: {placa}")
            df_placa = fotos_df[fotos_df["Placa do Caminhão"] == placa]
            for idx, row in df_placa.iterrows():
                links = extract_drive_links(row[col_fotos])
                itens_nc = [col for col in cols_itens if row[col].strip().lower() != "ok"]
                st.markdown(f"**{row['Data']} - {row['Motorista']} - Status: {row[col_status]}**")
                st.markdown(f"Itens com Não Conformidade: {', '.join(itens_nc)}")
                for i, link in enumerate(links, 1):
                    st.markdown(f"[🔗 Foto {i}]({link})")

if __name__ == "__main__":
    main()
