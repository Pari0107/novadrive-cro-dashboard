import streamlit as st
import pandas as pd
import re
import math
from io import BytesIO

import plotly.graph_objects as go


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

    return (
        supplier_network,
        supplier_entities,
        event_alerts
    )


supplier_network, supplier_entities, event_alerts = load_data()


# ============================================================
# GENERAL HELPERS
# ============================================================

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


# ============================================================
# BUILD CONFIRMED NETWORK
# ============================================================

network_nodes = set()

for _, row in supplier_network.iterrows():

    if pd.notna(row.get("From")):
        network_nodes.add(
            str(row["From"])
        )

    if pd.notna(row.get("To")):
        network_nodes.add(
            str(row["To"])
        )

network_nodes.add(
    "NovaDrive Technologies"
)

network_nodes = sorted(
    network_nodes
)


network_edges = []

for _, row in supplier_network.iterrows():

    if (
        pd.notna(row.get("From"))
        and
        pd.notna(row.get("To"))
    ):

        network_edges.append(
            (
                str(row["From"]),
                str(row["To"])
            )
        )

# ============================================================
# TIER FUNCTIONS
# ============================================================

def get_tier(node):

    if node == "NovaDrive Technologies":
        return "NovaDrive"

    matches = supplier_entities[
        supplier_entities["Entity"]
        .astype(str)
        == str(node)
    ]

    if len(matches) > 0:

        if "Tier" in matches.columns:

            return str(
                matches.iloc[0]["Tier"]
            )

    matches = supplier_network[
        supplier_network["From"]
        .astype(str)
        == str(node)
    ]

    if len(matches) > 0:

        if "From Tier" in matches.columns:

            return str(
                matches.iloc[0]["From Tier"]
            )

    return "Unknown"


tier1_nodes = [
    n for n in network_nodes
    if get_tier(n) == "Tier 1"
]

tier2_nodes = [
    n for n in network_nodes
    if get_tier(n) == "Tier 2"
]

tier3_nodes = [
    n for n in network_nodes
    if get_tier(n) == "Tier 3"
]


# ============================================================
# EXACT COLAB-STYLE ORDERING
# ============================================================

# Tier 1 was alphabetically ordered in the final Colab graph.

tier1_order = sorted(
    tier1_nodes
)

tier1_position = {
    node: i
    for i, node in enumerate(tier1_order)
}


# Tier 2:
# order by the average downstream Tier-1 position.

tier2_scores = {}

for node in tier2_nodes:

    downstream = [
        target
        for source, target in network_edges
        if source == node
        and target in tier1_position
    ]

    if downstream:

        avg_position = sum(
            tier1_position[x]
            for x in downstream
        ) / len(downstream)

    else:

        avg_position = 999

    tier2_scores[node] = avg_position


tier2_order = sorted(
    tier2_nodes,
    key=lambda x: (
        tier2_scores.get(x, 999),
        x
    )
)

tier2_position = {
    node: i
    for i, node in enumerate(tier2_order)
}


# Tier 3:
# order by the average downstream Tier-2 position.

tier3_scores = {}

for node in tier3_nodes:

    downstream = [
        target
        for source, target in network_edges
        if source == node
        and target in tier2_position
    ]

    if downstream:

        avg_position = sum(
            tier2_position[x]
            for x in downstream
        ) / len(downstream)

    else:

        avg_position = 999

    tier3_scores[node] = avg_position


tier3_order = sorted(
    tier3_nodes,
    key=lambda x: (
        tier3_scores.get(x, 999),
        x
    )
)


# ============================================================
# EXACT COLAB-STYLE MANUAL POSITIONS
# ============================================================

X_POSITIONS = {
    "Tier 3": 0,
    "Tier 2": 3.4,
    "Tier 1": 6.8,
    "NovaDrive": 10.2
}

vertical_spacing = 1.25


