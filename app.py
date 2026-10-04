import streamlit as st
import pandas as pd
import re
import math

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
# NETWORK PREPARATION
# ============================================================

def build_network():

    nodes = set()

    for _, row in supplier_network.iterrows():

        if pd.notna(row.get("From")):
            nodes.add(str(row["From"]))

        if pd.notna(row.get("To")):
            nodes.add(str(row["To"]))

    # NovaDrive should always appear
    nodes.add("NovaDrive Technologies")

    edges = []

    for _, row in supplier_network.iterrows():

        if pd.notna(row.get("From")) and pd.notna(row.get("To")):

            edges.append(
                (
                    str(row["From"]),
                    str(row["To"])
                )
            )

    return sorted(nodes), edges


network_nodes, network_edges = build_network()


# ============================================================
# NETWORK FUNCTIONS
# ============================================================

def build_adjacency():

    adjacency = {}

    for node in network_nodes:
        adjacency[node] = []

    for source, target in network_edges:

        if source not in adjacency:
            adjacency[source] = []

        adjacency[source].append(target)

    return adjacency


adjacency = build_adjacency()


def get_downstream_nodes(start_nodes):

    """
    Returns all confirmed downstream nodes affected by an issue
    at one or more supplier nodes.
    """

    affected = set()

    queue = list(start_nodes)

    while queue:

        current = queue.pop(0)

        if current in affected:
            continue

        affected.add(current)

        for downstream in adjacency.get(current, []):

            if downstream not in affected:
                queue.append(downstream)

    return affected


def get_tier(node):

    if node == "NovaDrive Technologies":
        return "NovaDrive"

    matches = supplier_entities[
        supplier_entities["Entity"].astype(str) == str(node)
    ]

    if len(matches) > 0 and "Tier" in matches.columns:
        return str(matches.iloc[0]["Tier"])

    # fallback from network
    matches = supplier_network[
        supplier_network["From"].astype(str) == str(node)
    ]

    if len(matches) > 0 and "From Tier" in matches.columns:
        return str(matches.iloc[0]["From Tier"])

    return "Unknown"


def get_supplier_facilities():

    facility_map = {}

    if "Facility" not in supplier_network.columns:
        return facility_map

    for _, row in supplier_network.iterrows():

        supplier = str(row.get("From", ""))

        facility = row.get("Facility")

        if pd.notna(facility):

            facility_map.setdefault(
                supplier,
                set()
            ).add(str(facility))

    return facility_map


supplier_facilities = get_supplier_facilities()


# ============================================================
# EVENT MATCHING
# ============================================================

