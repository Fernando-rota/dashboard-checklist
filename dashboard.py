import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard Checklist Veicular", layout="wide")
st.title("Dashboard Checklist Veicular")

# Upload dos arquivos na sidebar
uploaded_file_checklist = st.sidebar.file_uploader("Selecione o arquivo Excel do checklist:", type="xlsx")
uploaded_file_manut = st.sidebar.file_uploader("Selecione o arquivo Excel MANU. PREVENT:", type="xlsx")

if uploaded_file_checklist and uploaded_file_manut:
    df = pd.read_excel(uploaded_file_checklist)
    df.columns = df.columns.str.strip()
    manut = pd.read_excel(uploaded_file_manut)
    manut.columns = manut.columns.str.strip()

    # Filtros na sidebar
    motoristas = sorted(df["Motorista"].dropna().unique())
    motorista_sel = st.sidebar.radio("Filtrar por Motorista", options=["Todos"] + motoristas)

    placas = sorted(df["Placa do Caminhão"].dropna().unique())
    placa_sel = st.sidebar.radio("Filtrar por Placa", options=["Todas"] + placas)

    # Aplicar filtros
    if motorista_sel != "Todos":
        df = df[df["Motorista"] == motorista_sel]
    if placa_sel != "Todas":
        df = df[df["Placa do Caminhão"] == placa_sel]

    cols_itens = [col for col in df.columns if col not in [
        "Carimbo de data/hora", "Pontuação", "Data", "Motorista",
        "Placa do Caminhão", "Km atual", "Anexe as fotos das não conformidades"
    ]]
    df_reinc = df.copy()
    df_reinc["Reincidencias"] = df_reinc[cols_itens].apply(
        lambda row: sum(str(v).strip().lower() != "ok" for v in row), axis=1
    )
    reincidencias_por_placa = df_reinc.groupby("Placa do Caminhão")["Reincidencias"].sum().reset_index()
    reincidencias_por_placa = reincidencias_por_placa.sort_values(by="Reincidencias", ascending=False)

    cruzado = pd.merge(
        reincidencias_por_placa,
        manut,
        how="left",
        left_on="Placa do Caminhão",
        right_on="PLACA",
    )
    cruzado.rename(columns=lambda x: x.strip(), inplace=True)
    cruzado = cruzado.sort_values(by="Reincidencias", ascending=False)

    df_nci = pd.DataFrame(
        {
            "Item": [f"{i+1:02d}" for i in range(len(cols_itens))],
            "Descrição": cols_itens,
            "Não Conformidades": [
                df[col].astype(str).str.strip().str.lower().ne("ok").sum() for col in cols_itens
            ],
        }
    )
    df_nci = df_nci.sort_values(by="Não Conformidades", ascending=False)

    # Criar abas
    tab1, tab2, tab3 = st.tabs(["Reincidências por Veículo", "Manutenção x Reincidências", "Não Conformidades por Item"])

    with tab1:
        fig_reinc = px.bar(
            reincidencias_por_placa,
            x="Placa do Caminhão",
            y="Reincidencias",
            title="Quantidade de Não Conformidades por Veículo",
            color="Reincidencias",
        )
        st.plotly_chart(fig_reinc, use_container_width=True)

    with tab2:
        fig_cruzado = px.scatter(
            cruzado,
            x="Reincidencias",
            y="MANUT. PROGRAMADA",
            color="MODELO",
            hover_data=["PLACA"],
            title="Reincidências vs. Manutenção Programada",
        )
        st.plotly_chart(fig_cruzado, use_container_width=True)

    with tab3:
        fig_nci = px.bar(
            df_nci,
            x="Item",
            y="Não Conformidades",
            hover_data=["Descrição"],
            title="Quantidade de Não Conformidades por Item (Código)",
        )
        st.plotly_chart(fig_nci, use_container_width=True)
        with st.expander("Ver gabarito de Itens", expanded=False):
            st.dataframe(df_nci.set_index("Item"))

else:
    st.info("Por favor, envie os dois arquivos .xlsx para visualizar o dashboard.")