def make_positions():

    positions = {}

    # --------------------------------------------------------
    # Tier 1
    # --------------------------------------------------------

    if tier1_order:

        total = len(tier1_order)

        for i, node in enumerate(tier1_order):

            y = (
                (total - 1) / 2
                - i
            ) * vertical_spacing

            positions[node] = (
                X_POSITIONS["Tier 1"],
                y
            )

    # --------------------------------------------------------
    # Tier 2
    # --------------------------------------------------------

    if tier2_order:

        total = len(tier2_order)

        for i, node in enumerate(tier2_order):

            y = (
                (total - 1) / 2
                - i
            ) * vertical_spacing

            positions[node] = (
                X_POSITIONS["Tier 2"],
                y
            )

    # --------------------------------------------------------
    # Tier 3
    # --------------------------------------------------------

    if tier3_order:

        total = len(tier3_order)

        for i, node in enumerate(tier3_order):

            y = (
                (total - 1) / 2
                - i
            ) * vertical_spacing

            positions[node] = (
                X_POSITIONS["Tier 3"],
                y
            )

    # --------------------------------------------------------
    # NovaDrive
    # --------------------------------------------------------

    positions[
        "NovaDrive Technologies"
    ] = (
        X_POSITIONS["NovaDrive"],
        0
    )

    return positions


positions = make_positions()


# ============================================================
# SUPPLIER FACILITIES
# ============================================================

supplier_facilities = {}

if "Facility" in supplier_network.columns:

    for _, row in supplier_network.iterrows():

        supplier = str(
            row.get("From", "")
        )

        facility = row.get(
            "Facility"
        )

        if pd.notna(facility):

            supplier_facilities.setdefault(
                supplier,
                set()
            ).add(
                str(facility)
            )


# ============================================================
# GEOGRAPHIC ZONE MAPPING
# Based on confirmed Supplier Universe
# ============================================================

ZONE_SUPPLIERS = {

    "Z01": [
        "IonPeak Semiconductor Ltd.",
        "Jade Printed Circuits Ltd.",
        "Orion Ceramics Ltd.",
        "Umber Silicon Carbide Ltd."
    ],

    "Z02": [
        "Aster Power Assemblies Ltd.",
        "ForgeLine Enclosures Ltd.",
        "Quartz Alloy Ltd."
    ],

    "Z03": [
        "Delta Capacitor Works Ltd.",
        "Meridian Dielectrics Ltd.",
        "Zenith Polymer Ltd."
    ],

    "Z04": [
        "Cobalt Control Electronics Ltd.",
        "Grove Battery Controls Ltd.",
        "Lumen Magnetics Ltd.",
        "Rill Connectors Ltd.",
        "Xenon Resin Ltd."
    ],

    "Z05": [
        "Boreal Power Systems Ltd.",
        "HarborSense Electronics Ltd.",
        "Kestrel Microdevices Ltd."
    ],

    "Z06": [
        "Estuary Thermal Systems Ltd.",
        "Nacre Foils Ltd.",
        "Pine Thermal Metals Ltd.",
        "Warden Copper Foil Ltd."
    ],

    "Z08": [
        "Yarrow Specialty Minerals Ltd."
    ]
}


# ============================================================
# EVENT MATCHING
# ============================================================

def match_new_event(event_text):

    text = normalize_text(
        event_text
    )

    matches = []

    # --------------------------------------------------------
    # Facility matching
    # --------------------------------------------------------

    facilities_in_text = re.findall(
        r"SITE-\d+",
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


    # --------------------------------------------------------
    # Supplier matching
    # --------------------------------------------------------

    for supplier in network_nodes:

        if supplier == "NovaDrive Technologies":
            continue

        supplier_norm = normalize_text(
            supplier
        )

        # Full legal name
        if supplier_norm in text:

            matches.append(
                {
                    "Supplier": supplier,
                    "Match Type": "Supplier name",
                    "Matched On": supplier
                }
            )

            continue


        # Short name / distinctive words
        words = supplier_norm.split()

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
                math.ceil(
                    len(meaningful_words) * 0.7
                )
            ):

                # Avoid known false-positive pattern
                # such as Ion Peak Trading vs IonPeak Semiconductor.

                if (
                    supplier
                    == "IonPeak Semiconductor Ltd."
                    and
                    (
                        "trading" in text
                        or
                        "broker" in text
                    )
                ):
                    continue

                matches.append(
                    {
                        "Supplier": supplier,
                        "Match Type": "Supplier name",
                        "Matched On": supplier
                    }
                )


    # --------------------------------------------------------
    # Geographic matching
    # --------------------------------------------------------

    geography_aliases = {

        "east delta": "Z01",
        "east delta site": "Z01",

        "harbor district": None,

        "zone z01": "Z01",
        "zone z02": "Z02",
        "zone z03": "Z03",
        "zone z04": "Z04",
        "zone z05": "Z05",
        "zone z06": "Z06",
        "zone z08": "Z08"
    }


    for alias, zone in geography_aliases.items():

        if alias in text and zone:

            for supplier in ZONE_SUPPLIERS.get(
                zone,
                []
            ):

                if supplier in network_nodes:

                    matches.append(
                        {
                            "Supplier": supplier,
                            "Match Type": "Geography",
                            "Matched On": alias
                        }
                    )


    # --------------------------------------------------------
    # Remove duplicates
    # --------------------------------------------------------

    unique = {}

    for match in matches:

        key = (
            match["Supplier"],
            match["Match Type"]
        )

        unique[key] = match


    return list(
        unique.values()
    )