def normalize_text(text):

    if pd.isna(text):
        return ""

    text = str(text).lower()

    text = re.sub(
        r"[^a-z0-9\s\-]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def match_new_event(event_text):

    """
    Match a new event to confirmed network entities.

    Matching is intentionally conservative:
    supplier names and confirmed facility IDs are used.
    """

    text = normalize_text(event_text)

    matches = []

    # --------------------------------------------------------
    # Supplier name matching
    # --------------------------------------------------------

    for supplier in network_nodes:

        if supplier == "NovaDrive Technologies":
            continue

        supplier_norm = normalize_text(supplier)

        # Full supplier name
        if supplier_norm in text:

            matches.append(
                {
                    "Supplier": supplier,
                    "Match Type": "Supplier name",
                    "Matched On": supplier
                }
            )

            continue

        # Legal-name shortened matching
        words = supplier_norm.split()

        if len(words) >= 2:

            meaningful_words = [
                word
                for word in words
                if len(word) >= 5
            ]

            if meaningful_words:

                matched_words = sum(
                    word in text
                    for word in meaningful_words
                )

                if matched_words >= max(
                    1,
                    math.ceil(len(meaningful_words) * 0.7)
                ):

                    matches.append(
                        {
                            "Supplier": supplier,
                            "Match Type": "Supplier name",
                            "Matched On": supplier
                        }
                    )

                    continue

    # --------------------------------------------------------
    # Facility matching
    # --------------------------------------------------------

    facility_pattern = r"SITE-\d+"

    facilities_in_text = re.findall(
        facility_pattern,
        event_text.upper()
    )

    for facility in facilities_in_text:

        for supplier, facilities in supplier_facilities.items():

            if facility in facilities:

                matches.append(
                    {
                        "Supplier": supplier,
                        "Match Type": "Facility",
                        "Matched On": facility
                    }
                )

    # Remove duplicates
    unique = {}

    for match in matches:

        key = (
            match["Supplier"],
            match["Match Type"]
        )

        unique[key] = match

    return list(unique.values())


# ============================================================
# GRAPH LAYOUT
# ============================================================

def create_positions():

    """
    Create a stable left-to-right layout:
    Tier 3 → Tier 2 → Tier 1 → NovaDrive
    """

    tiers = {
        "Tier 3": [],
        "Tier 2": [],
        "Tier 1": [],
        "NovaDrive": []
    }

    for node in network_nodes:

        tier = get_tier(node)

        if tier in tiers:
            tiers[tier].append(node)

    positions = {}

    x_values = {
        "Tier 3": 0,
        "Tier 2": 1,
        "Tier 1": 2,
        "NovaDrive": 3
    }

    for tier, nodes in tiers.items():

        nodes = sorted(nodes)

        n = len(nodes)

        for i, node in enumerate(nodes):

            if n == 1:
                y = 0

            else:
                y = (
                    i
                    - (n - 1) / 2
                )

            positions[node] = (
                x_values[tier],
                -y
            )

    # Any unresolved nodes
    unresolved = [
        node
        for node in network_nodes
        if node not in positions
    ]

    for i, node in enumerate(unresolved):

        positions[node] = (
            1.5,
            i
        )

    return positions


positions = create_positions()


# ============================================================
# INTERACTIVE NETWORK GRAPH
# ============================================================

def show_network_graph(
    highlighted_nodes=None,
    selected_event_nodes=None
):

    highlighted_nodes = set(
        highlighted_nodes or []
    )

    selected_event_nodes = set(
        selected_event_nodes or []
    )

    try:

        import plotly.graph_objects as go

        edge_x = []
        edge_y = []

        for source, target in network_edges:

            if source not in positions:
                continue

            if target not in positions:
                continue

            x0, y0 = positions[source]
            x1, y1 = positions[target]

            edge_x.extend(
                [x0, x1, None]
            )

            edge_y.extend(
                [y0, y1, None]
            )

        edge_trace = go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line=dict(
                width=1.5,
                color="#A0A0A0"
            ),
            hoverinfo="none"
        )

        node_x = []
        node_y = []
        node_text = []
        node_colors = []
        node_sizes = []

        for node in network_nodes:

            x, y = positions[node]

            node_x.append(x)
            node_y.append(y)

            tier = get_tier(node)

            node_text.append(
                f"<b>{node}</b><br>"
                f"Tier: {tier}"
            )

            # Event source
            if node in selected_event_nodes:

                node_colors.append(
                    "#F59E0B"
                )

                node_sizes.append(32)

            # Downstream affected nodes
            elif node in highlighted_nodes:

                node_colors.append(
                    "#DC2626"
                )

                node_sizes.append(28)

            # NovaDrive
            elif node == "NovaDrive Technologies":

                node_colors.append(
                    "#1F2937"
                )

                node_sizes.append(36)

            # Normal node
            else:

                node_colors.append(
                    "#CBD5E1"
                )

                node_sizes.append(22)

        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            text=[
                node.replace(
                    " Ltd.",
                    ""
                ).replace(
                    " Technologies",
                    ""
                )
                for node in network_nodes
            ],
            textposition="middle right",
            textfont=dict(
                size=10
            ),
            hovertext=node_text,
            hoverinfo="text",
            marker=dict(
                size=node_sizes,
                color=node_colors,
                line=dict(
                    width=1,
                    color="#374151"
                )
            )
        )

        fig = go.Figure(
            data=[
                edge_trace,
                node_trace
            ]
        )

        fig.update_layout(

            height=650,

            margin=dict(
                l=20,
                r=20,
                t=30,
                b=20
            ),

            xaxis=dict(
                visible=False,
                range=[
                    -0.5,
                    3.7
                ]
            ),

            yaxis=dict(
                visible=False
            ),

            plot_bgcolor="white",

            hovermode="closest",

            showlegend=False
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            key="network_graph"
        )

        st.caption(
            "Tier 3 → Tier 2 → Tier 1 → NovaDrive. "
            "Orange = event source; red = downstream network exposure."
        )

    except ImportError:

        st.error(
            "Plotly is required for the interactive network graph. "
            "Add plotly to requirements.txt."
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
    "Confirmed network + event-driven risk"
)


# ============================================================
# EXECUTIVE OVERVIEW
# ============================================================

if page == "Executive Overview":

    st.title("NovaDrive CRO Dashboard")

    st.caption(
        "Supplier network visibility, risk prioritisation "
        "and event-driven management alerts"
    )

    st.divider()

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
        sum(
            get_tier(node) == "Tier 1"
            for node in network_nodes
        )
    )

    col4.metric(
        "Management Alerts",
        len(event_alerts)
    )

    st.divider()

    st.subheader("Network Exposure")

    show_network_graph()

    st.divider()

    st.subheader("Current Alert Summary")

    col1, col2, col3 = st.columns(3)

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

    col1.metric(
        "Critical",
        severity_count(
            event_alerts,
            "CRITICAL"
        )
    )

    col2.metric(
        "High",
        severity_count(
            event_alerts,
            "HIGH"
        )
    )

    col3.metric(
        "Medium",
        severity_count(
            event_alerts,
            "MEDIUM"
        )
    )


