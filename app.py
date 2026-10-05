            f"{results['Fitment Score'].max():.1f}"
        )

        col3.metric(
            "Component",
            (
                results["Component"].iloc[0]
                if "Component" in results.columns
                and str(results["Component"].iloc[0]) != "nan"
                else results["Component ID"].iloc[0]
            )
        )

        st.divider()

        # ----------------------------------------------------
        # CANDIDATE CARDS
        # ----------------------------------------------------

        for i, (_, row) in enumerate(
            results.iterrows(),
            start=1
        ):

            supplier_name = row[
                "Alternate Supplier"
            ]

            fit_score = row[
                "Fitment Score"
            ]

            with st.container():

                st.markdown(
                    f"### {i}. {supplier_name}"
                )

                col1, col2, col3, col4 = st.columns(4)

                col1.metric(
                    "Fitment",
                    f"{fit_score:.1f}/100"
                )

                col2.metric(
                    "Technical Fit",
                    f"{row['Technical Fit']:.1f}"
                )

                col3.metric(
                    "Application Fit",
                    f"{row['Application Fit']:.1f}"
                )

                col4.metric(
                    "Manufacturing",
                    f"{row['Manufacturing Footprint']:.1f}"
                )

                st.markdown(
                    f"**Industry / Scale:** "
                    f"{row['Industry / Scale']:.1f}"
                )

                st.markdown(
                    f"**Supplier Risk:** "
                    f"{row['Supplier Risk']}"
                )

                if pd.notna(
                    row.get(
                        "Supplier Risk Score",
                        None
                    )
                ):

                    st.markdown(
                        f"**Existing Risk Score:** "
                        f"{row['Supplier Risk Score']}"
                    )

                st.markdown(
                    "**Public Evidence:**"
                )

                st.write(
                    row["Evidence"]
                )

                st.markdown(
                    f"**Qualification Next Step:** "
                    f"{row['Qualification Next Step']}"
                )

                st.markdown(
                    f"[View source]({row['Source URL']})"
                )

                st.divider()

        # ----------------------------------------------------
        # FULL DATA TABLE
        # ----------------------------------------------------

        with st.expander(
            "View detailed sourcing assessment"
        ):

            st.dataframe(
                results,
                use_container_width=True,
                hide_index=True
            )

    elif (
        result_supplier
        == selected_alternate_supplier
        and
        results.empty
    ):

        st.warning(
            "No verified alternate suppliers were found "
            "for this supplier using the current public-source search."
        )