# ============================================================
# DOWNSTREAM IMPACT
# ============================================================

def build_adjacency():

    adjacency = {
        node: []
        for node in network_nodes
    }

    for source, target in network_edges:

        adjacency.setdefault(
            source,
            []
        ).append(
            target
        )

    return adjacency


adjacency = build_adjacency()


def get_downstream_nodes(
    start_nodes
):

    affected = set()

    queue = list(
        start_nodes
    )

    while queue:

        current = queue.pop(0)

        if current in affected:
            continue

        affected.add(
            current
        )

        for downstream in adjacency.get(
            current,
            []
        ):

            if downstream not in affected:

                queue.append(
                    downstream
                )

    return affected


# ============================================================
# LABEL WRAPPING
# ============================================================

def wrap_label(
    text,
    width=20
):

    words = str(text).replace(
        " Ltd.",
        ""
    ).replace(
        " Technologies",
        ""
    ).split()

    lines = []
    current = ""

    for word in words:

        if len(
            current + " " + word
        ) <= width:

            if current:
                current += " "

            current += word

        else:

            if current:
                lines.append(
                    current
                )

            current = word

    if current:
        lines.append(
            current
        )

    return "<br>".join(
        lines
    )


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

    # ========================================================
    # UNCERTAINTY LAYER
    # ========================================================

    uncertainty_edges = [
        {
            "From": "Verdant Process Gases Ltd.",
            "To": "IonPeak Semiconductor Ltd.",
            "Status": "Reasonable inference",
            "Color": "#E6A700"
        },
        {
            "From": "Alder Bauxite Ltd.",
            "To": "Quartz Alloy Ltd.",
            "Status": "Unresolved hypothesis",
            "Color": "#E67E22"
        },
        {
            "From": "Solace Optics",
            "To": "Grove Battery Controls Ltd.",
            "Status": "Unresolved hypothesis",
            "Color": "#E67E22"
        }
    ]

    # Copy existing confirmed positions
    display_positions = positions.copy()

    # Place the three uncertainty nodes separately
    display_positions[
        "Verdant Process Gases Ltd."
    ] = (
        X_POSITIONS["Tier 3"],
        -7.0
    )

    display_positions[
        "Alder Bauxite Ltd."
    ] = (
        X_POSITIONS["Tier 3"],
        -8.4
    )

    display_positions[
        "Solace Optics"
    ] = (
        X_POSITIONS["Tier 2"],
        -7.0
    )


    # ========================================================
    # BOX GEOMETRY
    # ========================================================

    BOX_WIDTH = 2.55
    BOX_HEIGHT = 0.72


    def boundary_point(
        source,
        target
    ):

        x0, y0 = display_positions[source]
        x1, y1 = display_positions[target]

        dx = x1 - x0
        dy = y1 - y0

        if dx == 0 and dy == 0:
            return x0, y0

        tx = (
            (BOX_WIDTH / 2) / abs(dx)
            if dx != 0
            else float("inf")
        )

        ty = (
            (BOX_HEIGHT / 2) / abs(dy)
            if dy != 0
            else float("inf")
        )

        t = min(tx, ty)

        return (
            x0 + dx * t,
            y0 + dy * t
        )


    # ========================================================
    # COLORS
    # ========================================================

    tier_colors = {
        "Tier 3": "#D6EAF8",
        "Tier 2": "#D5F5E3",
        "Tier 1": "#FCF3CF",
        "NovaDrive": "#F1948A"
    }


    # ========================================================
    # FIGURE
    # ========================================================

    fig = go.Figure()


    # ========================================================
    # CONFIRMED EDGES
    # ========================================================

    for source, target in network_edges:

        if (
            source not in display_positions
            or target not in display_positions
        ):
            continue

        start_x, start_y = boundary_point(
            source,
            target
        )

        end_x, end_y = boundary_point(
            target,
            source
        )


        affected_edge = (
            (
                source in highlighted_nodes
                or source in selected_event_nodes
            )
            and
            (
                target in highlighted_nodes
                or target in selected_event_nodes
                or target == "NovaDrive Technologies"
            )
        )


        if affected_edge:

            edge_color = "#DC2626"
            edge_width = 3
            opacity = 0.95

        else:

            edge_color = "#777777"
            edge_width = 1.25

            opacity = (
                0.20
                if (
                    highlighted_nodes
                    or selected_event_nodes
                )
                else 0.60
            )


        # Line
        fig.add_trace(
            go.Scatter(
                x=[
                    start_x,
                    end_x
                ],
                y=[
                    start_y,
                    end_y
                ],
                mode="lines",
                line=dict(
                    color=edge_color,
                    width=edge_width
                ),
                opacity=opacity,
                hoverinfo="skip",
                showlegend=False
            )
        )


        # Arrowhead at box boundary
        fig.add_annotation(
            x=end_x,
            y=end_y,
            ax=start_x,
            ay=start_y,
            xref="x",
            yref="y",
            axref="x",
            ayref="y",
            text="",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=edge_width,
            arrowcolor=edge_color,
            opacity=opacity
        )


    # ========================================================
    # UNCERTAINTY / HYPOTHESIS EDGES
    # ========================================================

    for edge in uncertainty_edges:

        source = edge["From"]
        target = edge["To"]

        start_x, start_y = boundary_point(
            source,
            target
        )

        end_x, end_y = boundary_point(
            target,
            source
        )


        fig.add_trace(
            go.Scatter(
                x=[
                    start_x,
                    end_x
                ],
                y=[
                    start_y,
                    end_y
                ],
                mode="lines",
                line=dict(
                    color=edge["Color"],
                    width=2,
                    dash="dash"
                ),
                opacity=0.9,
                hoverinfo="text",
                text=edge["Status"],
                showlegend=False
            )
        )


        fig.add_annotation(
            x=end_x,
            y=end_y,
            ax=start_x,
            ay=start_y,
            xref="x",
            yref="y",
            axref="x",
            ayref="y",
            text="",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            arrowcolor=edge["Color"],
            opacity=0.9
        )


    # ========================================================
    # NODE BOXES
    # ========================================================

    all_display_nodes = list(
        display_positions.keys()
    )


    for node in all_display_nodes:

        x, y = display_positions[node]


        # Tier for uncertainty nodes
        if node == "Verdant Process Gases Ltd.":
            tier = "Tier 3"

        elif node == "Alder Bauxite Ltd.":
            tier = "Tier 3"

        elif node == "Solace Optics":
            tier = "Tier 2"

        else:
            tier = get_tier(node)


        # ----------------------------------------------------
        # Event source
        # ----------------------------------------------------

        if node in selected_event_nodes:

            fill_color = "#FCA5A5"
            border_color = "#991B1B"
            border_width = 4
            opacity = 1.0


        # ----------------------------------------------------
        # Event downstream
        # ----------------------------------------------------

        elif node in highlighted_nodes:

            fill_color = "#F87171"
            border_color = "#991B1B"
            border_width = 3
            opacity = 1.0


        # ----------------------------------------------------
        # Uncertainty node
        # ----------------------------------------------------

        elif node in [
            "Verdant Process Gases Ltd.",
            "Alder Bauxite Ltd.",
            "Solace Optics"
        ]:

            fill_color = "#F3F4F6"
            border_color = "#E67E22"
            border_width = 2
            opacity = 0.75


        # ----------------------------------------------------
        # NovaDrive
        # ----------------------------------------------------

        elif node == "NovaDrive Technologies":

            fill_color = "#F1948A"
            border_color = "#7F1D1D"
            border_width = 3
            opacity = 1.0


        # ----------------------------------------------------
        # Normal confirmed node
        # ----------------------------------------------------

        else:

            fill_color = tier_colors.get(
                tier,
                "#E5E7EB"
            )

            border_color = "#666666"
            border_width = 1.2

            if (
                highlighted_nodes
                or selected_event_nodes
            ):

                opacity = 0.25

            else:

                opacity = 1.0


        # ----------------------------------------------------
        # Box
        # ----------------------------------------------------

        fig.add_shape(
            type="rect",
            x0=x - BOX_WIDTH / 2,
            x1=x + BOX_WIDTH / 2,
            y0=y - BOX_HEIGHT / 2,
            y1=y + BOX_HEIGHT / 2,
            fillcolor=fill_color,
            line=dict(
                color=border_color,
                width=border_width
            ),
            opacity=opacity,
            layer="above"
        )


        # ----------------------------------------------------
        # Label
        # ----------------------------------------------------

        label = (
            node
            .replace(
                " Ltd.",
                ""
            )
            .replace(
                " Technologies",
                ""
            )
        )


        fig.add_annotation(
            x=x,
            y=y,
            text=label,
            showarrow=False,
            font=dict(
                size=11.5,
                color="#1F2937"
            ),
            opacity=opacity,
            align="center",
            xanchor="center",
            yanchor="middle"
        )


    # ========================================================
    # TIER HEADINGS
    # ========================================================

    max_y = max(
        p[1]
        for p in display_positions.values()
    )

    headings = [
        ("Tier 3", 0),
        ("Tier 2", 3.4),
        ("Tier 1", 6.8),
        ("NovaDrive", 10.2)
    ]


    for heading, x in headings:

        fig.add_annotation(
            x=x,
            y=max_y + 0.8,
            text=f"<b>{heading}</b>",
            showarrow=False,
            font=dict(
                size=20,
                color="#1F2937"
            )
        )


    # ========================================================
    # LEGEND
    # ========================================================

    fig.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="lines",
            line=dict(
                color="#E6A700",
                width=2,
                dash="dash"
            ),
            name="Reasonable inference"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="lines",
            line=dict(
                color="#E67E22",
                width=2,
                dash="dash"
            ),
            name="Unresolved hypothesis"
        )
    )


    # ========================================================
    # LAYOUT
    # ========================================================

    fig.update_layout(

        height=850,

        margin=dict(
            l=40,
            r=40,
            t=80,
            b=40
        ),

        plot_bgcolor="white",

        paper_bgcolor="white",

        xaxis=dict(
            visible=False,
            range=[
                -1.7,
                11.7
            ]
        ),

        yaxis=dict(
            visible=False,
            range=[
                min(
                    p[1]
                    for p in display_positions.values()
                ) - 0.8,

                max(
                    p[1]
                    for p in display_positions.values()
                ) + 1.5
            ]
        ),

        showlegend=True,

        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),

        hovermode=False
    )


    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displayModeBar": True,
            "scrollZoom": True
        }
    )


    # ========================================================
    # CAPTION
    # ========================================================

    if (
        highlighted_nodes
        or selected_event_nodes
    ):

        st.caption(
            "Orange = directly affected supplier. "
            "Red = downstream exposure. "
            "Faded nodes = not part of the affected path."
        )

    else:

        st.caption(
            "Solid lines = confirmed relationships. "
            "Dashed yellow = reasonable inference. "
            "Dashed orange = unresolved hypothesis."
        )

