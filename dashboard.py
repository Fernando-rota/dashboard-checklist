import streamlit as st
import pandas as pd

st.set_page_config(page_title="Dashboard Checklist", layout="wide")

def carregar_dados():
    st.sidebar.title("📁 Upload dos Arquivos Excel")
    checklist_file = st.sidebar.file_uploader("Checklist Diário (.xlsx)", type=["xlsx"], key="checklist")
    prevent_file = st.sidebar.file_uploader("Manutenção Preventiva (.xlsx)", type=["xlsx"], key="prevent")

    if checklist_file is None or prevent_file is None:
        st.warning("Por favor, envie os dois arquivos para continuar.")
        st.stop()

    df = pd.read_excel(checklist_file)
    df_prevent = pd.read_excel(prevent_file)

    return df, df_prevent

def aplicar_filtros(df):
    st.sidebar.title("🔍 Filtros")

    df["Data"] = pd.to_datetime(df["Data"])
    datas = df["Data"].dt.date.sort_values().unique()
    data_sel = st.sidebar.multiselect("📅 Data", options=datas, default=datas)
    df = df[df["Data"].dt.date.isin(data_sel)]

    motoristas = sorted(df["Motorista"].dropna().unique())
    todos_motoristas = st.sidebar.checkbox("Todos os motoristas", value=True)
    motoristas_sel = motoristas if todos_motoristas else st.sidebar.multiselect("👤 Motorista", motoristas, default=motoristas)
    df = df[df["Motorista"].isin(motoristas_sel)]

    placas = sorted(df["Placa do Caminhão"].dropna().unique())
    todas_placas = st.sidebar.checkbox("Todas as placas", value=True)
    placas_sel = placas if todas_placas else st.sidebar.multiselect("🚛 Placa", placas, default=placas)
    df = df[df["Placa do Caminhão"].isin(placas_sel)]

    status_nc = sorted(df["Status NC"].dropna().unique())
    todos_status = st.sidebar.checkbox("Todos os status", value=True)
    status_sel = status_nc if todos_status else st.sidebar.multiselect("📌 Status NC", status_nc, default=status_nc)
    df = df[df["Status NC"].isin(status_sel)]

    return df

def gerar_kpis(df, df_prevent):
    total_registros = len(df)
    total_nc = df["Status NC"].str.lower().eq("não conforme").sum()
    percentual_nc = round((total_nc / total_registros) * 100, 1) if total_registros else 0

    placas_criticas = df[df["Status NC"].str.lower() == "não conforme"]["Placa do Caminhão"].value_counts()
    top_placas_nc = placas_criticas.head(3).to_dict()

    placas_manut = df_prevent["PLACA"].dropna().unique()
    em_manutencao = df[df["Placa do Caminhão"].isin(placas_manut)]["Placa do Caminhão"].nunique()

    return total_registros, total_nc, percentual_nc, top_placas_nc, em_manutencao

def exibir_kpis(total, nc, percentual, top_placas, manut):
    st.subheader("📊 Indicadores Gerais")
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total de Registros", total)
    col2.metric("Total com NC", nc)
    col3.metric("% NC", f"{percentual}%")
    col4.metric("Veículos com Preventiva", manut)

    st.markdown("#### 🚨 Top 3 Veículos com Mais NCs")
    for placa, count in top_placas.items():
        st.write(f"- {placa}: {count} NC(s)")

def main():
    st.title("✅ Dashboard de Checklist Veicular")

    df, df_prevent = carregar_dados()
    df = aplicar_filtros(df)

    aba1, aba2, aba3 = st.tabs(["📊 Visão Geral", "🛠️ Detalhamento", "🖼️ Fotos de NCs"])

    with aba1:
        total, nc, percentual, top_placas, manut = gerar_kpis(df, df_prevent)
        exibir_kpis(total, nc, percentual, top_placas, manut)

        # Gráfico de tendência pode ser adicionado aqui se quiser

    with aba2:
        st.markdown("### 📋 Tabela de Registros Filtrados")
        st.dataframe(df, use_container_width=True)

    with aba3:
        st.markdown("### 📸 Anexos de Não Conformidades")
        if "Anexe as fotos das não conformidades:" in df.columns:
            fotos = df[["Data", "Motorista", "Placa do Caminhão", "Anexe as fotos das não conformidades:"]]
            fotos = fotos.dropna(subset=["Anexe as fotos das não conformidades:"])
            for _, row in fotos.iterrows():
                st.markdown(f"**{row['Data'].date()} | {row['Motorista']} | {row['Placa do Caminhão']}**")
                st.image(row["Anexe as fotos das não conformidades:"], width=400)
        else:
            st.info("Coluna de fotos não encontrada.")

if __name__ == "__main__":
    main()
