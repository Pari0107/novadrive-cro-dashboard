import streamlit as st
import pandas as pd

# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="NovaDrive CRO Dashboard",
    page_icon="🏭",
    layout="wide"
)

# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data
def load_data():

    supplier_network = pd.read_csv(
        "data/supplier_network.csv"
    )

    supplier_entities = pd.read_csv(
        "data/supplier_entities.csv"
    )

    event_alerts = pd.read_csv(
        "data/event_alerts.csv"
    )

    return supplier_network, supplier_entities, event_alerts


supplier_network, supplier_entities, event_alerts = load_data()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def count_tier(df, tier):
    if "Tier" in df.columns:
        return int((df["Tier"] == tier).sum())

    if "From Tier" in df.columns:
        return int((df["From Tier"] == tier).sum())

    return 0


def severity_count(df, severity):
    if "Severity" not in df.columns:
        return 0

    return int(
        df["Severity"]
        .astype(str)
        .str.upper()
        .eq(severity.upper())
        .sum()
    )


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("NovaDrive CRO")

st.sidebar.caption(
    "Supplier Network & Risk Intelligence"
)

page = st.sidebar.radio(
    "Navigation",
    [
        "Executive Overview",
        "Supplier Network",
        "Risk Assessment",
        "Events & Alerts",
        "Alternate Suppliers"
    ]
)

st.sidebar.divider()

st.sidebar.caption(
    "Current scope: Confirmed network + event-driven risk"
)


# ============================================================
# EXECUTIVE OVERVIEW
# ============================================================

if page == "Executive Overview":

    st.title("NovaDrive CRO Dashboard")

    st.caption(
        "Supplier network visibility, risk prioritisation and "
        "event-driven management alerts"
    )

    st.divider()

    # --------------------------------------------------------
    # KEY METRICS
    # --------------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Confirmed Suppliers",
        len(supplier_entities)
    )

    col2.metric(
        "Confirmed Relationships",
        len(supplier_network)
    )

    col3.metric(
        "Tier-1 Suppliers",
        count_tier(supplier_entities, "Tier 1")
    )

    col4.metric(
        "Management Alerts",
        len(event_alerts)
    )

    st.divider()

    # --------------------------------------------------------
    # NETWORK BREAKDOWN
    # --------------------------------------------------------

    st.subheader("Supplier Network")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Tier 1",
        count_tier(supplier_entities, "Tier 1")
    )

    col2.metric(
        "Tier 2",
        count_tier(supplier_entities, "Tier 2")
    )

    col3.metric(
        "Tier 3",
        count_tier(supplier_entities, "Tier 3")
    )

    st.divider()

    # --------------------------------------------------------
    # ALERT SUMMARY
    # --------------------------------------------------------

    st.subheader("Current Alert Summary")

    alert_cols = st.columns(3)

    alert_cols[0].metric(
        "Critical",
        severity_count(event_alerts, "CRITICAL")
    )

    alert_cols[1].metric(
        "High",
        severity_count(event_alerts, "HIGH")
    )

    alert_cols[2].metric(
        "Medium",
        severity_count(event_alerts, "MEDIUM")
    )

    st.divider()

    st.info(
        "Use the navigation panel to investigate supplier "
        "relationships, risk context and event-driven alerts."
    )


# ============================================================
# SUPPLIER NETWORK
# ============================================================

