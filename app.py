import streamlit as st
import pandas as pd
import numpy as np
import networkx as nx
import plotly.graph_objects as go
from pathlib import Path


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="NovaDrive CRO Decision Support",
    page_icon="⚙️",
    layout="wide"
)


# ============================================================
# PATHS / DATA
# ============================================================

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

NETWORK_FILE = DATA_DIR / "supplier_network.csv"
ENTITIES_FILE = DATA_DIR / "supplier_entities.csv"
EVENT_FILE = DATA_DIR / "event_alerts.csv"


@st.cache_data
def load_data():

    network = pd.read_csv(NETWORK_FILE)
    entities = pd.read_csv(ENTITIES_FILE)
    events = pd.read_csv(EVENT_FILE)

    return network, entities, events


network_df, supplier_entities, event_alerts = load_data()


# ============================================================
# SUPPLIER / TIER INFORMATION
# ============================================================

supplier_tier = {}

if "Entity" in supplier_entities.columns and "Tier" in supplier_entities.columns:
    for _, r in supplier_entities.iterrows():
        supplier_tier[str(r["Entity"])] = str(r["Tier"])


# Explicit confirmed supplier universe
CONFIRMED_SUPPLIERS = [
    "Aster Power Assemblies Ltd.",
    "Boreal Power Systems Ltd.",
    "Cobalt Control Electronics Ltd.",
    "Delta Capacitor Works Ltd.",
    "Estuary Thermal Systems Ltd.",
    "ForgeLine Enclosures Ltd.",
    "Grove Battery Controls Ltd.",
    "HarborSense Electronics Ltd.",
    "IonPeak Semiconductor Ltd.",
    "Jade Printed Circuits Ltd.",
    "Kestrel Microdevices Ltd.",
    "Lumen Magnetics Ltd.",
    "Meridian Dielectrics Ltd.",
    "Nacre Foils Ltd.",
    "Orion Ceramics Ltd.",
    "Pine Thermal Metals Ltd.",
    "Quartz Alloy Ltd.",
    "Rill Connectors Ltd.",
    "Umber Silicon Carbide Ltd.",
    "Warden Copper Foil Ltd.",
    "Xenon Resin Ltd.",
    "Yarrow Specialty Minerals Ltd.",
    "Zenith Polymer Ltd."
]


# ============================================================
# EXISTING EVENT STATUS
# IMPORTANT:
# These are authoritative display values for the original
# event-feed cases.
# ============================================================

ALL_EVENT_STATUS = {

    "EV-001": {
        "classification": "Potential Geographic Exposure",
        "event_risk": "MEDIUM",
        "status": "Network-linked",
        "matched_suppliers": [
            "IonPeak Semiconductor Ltd.",
            "Jade Printed Circuits Ltd.",
            "Orion Ceramics Ltd.",
            "Umber Silicon Carbide Ltd."
        ],
        "why": (
            "The East Delta flood-watch signal maps to facilities in the "
            "confirmed NovaDrive supplier network. No facility shutdown or "
            "physical damage is confirmed yet."
        ),
        "action": (
            "Verify facility damage, production status and logistics "
            "disruption at the affected East Delta sites."
        )
    },

    "EV-002": {
        "classification": "Duplicate Evidence",
        "event_risk": "LOW",
        "status": "Excluded",
        "matched_suppliers": [],
        "why": (
            "This report repeats the same flood bulletin as EV-001 and "
            "shares the same source family."
        ),
        "action": (
            "Do not create a separate management alert. Continue monitoring "
            "the underlying flood situation through EV-001."
        )
    },

    "EV-003": {
        "classification": "Active Supplier Risk",
        "event_risk": "HIGH",
        "status": "Network-linked",
        "matched_suppliers": [
            "Meridian Dielectrics Ltd."
        ],
        "why": (
            "The financing-pressure signal specifically identifies "
            "Meridian Dielectrics, a confirmed upstream supplier to Delta "
            "Capacitor Works for C20."
        ),
        "action": (
            "Verify Meridian's financial and production continuity and "
            "assess NovaDrive's C20 exposure."
        )
    },

    "EV-004": {
        "classification": "Entity Mismatch",
        "event_risk": "LOW",
        "status": "Excluded",
        "matched_suppliers": [],
        "why": (
            "The event concerns Ion Peak Trading, a broker in Harbor "
            "District, rather than IonPeak Semiconductor Ltd."
        ),
        "action": (
            "No NovaDrive network action required unless independent "
            "evidence links the event to IonPeak Semiconductor."
        )
    },

    "EV-005": {
        "classification": "Historical / Stale Event",
        "event_risk": "LOW",
        "status": "Excluded",
        "matched_suppliers": [],
        "why": (
            "The port-strike report is historical and the strike ended "
            "in 2023."
        ),
        "action": (
            "No current management action. Monitor only if a new disruption "
            "is reported."
        )
    },

    "EV-007": {
        "classification": "Monitor",
        "event_risk": "LOW",
        "status": "Network Context Match",
        "matched_suppliers": [
            "Jade Printed Circuits Ltd."
        ],
        "why": (
            "The event concerns Jade Printed Circuits, a confirmed supplier "
            "in the NovaDrive network. The relocation is within Harbor "
            "District and production remains at SITE-081."
        ),
        "action": (
            "Continue monitoring SITE-081 production and confirm that the "
            "relocation does not affect supply continuity."
        )
    },

    "EV-009": {
        "classification": "Entity Mismatch",
        "event_risk": "LOW",
        "status": "Excluded",
        "matched_suppliers": [],
        "why": (
            "The allegation concerns Delta Consumer Plastics rather than "
            "Delta Capacitor Works Ltd."
        ),
        "action": (
            "No NovaDrive network action required."
        )
    },

    "EV-010": {
        "classification": "Unassessed External Exposure",
        "event_risk": "LOW",
        "status": "Unassessed",
        "matched_suppliers": [],
        "why": (
            "Current Gulf Arc port congestion is reported, but no confirmed "
            "NovaDrive supplier or facility is linked to Gulf Arc in the "
            "current network."
        ),
        "action": (
            "Check whether confirmed supplier shipments depend on Gulf Arc "
            "departures and assess shipment-specific exposure."
        )
    }
}


