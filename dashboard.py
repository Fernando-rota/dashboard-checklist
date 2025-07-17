import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime

st.set_page_config(page_title="Dashboard Checklist Veicular", layout="wide")

# --- Funções utilitárias ---

@st.cache_data
def load_excel(file):
    df = pd.read_excel(file)
    df.columns = df.columns.str.strip().str.replace(r'\s+', ' ', regex=True)
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    return df

@st.cache_data
def extract_drive_links(urls_string):
    if not urls_string or pd.isna(urls_string):
        return []
    urls = re.split(r'[,\s\n]+', str(urls_string).strip())
    links = []
    for url in urls:
        match = re.search(r'/d/([a-zA-Z0-9_-]+)', url) or re.search(r'id=([a-zA-Z0-9_-]+)', url)
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

def classificar_veiculo(nc_total, status):
    status = status.lower().strip()
    if status in ["aberto", "em andamento"] or nc_total > 5:
        return "🚫 Crítico"
    elif 2 <= nc_total <= 5:
        return "⚠️ Atenção"
    else:
        return "✅ OK"

# Mapeamento personalizado dos seus itens para categorias
CATEGORIAS = {
    "drenar a água acumulada": "Combustível e Filtros",
    "pré-filtro de combustivél": "Combustível e Filtros",
    "pneus": "Pneus",
    "estepe": "Pneus",
    "vazamentos": "Vazamentos e Fluídos",
    "níveis (água, óleo, fluidos": "Vazamentos e Fluídos",
    "faróis": "Iluminação",
    "lanternas": "Iluminação",
    "luzes indicadoras": "Iluminação",
    "luz de freio": "Iluminação",
    "luz de marcha": "Iluminação",
    "vidros": "Vidros e Retrovisores",
    "espelhos retrovisores": "Vidros e Retrovisores",
    "trincos": "Segurança",
    "fechaduras": "Segurança",
    "nível de fluido do sistema de freio": "Freios",
    "direção hidráulica": "Direção",
    "embreagem": "Embreagem",
    "reservatório do lavador": "Sistema de Limpeza",
    "funcionamento do limpador": "Sistema de Limpeza",
    "pressão pneumática do sistema de freios": "Freios",
    "funcionamento do tacógrafo": "Eletrônica",
    "funcionamento do alarme sonoro": "Eletrônica",
    "luzes de advertência": "Eletrônica",
    "abastecimento de combustível": "Combustível e Filtros",
}

def mapear_categoria(item):
    item = item.lower()
    for chave, cat in CATEGORIAS.items():
        if chave in item:
            return cat
    return "Outros"

# --- Função principal ---