elif page == "Supplier Network":

    st.title("Supplier Network")

    st.caption(
        "Confirmed material supplier relationships reconstructed "
        "from relationship evidence"
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Confirmed Relationships",
        len(supplier_network)
    )

    if "From Tier" in supplier_network.columns:

        col2.metric(
            "Tier-1 Relationships",
            count_tier(supplier_network, "Tier 1")
        )

        col3.metric(
            "Upstream Relationships",
            int(
                supplier_network["From Tier"]
                .isin(["Tier 2", "Tier 3"])
                .sum()
            )
        )

    st.divider()

    # --------------------------------------------------------
    # FILTERS
    # --------------------------------------------------------

    st.subheader("Explore Network")

    col1, col2, col3 = st.columns(3)

    # Tier filter
    with col1:

        if "From Tier" in supplier_network.columns:

            tier_options = ["All"] + sorted(
                supplier_network["From Tier"]
                .dropna()
                .unique()
                .tolist()
            )

            selected_tier = st.selectbox(
                "Supplier Tier",
                tier_options
            )

        else:
            selected_tier = "All"

    # Supplier filter
    with col2:

        supplier_column = "From"

        supplier_options = ["All"] + sorted(
            supplier_network[supplier_column]
            .dropna()
            .unique()
            .tolist()
        )

        selected_supplier = st.selectbox(
            "Supplier",
            supplier_options
        )

    # Component filter
    with col3:

        if "NovaDrive Component" in supplier_network.columns:

            component_options = ["All"] + sorted(
                supplier_network["NovaDrive Component"]
                .dropna()
                .unique()
                .tolist()
            )

            selected_component = st.selectbox(
                "NovaDrive Component",
                component_options
            )

        else:
            selected_component = "All"

    # --------------------------------------------------------
    # APPLY FILTERS
    # --------------------------------------------------------

    filtered_network = supplier_network.copy()

    if (
        selected_tier != "All"
        and "From Tier" in filtered_network.columns
    ):
        filtered_network = filtered_network[
            filtered_network["From Tier"] == selected_tier
        ]

    if selected_supplier != "All":

        filtered_network = filtered_network[
            filtered_network["From"] == selected_supplier
        ]

    if (
        selected_component != "All"
        and "NovaDrive Component" in filtered_network.columns
    ):

        filtered_network = filtered_network[
            filtered_network["NovaDrive Component"]
            == selected_component
        ]

    st.write(
        f"Showing **{len(filtered_network)}** confirmed relationships"
    )

    # --------------------------------------------------------
    # NETWORK TABLE
    # --------------------------------------------------------

    st.dataframe(
        filtered_network,
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------
    # SUPPLIER DETAIL
    # --------------------------------------------------------

    if selected_supplier != "All":

        st.divider()

        st.subheader(
            f"Supplier Detail — {selected_supplier}"
        )

        supplier_links = supplier_network[
            supplier_network["From"] == selected_supplier
        ]

        col1, col2 = st.columns(2)

        col1.metric(
            "Confirmed Relationships",
            len(supplier_links)
        )

        if "From Tier" in supplier_links.columns:

            tier_values = (
                supplier_links["From Tier"]
                .dropna()
                .unique()
            )

            col2.metric(
                "Tier",
                tier_values[0]
                if len(tier_values) > 0
                else "—"
            )

        st.markdown(
            "**Evidence-backed relationship details**"
        )

        detail_columns = [
            "Evidence ID",
            "From",
            "To",
            "Evidence Role",
            "NovaDrive Component",
            "Program",
            "Supplied Input",
            "Facility",
            "From Tier"
        ]

        available_columns = [
            column
            for column in detail_columns
            if column in supplier_links.columns
        ]

        st.dataframe(
            supplier_links[available_columns],
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# RISK ASSESSMENT
# ============================================================

elif page == "Risk Assessment":

    st.title("Risk Assessment")

    st.caption(
        "Supplier prioritisation and risk context"
    )

    st.info(
        "The current dashboard dataset contains the confirmed "
        "supplier network, supplier tiers and event-driven alerts. "
        "The detailed Part 2 risk-scorecard dataset can be connected "
        "here when its final export is added."
    )

    st.divider()

    st.subheader("Supplier Universe")

    # Tier summary

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Tier 1",
        count_tier(supplier_entities, "Tier 1")
    )

    col2.metric(
        "Tier 2",
        count_tier(supplier_entities, "Tier 2")
    )

    col3.metric(
        "Tier 3",
        count_tier(supplier_entities, "Tier 3")
    )

    st.divider()

    st.dataframe(
        supplier_entities,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# EVENTS & ALERTS
# ============================================================

elif page == "Events & Alerts":

    st.title("Events & Alerts")

    st.caption(
        "External risk signals matched to the confirmed "
        "NovaDrive supplier network"
    )

    # --------------------------------------------------------
    # ALERT METRICS
    # --------------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total Alerts",
        len(event_alerts)
    )

    col2.metric(
        "Critical",
        severity_count(event_alerts, "CRITICAL")
    )

    col3.metric(
        "High",
        severity_count(event_alerts, "HIGH")
    )

    col4.metric(
        "Medium",
        severity_count(event_alerts, "MEDIUM")
    )

    st.divider()

    # --------------------------------------------------------
    # SEVERITY FILTER
    # --------------------------------------------------------

    if "Severity" in event_alerts.columns:

        severity_options = [
            "All",
            "CRITICAL",
            "HIGH",
            "MEDIUM",
            "LOW"
        ]

        selected_severity = st.selectbox(
            "Filter by Severity",
            severity_options
        )

        filtered_alerts = event_alerts.copy()

        if selected_severity != "All":

            filtered_alerts = filtered_alerts[
                filtered_alerts["Severity"]
                .astype(str)
                .str.upper()
                == selected_severity
            ]

    else:

        filtered_alerts = event_alerts.copy()

    st.write(
        f"Showing **{len(filtered_alerts)}** alerts"
    )

    # --------------------------------------------------------
    # ALERT TABLE
    # --------------------------------------------------------

    st.dataframe(
        filtered_alerts,
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------
    # ALERT DETAIL
    # --------------------------------------------------------

    if len(filtered_alerts) > 0:

        st.divider()

        st.subheader("Inspect Alert")

        # Pick alert using Event ID if available
        if "Event ID" in filtered_alerts.columns:

            event_options = (
                filtered_alerts["Event ID"]
                .dropna()
                .astype(str)
                .tolist()
            )

            selected_event = st.selectbox(
                "Select Event",
                event_options
            )

            selected_row = filtered_alerts[
                filtered_alerts["Event ID"]
                .astype(str)
                == selected_event
            ].iloc[0]

            # Display important fields individually
            priority_fields = [
                "Event ID",
                "Title",
                "Affected Supplier",
                "Severity",
                "Risk Level",
                "Evidence Confidence",
                "Geography",
                "Facility",
                "Why It Matters",
                "Network Context",
                "Next Action"
            ]

            for field in priority_fields:

                if field in selected_row.index:

                    value = selected_row[field]

                    if pd.notna(value):

                        st.markdown(
                            f"**{field}:** {value}"
                        )


# ============================================================
# ALTERNATE SUPPLIERS
# ============================================================

elif page == "Alternate Suppliers":

    st.title("Alternate Suppliers")

    st.caption(
        "Alternate supplier discovery and fitment assessment"
    )

    st.info(
        "Part 4 alternate-supplier analysis will be connected "
        "here once the teammate's final dataset is available."
    )

    st.divider()

    st.markdown(
        """
        **Planned functionality**

        - Search alternatives for an affected component
        - Show technical/application relevance
        - Show manufacturing footprint and industry presence
        - Display public evidence and source/date
        - Separate supplier fitment from supplier risk
        - Identify qualification or engineering validation required
        """
    )