# ============================================================
# KNOWN SUPPLIER RISK
# Part 2 risk values already established for the suppliers
# appearing in current management alerts.
# ============================================================

KNOWN_SUPPLIER_RISK = {
    "IonPeak Semiconductor Ltd.": "CRITICAL",
    "Jade Printed Circuits Ltd.": "HIGH",
    "Orion Ceramics Ltd.": "MEDIUM",
    "Umber Silicon Carbide Ltd.": "CRITICAL",
    "Meridian Dielectrics Ltd.": "CRITICAL"
}


# ============================================================
# EXAMPLE EVENTS
# ============================================================

EXAMPLE_EVENTS = [
    (
        "🔥 SITE-081 disruption",
        "A major fire has been reported at SITE-081, causing the facility "
        "to suspend production of printed circuit substrates."
    ),
    (
        "⚡ SITE-074 disruption",
        "A production disruption has been reported at SITE-074, affecting "
        "power semiconductor die manufacturing."
    ),
    (
        "🔧 SITE-088 equipment failure",
        "A serious equipment failure at SITE-088 has halted microcontroller "
        "production for several days."
    ),
    (
        "🏭 SITE-116 disruption",
        "A major disruption at SITE-116 has temporarily stopped ceramic "
        "substrate production."
    ),
    (
        "🌊 SITE-137 flooding",
        "Flooding at SITE-137 has disrupted connector manufacturing and "
        "outbound shipments."
    ),
    (
        "📦 SITE-179 resin disruption",
        "A raw-material supply disruption is affecting production at SITE-179, "
        "with resin deliveries suspended."
    ),
    (
        "⚠️ SITE-102 disruption",
        "A severe disruption at SITE-102 has halted dielectric film production."
    ),
    (
        "🏢 Westport unrelated event",
        "A fire at a manufacturing facility in Westport has temporarily "
        "halted production of industrial sensors."
    )
]


# ============================================================
# SUPPLIER → SITE MAPPING
# ============================================================

