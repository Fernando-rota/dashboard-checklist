import streamlit as st
import pandas as pd
import plotly.express as px
import re

st.set_page_config(page_title="Dashboard Checklist Veicular", layout="wide")

def get_drive_direct_link(url):
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
    if match:
        file_id = match.group(1)
        return f"https://drive.google.com/uc?export=view&id={file_id}"
    return url

def severity_color(value, thresholds=(0.1, 0.3)):
    if value <= thresholds[0]:
        return "green"
    elif value <= thresholds[1]:
        return "yellow"
    else:
        return "red"

# Upload dos arquivos
uploaded_file_checklist = st.file_uploader("Selecione o arquivo Excel do checklist:", type="xlsx")
uploaded_file_manut = st.file_uploader("Selecione o arquivo Excel MANU. PREVENT:", type="xlsx")

if uploaded_file_checklist and uploaded_file_manut:
    df = pd.read_excel(uploaded_file_checklist)
    df.columns = df.columns.str.strip()
    manut = pd.read_excel(uploaded_file_manut)
    manut.columns = manut.columns.str.strip()

    # Filtros por botão
    col1, col2 = st.columns(2)
    with col1:
        motoristas = sorted(df["Motorista"].dropna().unique())
        motorista_sel = st.radio("Filtrar por Motorista", ["Todos"] + motoristas, horizontal=True)
    with col2:
        placas = sorted(df["Placa do Caminhão"].dropna().unique())
        placa_sel = st.radio("Filtrar por Placa", ["Todas"] + placas, horizontal=True)

    if motorista_sel != "Todos":
        df = df[df["Motorista"] == motorista_sel]
    if placa_sel != "Todas":
        df = df[df["Placa do Caminhão"] == placa_sel]

    # Seleciona apenas os itens do checklist
    cols_itens = [col for col in df.columns if col not in [
        "Carimbo de data/hora", "Pontuação", "Data", "Motorista",
        "Placa do Caminhão", "Km atual", "Anexe as fotos das não conformidades", "Observações"
    ]]

    df_reinc = df.copy()
    df_reinc[cols_itens] = df_reinc[cols_itens].astype(str)
    df_reinc["Reincidencias"] = df_reinc[cols_itens].apply(
        lambda row: sum(v.strip().lower() != "ok" for v in row), axis=1
    )

    reincidencias_por_placa = df_reinc.groupby("Placa do Caminhão")["Reincidencias"].sum().reset_index()
    reincidencias_por_placa = reincidencias_por_placa.sort_values(by="Reincidencias", ascending=False)

    total_itens = len(cols_itens)
    reincidencias_por_placa["Índice de Severidade"] = (reincidencias_por_placa["Reincidencias"] / total_itens).round(2)
    reincidencias_por_placa["Cor Severidade"] = reincidencias_por_placa["Índice de Severidade"].apply(severity_color)

    total_nc = df_reinc["Reincidencias"].sum()
    veiculo_top = reincidencias_por_placa.iloc[0]["Placa do Caminhão"] if not reincidencias_por_placa.empty else "N/A"
    nc_top = reincidencias_por_placa.iloc[0]["Reincidencias"] if not reincidencias_por_placa.empty else 0
    motorista_freq = df["Motorista"].value_counts().idxmax() if not df.empty else "N/A"

    # Abas
    aba1, aba2, aba3, aba4, aba5 = st.tabs([
        "KPIs", "Reincidências", "Manutenção x Reincidência",
        "Não Conformidades por Item", "Observações e Fotos"
    ])

    with aba1:
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total de Não Conformidades", total_nc)
        kpi2.metric("Veículo com Mais Reincidências", veiculo_top, f"{nc_top} ocorrências")
        kpi3.metric("Motorista com Mais Registros", motorista_freq)

    with aba2:
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

    with aba3:
        cruzado = pd.merge(reincidencias_por_placa, manut, how="left", left_on="Placa do Caminhão", right_on="PLACA")
        cruzado = cruzado.dropna(subset=["MANUT. PROGRAMADA"])
        cruzado = cruzado.sort_values(by="Reincidencias", ascending=False)

        def colored_severity(val):
            cor = severity_color(val)
            color_map = {"green": "#2ecc71", "yellow": "#f1c40f", "red": "#e74c3c"}
            return f'<span style="color:{color_map[cor]}; font-weight:bold;">{val}</span>'

        cruzado_display = cruzado[["PLACA", "MODELO", "MANUT. PROGRAMADA", "Reincidencias", "Índice de Severidade"]].copy()
        cruzado_display["Índice de Severidade"] = cruzado_display["Índice de Severidade"].apply(colored_severity)

        st.write("### Manutenção Programada x Reincidências")
        st.write(cruzado_display.to_html(escape=False), unsafe_allow_html=True)

    with aba4:
        df_nci = pd.DataFrame({
            "Item": cols_itens,
            "Não Conformidades": [
                df_reinc[col].astype(str).str.strip().str.lower().ne("ok").sum()
                for col in cols_itens
            ]
        })
        df_nci = df_nci[df_nci["Não Conformidades"] > 0]
        df_nci = df_nci.sort_values(by="Não Conformidades", ascending=False)
        df_nci["% do Total"] = ((df_nci["Não Conformidades"] / df_nci["Não Conformidades"].sum()) * 100).round(1)

        media_nc = df_nci["Não Conformidades"].mean().round(2)
        st.metric("Média de NC por Item", media_nc)

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

    with aba5:
        if "Observações" in df.columns:
            obs = df[["Data", "Motorista", "Placa do Caminhão", "Observações"]].dropna(subset=["Observações"])
            if not obs.empty:
                st.subheader("Observações")
                st.dataframe(obs)

        if "Anexe as fotos das não conformidades" in df.columns:
            fotos = df[["Data", "Motorista", "Placa do Caminhão", "Anexe as fotos das não conformidades"]].dropna()
            if not fotos.empty:
                st.subheader("Fotos das Não Conformidades")
                for _, row in fotos.iterrows():
                    st.markdown(f"**{row['Data']} - {row['Placa do Caminhão']} - {row['Motorista']}**")
                    link = get_drive_direct_link(row['Anexe as fotos das não conformidades'])
                    try:
                        st.image(link, width=400)
                    except:
                        st.markdown(f"[Ver foto]({link})")
else:
    st.info("Por favor, envie os dois arquivos .xlsx para visualizar o dashboard.")
