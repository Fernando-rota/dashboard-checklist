import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime

st.set_page_config(page_title="Dashboard Checklist Veicular", layout="wide")

# --- FUNÇÕES AUXILIARES ---

@st.cache_data
def load_excel(file):
    df = pd.read_excel(file)
    df.columns = df.columns.str.strip()
    return df

def extract_drive_links(urls_string):
    """Extrai lista de links diretos do Google Drive a partir de string com links separados."""
    if not urls_string or pd.isna(urls_string):
        return []
    urls = re.split(r'[,\s\n]+', str(urls_string).strip())
    links = []
    for url in urls:
        match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
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

def colorize_severity(val):
    cor = severity_color(val)
    colors = {"green": "#2ecc71", "yellow": "#f1c40f", "red": "#e74c3c"}
    return f'<span style="color:{colors[cor]}; font-weight:bold;">{val}</span>'

def display_image_gallery(links, cols=3, width=200):
    cols_st = st.columns(cols)
    for i, link in enumerate(links):
        with cols_st[i % cols]:
            try:
                st.image(link, width=width)
            except:
                st.markdown(f"[Ver foto]({link})")

# --- FUNÇÃO PRINCIPAL ---

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

    # Mostrar colunas para debug (opcional)
    st.sidebar.markdown("### Colunas do checklist:")
    st.sidebar.write(df.columns.tolist())

    # Ajustar nomes das colunas conforme seu arquivo
    col_fotos = "Anexe as fotos das não conformidades:"
    col_obs = "Observações:"

    checklist_required = [
        "Carimbo de data/hora", "Motorista", "Placa do Caminhão",
        "Pontuação", col_fotos, col_obs
    ]

    missing = [col for col in checklist_required if col not in df.columns]
    if missing:
        st.error(f"Colunas faltantes no checklist: {missing}")
        return

    manut_required = ["PLACA", "MODELO", "MANUT. PROGRAMADA"]
    missing_manut = [col for col in manut_required if col not in manut.columns]
    if missing_manut:
        st.error(f"Colunas faltantes no arquivo de manutenção: {missing_manut}")
        return

    # Ajustes iniciais
    df["Carimbo de data/hora"] = pd.to_datetime(df["Carimbo de data/hora"], errors='coerce')
    df["Data"] = df["Carimbo de data/hora"].dt.date

    # Filtros de data no sidebar
    min_date, max_date = df["Carimbo de data/hora"].min(), df["Carimbo de data/hora"].max()
    start_date = st.sidebar.date_input("Data inicial", min_date.date() if pd.notnull(min_date) else datetime.today())
    end_date = st.sidebar.date_input("Data final", max_date.date() if pd.notnull(max_date) else datetime.today())

    if start_date > end_date:
        st.sidebar.error("Data inicial não pode ser maior que a final.")
        return

    df = df[(df["Carimbo de data/hora"] >= pd.Timestamp(start_date)) & (df["Carimbo de data/hora"] <= pd.Timestamp(end_date) + pd.Timedelta(days=1))]

    # Filtros Motorista e Placa
    motoristas = sorted(df["Motorista"].dropna().unique())
    placas = sorted(df["Placa do Caminhão"].dropna().unique())

    motorista_sel = st.sidebar.multiselect("Filtrar Motorista(s)", options=motoristas, default=motoristas)
    placa_sel = st.sidebar.multiselect("Filtrar Placa(s)", options=placas, default=placas)

    if motorista_sel:
        df = df[df["Motorista"].isin(motorista_sel)]
    if placa_sel:
        df = df[df["Placa do Caminhão"].isin(placa_sel)]

    # Itens de checklist (excluindo fixos e colunas de texto/fotos)
    cols_excluir = checklist_required + ["Data", "Km atual"]
    cols_itens = [col for col in df.columns if col not in cols_excluir]

    df_itens = df[cols_itens].astype(str).applymap(lambda x: x.strip().lower())
    df["Reincidencias"] = df_itens.apply(lambda row: sum(v != "ok" and v != "" for v in row), axis=1)

    reincid_por_placa = df.groupby("Placa do Caminhão")["Reincidencias"].sum().reset_index()
    total_itens = len(cols_itens)
    reincid_por_placa["Índice de Severidade"] = (reincid_por_placa["Reincidencias"] / total_itens).round(3)

    total_nc = df["Reincidencias"].sum()
    veiculo_top = reincid_por_placa.iloc[0]["Placa do Caminhão"] if not reincid_por_placa.empty else "N/A"
    nc_top = reincid_por_placa.iloc[0]["Reincidencias"] if not reincid_por_placa.empty else 0
    motorista_freq = df["Motorista"].value_counts().idxmax() if not df.empty else "N/A"

    # KPIs
    st.markdown("## KPIs Gerais")
    k1, k2, k3 = st.columns(3)
    k1.metric("Total de Não Conformidades", total_nc)
    k2.metric("Veículo com Mais Não Conformidades", veiculo_top, f"{nc_top} ocorrências")
    k3.metric("Motorista com Mais Registros", motorista_freq)

    # Gráfico reincidências
    st.markdown("## Não Conformidades por Veículo")
    fig1 = px.bar(
        reincid_por_placa.sort_values("Reincidencias", ascending=True),
        x="Reincidencias",
        y="Placa do Caminhão",
        orientation="h",
        color="Reincidencias",
        color_continuous_scale=["green", "yellow", "red"],
        labels={"Reincidencias": "Qtde de Não Conformidades", "Placa do Caminhão": "Placa"}
    )
    st.plotly_chart(fig1, use_container_width=True)

    # Cruzamento com manutenção
    manut = manut.rename(columns=lambda x: x.strip())
    cruzado = pd.merge(reincid_por_placa, manut, how="left", left_on="Placa do Caminhão", right_on="PLACA")
    cruzado = cruzado.dropna(subset=["MANUT. PROGRAMADA"]).sort_values(by="Reincidencias", ascending=False)
    cruzado_display = cruzado[["PLACA", "MODELO", "MANUT. PROGRAMADA", "Reincidencias", "Índice de Severidade"]].copy()
    cruzado_display["Índice de Severidade"] = cruzado_display["Índice de Severidade"].apply(colorize_severity)
    st.markdown("## Cruzamento Manutenção Programada x Não Conformidades")
    st.write(cruzado_display.to_html(escape=False), unsafe_allow_html=True)

    # Não conformidades por item
    st.markdown("## Não Conformidades por Item")
    df_nc_item = pd.DataFrame({
        "Item": cols_itens,
        "Não Conformidades": [df_itens[col].ne("ok").sum() for col in cols_itens]
    })
    df_nc_item = df_nc_item[df_nc_item["Não Conformidades"] > 0].sort_values(by="Não Conformidades", ascending=False)
    df_nc_item["% do Total"] = ((df_nc_item["Não Conformidades"] / df_nc_item["Não Conformidades"].sum()) * 100).round(1)
    fig2 = px.bar(
        df_nc_item,
        y="Item",
        x="Não Conformidades",
        orientation="h",
        color="Não Conformidades",
        color_continuous_scale=["green", "yellow", "red"],
        labels={"Não Conformidades": "Quantidade", "Item": "Item de Checklist"}
    )
    st.plotly_chart(fig2, use_container_width=True)
    st.dataframe(df_nc_item.reset_index(drop=True))

    # Observações
    if col_obs in df.columns:
        obs = df[["Data", "Motorista", "Placa do Caminhão", col_obs]].dropna(subset=[col_obs])
        if not obs.empty:
            st.markdown("## Observações Registradas")
            st.dataframe(obs)

    # Fotos
    st.markdown("## Fotos das Não Conformidades")
    if col_fotos in df.columns:
        fotos_df = df[["Data", "Motorista", "Placa do Caminhão", col_fotos]].dropna(subset=[col_fotos])
        if fotos_df.empty:
            st.write("Nenhuma foto anexada.")
        else:
            for _, row in fotos_df.iterrows():
                st.markdown(f"**{row['Data']} - {row['Placa do Caminhão']} - {row['Motorista']}**")
                links = extract_drive_links(row[col_fotos])
                display_image_gallery(links, cols=3, width=250)
    else:
        st.write("Coluna de fotos não encontrada no arquivo.")

if __name__ == "__main__":
    main()
