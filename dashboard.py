# DASHBOARD CHECKLIST VEICULAR
# Arquivo completo com visualização de fotos via st.image e upload simplificado

import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime

st.set_page_config(page_title="Dashboard Checklist Veicular", layout="wide")

@st.cache_data
def load_excel(file):
    df = pd.read_excel(file)
    df.columns = df.columns.str.strip().str.replace('\s+', ' ', regex=True)
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    return df

def extract_drive_links(urls_string):
    if not urls_string or pd.isna(urls_string):
        return []
    urls = re.split(r'[\s,\n]+', str(urls_string).strip())
    links = []
    for url in urls:
        match = re.search(r'/d/([a-zA-Z0-9_-]+)', url) or re.search(r'id=([a-zA-Z0-9_-]+)', url)
        if match:
            file_id = match.group(1)
            links.append(f"https://drive.google.com/uc?export=view&id={file_id}")
        else:
            links.append(url)
    return links

def main():
    st.title("\U0001F69B Dashboard Checklist Veicular")

    checklist_file = st.file_uploader("Checklist (.xlsx)", type="xlsx", label_visibility="collapsed")
    manut_file = st.file_uploader("Manutenção (.xlsx)", type="xlsx", label_visibility="collapsed")
    
    if not checklist_file or not manut_file:
        st.warning("Envie os dois arquivos Excel para visualizar o dashboard.")
        return

    df = load_excel(checklist_file)
    manut = load_excel(manut_file)

    col_fotos = "Anexe as fotos das não conformidades:"
    col_obs = "Observações:"
    col_status = "Status NC"

    obrigatorias = ["Carimbo de data/hora", "Motorista", "Placa do Caminhão", col_fotos, col_obs, col_status]
    for col in obrigatorias:
        if col not in df.columns:
            st.error(f"Coluna obrigatória ausente: {col}")
            return

    df["Carimbo de data/hora"] = pd.to_datetime(df["Carimbo de data/hora"], errors="coerce")
    df["Data"] = df["Carimbo de data/hora"].dt.strftime("%d/%m/%Y")
    df[col_status] = df[col_status].fillna('').str.lower().str.strip()

    # Filtros
    st.sidebar.header("Filtros")
    min_dt, max_dt = df["Carimbo de data/hora"].min(), df["Carimbo de data/hora"].max()
    start = st.sidebar.date_input("Data inicial", min_dt.date())
    end = st.sidebar.date_input("Data final", max_dt.date())

    if start > end:
        st.sidebar.error("Data inicial maior que final.")
        return

    df = df[(df["Carimbo de data/hora"] >= pd.to_datetime(start)) & (df["Carimbo de data/hora"] <= pd.to_datetime(end) + pd.Timedelta(days=1))]

    placas = sorted(df["Placa do Caminhão"].dropna().unique())
    placas_sel = st.sidebar.multiselect("Placas", placas, default=placas)
    df = df[df["Placa do Caminhão"].isin(placas_sel)]

    itens = [col for col in df.columns if col not in obrigatorias + ["Data", "Km atual"]]
    df_itens = df[itens].fillna("").astype(str).applymap(lambda x: x.strip().lower())
    df["Reincidencias"] = df_itens.apply(lambda row: sum(v != "ok" and v != "" for v in row), axis=1)

    aba1, aba2, aba3 = st.tabs(["\U0001F4CA Visão Geral", "\U0001F4DD Observações", "\U0001F4F8 Fotos das NCs"])

    with aba1:
        resumo = df.groupby("Placa do Caminhão")["Reincidencias"].sum().reset_index()
        fig = px.bar(
            resumo.sort_values("Reincidencias"),
            x="Reincidencias", y="Placa do Caminhão", orientation="h",
            color="Reincidencias", color_continuous_scale=["green", "yellow", "red"]
        )
        st.plotly_chart(fig, use_container_width=True)

    with aba2:
        obs_df = df[["Data", "Motorista", "Placa do Caminhão", col_obs, col_status]].dropna(subset=[col_obs])
        if not obs_df.empty:
            st.dataframe(obs_df)
        else:
            st.info("Nenhuma observação registrada.")

    with aba3:
        st.markdown("### ✨ Visualização das Fotos de Não Conformidades")
        fotos_df = df.dropna(subset=[col_fotos])
        for _, row in fotos_df.iterrows():
            links = extract_drive_links(row[col_fotos])
            st.markdown(f"**{row['Data']} - {row['Placa do Caminhão']} - {row['Motorista']}**")
            nc_itens = [col for col in itens if row[col].strip().lower() != "ok"]
            if nc_itens:
                st.markdown(f"<span style='color:red'>❌ Itens NC:</span> {', '.join(nc_itens)}", unsafe_allow_html=True)
            for link in links:
                st.image(link, width=300)
            st.markdown("---")

if __name__ == "__main__":
    main()
