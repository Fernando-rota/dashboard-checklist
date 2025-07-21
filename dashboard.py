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
    urls = re.split(r'[,\s]+', str(urls_string).strip())
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
    if status in ["aberto", "em andamento"] or nc_total > 5:
        return "🚫 Crítico"
    elif 2 <= nc_total <= 5:
        return "⚠️ Atenção"
    else:
        return "✅ OK"

CATEGORIAS = {
    "Drenar a água acumulada": "Combustível e Filtros",
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
    for chave, cat in CATEGORIAS.items():
        if chave.lower() in item.lower():
            return cat
    return "Outros"

def main():
    st.title("🚛 Dashboard Checklist Veicular")

    col1, col2 = st.columns(2)
    with col1:
        checklist_file = st.file_uploader("📁 Checklist Excel", type="xlsx", label_visibility="collapsed")
    with col2:
        manut_file = st.file_uploader("📁 MANU.PREVENT Excel", type="xlsx", label_visibility="collapsed")

    if not checklist_file or not manut_file:
        st.info("📌 Envie os dois arquivos para continuar.")
        return

    with st.spinner("🔄 Carregando dados..."):
        df = load_excel(checklist_file)
        manut = load_excel(manut_file)

    col_fotos = "Anexe as fotos das não conformidades:"
    col_obs = "Observações:"
    col_status = "Status NC"
    obrigatorias = ["Carimbo de data/hora", "Motorista", "Placa do Caminhão", "Pontuação", col_fotos, col_obs, col_status]

    if any(col not in df.columns for col in obrigatorias):
        st.error(f"❌ Colunas obrigatórias ausentes: {[c for c in obrigatorias if c not in df.columns]}")
        return

    df["Carimbo de data/hora"] = pd.to_datetime(df["Carimbo de data/hora"], errors="coerce")
    if df["Carimbo de data/hora"].isna().all():
        st.error("❌ Nenhuma data válida encontrada.")
        return

    df["Data"] = df["Carimbo de data/hora"].dt.strftime("%d/%m/%Y")
    df[col_status] = df[col_status].fillna("").str.lower().str.strip()

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

    todos_motoristas = st.sidebar.checkbox("Selecionar todos os motoristas", value=True)
    if todos_motoristas:
        sel_motorista = motoristas
    else:
        sel_motorista = st.sidebar.multiselect("Motoristas", motoristas)

    todas_placas = st.sidebar.checkbox("Selecionar todas as placas", value=True)
    if todas_placas:
        sel_placa = placas
    else:
        sel_placa = st.sidebar.multiselect("Placas", placas)

    df = df[df["Motorista"].isin(sel_motorista)]
    df = df[df["Placa do Caminhão"].isin(sel_placa)]

    status_opcoes = ["Todos", "Aberto / Em andamento", "Concluído"]
    status_sel = st.sidebar.selectbox("Status da NC", status_opcoes)

    if status_sel == "Aberto / Em andamento":
        df = df[df[col_status].isin(["aberto", "em andamento"])]
    elif status_sel == "Concluído":
        df = df[df[col_status] == "concluído"]

    cols_excluir = obrigatorias + ["Data", "Km atual"]
    itens = [col for col in df.columns if col not in cols_excluir]

    df_itens = df[itens].fillna("").astype(str).applymap(lambda x: x.strip().lower())
    df["Reincidencias"] = df_itens.apply(lambda row: sum(v != "ok" and v != "" for v in row), axis=1)

    df_veic_nc = df.groupby("Placa do Caminhão").agg(
        Total_NC=pd.NamedAgg(column="Reincidencias", aggfunc="sum"),
        Status_Aberto=pd.NamedAgg(column=col_status, aggfunc=lambda s: any(x in ["aberto", "em andamento"] for x in s))
    ).reset_index()
    df_veic_nc["Classificação"] = df_veic_nc.apply(lambda row: classificar_veiculo(row["Total_NC"], "aberto" if row["Status_Aberto"] else "concluído"), axis=1)

    categorias = [mapear_categoria(item) for item in itens]

    df_cat = pd.DataFrame({
        "Item": itens,
        "Categoria": categorias,
        "NCs": [df_itens[col].ne("ok").sum() for col in itens]
    })
    df_cat = df_cat[df_cat["NCs"] > 0]
    df_cat_grouped = df_cat.groupby("Categoria").sum().reset_index().sort_values("NCs", ascending=False)

    aba1, aba2, aba3, aba4, aba5 = st.tabs([
        "📊 Visão Geral", "🛠️ Manutenção", "📌 Itens Críticos", "📝 Observações", "📸 Fotos"
    ])

    with aba5:
        st.markdown("### 📸 Galeria de Fotos de Não Conformidades")
        fotos_df = df.dropna(subset=[col_fotos])
        fotos_df = fotos_df[["Data", "Motorista", "Placa do Caminhão", col_status, col_fotos] + itens]

        if fotos_df.empty:
            st.info("Nenhuma foto registrada.")
        else:
            for _, row in fotos_df.iterrows():
                links = extract_drive_links(row[col_fotos])
                nc_itens = [col for col in itens if row[col].strip().lower() != "ok"]

                st.markdown(f"""
📅 **{row['Data']}**  
👨‍✈️ **Motorista:** {row['Motorista']}  
🚚 **Placa:** {row['Placa do Caminhão']}  
📍 **Status:** {row[col_status]}  
🔧 **Itens NC:** {', '.join(nc_itens)}
""")
                for link in links:
                    st.markdown(f"[🔗 Link da Foto]({link})")
                st.markdown("---")

if __name__ == "__main__":
    main()