# ============================================================
# EXCEL DOWNLOAD
# ============================================================

def create_network_excel():

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        supplier_network.to_excel(
            writer,
            sheet_name="Confirmed Relationships",
            index=False
        )

        supplier_entities.to_excel(
            writer,
            sheet_name="Supplier Universe",
            index=False
        )

        summary = pd.DataFrame(
            {
                "Metric": [
                    "Confirmed relationships",
                    "Total supplier nodes",
                    "Tier-1 suppliers",
                    "Tier-2 suppliers",
                    "Tier-3 suppliers",
                    "Total nodes including NovaDrive"
                ],

                "Count": [
                    len(supplier_network),

                    len(
                        supplier_entities
                    ),

                    len(tier1_nodes),

                    len(tier2_nodes),

                    len(tier3_nodes),

                    len(network_nodes)
                ]
            }
        )

        summary.to_excel(
            writer,
            sheet_name="Network Summary",
            index=False
        )


    output.seek(0)

    return output


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(
    "NovaDrive CRO"
)

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

    st.title(
        "NovaDrive CRO Dashboard"
    )

    st.caption(
        "Supplier network visibility, risk prioritisation "
        "and event-driven management alerts"
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
        len(tier1_nodes)
    )

    col4.metric(
        "Management Alerts",
        len(event_alerts)
    )


    st.divider()


    # --------------------------------------------------------
    # NETWORK BREAKDOWN
    # --------------------------------------------------------

    st.subheader(
        "Supplier Network"
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Tier 1",
        len(tier1_nodes)
    )

    col2.metric(
        "Tier 2",
        len(tier2_nodes)
    )

    col3.metric(
        "Tier 3",
        len(tier3_nodes)
    )


    st.divider()


    # --------------------------------------------------------
    # ALERT SUMMARY
    # --------------------------------------------------------

    st.subheader(
        "Current Alert Summary"
    )

    col1, col2, col3 = st.columns(3)

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


    st.divider()

    st.info(
        "Use the navigation panel to investigate supplier "
        "relationships, risk context and event-driven alerts."
    )