# DASHBOARD CHECKLIST VEICULAR
# Arquivo completo com visualização de fotos via st.image e upload simplificado

import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime

st.set_page_config(page_title="Dashboard Checklist Veicular", layout="wide")

@st.cache_data
def load_excel(file):
    df = pd.read_excel(file)
    df.columns = df.columns.str.strip().str.replace('\s+', ' ', regex=True)
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    return df

def extract_drive_links(urls_string):
    if not urls_string or pd.isna(urls_string):
        return []
    urls = re.split(r'[\s,\n]+', str(urls_string).strip())
    links = []
    for url in urls:
        match = re.search(r'/d/([a-zA-Z0-9_-]+)', url) or re.search(r'id=([a-zA-Z0-9_-]+)', url)
        if match:
            file_id = match.group(1)
            links.append(f"https://drive.google.com/uc?export=view&id={file_id}")
        else:
            links.append(url)
    return links

def main():
    st.title("\U0001F69B Dashboard Checklist Veicular")

    checklist_file = st.file_uploader("Checklist (.xlsx)", type="xlsx", label_visibility="collapsed")
    manut_file = st.file_uploader("Manutenção (.xlsx)", type="xlsx", label_visibility="collapsed")
    
    if not checklist_file or not manut_file:
        st.warning("Envie os dois arquivos Excel para visualizar o dashboard.")
        return

    df = load_excel(checklist_file)
    manut = load_excel(manut_file)

    col_fotos = "Anexe as fotos das não conformidades:"
    col_obs = "Observações:"
    col_status = "Status NC"

    obrigatorias = ["Carimbo de data/hora", "Motorista", "Placa do Caminhão", col_fotos, col_obs, col_status]
    for col in obrigatorias:
        if col not in df.columns:
            st.error(f"Coluna obrigatória ausente: {col}")
            return

    df["Carimbo de data/hora"] = pd.to_datetime(df["Carimbo de data/hora"], errors="coerce")
    df["Data"] = df["Carimbo de data/hora"].dt.strftime("%d/%m/%Y")
    df[col_status] = df[col_status].fillna('').str.lower().str.strip()

    # Filtros
    st.sidebar.header("Filtros")
    min_dt, max_dt = df["Carimbo de data/hora"].min(), df["Carimbo de data/hora"].max()
    start = st.sidebar.date_input("Data inicial", min_dt.date())
    end = st.sidebar.date_input("Data final", max_dt.date())

    if start > end:
        st.sidebar.error("Data inicial maior que final.")
        return

    df = df[(df["Carimbo de data/hora"] >= pd.to_datetime(start)) & (df["Carimbo de data/hora"] <= pd.to_datetime(end) + pd.Timedelta(days=1))]

    placas = sorted(df["Placa do Caminhão"].dropna().unique())
    placas_sel = st.sidebar.multiselect("Placas", placas, default=placas)
    df = df[df["Placa do Caminhão"].isin(placas_sel)]

    itens = [col for col in df.columns if col not in obrigatorias + ["Data", "Km atual"]]
    df_itens = df[itens].fillna("").astype(str).applymap(lambda x: x.strip().lower())
    df["Reincidencias"] = df_itens.apply(lambda row: sum(v != "ok" and v != "" for v in row), axis=1)

    aba1, aba2, aba3 = st.tabs(["\U0001F4CA Visão Geral", "\U0001F4DD Observações", "\U0001F4F8 Fotos das NCs"])

    with aba1:
        resumo = df.groupby("Placa do Caminhão")["Reincidencias"].sum().reset_index()
        fig = px.bar(
            resumo.sort_values("Reincidencias"),
            x="Reincidencias", y="Placa do Caminhão", orientation="h",
            color="Reincidencias", color_continuous_scale=["green", "yellow", "red"]
        )
        st.plotly_chart(fig, use_container_width=True)

    with aba2:
        obs_df = df[["Data", "Motorista", "Placa do Caminhão", col_obs, col_status]].dropna(subset=[col_obs])
        if not obs_df.empty:
            st.dataframe(obs_df)
        else:
            st.info("Nenhuma observação registrada.")

    with aba3:
        st.markdown("### ✨ Visualização das Fotos de Não Conformidades")
        fotos_df = df.dropna(subset=[col_fotos])
        for _, row in fotos_df.iterrows():
            links = extract_drive_links(row[col_fotos])
            st.markdown(f"**{row['Data']} - {row['Placa do Caminhão']} - {row['Motorista']}**")
            nc_itens = [col for col in itens if row[col].strip().lower() != "ok"]
            if nc_itens:
                st.markdown(f"<span style='color:red'>❌ Itens NC:</span> {', '.join(nc_itens)}", unsafe_allow_html=True)
            for link in links:
                st.image(link, width=300)
            st.markdown("---")

if __name__ == "__main__":
    main()
