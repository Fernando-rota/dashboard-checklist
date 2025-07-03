import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime

st.set_page_config(page_title="Dashboard Checklist Veicular", layout="wide")

@st.cache_data
def load_excel(file):
    df = pd.read_excel(file)
    df.columns = df.columns.str.strip()
    return df

def get_drive_direct_links(urls_string):
    # Trata múltiplos links separados por vírgula ou espaço
    urls = re.split(r'[,\s]+', str(urls_string).strip())
    direct_links = []
    for url in urls:
        match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
        if match:
            file_id = match.group(1)
            direct_links.append(f"https://drive.google.com/uc?export=view&id={file_id}")
        else:
            direct_links.append(url)
    return direct_links

def severity_color(value, thresholds=(0.1, 0.3)):
    if value <= thresholds[0]:
        return "green"
    elif value <= thresholds[1]:
        return "yellow"
    else:
        return "red"

def extrair_problemas(pont):
    if isinstance(pont, str) and '/' in pont:
        try:
            parts = pont.split('/')
            return int(parts[0].strip())
        except:
            return None
    return None

uploaded_file_checklist = st.file_uploader("Selecione o arquivo Excel do checklist:", type="xlsx")
uploaded_file_manut = st.file_uploader("Selecione o arquivo Excel MANU. PREVENT:", type="xlsx")