SUPPLIER_SITE = {
    "IonPeak Semiconductor Ltd.": "SITE-074",
    "Jade Printed Circuits Ltd.": "SITE-081",
    "Orion Ceramics Ltd.": "SITE-116",
    "Umber Silicon Carbide Ltd.": "SITE-158",

    "Aster Power Assemblies Ltd.": "SITE-018",
    "ForgeLine Enclosures Ltd.": "SITE-053",
    "Quartz Alloy Ltd.": "SITE-130",

    "Delta Capacitor Works Ltd.": "SITE-039",
    "Meridian Dielectrics Ltd.": "SITE-102",
    "Zenith Polymer Ltd.": "SITE-193",

    "Cobalt Control Electronics Ltd.": "SITE-032",
    "Grove Battery Controls Ltd.": "SITE-060",
    "Lumen Magnetics Ltd.": "SITE-095",
    "Rill Connectors Ltd.": "SITE-137",
    "Xenon Resin Ltd.": "SITE-179",

    "Boreal Power Systems Ltd.": "SITE-025",
    "HarborSense Electronics Ltd.": "SITE-067",
    "Kestrel Microdevices Ltd.": "SITE-088",

    "Estuary Thermal Systems Ltd.": "SITE-046",
    "Nacre Foils Ltd.": "SITE-109",
    "Pine Thermal Metals Ltd.": "SITE-123",
    "Warden Copper Foil Ltd.": "SITE-172",

    "Yarrow Specialty Minerals Ltd.": "SITE-186"
}


# ============================================================
# RISK HELPERS
# ============================================================

RISK_ORDER = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
    "UNASSESSED": 0
}


def risk_color(level):

    level = str(level).upper()

    if level == "CRITICAL":
        return "#B91C1C"

    if level == "HIGH":
        return "#EA580C"

    if level == "MEDIUM":
        return "#CA8A04"

    if level == "LOW":
        return "#16A34A"

    return "#64748B"


def show_risk_badge(level, label="Risk Level"):

    level = str(level).upper()

    color = risk_color(level)

    st.markdown(
        f"""
        <div style="
            display:inline-block;
            padding:8px 16px;
            border-radius:8px;
            background:{color};
            color:white;
            font-weight:700;
            font-size:15px;
            margin:4px 0 10px 0;
        ">
            {label}: {level}
        </div>
        """,
        unsafe_allow_html=True
    )


def highest_supplier_risk(suppliers):

    levels = []

    for supplier in suppliers:

        if supplier in KNOWN_SUPPLIER_RISK:
            levels.append(KNOWN_SUPPLIER_RISK[supplier])

    if not levels:
        return None

    return max(
        levels,
        key=lambda x: RISK_ORDER.get(x, 0)
    )


def calculate_network_impact_risk(matched_suppliers):

    if not matched_suppliers:
        return "LOW"

    tiers = []

    for supplier in matched_suppliers:

        tier = str(supplier_tier.get(supplier, "")).lower()

        if "tier 3" in tier or tier == "3":
            tiers.append(3)

        elif "tier 2" in tier or tier == "2":
            tiers.append(2)

        elif "tier 1" in tier or tier == "1":
            tiers.append(1)

    # Upstream Tier-3 disruption is inherently critical
    if 3 in tiers:
        return "CRITICAL"

    # Multiple Tier-1 dependencies
    tier1_count = sum(t == 1 for t in tiers)

    if tier1_count >= 2:
        return "CRITICAL"

    if 2 in tiers:
        return "HIGH"

    if 1 in tiers:
        return "MEDIUM"

    return "LOW"


def get_recommended_action(risk, matched_suppliers):

    if risk == "CRITICAL":
        return (
            "Immediately verify production continuity, quantify affected "
            "NovaDrive exposure and activate alternate-source / contingency "
            "planning."
        )

    if risk == "HIGH":
        return (
            "Verify the affected supplier's production and shipment status "
            "and assess near-term downstream exposure."
        )

    if risk == "MEDIUM":
        return (
            "Validate the event at the facility level and monitor supply "
            "continuity and logistics."
        )

    return (
        "Continue monitoring and verify whether the event develops into "
        "a confirmed network disruption."
    )


def show_risk_legend():

    st.markdown("#### Risk scale")

    cols = st.columns(4)

    for col, level in zip(
        cols,
        ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    ):

        with col:

            color = risk_color(level)

            st.markdown(
                f"""
                <div style="
                    border-left:6px solid {color};
                    padding:8px 12px;
                    background:#F8FAFC;
                    border-radius:5px;
                ">
                    <b style="color:{color}">{level}</b>
                </div>
                """,
                unsafe_allow_html=True
            )


# ============================================================
# GRAPH CONSTRUCTION
# ============================================================

def build_graph():

    G = nx.MultiDiGraph()

    # Confirmed relationships
    for _, row in network_df.iterrows():

        source = str(row.get("From", row.get("Supplier", "")))
        target = str(row.get("To", row.get("Customer", "")))

        if not source or not target:
            continue

        G.add_edge(
            source,
            target,
            status="confirmed"
        )

    # Uncertainty layer
    G.add_edge(
        "Verdant Process Gases Ltd.",
        "IonPeak Semiconductor Ltd.",
        status="inference"
    )

    G.add_edge(
        "Alder Bauxite Ltd.",
        "Quartz Alloy Ltd.",
        status="hypothesis"
    )

    G.add_edge(
        "Solace Optics",
        "Grove Battery Controls Ltd.",
        status="hypothesis"
    )

    return G