# ============================================================
# SUPPLIER NETWORK
# ============================================================

elif page == "Supplier Network":

    st.title(
        "Supplier Network"
    )

    st.caption(
        "Interactive reconstruction of the confirmed "
        "NovaDrive supplier network"
    )


    # --------------------------------------------------------
    # SUPPLIER SELECTOR
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

    selected_event_nodes = set()


    if selected_supplier != "None":

        highlighted = get_downstream_nodes(
            [selected_supplier]
        )

        highlighted.discard(
            selected_supplier
        )

        selected_event_nodes.add(
            selected_supplier
        )


    # --------------------------------------------------------
    # GRAPH
    # --------------------------------------------------------

    show_network_graph(
        highlighted_nodes=highlighted,
        selected_event_nodes=selected_event_nodes
    )


    # --------------------------------------------------------
    # SUPPLIER IMPACT
    # --------------------------------------------------------

    if selected_supplier != "None":

        st.divider()

        st.subheader(
            f"Supplier Impact — {selected_supplier}"
        )

        col1, col2 = st.columns(2)

        col1.metric(
            "Tier",
            get_tier(
                selected_supplier
            )
        )

        col2.metric(
            "Downstream Nodes",
            len(highlighted)
        )


        downstream_display = sorted(
            highlighted
        )

        if downstream_display:

            st.write(
                "**Confirmed downstream network:**"
            )

            for node in downstream_display:

                st.write(
                    f"- {node} "
                    f"({get_tier(node)})"
                )

        else:

            st.info(
                "No confirmed downstream dependency identified."
            )


    # --------------------------------------------------------
    # EXCEL
    # --------------------------------------------------------

    st.divider()

    st.subheader(
        "Network Data"
    )

    st.download_button(
        label="Download Network Excel",
        data=create_network_excel(),
        file_name="NovaDrive_Point1_Network_Reconstruction.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )

    st.dataframe(
        supplier_network,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# RISK ASSESSMENT
# ============================================================

elif page == "Risk Assessment":

    st.title(
        "Risk Assessment"
    )

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

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Tier 1",
        len(tier1_nodes)
    )

    col2.metric(
        "Tier 2",
        len(tier2_nodes)
    )

    col3.metric(
        "Tier 3",
        len(tier3_nodes)
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

    st.title(
        "Events & Alerts"
    )

    st.caption(
        "Match external events to the confirmed network "
        "and visualise the resulting exposure"
    )


    existing_tab, new_tab = st.tabs(
        [
            "Existing Alerts",
            "Analyze New Event"
        ]
    )


    # ========================================================
    # EXISTING ALERTS
    # ========================================================

    with existing_tab:

        st.subheader(
            "Current Management Alerts"
        )


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
                .unique()
                .tolist()
            )

            selected_event = st.selectbox(
                "Select an event",
                event_options
            )


            # ------------------------------------------------
            # IMPORTANT:
            # Get ALL alert rows belonging to this event.
            # EV-001 therefore correctly gives all four
            # affected suppliers.
            # ------------------------------------------------

            selected_event_rows = event_alerts[
                event_alerts[
                    "Event ID"
                ]
                .astype(str)
                ==
                selected_event
            ]


            affected_suppliers = []


            # ------------------------------------------------
            # Affected Supplier column
            # ------------------------------------------------

            if "Affected Supplier" in event_alerts.columns:

                for value in selected_event_rows[
                    "Affected Supplier"
                ].dropna():

                    value_text = normalize_text(
                        value
                    )

                    for supplier in network_nodes:

                        if supplier == "NovaDrive Technologies":
                            continue

                        if normalize_text(
                            supplier
                        ) in value_text:

                            if supplier not in affected_suppliers:

                                affected_suppliers.append(
                                    supplier
                                )


            # ------------------------------------------------
            # Also run event matcher against event text
            # ------------------------------------------------

            event_text_parts = []

            for _, row in selected_event_rows.iterrows():

                for field in [
                    "Title",
                    "Event Detail"
                ]:

                    if field in row.index:

                        event_text_parts.append(
                            str(
                                row[field]
                            )
                        )


            event_text = " ".join(
                event_text_parts
            )


            matches = match_new_event(
                event_text
            )


            for match in matches:

                supplier = match[
                    "Supplier"
                ]

                if supplier not in affected_suppliers:

                    affected_suppliers.append(
                        supplier
                    )


            # ------------------------------------------------
            # Downstream impact
            # ------------------------------------------------

            affected_network = get_downstream_nodes(
                affected_suppliers
            )

            downstream_only = (
                affected_network
                - set(affected_suppliers)
            )


            # ------------------------------------------------
            # GRAPH
            # ------------------------------------------------

            st.subheader(
                "Network Impact"
            )

            show_network_graph(
                highlighted_nodes=downstream_only,
                selected_event_nodes=affected_suppliers
            )


            # ------------------------------------------------
            # ALERT DETAILS
            # ------------------------------------------------

            st.subheader(
                "Management Alert"
            )


            # Display the first alert row as the primary
            # management alert.

            selected_row = (
                selected_event_rows.iloc[0]
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

                if field in selected_row.index:

                    value = selected_row[field]

                    if pd.notna(value):

                        st.markdown(
                            f"**{field}:** {value}"
                        )


            # ------------------------------------------------
            # AFFECTED NETWORK
            # ------------------------------------------------

            if affected_suppliers:

                st.divider()

                st.subheader(
                    "Affected Confirmed Network"
                )


                for supplier in affected_suppliers:

                    st.write(
                        f"🟠 **{supplier}** — "
                        f"{get_tier(supplier)}"
                    )


                for node in sorted(
                    downstream_only
                ):

                    st.write(
                        f"🔴 {node} — "
                        f"{get_tier(node)}"
                    )


            else:

                st.info(
                    "No confirmed supplier node was identified "
                    "from this event. Treat this as an external "
                    "exposure requiring verification."
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
            "The platform will match it against confirmed "
            "supplier names, facilities and network geographies."
        )


        new_event = st.text_area(
            "Event description",
            placeholder=(
                "Example: Fire reported at SITE-081 "
                "affecting production..."
            ),
            height=150
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
                        "No confirmed supplier, facility or "
                        "network geography was identified."
                    )

                    st.info(
                        "This should be treated as an "
                        "**Unassessed External Exposure**. "
                        "The platform deliberately does not "
                        "invent a supplier relationship."
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


                    # ----------------------------------------
                    # MATCH
                    # ----------------------------------------

                    st.success(
                        f"Matched {len(matched_suppliers)} "
                        f"confirmed supplier node(s)."
                    )


                    st.subheader(
                        "Event Match"
                    )


                    st.dataframe(
                        pd.DataFrame(
                            matches
                        ),
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
                    # SUMMARY
                    # ----------------------------------------

                    st.subheader(
                        "Impact Summary"
                    )


                    col1, col2, col3 = st.columns(3)


                    col1.metric(
                        "Directly Matched Nodes",
                        len(
                            matched_suppliers
                        )
                    )


                    col2.metric(
                        "Downstream Nodes Exposed",
                        len(
                            downstream_only
                        )
                    )


                    col3.metric(
                        "NovaDrive Exposure",
                        (
                            "Yes"
                            if
                            "NovaDrive Technologies"
                            in affected_network
                            else
                            "No"
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


                    # ----------------------------------------
                    # MANAGEMENT INTERPRETATION
                    # ----------------------------------------

                    st.divider()

                    st.subheader(
                        "Management Interpretation"
                    )


                    if (
                        "NovaDrive Technologies"
                        in affected_network
                    ):

                        st.error(
                            "The matched supplier sits on a "
                            "confirmed path to NovaDrive. "
                            "The event therefore has potential "
                            "direct network relevance."
                        )


                        st.markdown(
                            """
**Recommended next action**

1. Verify whether the event caused an actual production or shipment impact.
2. Check affected facility / material availability.
3. Assess inventory and time-to-impact.
4. Initiate alternate-supplier review if the exposure is material.
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

    st.title(
        "Alternate Suppliers"
    )

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
