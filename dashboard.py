# ... código anterior permanece igual até a parte das abas ...

with aba4:
    # Não Conformidades só dos itens do checklist, sem fotos nem observações
    df_nci = pd.DataFrame({
        "Item": cols_itens,
        "Não Conformidades": [
            df[col].astype(str).str.strip().str.lower().ne("ok").sum() for col in cols_itens
        ]
    })
    df_nci = df_nci[df_nci["Não Conformidades"] > 0]
    df_nci = df_nci.sort_values(by="Não Conformidades", ascending=False)
    df_nci["% do Total"] = ((df_nci["Não Conformidades"] / df_nci["Não Conformidades"].sum()) * 100).round(1)

    fig_nci = px.bar(
        df_nci,
        y="Item",
        x="Não Conformidades",
        title="Não Conformidades por Item",
        color="Não Conformidades",
        color_continuous_scale=["green", "yellow", "red"],
        orientation="h"
    )
    st.plotly_chart(fig_nci, use_container_width=True)
    st.dataframe(df_nci.reset_index(drop=True))

with aba5:
    # Observações (apenas elas)
    if "Observações" in df.columns:
        obs = df[["Data", "Motorista", "Placa do Caminhão", "Observações"]].dropna(subset=["Observações"])
        if not obs.empty:
            st.subheader("Observações")
            st.dataframe(obs)

    # Fotos (apenas elas)
    if "Anexe as fotos das não conformidades" in df.columns:
        fotos = df[["Data", "Motorista", "Placa do Caminhão", "Anexe as fotos das não conformidades"]].dropna(subset=["Anexe as fotos das não conformidades"])
        if not fotos.empty:
            st.subheader("Fotos das Não Conformidades")
            for _, row in fotos.iterrows():
                st.markdown(f"**{row['Data']} - {row['Placa do Caminhão']} - {row['Motorista']}**")
                direct_link = get_drive_direct_link(row['Anexe as fotos das não conformidades'])
                try:
                    st.image(direct_link, width=400)
                except:
                    st.markdown(f"[Ver foto]({direct_link})")