G = build_graph()


# ============================================================
# TIER ORDER / POSITIONS
# ============================================================

tier3_order = [
    "Umber Silicon Carbide Ltd.",
    "Lumen Magnetics Ltd.",
    "Orion Ceramics Ltd.",
    "Kestrel Microdevices Ltd.",
    "Rill Connectors Ltd.",
    "Nacre Foils Ltd.",
    "Pine Thermal Metals Ltd.",
    "Warden Copper Foil Ltd.",
    "Xenon Resin Ltd.",
    "Yarrow Specialty Minerals Ltd.",
    "Verdant Process Gases Ltd.",
    "Alder Bauxite Ltd."
]

tier2_order = [
    "IonPeak Semiconductor Ltd.",
    "Jade Printed Circuits Ltd.",
    "Kestrel Microdevices Ltd.",
    "Lumen Magnetics Ltd.",
    "Orion Ceramics Ltd.",
    "Rill Connectors Ltd.",
    "Meridian Dielectrics Ltd.",
    "Nacre Foils Ltd.",
    "Pine Thermal Metals Ltd.",
    "Quartz Alloy Ltd.",
    "Solace Optics"
]

tier1_order = [
    "Aster Power Assemblies Ltd.",
    "Boreal Power Systems Ltd.",
    "Cobalt Control Electronics Ltd.",
    "Delta Capacitor Works Ltd.",
    "Estuary Thermal Systems Ltd.",
    "ForgeLine Enclosures Ltd.",
    "Grove Battery Controls Ltd.",
    "HarborSense Electronics Ltd."
]


def make_positions():

    positions = {}

    def assign(nodes, x):

        n = len(nodes)

        if n == 1:
            ys = [0]
        else:
            ys = np.linspace(n / 2, -n / 2, n)

        for node, y in zip(nodes, ys):
            positions[node] = (x, y)

    assign(tier3_order, 0)
    assign(tier2_order, 1)
    assign(tier1_order, 2)

    positions["NovaDrive Technologies Ltd."] = (3, 0)

    return positions


POSITIONS = make_positions()


# ============================================================
# RECTANGULAR EDGE BOUNDARY
# ============================================================

def boundary_point(x1, y1, x2, y2, width=0.42, height=0.22):

    dx = x2 - x1
    dy = y2 - y1

    if dx == 0 and dy == 0:
        return x1, y1

    candidates = []

    if dx != 0:
        t = width / abs(dx)
        candidates.append(t)

    if dy != 0:
        t = height / abs(dy)
        candidates.append(t)

    t = min(candidates)

    return (
        x1 + dx * t,
        y1 + dy * t
    )


# ============================================================
# GRAPH DRAWING
# ============================================================