# ============================================================
# SUPPLIER NETWORK
# ============================================================

elif page == "Supplier Network":

    st.title("Supplier Network")

    st.caption(
        "Interactive view of the confirmed material supplier network"
    )

    # --------------------------------------------------------
    # Supplier selector
    # --------------------------------------------------------

    supplier_options = [
        "None"
    ] + [
        node
        for node in network_nodes
        if node != "NovaDrive Technologies"
    ]

    selected_supplier = st.selectbox(
        "Select a supplier to highlight its downstream exposure",
        supplier_options
    )

    highlighted = set()

    if selected_supplier != "None":

        highlighted = get_downstream_nodes(
            [selected_supplier]
        )

        highlighted.discard(
            selected_supplier
        )

    show_network_graph(
        highlighted_nodes=highlighted,
        selected_event_nodes=(
            [selected_supplier]
            if selected_supplier != "None"
            else []
        )
    )

    if selected_supplier != "None":

        st.divider()

        st.subheader(
            f"Supplier Impact — {selected_supplier}"
        )

        st.write(
            f"**Tier:** {get_tier(selected_supplier)}"
        )

        st.write(
            f"**Confirmed downstream nodes affected:** "
            f"{len(highlighted)}"
        )

        downstream_display = [
            node
            for node in highlighted
            if node != "NovaDrive Technologies"
        ]

        if downstream_display:

            st.write(
                "**Downstream network:**"
            )

            for node in downstream_display:

                st.write(
                    f"- {node} ({get_tier(node)})"
                )

        else:

            st.info(
                "No confirmed downstream dependency identified."
            )

    st.divider()

    st.subheader("Relationship Evidence")

    st.dataframe(
        supplier_network,
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
        "Match an external event to the confirmed supplier network "
        "and visualise its downstream impact"
    )

    # ========================================================
    # TABS
    # ========================================================

    existing_tab, new_tab = st.tabs(
        [
            "Existing Alerts",
            "Analyze New Event"
        ]
    )

    # ========================================================
    # EXISTING EVENTS
    # ========================================================

    with existing_tab:

        st.subheader("Current Management Alerts")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Total Alerts",
            len(event_alerts)
        )

        col2.metric(
            "Critical",
            severity_count(
                event_alerts,
                "CRITICAL"
            )
        )

        col3.metric(
            "High",
            severity_count(
                event_alerts,
                "HIGH"
            )
        )

        col4.metric(
            "Medium",
            severity_count(
                event_alerts,
                "MEDIUM"
            )
        )

        st.divider()

        if len(event_alerts) > 0:

            event_options = (
                event_alerts[
                    "Event ID"
                ]
                .dropna()
                .astype(str)
                .tolist()
            )

            selected_event = st.selectbox(
                "Select an event",
                event_options
            )

            selected_event_row = event_alerts[
                event_alerts["Event ID"]
                .astype(str)
                == selected_event
            ].iloc[0]

            # ------------------------------------------------
            # Determine affected suppliers
            # ------------------------------------------------

            affected_suppliers = []

            if "Affected Supplier" in selected_event_row.index:

                value = selected_event_row[
                    "Affected Supplier"
                ]

                if pd.notna(value):

                    for supplier in network_nodes:

                        if supplier == "NovaDrive Technologies":
                            continue

                        if normalize_text(supplier) in normalize_text(value):

                            affected_suppliers.append(
                                supplier
                            )

            # Also search title/detail
            event_text = " ".join(
                [
                    str(
                        selected_event_row.get(
                            "Title",
                            ""
                        )
                    ),
                    str(
                        selected_event_row.get(
                            "Event Detail",
                            ""
                        )
                    )
                ]
            )

            matches = match_new_event(
                event_text
            )

            for match in matches:

                if match["Supplier"] not in affected_suppliers:

                    affected_suppliers.append(
                        match["Supplier"]
                    )

            downstream = get_downstream_nodes(
                affected_suppliers
            )

            downstream.discard(
                *affected_suppliers
            )

            # ------------------------------------------------
            # Graph
            # ------------------------------------------------

            st.subheader(
                "Network Impact"
            )

            show_network_graph(
                highlighted_nodes=downstream,
                selected_event_nodes=affected_suppliers
            )

            # ------------------------------------------------
            # Alert details
            # ------------------------------------------------

            st.subheader(
                "Management Alert"
            )

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

                if field in selected_event_row.index:

                    value = selected_event_row[field]

                    if pd.notna(value):

                        st.markdown(
                            f"**{field}:** {value}"
                        )

            if affected_suppliers:

                st.divider()

                st.subheader(
                    "Affected Confirmed Network"
                )

                for supplier in affected_suppliers:

                    st.write(
                        f"🔴 **{supplier}** — "
                        f"{get_tier(supplier)}"
                    )

                for node in downstream:

                    st.write(
                        f"🔴 {node} — "
                        f"{get_tier(node)}"
                    )

            else:

                st.info(
                    "No confirmed supplier node was identified "
                    "from this event. Treat as an external exposure "
                    "requiring verification rather than inventing "
                    "a network relationship."
                )

        st.divider()

        st.subheader(
            "All Management Alerts"
        )

        st.dataframe(
            event_alerts,
            use_container_width=True,
            hide_index=True
        )

    # ========================================================
    # NEW EVENT
    # ========================================================

    with new_tab:

        st.subheader(
            "Analyze a New Event"
        )

        st.write(
            "Enter an external risk signal in plain language. "
            "The platform will attempt to match it to a confirmed "
            "supplier or production facility."
        )

        new_event = st.text_area(
            "Event description",
            placeholder=(
                "Example: Fire reported at SITE-081 "
                "affecting production..."
            ),
            height=140
        )

        analyze = st.button(
            "Analyze Event",
            type="primary"
        )

        if analyze:

            if not new_event.strip():

                st.warning(
                    "Please enter an event description."
                )

            else:

                matches = match_new_event(
                    new_event
                )

                if not matches:

                    st.warning(
                        "No confirmed supplier or facility match "
                        "was identified."
                    )

                    st.info(
                        "This should be treated as an "
                        "**Unassessed External Exposure**. "
                        "The platform deliberately does not create "
                        "a supplier relationship from an ambiguous "
                        "event."
                    )

                else:

                    matched_suppliers = list(
                        dict.fromkeys(
                            [
                                match["Supplier"]
                                for match in matches
                            ]
                        )
                    )

                    affected_network = (
                        get_downstream_nodes(
                            matched_suppliers
                        )
                    )

                    downstream_only = (
                        affected_network
                        - set(matched_suppliers)
                    )

                    st.success(
                        f"Matched {len(matched_suppliers)} "
                        f"confirmed supplier node(s)."
                    )

                    # ----------------------------------------
                    # MATCH DETAILS
                    # ----------------------------------------

                    st.subheader(
                        "Event Match"
                    )

                    match_table = pd.DataFrame(
                        matches
                    )

                    st.dataframe(
                        match_table,
                        use_container_width=True,
                        hide_index=True
                    )

                    # ----------------------------------------
                    # NETWORK GRAPH
                    # ----------------------------------------

                    st.subheader(
                        "Network Impact"
                    )

                    show_network_graph(
                        highlighted_nodes=downstream_only,
                        selected_event_nodes=matched_suppliers
                    )

                    # ----------------------------------------
                    # IMPACT SUMMARY
                    # ----------------------------------------

                    st.subheader(
                        "Impact Summary"
                    )

                    col1, col2, col3 = st.columns(3)

                    col1.metric(
                        "Event-Affected Supplier Nodes",
                        len(matched_suppliers)
                    )

                    col2.metric(
                        "Downstream Nodes Exposed",
                        len(downstream_only)
                    )

                    col3.metric(
                        "NovaDrive Exposure",
                        (
                            "Yes"
                            if "NovaDrive Technologies"
                            in affected_network
                            else "No"
                        )
                    )

                    st.divider()

                    st.subheader(
                        "Affected Network"
                    )

                    st.write(
                        "**Directly matched supplier(s):**"
                    )

                    for supplier in matched_suppliers:

                        st.write(
                            f"🟠 **{supplier}** "
                            f"({get_tier(supplier)})"
                        )

                    if downstream_only:

                        st.write(
                            "**Downstream network potentially affected:**"
                        )

                        for node in sorted(
                            downstream_only
                        ):

                            st.write(
                                f"🔴 {node} "
                                f"({get_tier(node)})"
                            )

                    else:

                        st.info(
                            "No downstream confirmed dependency "
                            "was identified."
                        )

                    st.divider()

                    st.subheader(
                        "Management Interpretation"
                    )

                    if "NovaDrive Technologies" in affected_network:

                        st.error(
                            "The matched supplier sits on a confirmed "
                            "path to NovaDrive. The event therefore has "
                            "potential direct network relevance."
                        )

                        st.markdown(
                            """
                            **Recommended next action**

                            1. Verify whether the event has caused
                               an actual production or shipment impact.
                            2. Check affected facility / material
                               availability.
                            3. Assess inventory and time-to-impact.
                            4. Initiate alternate-supplier review if
                               the exposure is material.
                            """
                        )

                    else:

                        st.warning(
                            "The event matches a confirmed supplier "
                            "but no confirmed downstream NovaDrive "
                            "path was identified."
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
