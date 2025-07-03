import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard Checklist Veicular", layout="wide")
st.title("Dashboard Checklist Veicular — Filtros por Botões")

# Upload dos arquivos
uploaded_file_checklist = st.file_uploader("Selecione o arquivo Excel do checklist:", type="xlsx")
uploaded_file_manut = st.file_uploader("Selecione o arquivo Excel MANU. PREVENT:", type="xlsx")

if uploaded_file_checklist is not None and uploaded_file_manut is not None:
    df = pd.read_excel(uploaded_file_checklist)
    df.columns = df.columns.str.strip()
    manut = pd.read_excel(uploaded_file_manut)
    manut.columns = manut.columns.str.strip()

    # Filtros por botão
    col1, col2 = st.columns(2)
    with col1:
        motoristas = sorted(df["Motorista"].dropna().unique())
        motorista_sel = st.radio("Filtrar por Motorista", options=["Todos"] + motoristas, horizontal=True)
    with col2:
        placas = sorted(df["Placa do Caminhão"].dropna().unique())
        placa_sel = st.radio("Filtrar por Placa", options=["Todas"] + placas, horizontal=True)

    if motorista_sel != "Todos":
        df = df[df["Motorista"] == motorista_sel]
    if placa_sel != "Todas":
        df = df[df["Placa do Caminhão"] == placa_sel]

    st.markdown("---")

    # KPIs
    cols_itens = [col for col in df.columns if col not in [
        "Carimbo de data/hora", "Pontuação", "Data", "Motorista",
        "Placa do Caminhão", "Km atual", "Anexe as fotos das não conformidades"
    ]]
    df_reinc = df.copy()
    df_reinc[cols_itens] = df_reinc[cols_itens].astype(str)
    df_reinc["Reincidencias"] = df_reinc[cols_itens].apply(lambda row: sum(v.strip().lower() != "ok" for v in row), axis=1)

    reincidencias_por_placa = df_reinc.groupby("Placa do Caminhão")["Reincidencias"].sum().reset_index()
    reincidencias_por_placa = reincidencias_por_placa.sort_values(by="Reincidencias", ascending=False)

    total_nc = df_reinc["Reincidencias"].sum()
    veiculo_top = reincidencias_por_placa.iloc[0]["Placa do Caminhão"]
    nc_top = reincidencias_por_placa.iloc[0]["Reincidencias"]
    motorista_freq = df["Motorista"].value_counts().idxmax()

    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Total de Não Conformidades", total_nc)
    kpi2.metric("Veículo com Mais Reincidências", veiculo_top, f"{nc_top} ocorrências")
    kpi3.metric("Motorista com Mais Registros", motorista_freq)

    st.markdown("---")

    # Reincidências por Veículo
    st.subheader("Reincidências por Veículo")
    fig_reinc = px.bar(
        reincidencias_por_placa,
        x="Placa do Caminhão",
        y="Reincidencias",
        title="Quantidade de Não Conformidades por Veículo",
        color="Reincidencias",
        color_continuous_scale="Reds"
    )
    st.plotly_chart(fig_reinc, use_container_width=True)

    # Indicador cruzado aprimorado
    st.subheader("Indicador Cruzado: Manutenção Programada x Reincidências")
    cruzado = pd.merge(reincidencias_por_placa, manut, how="left", left_on="Placa do Caminhão", right_on="PLACA")
    cruzado = cruzado.dropna(subset=["MANUT. PROGRAMADA"])
    fig_cruzado = px.scatter(
        cruzado,
        x="Reincidencias",
        y="MANUT. PROGRAMADA",
        size="Reincidencias",
        color="MODELO",
        hover_data=["PLACA", "MANUT. PROGRAMADA"],
        title="Relação entre Manutenção Programada e Reincidências",
        labels={"MANUT. PROGRAMADA": "Próxima Manutenção"}
    )
    st.plotly_chart(fig_cruzado, use_container_width=True)

    # Não Conformidades por Item (ordenado e sem fotos)
    st.subheader("Não Conformidades por Item")
    item_labels = {f"{i+1:02d}": col for i, col in enumerate(cols_itens)}
    df_nci = pd.DataFrame({
        "Item": list(item_labels.keys()),
        "Descrição": list(item_labels.values()),
        "Não Conformidades": [
            df[col].astype(str).str.strip().str.lower().ne("ok").sum() for col in cols_itens
        ]
    })
    df_nci = df_nci.sort_values(by="Não Conformidades", ascending=False)

    fig_nci = px.bar(
        df_nci,
        x="Item",
        y="Não Conformidades",
        hover_data=["Descrição"],
        title="Quantidade de Não Conformidades por Item (Código)",
        color="Não Conformidades",
        color_continuous_scale="Reds"
    )
    st.plotly_chart(fig_nci, use_container_width=True)

    with st.expander("Ver gabarito de Itens", expanded=False):
        st.dataframe(df_nci.set_index("Item"))

    # Fotos relacionadas com o item não conforme
    if "Anexe as fotos das não conformidades" in df.columns:
        st.subheader("Fotos das Não Conformidades")
        fotos = df[["Placa do Caminhão", "Motorista", "Anexe as fotos das não conformidades"] + cols_itens].dropna(subset=["Anexe as fotos das não conformidades"])
        for _, row in fotos.iterrows():
            problemas = [col for col in cols_itens if str(row[col]).strip().lower() != "ok"]
            if problemas:
                st.markdown(f"**{row['Placa do Caminhão']} - {row['Motorista']}** - Problemas: {', '.join(problemas)}")
                st.image(row["Anexe as fotos das não conformidades"], use_column_width=True)
else:
    st.info("Por favor, envie os dois arquivos .xlsx para visualizar o dashboard.")
