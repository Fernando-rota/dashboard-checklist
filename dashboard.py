import streamlit as st
import pandas as pd

def filtros_sidebar(df):
    st.sidebar.markdown("## 🔎 Filtros do Dashboard")

    # Padroniza nomes das colunas
    df.columns = df.columns.str.strip().str.lower()

    df["carimbo de data/hora"] = pd.to_datetime(df["carimbo de data/hora"])

    with st.sidebar.expander("🎛️ Filtros", expanded=True):
        # Botão de reset
        if st.button("🔁 Limpar filtros"):
            st.session_state.clear()
            st.experimental_rerun()

        # Filtro de texto por motorista ou placa
        busca_texto = st.text_input("🔍 Buscar motorista ou placa")

        # Filtro por data
        data_min = df["carimbo de data/hora"].min().date()
        data_max = df["carimbo de data/hora"].max().date()

        start_date = st.date_input("📅 De", data_min, key="start_date")
        end_date = st.date_input("📅 Até", data_max, key="end_date")

        def multiselect_com_todos(label, options, key):
            selecionar_todos = st.checkbox(f"Selecionar todos os {label.lower()}", value=True, key=f"chk_{key}")
            if selecionar_todos:
                return options
            else:
                return st.multiselect(label, options, default=[], key=f"multi_{key}")

        # Motoristas
        motoristas = sorted(df["motorista"].dropna().unique())
        sel_motoristas = multiselect_com_todos("Motoristas", motoristas, "motorista")

        # Placas
        placas = sorted(df["placa do caminhão"].dropna().unique())
        sel_placas = multiselect_com_todos("Placas", placas, "placa")

        # Status NC
        status_nc = sorted(df["status nc"].dropna().unique())
        sel_status = multiselect_com_todos("Status NC", status_nc, "status")

        # Categoria (se houver)
        if "categoria" in df.columns:
            categorias = sorted(df["categoria"].dropna().unique())
            sel_categorias = multiselect_com_todos("Categorias", categorias, "categoria")
        else:
            sel_categorias = None

        # Nº mínimo de NCs
        if "nº nc" in df.columns:
            nc_min = st.slider("🔢 Nº mínimo de Não Conformidades", 0, 20, 0)
        else:
            nc_min = 0

    # Aplica os filtros
    df_filtrado = df[
        (df["carimbo de data/hora"].dt.date >= start_date) &
        (df["carimbo de data/hora"].dt.date <= end_date) &
        (df["motorista"].isin(sel_motoristas)) &
        (df["placa do caminhão"].isin(sel_placas)) &
        (df["status nc"].isin(sel_status))
    ]

    if sel_categorias is not None:
        df_filtrado = df_filtrado[df_filtrado["categoria"].isin(sel_categorias)]

    if "nº nc" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["nº nc"] >= nc_min]

    if busca_texto:
        busca_texto = busca_texto.lower()
        df_filtrado = df_filtrado[
            df_filtrado["motorista"].str.lower().str.contains(busca_texto, na=False) |
            df_filtrado["placa do caminhão"].str.lower().str.contains(busca_texto, na=False)
        ]

    return df_filtrado


# App principal com abas
def main():
    st.set_page_config(page_title="Checklist Veicular", layout="wide")
    st.title("🚛 Dashboard Checklist Veicular")

    uploaded_file = st.file_uploader("📤 Envie a planilha de checklist (.xlsx)", type=["xlsx"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)

        df_filtrado = filtros_sidebar(df)
        st.success(f"{len(df_filtrado)} registros encontrados.")

        # Abas com base nos dados filtrados
        aba1, aba2, aba3 = st.tabs(["📋 Tabela", "📊 Gráficos", "📸 Não Conformidades"])

        with aba1:
            st.markdown("### ✅ Dados Filtrados")
            st.dataframe(df_filtrado, use_container_width=True)

        with aba2:
            st.markdown("### 📈 Gráficos e Indicadores")
            # aqui você adiciona os gráficos desejados com base em df_filtrado

        with aba3:
            st.markdown("### 🚫 Não Conformidades com Fotos")
            # exiba imagens e observações dos registros com não conformidades

    else:
        st.info("Faça upload de um arquivo Excel (.xlsx) para começar.")


if __name__ == "__main__":
    main()