def main():
    st.title("🚛 Dashboard Checklist Veicular")

    checklist_file = st.file_uploader("📁 Checklist Excel", type="xlsx")
    manut_file = st.file_uploader("📁 MANU.PREVENT Excel", type="xlsx")
    if not checklist_file or not manut_file:
        st.info("📌 Envie os dois arquivos para continuar.")
        return

    with st.spinner("🔄 Carregando dados..."):
        df = load_excel(checklist_file)
        manut = load_excel(manut_file)

    col_fotos = "Anexe as fotos das não conformidades:"
    col_obs = "Observações:"
    col_status = "Status NC"

    # Ajuste da lista de colunas obrigatórias (removendo "Pontuação" que não existe)
    obrigatorias = ["Carimbo de data/hora", "Motorista", "Placa do Caminhão", col_fotos, col_obs, col_status]

    # Validação colunas obrigatórias
    faltantes = [c for c in obrigatorias if c not in df.columns]
    if faltantes:
        st.error(f"❌ Colunas obrigatórias ausentes: {faltantes}")
        return

    # Padronização de datas e status
    df["Carimbo de data/hora"] = pd.to_datetime(df["Carimbo de data/hora"], errors="coerce")
    if df["Carimbo de data/hora"].isna().all():
        st.error("❌ Nenhuma data válida encontrada.")
        return
    df["Data"] = df["Carimbo de data/hora"].dt.strftime("%d/%m/%Y")

    df[col_status] = df[col_status].fillna("").astype(str).str.lower().str.strip()

    # Filtros no sidebar
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

    if sel_motorista:
        df = df[df["Motorista"].isin(sel_motorista)]
    if sel_placa:
        df = df[df["Placa do Caminhão"].isin(sel_placa)]

    status_opcoes = ["Todos", "Aberto / Em andamento", "Concluído"]
    status_sel = st.sidebar.selectbox("Status da NC", status_opcoes)

    if status_sel == "Aberto / Em andamento":
        df = df[df[col_status].isin(["aberto", "em andamento"])]
    elif status_sel == "Concluído":
        df = df[df[col_status] == "concluído"]

    # Definir itens do checklist excluindo colunas não relacionadas
    cols_excluir = obrigatorias + ["Data", "Km atual"]
    itens = [col for col in df.columns if col not in cols_excluir]

    # Padronizar respostas do checklist (minúsculas, sem espaços)
    df_itens = df[itens].fillna("").astype(str).applymap(lambda x: x.strip().lower())

    # Cálculo de reincidências (NCs) por checklist
    df["Reincidencias"] = df_itens.apply(lambda row: sum((v != "ok") and (v != "") for v in row), axis=1)

    # Taxa de conformidade (% itens ok)
    df_itens_ok = df_itens.applymap(lambda x: x == "ok")
    df["Taxa_Conformidade"] = df_itens_ok.sum(axis=1) / len(itens)

    # Classificação dos veículos
    df_veic_nc = df.groupby("Placa do Caminhão").agg(
        Total_NC=pd.NamedAgg(column="Reincidencias", aggfunc="sum"),
        Status_Aberto=pd.NamedAgg(column=col_status, aggfunc=lambda s: any(x in ["aberto", "em andamento"] for x in s))
    ).reset_index()
    df_veic_nc["Classificação"] = df_veic_nc.apply(
        lambda row: classificar_veiculo(row["Total_NC"], "aberto" if row["Status_Aberto"] else "concluído"), axis=1)

    # Mapear categorias para itens
    categorias = [mapear_categoria(item) for item in itens]

    # DataFrame para análise por categoria
    df_cat = pd.DataFrame({
        "Item": itens,
        "Categoria": categorias,
        "NCs": [df_itens[col].ne("ok").sum() for col in itens]
    })
    df_cat = df_cat[df_cat["NCs"] > 0]
    df_cat_grouped = df_cat.groupby("Categoria").sum().reset_index().sort_values("NCs", ascending=False)

    # === TABS ===
    aba1, aba2, aba3, aba4, aba5 = st.tabs([
        "📊 Visão Geral", "🛠️ Manutenção", "📌 Itens Críticos", "📝 Observações", "📸 Fotos"
    ])

    # --- Aba 1: Visão Geral ---
    with aba1:
        st.markdown("### 🔢 Indicadores")

        resumo = df.groupby("Placa do Caminhão")["Reincidencias"].sum().reset_index()
        veic_top = resumo.loc[resumo["Reincidencias"].idxmax(), "Placa do Caminhão"] if not resumo.empty else "N/A"
        total_nc = resumo["Reincidencias"].max() if not resumo.empty else 0
        total_checklists = len(df)
        checklists_com_nc = df["Reincidencias"].gt(0).sum()
        pct_checklists_com_nc = round((checklists_com_nc / total_checklists) * 100, 1) if total_checklists > 0 else 0
        media_nc_por_checklist = round(df["Reincidencias"].mean(), 2)
        total_itens_verificados = total_checklists * len(itens)
        media_pct_nc_por_checklist = round((df["Reincidencias"] / len(itens)).mean() * 100, 1)
        media_taxa_conformidade = round(df["Taxa_Conformidade"].mean() * 100, 2)

        kpi1, kpi2 = st.columns(2)
        kpi1.metric("🚛 Veículo com Mais NCs", veic_top, f"{int(total_nc)} ocorrências")
        kpi2.metric("📋 Checklists no Período", total_checklists)

        kpi3, kpi4 = st.columns(2)
        kpi3.metric("📉 % de Checklists com NC", f"{pct_checklists_com_nc}%", f"{checklists_com_nc} com NC")
        kpi4.metric("⚠️ Média de NCs por Checklist", media_nc_por_checklist)

        kpi5, kpi6 = st.columns(2)
        kpi5.metric("🧾 Total de Itens Verificados", f"{total_itens_verificados:,}")
        kpi6.metric("🔧 % Médio de Itens NC por Checklist", f"{media_pct_nc_por_checklist}%")

        kpi7 = st.metric("✅ Média de Itens Conformes (%)", f"{media_taxa_conformidade}%")

        st.markdown("### 🏷️ Classificação dos Veículos")
        st.dataframe(df_veic_nc[["Placa do Caminhão", "Total_NC", "Classificação"]]
                     .sort_values("Total_NC", ascending=False)
                     .reset_index(drop=True))

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

        st.markdown("### 📅 Tendência Temporal de NCs")
        agrupamento = st.selectbox("Agrupar por", ["Diário", "Semanal", "Mensal"], index=2)

        if agrupamento == "Diário":
            df_tend = df.groupby(df["Carimbo de data/hora"].dt.date).agg(
                Checklists_Com_NC=("Reincidencias", lambda x: (x > 0).sum())
            ).reset_index()
            df_tend.rename(columns={"Carimbo de data/hora": "Data"}, inplace=True)
            xaxis_title = "Data"

        elif agrupamento == "Semanal":
            df_tend = df.groupby(df["Carimbo de data/hora"].dt.to_period("W")).agg(
                Checklists_Com_NC=("Reincidencias", lambda x: (x > 0).sum())
            ).reset_index()
            df_tend["Data"] = df_tend["Carimbo de data/hora"].dt.start_time
            xaxis_title = "Semana"

        else:  # Mensal
            df_tend = df.groupby(df["Carimbo de data/hora"].dt.to_period("M")).agg(
                Checklists_Com_NC=("Reincidencias", lambda x: (x > 0).sum())
            ).reset_index()
            df_tend["Data"] = df_tend["Carimbo de data/hora"].dt.start_time
            xaxis_title = "Mês"

        fig_tend = px.line(df_tend, x="Data", y="Checklists_Com_NC", markers=True,
                           labels={"Checklists_Com_NC": "Checklists com NC", "Data": xaxis_title},
                           title="Tendência de Checklists com Não Conformidades")
        st.plotly_chart(fig_tend, use_container_width=True)

    # --- Aba 2: Manutenção ---
    with aba2:
        manut.columns = manut.columns.str.strip()
        if "PLACA" not in manut.columns or "MANUT. PROGRAMADA" not in manut.columns:
            st.warning("❌ Colunas 'PLACA' ou 'MANUT. PROGRAMADA' ausentes.")
        else:
            cruzado = pd.merge(df_veic_nc[["Placa do Caminhão", "Total_NC"]], manut,
                               how="left", left_on="Placa do Caminhão", right_on="PLACA")
            cruzado = cruzado.dropna(subset=["MANUT. PROGRAMADA"]).sort_values(by="Total_NC", ascending=False)
            cruzado["Índice de Severidade"] = (
                (cruzado["Total_NC"] / len(itens)).round(3).apply(severity_color)
            )
            st.markdown("### 🛠️ Manutenção Programada x NCs")
            st.write(cruzado[["PLACA", "MODELO", "MANUT. PROGRAMADA", "Total_NC", "Índice de Severidade"]]
                     .to_html(escape=False), unsafe_allow_html=True)

    # --- Aba 3: Itens Críticos ---
    with aba3:
        st.markdown("### 📌 Itens Críticos por Categoria")
        fig_cat = px.bar(df_cat_grouped,
                         x="NCs",
                         y="Categoria",
                         orientation="h",
                         color="NCs",
                         color_continuous_scale=["green", "yellow", "red"],
                         labels={"NCs": "Não Conformidades", "Categoria": "Categoria"})
        st.plotly_chart(fig_cat, use_container_width=True)
        st.dataframe(df_cat.sort_values("NCs", ascending=False).reset_index(drop=True))

    # --- Aba 4: Observações ---
    with aba4:
        st.markdown("### 📝 Observações dos Motoristas")
        obs = df[["Data", "Motorista", "Placa do Caminhão", col_obs, col_status]].dropna(subset=[col_obs])
        if not obs.empty:
            st.dataframe(obs)
        else:
            st.info("Nenhuma observação registrada.")

    # --- Aba 5: Fotos ---
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
                    try:
                        st.image(link, use_column_width=True)
                    except Exception:
                        st.markdown(f"[🔗 Foto {i}]({link})")
                st.markdown("---")

if __name__ == "__main__":
    main()
