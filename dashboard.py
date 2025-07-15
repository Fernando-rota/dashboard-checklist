import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime

st.set_page_config(page_title="Checklist Veicular", layout="wide")

@st.cache_data
def load_excel(file):
    df = pd.read_excel(file)
    df.columns = df.columns.str.strip().str.replace('\s+', ' ', regex=True)
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
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

def severity_color(val):
    if val <= 0.1:
        return f'<span style="color:#2ecc71;font-weight:bold;">{val:.3f}</span>'
    elif val <= 0.3:
        return f'<span style="color:#f1c40f;font-weight:bold;">{val:.3f}</span>'
    else:
        return f'<span style="color:#e74c3c;font-weight:bold;">{val:.3f}</span>'

def main():
    st.title("🚛 Dashboard Checklist Veicular")

    # Upload
    checklist_file = st.file_uploader("📁 Checklist Excel", type="xlsx")
    manut_file = st.file_uploader("📁 MANU.PREVENT Excel", type="xlsx")
    if not checklist_file or not manut_file:
        st.info("📌 Envie os dois arquivos para continuar.")
        return

    with st.spinner("🔄 Carregando..."):
        df = load_excel(checklist_file)
        manut = load_excel(manut_file)

    # Colunas principais
    col_fotos = "Anexe as fotos das não conformidades:"
    col_obs = "Observações:"
    col_status = "Status NC"

    obrigatorias = ["Carimbo de data/hora", "Motorista", "Placa do Caminhão", "Pontuação", col_fotos, col_obs, col_status]
    if any(col not in df.columns for col in obrigatorias):
        st.error(f"❌ Colunas obrigatórias ausentes: {[c for c in obrigatorias if c not in df.columns]}")
        return

    # Limpeza inicial
    df["Carimbo de data/hora"] = pd.to_datetime(df["Carimbo de data/hora"], errors="coerce")
    if df["Carimbo de data/hora"].isna().all():
        st.error("❌ Nenhuma data válida encontrada em 'Carimbo de data/hora'.")
        return

    df["Data"] = df["Carimbo de data/hora"].dt.strftime("%d/%m/%Y")
    df[col_status] = df[col_status].fillna("").str.lower().str.strip()

    # Filtros globais
    st.sidebar.markdown("### 📅 Filtros")
    min_date, max_date = df["Carimbo de data/hora"].min(), df["Carimbo de data/hora"].max()
    start_date = st.sidebar.date_input("Data inicial", min_date.date())
    end_date = st.sidebar.date_input("Data final", max_date.date())

    if start_date > end_date:
        st.sidebar.error("Data inicial não pode ser maior que a final.")
        return

    df = df[(df["Carimbo de data/hora"] >= pd.Timestamp(start_date)) & 
            (df["Carimbo de data/hora"] <= pd.Timestamp(end_date) + pd.Timedelta(days=1))]

    motoristas = sorted(df["Motorista"].dropna().unique())
    placas = sorted(df["Placa do Caminhão"].dropna().unique())

    sel_motorista = st.sidebar.multiselect("Motoristas", motoristas, default=motoristas)
    sel_placa = st.sidebar.multiselect("Placas", placas, default=placas)

    df = df[df["Motorista"].isin(sel_motorista)]
    df = df[df["Placa do Caminhão"].isin(sel_placa)]

    status_opcoes = ["Todos", "Aberto / Em andamento", "Concluído"]
    status_sel = st.sidebar.selectbox("Status da NC", status_opcoes)

    if status_sel == "Aberto / Em andamento":
        df = df[df[col_status].isin(["aberto", "em andamento"])]
    elif status_sel == "Concluído":
        df = df[df[col_status] == "concluído"]

    # Itens de checklist
    cols_excluir = obrigatorias + ["Data", "Km atual"]
    itens = [col for col in df.columns if col not in cols_excluir]

    df_itens = df[itens].fillna("").astype(str).applymap(lambda x: x.strip().lower())
    df["Reincidencias"] = df_itens.apply(lambda row: sum(v != "ok" and v != "" for v in row), axis=1)

    # Tabs
    aba1, aba2, aba3, aba4, aba5 = st.tabs([
        "📊 Visão Geral", "🛠️ Manutenção", "📌 Itens Críticos", "📝 Observações", "📸 Fotos"
    ])

    with aba1:
        st.markdown("### 🔢 Indicadores")
        resumo = df.groupby("Placa do Caminhão")["Reincidencias"].sum().reset_index()
        veic_top = resumo.loc[resumo["Reincidencias"].idxmax(), "Placa do Caminhão"] if not resumo.empty else "N/A"
        total_nc = resumo["Reincidencias"].max() if not resumo.empty else 0

        col1, col2 = st.columns(2)
        col1.metric("🚛 Veículo com Mais NCs", veic_top, f"{int(total_nc)} ocorrências")
        col2.metric("📋 Checklists no Período", len(df))

        st.markdown("### 📉 NCs por Veículo")
        fig = px.bar(
            resumo.sort_values("Reincidencias"),
            x="Reincidencias",
            y="Placa do Caminhão",
            color="Reincidencias",
            orientation="h",
            color_continuous_scale=["green", "yellow", "red"],
            labels={"Reincidencias": "Não Conformidades", "Placa do Caminhão": "Placa"}
        )
        st.plotly_chart(fig, use_container_width=True)

    with aba2:
        manut.columns = manut.columns.str.strip()
        if "PLACA" not in manut.columns or "MANUT. PROGRAMADA" not in manut.columns:
            st.warning("❌ Colunas 'PLACA' ou 'MANUT. PROGRAMADA' ausentes.")
        else:
            cruzado = pd.merge(resumo, manut, how="left", left_on="Placa do Caminhão", right_on="PLACA")
            cruzado = cruzado.dropna(subset=["MANUT. PROGRAMADA"]).sort_values(by="Reincidencias", ascending=False)
            cruzado["Índice de Severidade"] = (
                (cruzado["Reincidencias"] / len(itens)).round(3).apply(severity_color)
            )
            st.markdown("### 🛠️ Manutenção Programada x NCs")
            st.write(cruzado[["PLACA", "MODELO", "MANUT. PROGRAMADA", "Reincidencias", "Índice de Severidade"]].to_html(escape=False), unsafe_allow_html=True)

    with aba3:
        st.markdown("### 📌 Itens com Mais Não Conformidades")
        df_nc_item = pd.DataFrame({
            "Item": itens,
            "Não Conformidades": [df_itens[col].ne("ok").sum() for col in itens]
        }).query("`Não Conformidades` > 0").sort_values("Não Conformidades", ascending=False)
        df_nc_item["%"] = ((df_nc_item["Não Conformidades"] / df_nc_item["Não Conformidades"].sum()) * 100).round(1)

        st.plotly_chart(px.bar(
            df_nc_item,
            x="Não Conformidades",
            y="Item",
            orientation="h",
            color="Não Conformidades",
            color_continuous_scale=["green", "yellow", "red"]
        ), use_container_width=True)

        st.dataframe(df_nc_item)

    with aba4:
        st.markdown("### 📝 Observações dos Motoristas")
        obs = df[["Data", "Motorista", "Placa do Caminhão", col_obs, col_status]].dropna(subset=[col_obs])
        if not obs.empty:
            st.dataframe(obs)
        else:
            st.info("Nenhuma observação registrada.")

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

if __name__ == "__main__":
    main()