if uploaded_file_checklist and uploaded_file_manut:
    df = load_excel(uploaded_file_checklist)
    manut = load_excel(uploaded_file_manut)

    # Convertendo carimbo para datetime e criando filtros de data
    df["Carimbo de data/hora"] = pd.to_datetime(df["Carimbo de data/hora"], errors='coerce')
    min_date = df["Carimbo de data/hora"].min()
    max_date = df["Carimbo de data/hora"].max()
    
    st.sidebar.markdown("### Filtros")
    start_date = st.sidebar.date_input("Data inicial", min_date.date() if pd.notnull(min_date) else datetime.today())
    end_date = st.sidebar.date_input("Data final", max_date.date() if pd.notnull(max_date) else datetime.today())
    
    # Garantir que start_date <= end_date
    if start_date > end_date:
        st.sidebar.error("Data inicial não pode ser maior que data final.")
    else:
        df = df[(df["Carimbo de data/hora"] >= pd.Timestamp(start_date)) & 
                (df["Carimbo de data/hora"] <= pd.Timestamp(end_date) + pd.Timedelta(days=1))]

        motoristas = sorted(df["Motorista"].dropna().unique())
        motorista_sel = st.sidebar.selectbox("Filtrar por Motorista", options=["Todos"] + motoristas)
        
        placas = sorted(df["Placa do Caminhão"].dropna().unique())
        placa_sel = st.sidebar.selectbox("Filtrar por Placa", options=["Todas"] + placas)
        
        if motorista_sel != "Todos":
            df = df[df["Motorista"] == motorista_sel]
        if placa_sel != "Todas":
            df = df[df["Placa do Caminhão"] == placa_sel]

        cols_itens = [col for col in df.columns if col not in [
            "Carimbo de data/hora", "Pontuação", "Data", "Motorista",
            "Placa do Caminhão", "Km atual",
            "Anexe as fotos das não conformidades", "Observações"
        ]]

        df_reinc = df.copy()
        df_reinc[cols_itens] = df_reinc[cols_itens].astype(str)
        df_reinc["Reincidencias"] = df_reinc[cols_itens].apply(lambda row: sum(v.strip().lower() != "ok" for v in row), axis=1)
        df_reinc["Problemas_Extraidos"] = df_reinc["Pontuação"].apply(extrair_problemas)

        reincidencias_por_placa = df_reinc.groupby("Placa do Caminhão")["Reincidencias"].sum().reset_index()
        total_itens = len(cols_itens)
        reincidencias_por_placa["Índice de Severidade"] = (reincidencias_por_placa["Reincidencias"] / total_itens).round(2)
        reincidencias_por_placa["Cor Severidade"] = reincidencias_por_placa["Índice de Severidade"].apply(severity_color)

        total_nc = df_reinc["Reincidencias"].sum()
        veiculo_top = reincidencias_por_placa.iloc[0]["Placa do Caminhão"] if not reincidencias_por_placa.empty else "N/A"
        nc_top = reincidencias_por_placa.iloc[0]["Reincidencias"] if not reincidencias_por_placa.empty else 0
        motorista_freq = df["Motorista"].value_counts().idxmax() if not df.empty else "N/A"

        st.title("Dashboard Checklist Veicular")

        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Total de Não Conformidades", total_nc)
        kpi2.metric("Veículo com Mais Reincidências", veiculo_top, f"{nc_top} ocorrências")
        kpi3.metric("Motorista com Mais Registros", motorista_freq)

        st.subheader("Não Conformidades por Veículo")
        fig_reinc = px.bar(
            reincidencias_por_placa,
            y="Placa do Caminhão",
            x="Reincidencias",
            title="Quantidade de Não Conformidades por Veículo",
            color="Reincidencias",
            color_continuous_scale=["green", "yellow", "red"],
            orientation="h"
        )
        st.plotly_chart(fig_reinc, use_container_width=True)
        st.dataframe(reincidencias_por_placa.drop(columns=["Cor Severidade"]))

        # Cruzamento com manutenção programada
        st.subheader("Manutenção Programada x Reincidências")
        cruzado = pd.merge(reincidencias_por_placa, manut, how="left", left_on="Placa do Caminhão", right_on="PLACA")
        cruzado = cruzado.dropna(subset=["MANUT. PROGRAMADA"])
        cruzado = cruzado.sort_values(by="Reincidencias", ascending=False)
        
        def colored_severity(val):
            cor = severity_color(val)
            color_map = {"green": "#2ecc71", "yellow": "#f1c40f", "red": "#e74c3c"}
            return f'<span style="color:{color_map[cor]}; font-weight:bold;">{val}</span>'
        
        cruzado_display = cruzado[["PLACA", "MODELO", "MANUT. PROGRAMADA", "Reincidencias", "Índice de Severidade"]].copy()
        cruzado_display["Índice de Severidade"] = cruzado_display["Índice de Severidade"].apply(colored_severity)
        st.write(cruzado_display.to_html(escape=False), unsafe_allow_html=True)

        # Não conformidades por item
        st.subheader("Não Conformidades por Item")
        df_nci = pd.DataFrame({
            "Item": cols_itens,
            "Não Conformidades": [
                df[col].astype(str).str.strip().str.lower().ne("ok").sum() for col in cols_itens
            ]
        })
        df_nci = df_nci[df_nci["Não Conformidades"] > 0]
        df_nci = df_nci.sort_values(by="Não Conformidades", ascending=False)
        df_nci["% do Total"] = ((df_nci["Não Conformidades"] / df_nci["Não Conformidades"].sum()) * 100).round(1)

        fig_nci = px.bar(
            df_nci,
            y="Item",
            x="Não Conformidades",
            title="Não Conformidades por Item",
            color="Não Conformidades",
            color_continuous_scale=["green", "yellow", "red"],
            orientation="h"
        )
        st.plotly_chart(fig_nci, use_container_width=True)
        st.dataframe(df_nci.reset_index(drop=True))

        # Observações
        if "Observações" in df.columns:
            obs = df[["Data", "Motorista", "Placa do Caminhão", "Observações"]].dropna(subset=["Observações"])
            if not obs.empty:
                st.subheader("Observações")
                st.dataframe(obs)

        # Fotos das não conformidades
        st.subheader("Fotos das Não Conformidades")
        fotos_df = df[["Data", "Motorista", "Placa do Caminhão", "Anexe as fotos das não conformidades"]].dropna(subset=["Anexe as fotos das não conformidades"])
        if not fotos_df.empty:
            for _, row in fotos_df.iterrows():
                st.markdown(f"**{row['Data']} - {row['Placa do Caminhão']} - {row['Motorista']}**")
                links = get_drive_direct_links(row['Anexe as fotos das não conformidades'])
                for link in links:
                    try:
                        st.image(link, width=300)
                    except:
                        st.markdown(f"[Ver foto]({link})")
        else:
            st.write("Nenhuma foto anexada.")

else:
    st.info("Por favor, envie os dois arquivos .xlsx para visualizar o dashboard.")