def draw_network_graph(
    highlighted_suppliers=None,
    title="NovaDrive Supplier Network"
):

    highlighted_suppliers = set(highlighted_suppliers or [])

    all_nodes = set(POSITIONS.keys())

    # Add uncertainty nodes to visual positions
    positions = POSITIONS.copy()

    positions["Verdant Process Gases Ltd."] = (-0.15, -7.0)
    positions["Alder Bauxite Ltd."] = (-0.15, -8.4)
    positions["Solace Optics"] = (1.0, -7.0)

    # Determine downstream confirmed nodes
    active_nodes = set(highlighted_suppliers)

    changed = True

    while changed:

        changed = False

        for u, v in G.edges():

            if v in active_nodes and u not in active_nodes:

                active_nodes.add(u)
                changed = True

    # If an upstream supplier is selected, show downstream impact
    # by following supplier → customer direction.
    if highlighted_suppliers:

        active_nodes = set(highlighted_suppliers)

        frontier = list(highlighted_suppliers)

        while frontier:

            current = frontier.pop()

            for _, downstream in G.out_edges(current):

                if downstream not in active_nodes:

                    active_nodes.add(downstream)
                    frontier.append(downstream)

    fig = go.Figure()

    # --------------------------------------------------------
    # EDGES
    # --------------------------------------------------------

    for u, v, data in G.edges(data=True):

        if u not in positions or v not in positions:
            continue

        x1, y1 = positions[u]
        x2, y2 = positions[v]

        sx, sy = boundary_point(
            x1, y1, x2, y2
        )

        ex, ey = boundary_point(
            x2, y2, x1, y1
        )

        status = data.get("status", "confirmed")

        affected = (
            not highlighted_suppliers
            or (u in active_nodes and v in active_nodes)
        )

        if status == "confirmed":

            line_color = "#DC2626" if (
                highlighted_suppliers
                and u in active_nodes
                and v in active_nodes
            ) else "#6B7280"

            opacity = 1.0 if affected else 0.12
            dash = "solid"

        elif status == "inference":

            line_color = "#EAB308"
            opacity = 0.95 if not highlighted_suppliers else 0.12
            dash = "dash"

        else:

            line_color = "#F97316"
            opacity = 0.95 if not highlighted_suppliers else 0.12
            dash = "dash"

        fig.add_trace(
            go.Scatter(
                x=[sx, ex],
                y=[sy, ey],
                mode="lines",
                line=dict(
                    color=line_color,
                    width=2,
                    dash=dash
                ),
                opacity=opacity,
                hoverinfo="text",
                text=f"{u} → {v}",
                showlegend=False
            )
        )

        # Arrowhead
        fig.add_annotation(
            x=ex,
            y=ey,
            ax=sx,
            ay=sy,
            xref="x",
            yref="y",
            axref="x",
            ayref="y",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=1.5,
            arrowcolor=line_color,
            opacity=opacity
        )

    # --------------------------------------------------------
    # NODES
    # --------------------------------------------------------

    node_colors = []
    node_sizes = []
    node_opacities = []
    node_text = []
    node_x = []
    node_y = []

    for node, (x, y) in positions.items():

        node_x.append(x)
        node_y.append(y)

        is_uncertainty = node in [
            "Verdant Process Gases Ltd.",
            "Alder Bauxite Ltd.",
            "Solace Optics"
        ]

        if is_uncertainty:

            if node == "Verdant Process Gases Ltd.":
                color = "#EAB308"
            else:
                color = "#F97316"

            opacity = (
                0.95 if not highlighted_suppliers else 0.18
            )

        elif node == "NovaDrive Technologies Ltd.":

            color = "#111827"
            opacity = 1.0

        elif highlighted_suppliers:

            if node in active_nodes:
                color = "#DC2626"
                opacity = 1.0
            else:
                color = "#94A3B8"
                opacity = 0.25

        else:

            color = "#FFFFFF"
            opacity = 1.0

        node_colors.append(color)
        node_opacities.append(opacity)

        if node == "NovaDrive Technologies Ltd.":
            node_sizes.append(45)
        else:
            node_sizes.append(30)

        node_text.append(node)

    fig.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            text=node_text,
            textposition="middle center",
            textfont=dict(
                size=10,
                color="#111827"
            ),
            marker=dict(
                size=node_sizes,
                color=node_colors,
                opacity=node_opacities,
                line=dict(
                    color="#374151",
                    width=1
                ),
                symbol="square"
            ),
            hovertext=node_text,
            hoverinfo="text",
            showlegend=False
        )
    )

    # --------------------------------------------------------
    # TIER HEADINGS
    # --------------------------------------------------------

    fig.add_annotation(
        x=0,
        y=2.0,
        text="<b>Tier 3</b>",
        showarrow=False,
        font=dict(size=16, color="#1F2937")
    )

    fig.add_annotation(
        x=1,
        y=2.0,
        text="<b>Tier 2</b>",
        showarrow=False,
        font=dict(size=16, color="#1F2937")
    )

    fig.add_annotation(
        x=2,
        y=2.0,
        text="<b>Tier 1</b>",
        showarrow=False,
        font=dict(size=16, color="#1F2937")
    )

    fig.add_annotation(
        x=3,
        y=2.0,
        text="<b>NovaDrive</b>",
        showarrow=False,
        font=dict(size=16, color="#1F2937")
    )

    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=20)
        ),
        height=1000,
        margin=dict(
            l=40,
            r=40,
            t=120,
            b=100
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(
            visible=False,
            range=[-0.8, 3.8]
        ),
        yaxis=dict(
            visible=False,
            range=[-9.3, 2.5]
        ),
        hovermode="closest"
    )

    return fig


# ============================================================
# EVENT MATCHING
# ============================================================

