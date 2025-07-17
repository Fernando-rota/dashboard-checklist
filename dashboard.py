import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Checklist Veicular", layout="wide")

def carregar_dados():
    checklist_file = st.sidebar.file_uploader("📄 Upload Planilha de Checklist", type=["xlsx"])
    manut_file = st.sidebar.file_uploader("🛠 Upload MANU.PREVENT", type=["xlsx"])
    
    if not checklist_file or not manut_file:
        st.warning("⚠️ Faça o upload das duas planilhas.")
        st.stop()

    df_checklist = pd.read_excel(checklist_file)
    df_manut = pd.read_excel(manut_file)

    df_checklist["Carimbo de data/hora"] = pd.to_datetime(df_checklist["Carimbo de data/hora"])
    df_checklist["Data"] = pd.to_datetime(df_checklist["Data"], errors="coerce")
    return df_checklist, df_manut

def filtros_sidebar(df, col_status):
    st.sidebar.markdown("### 📅 Filtros")

    # Datas
    min_date, max_date = df["Carimbo de data/hora"].min(), df["Carimbo de data/hora"].max()
    start_date = st.sidebar.date_input("Data inicial", min_date.date())
    end_date = st.sidebar.date_input("Data final", max_date.date())
    if start_date > end_date:
        st.sidebar.error("Data inicial maior que final.")
        st.stop()

    with st.sidebar.expander("🔎 Filtrar Motorista"):
        motoristas = sorted(df["Motorista"].dropna().unique())
        selecionar_todos_motorista = st.checkbox("Selecionar Todos Motoristas", value=True, key="todos_motorista")
        if selecionar_todos_motorista:
            sel_motorista = motoristas
        else:
            sel_motorista = st.multiselect("Motoristas", motoristas, default=motoristas)

    with st.sidebar.expander("🔎 Filtrar Placa"):
        placas = sorted(df["Placa do Caminhão"].dropna().unique())
        selecionar_todos_placa = st.checkbox("Selecionar Todas as Placas", value=True, key="todos_placa")
        if selecionar_todos_placa:
            sel_placa = placas
        else:
            sel_placa = st.multiselect("Placas", placas, default=placas)

    with st.sidebar.expander("🔎 Filtrar Status NC"):
        status_opcoes = ["Aberto", "Em andamento", "Concluído"]
        selecionar_todos_status = st.checkbox("Selecionar Todos os Status", value=True, key="todos_status")
        if selecionar_todos_status:
            sel_status = status_opcoes
        else:
            sel_status = st.multiselect("Status da NC", status_opcoes, default=status_opcoes)

    df_filtrado = df[
        (df["Carimbo de data/hora"] >= pd.Timestamp(start_date)) &
        (df["Carimbo de data/hora"] <= pd.Timestamp(end_date) + pd.Timedelta(days=1)) &
        (df["Motorista"].isin(sel_motorista)) &
        (df["Placa do Caminhão"].isin(sel_placa)) &
        (df[col_status].str.capitalize().isin(sel_status))
    ]
    return df_filtrado

def resumo_geral(df, col_status, itens):
    st.subheader("📊 Resumo Geral")
    total = len(df)
    abertas = (df[col_status].str.lower() == "aberto").sum()
    concluidas = (df[col_status].str.lower() == "concluído").sum()
    andamento = (df[col_status].str.lower() == "em andamento").sum()

    st.metric("Checklists Analisados", total)
    st.metric("Não Conformidades Abertas", abertas)
    st.metric("Concluídas", concluidas)
    st.metric("Em Andamento", andamento)

    st.markdown("---")

    nc_por_item = {
        item: (df[item].astype(str).str.lower() == "não conforme").sum()
        for item in itens
    }

    nc_df = pd.DataFrame(list(nc_por_item.items()), columns=["Item", "Total NC"]).sort_values("Total NC", ascending=False)
    st.dataframe(nc_df, use_container_width=True)

def fotos_nc(df, col_fotos, itens):
    st.subheader("📸 Fotos das Não Conformidades")
    fotos_df = df[df[col_fotos].notna()]

    if fotos_df.empty:
        st.info("Nenhuma foto encontrada.")
        return

    for _, row in fotos_df.iterrows():
        nc_itens = [col for col in itens if str(row[col]).lower().strip() == "não conforme"]
        links = extract_drive_links(row[col_fotos])

        st.markdown(f"**🧑 Motorista:** {row['Motorista']} &nbsp;&nbsp; **🚛 Placa:** {row['Placa do Caminhão']}  \n📅 {row['Data'].strftime('%d/%m/%Y')}")
        st.markdown(f"**🛠 Itens com NC:** {', '.join(nc_itens)}")

        for link in links:
            st.image(link, width=300)

        st.markdown("---")

def extract_drive_links(cell):
    if isinstance(cell, str):
        return [l.strip() for l in cell.split(",") if "http" in l]
    return []

def indicadores_manutencao(df, df_manut):
    st.subheader("🔧 Indicadores MANU.PREVENT")
    df_manut = df_manut.rename(columns=lambda c: c.strip().upper())
    placas_nc = df["Placa do Caminhão"].unique()
    df_indicadores = df_manut[df_manut["PLACA"].isin(placas_nc)]

    st.dataframe(df_indicadores[["PLACA", "MODELO", "MANUT. PROGRAMADA"]], use_container_width=True)

def main():
    st.title("🚛 Dashboard Checklist Veicular")

    df, df_manut = carregar_dados()

    col_status = "Status NC"
    col_fotos = "Anexe as fotos das não conformidades:"
    itens = [col for col in df.columns if ":" in col and col != col_fotos]

    df[col_status] = df[col_status].fillna("").str.lower().str.strip()

    df = filtros_sidebar(df, col_status)

    aba = st.tabs(["📊 Resumo Geral", "📷 Fotos NC", "🛠 Indicadores MANU.PREVENT"])

    with aba[0]:
        resumo_geral(df, col_status, itens)
    with aba[1]:
        fotos_nc(df, col_fotos, itens)
    with aba[2]:
        indicadores_manutencao(df, df_manut)

if __name__ == "__main__":
    main()
