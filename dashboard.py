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
    """
    Recebe uma string com URLs (separadas por vírgula ou espaço),
    extrai os file_ids do Google Drive e retorna lista de links diretos para exibir imagens.
    """
    if not urls_string or pd.isna(urls_string):
        return []
    urls = re.split(r'[,\s]+', str(urls_string).strip())
    direct_links = []
    for url in urls:
        match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
        if match:
            file_id = match.group(1)
            direct_links.append(f"https://drive.google.com/uc?export=view&id={file_id}")
        else:
            # Se não for link do drive, retorna a URL original
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
    """
    Extrai número de problemas da string '0 / 3' ou similar.
    Retorna int ou None.
    """
    if isinstance(pont, str) and '/' in pont:
        try:
            parts = pont.split('/')
            return int(parts[0].strip())
        except:
            return None
    return None

def main():
    st.title("Dashboard Checklist Veicular")

    uploaded_file_checklist = st.file_uploader("Selecione o arquivo Excel do checklist:", type="xlsx")
    uploaded_file_manut = st.file_uploader("Selecione o arquivo Excel MANU. PREVENT:", type="xlsx")

    if uploaded_file_checklist is None or uploaded_file_manut is None:
        st.info("Por favor, envie os dois arquivos .xlsx para visualizar o dashboard.")
        return

    # Carrega os dados
    df = load_excel(uploaded_file_checklist)
    manut = load_excel(uploaded_file_manut)

    # Verifique nomes das colunas para evitar erro de digitação
    # Ajuste se os nomes estiverem diferentes no seu arquivo
    col_timestamp = "Carimbo de data/hora"
    col_motorista = "Motorista"
    col_placa = "Placa do Caminhão"
    col_fotos = "Anexe as fotos das não conformidades"
    col_obs = "Observações"
    col_pontuacao = "Pontuação"

    # Conversão para datetime
    df[col_timestamp] = pd.to_datetime(df[col_timestamp], errors='coerce')

    # Filtros por data
    min_date = df[col_timestamp].min()
    max_date = df[col_timestamp].max()

    st.sidebar.markdown("### Filtros")

    start_date = st.sidebar.date_input("Data inicial", min_date.date() if pd.notnull(min_date) else datetime.today())
    end_date = st.sidebar.date_input("Data final", max_date.date() if pd.notnull(max_date) else datetime.today())

    if start_date > end_date:
        st.sidebar.error("Data inicial não pode ser maior que data final.")
        return

    df = df[(df[col_timestamp] >= pd.Timestamp(start_date)) & (df[col_timestamp] <= pd.Timestamp(end_date) + pd.Timedelta(days=1))]

    # Filtros motorista e placa
    motoristas = sorted(df[col_motorista].dropna().unique())
    motorista_sel = st.sidebar.selectbox("Filtrar por Motorista", options=["Todos"] + motoristas)

    placas = sorted(df[col_placa].dropna().unique())
    placa_sel = st.sidebar.selectbox("Filtrar por Placa", options=["Todas"] + placas)

    if motorista_sel != "Todos":
        df = df[df[col_motorista] == motorista_sel]

    if placa_sel != "Todas":
        df = df[df[col_placa] == placa_sel]

    # Itens de checklist - removendo colunas fixas
    itens_excluir = [
        col_timestamp, col_pontuacao, "Data", col_motorista,
        col_placa, "Km atual", col_fotos, col_obs
    ]
    cols_itens = [col for col in df.columns if col not in itens_excluir]

    # Calcular reincidências por checklist (quantidade de "Não Conforme")
    df_itens = df[cols_itens].astype(str).applymap(lambda x: x.strip().lower())
    df["Reincidencias"] = df_itens.apply(lambda row: sum(v != "ok" and v != "" for v in row), axis=1)

    # Extração da pontuação (se desejar usar)
    df["Problemas_Extraidos"] = df[col_pontuacao].apply(extrair_problemas)

    # Agrupamento por placa
    reincidencias_por_placa = df.groupby(col_placa)["Reincidencias"].sum().reset_index()
    total_itens = len(cols_itens)
    reincidencias_por_placa["Índice de Severidade"] = (reincidencias_por_placa["Reincidencias"] / total_itens).round(2)
    reincidencias_por_placa["Cor Severidade"] = reincidencias_por_placa["Índice de Severidade"].apply(severity_color)

    total_nc = df["Reincidencias"].sum()
    veiculo_top = reincidencias_por_placa.iloc[0][col_placa] if not reincidencias_por_placa.empty else "N/A"
    nc_top = reincidencias_por_placa.iloc[0]["Reincidencias"] if not reincidencias_por_placa.empty else 0
    motorista_freq = df[col_motorista].value_counts().idxmax() if not df.empty else "N/A"

    # KPIs
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Total de Não Conformidades", total_nc)
    kpi2.metric("Veículo com Mais Reincidências", veiculo_top, f"{nc_top} ocorrências")
    kpi3.metric("Motorista com Mais Registros", motorista_freq)

    # Gráfico reincidências por veículo
    st.subheader("Não Conformidades por Veículo")
    fig_reinc = px.bar(
        reincidencias_por_placa,
        y=col_placa,
        x="Reincidencias",
        title="Quantidade de Não Conformidades por Veículo",
        color="Reincidencias",
        color_continuous_scale=["green", "yellow", "red"],
        orientation="h"
    )
    st.plotly_chart(fig_reinc, use_container_width=True)
    st.dataframe(reincidencias_por_placa.drop(columns=["Cor Severidade"]))

    # Cruzamento manutenção programada x reincidências
    st.subheader("Manutenção Programada x Reincidências")
    manut = manut.rename(columns=lambda x: x.strip())
    cruzado = pd.merge(reincidencias_por_placa, manut, how="left", left_on=col_placa, right_on="PLACA")
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
    if col_obs in df.columns:
        obs = df[["Data", col_motorista, col_placa, col_obs]].dropna(subset=[col_obs])
        if not obs.empty:
            st.subheader("Observações")
            st.dataframe(obs)

    # Fotos das não conformidades
    st.subheader("Fotos das Não Conformidades")
    if col_fotos in df.columns:
        fotos_df = df[["Data", col_motorista, col_placa, col_fotos]].dropna(subset=[col_fotos])
        if not fotos_df.empty:
            for _, row in fotos_df.iterrows():
                st.markdown(f"**{row['Data']} - {row[col_placa]} - {row[col_motorista]}**")
                links = get_drive_direct_links(row[col_fotos])
                for link in links:
                    try:
                        st.image(link, width=300)
                    except:
                        st.markdown(f"[Ver foto]({link})")
        else:
            st.write("Nenhuma foto anexada.")
    else:
        st.write("Coluna de fotos não encontrada no arquivo.")

if __name__ == "__main__":
    main()