def match_new_event(event_text):

    text = str(event_text).lower()

    matches = []

    # Facility-first matching
    for supplier, site in SUPPLIER_SITE.items():

        if site.lower() in text:

            matches.append(supplier)

    # Exact supplier-name matching
    for supplier in CONFIRMED_SUPPLIERS:

        short_name = supplier.lower().replace(" ltd.", "").strip()

        if short_name in text or supplier.lower() in text:

            if supplier not in matches:
                matches.append(supplier)

    # Important false-match protection
    if (
        "ion peak trading" in text
        or "ion peak broker" in text
        or (
            "ion peak trading" in text
            and "ionpeak semiconductor" not in text
        )
    ):

        matches = [
            x for x in matches
            if x != "IonPeak Semiconductor Ltd."
        ]

    return matches


# ============================================================
# DOWNSTREAM NETWORK
# ============================================================

def downstream_nodes(suppliers):

    affected = set(suppliers)

    frontier = list(suppliers)

    while frontier:

        current = frontier.pop()

        for _, downstream in G.out_edges(current):

            if downstream not in affected:

                affected.add(downstream)
                frontier.append(downstream)

    return affected


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("NovaDrive CRO")

page = st.sidebar.radio(
    "Navigate",
    [
        "Executive Overview",
        "Supplier Network",
        "Risk Assessment",
        "Events & Alerts",
        "Alternate Suppliers"
    ]
)


# ============================================================
# EXECUTIVE OVERVIEW
# ============================================================

if page == "Executive Overview":

    st.title("NovaDrive CRO Decision Support")

    st.markdown(
        """
        This dashboard brings together NovaDrive's reconstructed supplier
        network, supplier risk assessment, external-risk event matching and
        management alerts.
        """
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("Confirmed Suppliers", "23")

    with c2:
        st.metric("Confirmed Relationships", "31")

    with c3:
        st.metric("Network Tiers", "3")

    with c4:
        st.metric("Network-linked Events", "3")

    st.divider()

    st.subheader("Key CRO observations")

    st.markdown(
        """
        - **IonPeak Semiconductor** is a critical upstream dependency for
          Aster and Boreal.
        - **Jade Printed Circuits** is a shared upstream dependency for
          Cobalt, Grove and HarborSense.
        - **Meridian Dielectrics** represents an active financial-risk signal
          affecting the C20 chain.
        - The network contains several unresolved upstream relationships that
          should remain visually separate from confirmed relationships.
        """
    )

    show_risk_legend()


# ============================================================
# SUPPLIER NETWORK
# ============================================================

elif page == "Supplier Network":

    st.title("Supplier Network")

    st.markdown(
        """
        Confirmed relationships are shown as solid links. Reasonable
        inferences and unresolved hypotheses are shown separately as dashed
        links.
        """
    )

    st.plotly_chart(
        draw_network_graph(),
        use_container_width=True,
        key="main_network"
    )

    st.subheader("Confirmed relationship data")

    st.dataframe(
        network_df,
        use_container_width=True,
        hide_index=True
    )

    st.subheader("Uncertainty layer")

    uncertainty_df = pd.DataFrame({
        "From": [
            "Verdant Process Gases Ltd.",
            "Alder Bauxite Ltd.",
            "Solace Optics"
        ],
        "To": [
            "IonPeak Semiconductor Ltd.",
            "Quartz Alloy Ltd.",
            "Grove Battery Controls Ltd."
        ],
        "Status": [
            "Reasonable inference",
            "Unresolved hypothesis",
            "Unresolved hypothesis"
        ],
        "Confidence": [
            "Medium",
            "Low",
            "Low-Medium"
        ]
    })

    st.dataframe(
        uncertainty_df,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# RISK ASSESSMENT
# ============================================================

elif page == "Risk Assessment":

    st.title("Supplier Risk Assessment")

    st.markdown(
        """
        Risk and evidence confidence are treated separately. Missing
        information is not automatically treated as low risk.
        """
    )

    show_risk_legend()

    st.divider()

    risk_rows = []

    for supplier, risk in KNOWN_SUPPLIER_RISK.items():

        risk_rows.append({
            "Supplier": supplier,
            "Risk Level": risk,
            "Risk Basis": (
                "Established supplier risk assessment from the "
                "NovaDrive scorecard."
            )
        })

    risk_df = pd.DataFrame(risk_rows)

    st.dataframe(
        risk_df,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# EVENTS & ALERTS
# ============================================================

elif page == "Events & Alerts":

    st.title("Events & Alerts")

    st.markdown(
        """
        Select an event from the original event feed to inspect how it was
        classified, whether it affects the confirmed network, its risk level,
        and the recommended management action.
        """
    )

    event_ids = list(ALL_EVENT_STATUS.keys())

    selected_event = st.selectbox(
        "Select event",
        event_ids
    )

    status = ALL_EVENT_STATUS[selected_event]

    # --------------------------------------------------------
    # EVENT DETAILS
    # --------------------------------------------------------

    selected_row = event_alerts[
        event_alerts["Event ID"].astype(str) == selected_event
    ]

    if not selected_row.empty:

        row = selected_row.iloc[0]

        st.subheader(str(row.get("Title", selected_event)))

        st.info(
            str(
                row.get(
                    "Event Detail",
                    "No event detail available."
                )
            )
        )

    else:

        st.subheader(selected_event)

    # --------------------------------------------------------
    # RISK — FIXED FOR EXISTING EVENTS
    # --------------------------------------------------------

    st.markdown("### Event assessment")

    c1, c2, c3 = st.columns(3)

    with c1:

        # AUTHORITATIVE EVENT-ID FALLBACK
        event_risk = status.get(
            "event_risk",
            "UNASSESSED"
        )

        show_risk_badge(
            event_risk,
            "Event Risk"
        )

    with c2:

        matched = status.get(
            "matched_suppliers",
            []
        )

        supplier_risk = highest_supplier_risk(matched)

        if supplier_risk:

            show_risk_badge(
                supplier_risk,
                "Highest Supplier Risk"
            )

        else:

            st.markdown(
                "**Supplier Risk:** No confirmed supplier risk"
            )

    with c3:

        st.markdown(
            f"**Classification**  \n"
            f"{status.get('classification', 'Unassessed')}"
        )

    st.markdown(
        f"**Status:** {status.get('status', 'Unassessed')}"
    )

    st.markdown(
        f"**Why it matters:** {status.get('why', '')}"
    )

    st.markdown(
        f"**Recommended action:** {status.get('action', '')}"
    )

    # --------------------------------------------------------
    # SUPPLIER RISK BREAKDOWN
    # --------------------------------------------------------

    matched = status.get("matched_suppliers", [])

    if matched:

        st.markdown("### Affected suppliers")

        supplier_rows = []

        for supplier in matched:

            supplier_rows.append({
                "Supplier": supplier,
                "Network Tier": supplier_tier.get(
                    supplier,
                    "Not available"
                ),
                "Established Supplier Risk":
                    KNOWN_SUPPLIER_RISK.get(
                        supplier,
                        "Not scored"
                    )
            })

        st.dataframe(
            pd.DataFrame(supplier_rows),
            use_container_width=True,
            hide_index=True
        )

        # ----------------------------------------------------
        # GRAPH
        # ----------------------------------------------------

        st.markdown("### Network impact")

        st.plotly_chart(
            draw_network_graph(
                highlighted_suppliers=matched,
                title=f"{selected_event} — Network Impact"
            ),
            use_container_width=True,
            key=f"existing_event_graph_{selected_event}"
        )

    else:

        st.info(
            "No confirmed NovaDrive supplier is affected by this event. "
            "The event is therefore shown for completeness but does not "
            "create a confirmed network impact."
        )

    st.divider()

    st.markdown("### Original event feed")

    display_cols = [
        c for c in [
            "Event ID",
            "Published At",
            "Effective At",
            "Title",
            "Event Detail",
            "Source Family ID",
            "Source Type"
        ]
        if c in event_alerts.columns
    ]

    st.dataframe(
        event_alerts[display_cols],
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# ALTERNATE SUPPLIERS
# ============================================================

elif page == "Alternate Suppliers":

    st.title("Alternate Suppliers")

    st.markdown(
        """
        Use this section to investigate potential alternatives for an
        affected supplier or upstream component. Fitment and supplier risk
        should be assessed separately.
        """
    )

    supplier_options = sorted(CONFIRMED_SUPPLIERS)

    selected_supplier = st.selectbox(
        "Select affected supplier",
        supplier_options
    )

    st.info(
        f"Selected supplier: **{selected_supplier}**"
    )

    st.markdown(
        """
        Public-source alternate-supplier research can be attached here for
        the affected component/application. Engineering qualification,
        manufacturing footprint and supplier risk should be validated
        separately before any sourcing decision.
        """
    )


# ============================================================
# NEW EVENT ANALYSIS
# ============================================================

st.sidebar.divider()

st.sidebar.markdown("### Quick Event Analysis")

if st.sidebar.button(
    "Open New Event Analyzer",
    use_container_width=True
):
    st.session_state["open_new_event"] = True


# ============================================================
# NEW EVENT ANALYZER
# ============================================================

if st.session_state.get("open_new_event", False):

    st.divider()

    st.header("Analyze New Event")

    st.markdown(
        """
        Enter an external event below, or click one of the example cases.
        The example will automatically populate the event box — no
        copy-pasting is required.
        """
    )

    # --------------------------------------------------------
    # EXAMPLE CASE BUTTONS
    # --------------------------------------------------------

    st.markdown("### Try an example")

    # Initialize event text
    if "new_event_input" not in st.session_state:
        st.session_state["new_event_input"] = ""

    cols = st.columns(2)

    for i, (label, description) in enumerate(EXAMPLE_EVENTS):

        with cols[i % 2]:

            if st.button(
                label,
                key=f"example_event_{i}",
                use_container_width=True,
                help=description
            ):

                st.session_state["new_event_input"] = description
                st.session_state["selected_example"] = i

                st.rerun()

    # --------------------------------------------------------
    # EVENT INPUT
    # --------------------------------------------------------

    event_text = st.text_area(
        "Event description",
        key="new_event_input",
        height=130,
        placeholder=(
            "Describe an external event affecting a supplier, facility, "
            "component or geography..."
        )
    )

    if st.button(
        "Analyze Event",
        type="primary",
        use_container_width=True
    ):

        if not event_text.strip():

            st.warning(
                "Please enter an event or select one of the examples above."
            )

        else:

            matched_suppliers = match_new_event(event_text)

            # ------------------------------------------------
            # MATCH RESULT
            # ------------------------------------------------

            st.markdown("## Analysis Result")

            if matched_suppliers:

                st.success(
                    f"Confirmed network match: "
                    f"{', '.join(matched_suppliers)}"
                )

                match_rows = []

                for supplier in matched_suppliers:

                    match_rows.append({
                        "Matched Supplier": supplier,
                        "Facility": SUPPLIER_SITE.get(
                            supplier,
                            "Not available"
                        ),
                        "Network Tier": supplier_tier.get(
                            supplier,
                            "Not available"
                        ),
                        "Established Supplier Risk":
                            KNOWN_SUPPLIER_RISK.get(
                                supplier,
                                "Not scored"
                            )
                    })

                st.dataframe(
                    pd.DataFrame(match_rows),
                    use_container_width=True,
                    hide_index=True
                )

                # --------------------------------------------
                # EVENT / NETWORK RISK
                # --------------------------------------------

                network_risk = calculate_network_impact_risk(
                    matched_suppliers
                )

                supplier_risk = highest_supplier_risk(
                    matched_suppliers
                )

                c1, c2 = st.columns(2)

                with c1:

                    show_risk_badge(
                        network_risk,
                        "Event / Network Impact Risk"
                    )

                with c2:

                    if supplier_risk:

                        show_risk_badge(
                            supplier_risk,
                            "Established Supplier Risk"
                        )

                    else:

                        st.markdown(
                            "**Established Supplier Risk:** "
                            "Not scored for this supplier"
                        )

                st.markdown("### What should we do?")

                st.info(
                    get_recommended_action(
                        network_risk,
                        matched_suppliers
                    )
                )

                # --------------------------------------------
                # AFFECTED NETWORK
                # --------------------------------------------

                affected = downstream_nodes(
                    matched_suppliers
                )

                st.markdown(
                    "### Affected network"
                )

                st.markdown(
                    f"""
                    The event directly matches **{
                        ", ".join(matched_suppliers)
                    }**. The highlighted network shows the confirmed
                    downstream path toward NovaDrive.
                    """
                )

                st.plotly_chart(
                    draw_network_graph(
                        highlighted_suppliers=matched_suppliers,
                        title="New Event — Network Impact"
                    ),
                    use_container_width=True,
                    key="new_event_network"
                )

            else:

                st.warning(
                    "No confirmed NovaDrive supplier or facility was matched "
                    "to this event."
                )

                show_risk_badge(
                    "LOW",
                    "Event / Network Impact Risk"
                )

                st.info(
                    "Recommended action: verify whether the event has any "
                    "indirect connection to a confirmed NovaDrive supplier "
                    "or facility before escalating it."
                )

                st.markdown("### Network impact")

                st.plotly_chart(
                    draw_network_graph(
                        highlighted_suppliers=[],
                        title="No Confirmed Network Match"
                    ),
                    use_container_width=True,
                    key="new_event_no_match_network"
                )
