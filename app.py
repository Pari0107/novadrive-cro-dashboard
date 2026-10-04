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

    # Part 2 supplier risk scorecard
    supplier_risk = pd.read_csv(
        "data/novadrive_supplier_risk_scorecard.csv"
    )

    return (
        supplier_network,
        supplier_entities,
        event_alerts,
        supplier_risk
    )


supplier_network, supplier_entities, event_alerts, supplier_risk = load_data()


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
# ALL ORIGINAL EVENT FEED STATUS
# ============================================================
#
# These are the original event-feed cases.
# They are shown in Existing Alerts even when they did not
# become management alerts.
#
# This preserves the distinction between:
#   - event exists
#   - event is relevant
#   - event becomes a management alert
# ============================================================

ALL_EVENT_STATUS = {

    "EV-001": {
        "Title": "East Delta flood watch",
        "Status": "Network-linked event",
        "Impact": "Confirmed potential geographic exposure",
        "Explanation": (
            "The flood watch is geographically relevant to the "
            "confirmed Z01 supplier network. No physical damage "
            "or production shutdown was confirmed at the time "
            "of the event."
        ),
        "Action": (
            "Verify facility conditions, production status, "
            "inventory and logistics impact."
        )
    },

    "EV-002": {
        "Title": "Trade-wire repeats East Delta flood bulletin",
        "Status": "Duplicate evidence",
        "Impact": "No additional network impact",
        "Explanation": (
            "This event repeats the same underlying flood bulletin "
            "as EV-001 and carries the same source family. It is "
            "therefore not treated as an independent risk event."
        ),
        "Action": (
            "Use EV-001 as the authoritative event and do not "
            "double-count the signal."
        )
    },

    "EV-003": {
        "Title": "Meridian financing pressure",
        "Status": "Network-linked event",
        "Impact": "Active supplier risk",
        "Explanation": (
            "Meridian Dielectrics is a confirmed upstream supplier "
            "for Delta Capacitor Works. The reported financing "
            "pressure therefore has direct supplier-network relevance."
        ),
        "Action": (
            "Verify Meridian's financial and production continuity "
            "and assess C20 exposure."
        )
    },

    "EV-004": {
        "Title": "Ion Peak Trading insolvency",
        "Status": "Entity mismatch",
        "Impact": "No confirmed NovaDrive network impact",
        "Explanation": (
            "The event concerns Ion Peak Trading, not IonPeak "
            "Semiconductor Ltd. The two entities must not be treated "
            "as the same supplier."
        ),
        "Action": (
            "No NovaDrive supplier action unless independent evidence "
            "links the event to IonPeak Semiconductor."
        )
    },

    "EV-005": {
        "Title": "Archived port strike repost",
        "Status": "Historical / stale event",
        "Impact": "No current network impact",
        "Explanation": (
            "The reported port strike relates to a historical period "
            "and had already ended. It is therefore not treated as "
            "a current NovaDrive risk event."
        ),
        "Action": (
            "No immediate action. Monitor only if a current logistics "
            "event emerges."
        )
    },

    "EV-007": {
        "Title": "Jade HQ relocation",
        "Status": "Network context match",
        "Impact": "Monitor; production unaffected",
        "Explanation": (
            "Jade Printed Circuits is a confirmed supplier in the "
            "NovaDrive network, but the reported relocation concerned "
            "the headquarters. Production remained at SITE-081."
        ),
        "Action": (
            "Monitor SITE-081 production and shipment continuity."
        )
    },

    "EV-009": {
        "Title": "Delta packaging allegation",
        "Status": "Entity mismatch",
        "Impact": "No confirmed NovaDrive network impact",
        "Explanation": (
            "The allegation concerns Delta Consumer Plastics, not "
            "Delta Capacitor Works Ltd. The event therefore cannot "
            "be attributed to the NovaDrive supplier."
        ),
        "Action": (
            "No supplier action unless independent evidence identifies "
            "Delta Capacitor Works as the affected entity."
        )
    },

    "EV-010": {
        "Title": "Gulf Arc port congestion",
        "Status": "Unassessed external exposure",
        "Impact": "No confirmed network match",
        "Explanation": (
            "Current congestion was reported at Gulf Arc, but the "
            "available evidence does not establish a confirmed link "
            "to a NovaDrive supplier or facility."
        ),
        "Action": (
            "Check whether confirmed supplier shipments depend on "
            "Gulf Arc departures and assess shipment-specific exposure."
        )
    }
}


# ============================================================
# EXAMPLE NEW EVENTS
# ============================================================

EXAMPLE_EVENTS = [

    (
        "SITE-081 — Jade disruption",
        "A major fire has been reported at SITE-081, causing "
        "the facility to suspend production of printed circuit substrates."
    ),

    (
        "SITE-074 — IonPeak disruption",
        "A production disruption has been reported at SITE-074, "
        "affecting power semiconductor die manufacturing."
    ),

    (
        "SITE-088 — Kestrel disruption",
        "A serious equipment failure at SITE-088 has halted "
        "microcontroller production for several days."
    ),

    (
        "SITE-116 — Orion disruption",
        "A major disruption at SITE-116 has temporarily stopped "
        "ceramic substrate production."
    ),

    (
        "SITE-137 — Rill disruption",
        "Flooding at SITE-137 has disrupted connector manufacturing "
        "and outbound shipments."
    ),

    (
        "SITE-179 — Xenon disruption",
        "A raw-material supply disruption is affecting production "
        "at SITE-179, with resin deliveries suspended."
    ),

    (
        "SITE-102 — Meridian disruption",
        "A severe disruption at SITE-102 has halted dielectric "
        "film production."
    ),

    (
        "Westport — unrelated event",
        "A fire at a manufacturing facility in Westport has "
        "temporarily halted production of industrial sensors."
    )
]


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

tier1_order = sorted(
    tier1_nodes
)

tier1_position = {
    node: i
    for i, node in enumerate(tier1_order)
}


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
# POSITIONS
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

        if supplier_norm in text:

            matches.append(
                {
                    "Supplier": supplier,
                    "Match Type": "Supplier name",
                    "Matched On": supplier
                }
            )

            continue


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
# RISK / MANAGEMENT HELPERS
# ============================================================

# Established supplier-risk classifications that are already
# present in the Part 3 management-alert output.

KNOWN_SUPPLIER_RISK = {

    "IonPeak Semiconductor Ltd.": "CRITICAL",

    "Jade Printed Circuits Ltd.": "HIGH",

    "Orion Ceramics Ltd.": "MEDIUM",

    "Umber Silicon Carbide Ltd.": "CRITICAL",

    "Meridian Dielectrics Ltd.": "CRITICAL"
}


def risk_color(level):

    level = str(level).upper()

    if level == "CRITICAL":
        return "#B91C1C"

    if level == "HIGH":
        return "#EA580C"

    if level == "MEDIUM":
        return "#D97706"

    if level == "LOW":
        return "#16A34A"

    return "#6B7280"

# Risk levels for the original event-feed cases
EXISTING_EVENT_RISK = {
    "EV-001": "MEDIUM",
    "EV-002": "LOW",
    "EV-003": "HIGH",
    "EV-004": "LOW",
    "EV-005": "LOW",
    "EV-007": "LOW",
    "EV-009": "LOW",
    "EV-010": "LOW",
}

def show_risk_badge(
    label,
    level
):

    color = risk_color(
        level
    )

    st.markdown(
        f"""
        <div style="
            border-left: 7px solid {color};
            background-color: {color}18;
            padding: 14px 18px;
            border-radius: 7px;
            margin-bottom: 12px;
        ">
            <div style="
                font-size: 13px;
                color: #6B7280;
                margin-bottom: 4px;
            ">
                {label}
            </div>
            <div style="
                font-size: 25px;
                font-weight: 700;
                color: {color};
            ">
                {level}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def calculate_network_impact_risk(
    affected_suppliers,
    downstream_only
):

    if not affected_suppliers:
        return "LOW"

    tiers = [
        get_tier(
            supplier
        )
        for supplier in affected_suppliers
    ]

    tier1_downstream = [
        node
        for node in downstream_only
        if get_tier(node) == "Tier 1"
    ]

    # Broad upstream exposure or a Tier-3 source
    if (
        "Tier 3" in tiers
        or
        len(tier1_downstream) >= 2
    ):
        return "CRITICAL"

    # Confirmed Tier-2 disruption reaching production
    if "Tier 2" in tiers:
        return "HIGH"

    # Direct Tier-1 exposure
    if "Tier 1" in tiers:
        return "MEDIUM"

    return "LOW"


def get_supplier_risk(
    supplier
):

    return KNOWN_SUPPLIER_RISK.get(
        supplier,
        None
    )


def get_recommended_action(
    risk_level
):

    risk_level = str(
        risk_level
    ).upper()

    if risk_level == "CRITICAL":

        return (
            "Immediate verification: confirm production/shipment "
            "impact, assess inventory and time-to-impact, and "
            "initiate contingency / alternate-supplier review."
        )

    if risk_level == "HIGH":

        return (
            "Verify production and shipment continuity, assess "
            "inventory exposure, and prepare alternate-supplier "
            "options if disruption persists."
        )

    if risk_level == "MEDIUM":

        return (
            "Verify the reported event, monitor production and "
            "shipments, and assess whether the exposure could "
            "develop into a supply interruption."
        )

    return (
        "No confirmed network action required. Continue monitoring "
        "if the external situation develops."
    )


def show_risk_legend():

    st.markdown(
        """
        **Risk interpretation**

        🔴 **Critical** — immediate management attention  
        🟠 **High** — active investigation / contingency planning  
        🟡 **Medium** — verify and monitor  
        🟢 **Low** — limited or no confirmed network impact
        """
    )


# ============================================================
# EDGE / GRAPH LABEL HELPERS
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


    display_positions = positions.copy()


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

        t = min(
            tx,
            ty
        )

        return (
            x0 + dx * t,
            y0 + dy * t
        )


    tier_colors = {

        "Tier 3": "#D6EAF8",

        "Tier 2": "#D5F5E3",

        "Tier 1": "#FCF3CF",

        "NovaDrive": "#F1948A"
    }


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


        if (
            highlighted_nodes
            or selected_event_nodes
        ):

            uncertainty_opacity = 0.12

        else:

            uncertainty_opacity = 0.9


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
                opacity=uncertainty_opacity,
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
            opacity=uncertainty_opacity
        )


    # ========================================================
    # NODE BOXES
    # ========================================================

    all_display_nodes = list(
        display_positions.keys()
    )


    for node in all_display_nodes:

        x, y = display_positions[node]


        if node == "Verdant Process Gases Ltd.":

            tier = "Tier 3"

        elif node == "Alder Bauxite Ltd.":

            tier = "Tier 3"

        elif node == "Solace Optics":

            tier = "Tier 2"

        else:

            tier = get_tier(node)


        if node in selected_event_nodes:

            fill_color = "#FCA5A5"
            border_color = "#991B1B"
            border_width = 4
            opacity = 1.0


        elif node in highlighted_nodes:

            fill_color = "#F87171"
            border_color = "#991B1B"
            border_width = 3
            opacity = 1.0


        elif node in [
            "Verdant Process Gases Ltd.",
            "Alder Bauxite Ltd.",
            "Solace Optics"
        ]:

            fill_color = "#F3F4F6"
            border_color = "#E67E22"
            border_width = 2

            if (
                highlighted_nodes
                or selected_event_nodes
            ):

                opacity = 0.18

            else:

                opacity = 0.75


        elif node == "NovaDrive Technologies":

            fill_color = "#F1948A"
            border_color = "#7F1D1D"
            border_width = 3
            opacity = 1.0


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
    # UNCERTAINTY LEGEND
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

        height=1000,

        margin=dict(
            l=60,
            r=60,
            t=120,
            b=100
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
            x=1,
            font=dict(
                color="#1F2937",
                size=13
            )
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
                    len(supplier_entities),
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


    show_network_graph(
        highlighted_nodes=highlighted,
        selected_event_nodes=selected_event_nodes
    )


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
        "Supplier risk prioritisation based on the Part 2 "
        "risk scorecard"
    )


    # --------------------------------------------------------
    # CONFIRMED NETWORK ONLY
    # --------------------------------------------------------

    excluded_risk_entities = [
        "Verdant Process Gases Ltd.",
        "Solace Optics Ltd."
    ]

    risk_df = supplier_risk[
        ~supplier_risk["Legal Name"].isin(
            excluded_risk_entities
        )
    ].copy()


    # --------------------------------------------------------
    # KEY METRICS
    # --------------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Suppliers Assessed",
        len(risk_df)
    )

    col2.metric(
        "Critical",
        int(
            (
                risk_df["Risk_Category"]
                .astype(str)
                .str.upper()
                == "CRITICAL"
            ).sum()
        )
    )

    col3.metric(
        "High",
        int(
            (
                risk_df["Risk_Category"]
                .astype(str)
                .str.upper()
                == "HIGH"
            ).sum()
        )
    )

    col4.metric(
        "Medium",
        int(
            (
                risk_df["Risk_Category"]
                .astype(str)
                .str.upper()
                == "MEDIUM"
            ).sum()
        )
    )


    st.divider()


    # --------------------------------------------------------
    # RISK METHODOLOGY
    # --------------------------------------------------------

    with st.expander(
        "How is supplier risk calculated?"
    ):

        st.markdown(
            """
### Composite Risk Score

The supplier risk score combines four dimensions:

- **30% — Network Exposure**
- **25% — Financial Risk**
- **25% — Operational Risk**
- **20% — Geographic / External Risk**

Each dimension is converted to a 0–100 risk score.

**Higher score = higher supplier risk.**

Evidence confidence is reported separately from risk. Missing
financial information is not automatically treated as low risk;
the available dimensions are reweighted where required.

### Risk Categories

| Composite Score | Risk Category |
|---:|---|
| ≥ 70 | 🔴 Critical |
| 55–69.99 | 🟠 High |
| 45–54.99 | 🟡 Medium |
| < 45 | 🟢 Low |
"""
        )


    st.divider()


    # --------------------------------------------------------
    # RISK PRIORITY TABLE
    # --------------------------------------------------------

    st.subheader(
        "Supplier Risk Priority"
    )

    display_cols = [
        "Legal Name",
        "Tier",
        "Composite_Risk_Score",
        "Risk_Category",
        "Financial_Risk_Score",
        "Operational_Risk_Score",
        "Geo_Risk_Score",
        "Network_Exposure_Score",
        "Evidence_Confidence (%)"
    ]

    display_df = risk_df[
        display_cols
    ].copy()

    display_df = display_df.sort_values(
        "Composite_Risk_Score",
        ascending=False
    )

    display_df["Composite_Risk_Score"] = (
        display_df["Composite_Risk_Score"]
        .round(1)
    )

    display_df["Financial_Risk_Score"] = (
        display_df["Financial_Risk_Score"]
        .round(1)
    )

    display_df["Operational_Risk_Score"] = (
        display_df["Operational_Risk_Score"]
        .round(1)
    )

    display_df["Geo_Risk_Score"] = (
        display_df["Geo_Risk_Score"]
        .round(1)
    )

    display_df["Network_Exposure_Score"] = (
        display_df["Network_Exposure_Score"]
        .round(1)
    )

    display_df["Evidence_Confidence (%)"] = (
        display_df["Evidence_Confidence (%)"]
        .round(1)
    )


    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )


    st.divider()


    # --------------------------------------------------------
    # SUPPLIER DETAIL
    # --------------------------------------------------------

    st.subheader(
        "Inspect Supplier Risk"
    )

    supplier_options = (
        risk_df["Legal Name"]
        .sort_values()
        .tolist()
    )

    selected_risk_supplier = st.selectbox(
        "Select a supplier",
        supplier_options
    )

    selected_row = risk_df[
        risk_df["Legal Name"]
        == selected_risk_supplier
    ].iloc[0]


    # --------------------------------------------------------
    # RISK HEADER
    # --------------------------------------------------------

    # --------------------------------------------------------
    # RISK SUMMARY
    # --------------------------------------------------------
    
    risk_level = str(
        selected_row["Risk_Category"]
    ).upper()
    
    
    if risk_level == "CRITICAL":
    
        st.error(
            f"🔴 **CRITICAL RISK**  |  "
            f"{selected_risk_supplier}  |  "
            f"{selected_row['Tier']}"
        )
    
    elif risk_level == "HIGH":
    
        st.warning(
            f"🟠 **HIGH RISK**  |  "
            f"{selected_risk_supplier}  |  "
            f"{selected_row['Tier']}"
        )
    
    elif risk_level == "MEDIUM":
    
        st.warning(
            f"🟡 **MEDIUM RISK**  |  "
            f"{selected_risk_supplier}  |  "
            f"{selected_row['Tier']}"
        )
    
    else:
    
        st.success(
            f"🟢 **LOW RISK**  |  "
            f"{selected_risk_supplier}  |  "
            f"{selected_row['Tier']}"
        )
    
    
    st.metric(
        "Composite Risk Score",
        f'{selected_row["Composite_Risk_Score"]:.1f}'
    )
    
    
    # --------------------------------------------------------
    # COMPONENT RISK SCORES
    # --------------------------------------------------------
    
    st.subheader(
        "Risk Dimension Breakdown"
    )
    
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric(
        "Network Exposure",
        f'{selected_row["Network_Exposure_Score"]:.1f}'
    )
    
    col2.metric(
        "Financial Risk",
        (
            "Not available"
            if pd.isna(
                selected_row["Financial_Risk_Score"]
            )
            else
            f'{selected_row["Financial_Risk_Score"]:.1f}'
        )
    )
    
    col3.metric(
        "Operational Risk",
        f'{selected_row["Operational_Risk_Score"]:.1f}'
    )
    
    col4.metric(
        "Geographic Risk",
        f'{selected_row["Geo_Risk_Score"]:.1f}'
    )
    
    
    # --------------------------------------------------------
    # EVIDENCE CONFIDENCE
    # --------------------------------------------------------
    
    st.write(
        f'**Evidence Confidence:** '
        f'{selected_row["Evidence_Confidence (%)"]:.1f}%'
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
    # EXISTING EVENTS
    # ========================================================

    with existing_tab:

        st.subheader(
            "Current Event Feed"
        )

        st.write(
            "All events from the original event feed are shown here. "
            "Only validated, network-relevant events become management "
            "alerts."
        )


        # ----------------------------------------------------
        # All 8 event IDs
        # ----------------------------------------------------

        all_event_ids = list(
            ALL_EVENT_STATUS.keys()
        )


        selected_event = st.selectbox(
            "Select an event",
            all_event_ids,
            format_func=lambda x:
                f"{x} — {ALL_EVENT_STATUS[x]['Title']}"
        )


        metadata = ALL_EVENT_STATUS[
            selected_event
        ]


        # ----------------------------------------------------
        # Existing management-alert rows for event
        # ----------------------------------------------------

        selected_event_rows = event_alerts[
            event_alerts[
                "Event ID"
            ]
            .astype(str)
            ==
            selected_event
        ]


        # ----------------------------------------------------
        # CASE STATUS
        # ----------------------------------------------------

        st.divider()

        st.subheader(
            "Event Assessment"
        )


        status = metadata[
            "Status"
        ]

        impact = metadata[
            "Impact"
        ]


        if selected_event_rows.empty:

            if status == "Duplicate evidence":

                st.warning(
                    f"**{status}** — {impact}"
                )

            elif status in [
                "Entity mismatch",
                "Historical / stale event"
            ]:

                st.info(
                    f"**{status}** — {impact}"
                )

            else:

                st.info(
                    f"**{status}** — {impact}"
                )


        else:

            st.success(
                f"**{status}** — {impact}"
            )


        st.markdown(
            f"**Why this classification?**  \n"
            f"{metadata['Explanation']}"
        )


        # ----------------------------------------------------
        # MANAGEMENT ALERT RISK
        # ----------------------------------------------------


        st.divider()

        st.subheader(
            "Risk & Management Priority"
        )

        # Event risk comes from the authoritative event classification
        event_risk = EXISTING_EVENT_RISK.get(
            selected_event,
            "LOW"
        )

        # Show the risk of the event itself
        col1, col2 = st.columns(2)

        with col1:

            show_risk_badge(
                "Management Alert Risk",
                event_risk
            )

        # ----------------------------------------------------
        # SUPPLIER RISK
        # ----------------------------------------------------

        # Use the known network mapping for the original events
        known_event_suppliers = {

            "EV-001": [
                "IonPeak Semiconductor Ltd.",
                "Jade Printed Circuits Ltd.",
                "Orion Ceramics Ltd.",
                "Umber Silicon Carbide Ltd."
            ],

            "EV-003": [
                "Meridian Dielectrics Ltd."
            ],

            "EV-007": [
                "Jade Printed Circuits Ltd."
            ]
        }

        risk_suppliers = known_event_suppliers.get(
            selected_event,
            []
        )

        supplier_risks = []

        for supplier in risk_suppliers:

            supplier_risk = get_supplier_risk(
                supplier
            )

            if supplier_risk:

                supplier_risks.append(
                    (supplier, supplier_risk)
                )

        with col2:

            if supplier_risks:

                highest_risk = max(
                    supplier_risks,
                    key=lambda x: {
                        "CRITICAL": 4,
                        "HIGH": 3,
                        "MEDIUM": 2,
                        "LOW": 1
                    }.get(x[1], 0)
                )[1]

                show_risk_badge(
                    "Highest Supplier Risk",
                    highest_risk
                )

            else:

                show_risk_badge(
                    "Supplier Risk",
                    "LOW"
                )

        # ----------------------------------------------------
        # SUPPLIER-BY-SUPPLIER BREAKDOWN
        # ----------------------------------------------------

        if supplier_risks:

            st.markdown(
                "**Affected Supplier Risk:**"
            )

            for supplier, supplier_risk in supplier_risks:

                show_risk_badge(
                    supplier,
                    supplier_risk
                )

        # ----------------------------------------------------
        # MANAGEMENT ACTION
        # ----------------------------------------------------

        if not selected_event_rows.empty:

            for _, alert_row in selected_event_rows.iterrows():

                affected_supplier = alert_row.get(
                    "Affected Supplier",
                    "—"
                )

                if (
                    "Next Action"
                    in alert_row.index
                    and
                    pd.notna(
                        alert_row["Next Action"]
                    )
                ):

                    st.markdown(
                        f"**Recommended Action for "
                        f"{affected_supplier}:** "
                        f"{alert_row['Next Action']}"
                    )

        else:

            st.markdown(
                f"**Recommended Action:** "
                f"{metadata['Action']}"
            )

        # ----------------------------------------------------
        # NETWORK VISUALISATION
        # ----------------------------------------------------

        affected_suppliers = []


        if not selected_event_rows.empty:

            if (
                "Affected Supplier"
                in selected_event_rows.columns
            ):

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


        # Search original event text too.
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


        # For the three network-linked cases,
        # use the known original event mapping.

        known_event_suppliers = {

            "EV-001": [
                "IonPeak Semiconductor Ltd.",
                "Jade Printed Circuits Ltd.",
                "Orion Ceramics Ltd.",
                "Umber Silicon Carbide Ltd."
            ],

            "EV-003": [
                "Meridian Dielectrics Ltd."
            ],

            "EV-007": [
                "Jade Printed Circuits Ltd."
            ]
        }


        for supplier in known_event_suppliers.get(
            selected_event,
            []
        ):

            if supplier not in affected_suppliers:

                affected_suppliers.append(
                    supplier
                )


        affected_network = get_downstream_nodes(
            affected_suppliers
        )


        downstream_only = (
            affected_network
            - set(affected_suppliers)
        )


        if affected_suppliers:

            st.divider()

            st.subheader(
                "Network Impact"
            )


            show_network_graph(
                highlighted_nodes=downstream_only,
                selected_event_nodes=affected_suppliers
            )


        else:

            st.divider()

            st.subheader(
                "Network Impact"
            )

            st.info(
                "No confirmed supplier relationship is associated "
                "with this event, so no network chain is highlighted."
            )


        # ----------------------------------------------------
        # ORIGINAL ALERT DATA
        # ----------------------------------------------------

        if not selected_event_rows.empty:

            st.divider()

            st.subheader(
                "Management Alert Details"
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

                if field in selected_event_rows.columns:

                    values = (
                        selected_event_rows[field]
                        .dropna()
                        .astype(str)
                        .unique()
                    )

                    if len(values) > 0:

                        st.markdown(
                            f"**{field}:** "
                            f"{' | '.join(values)}"
                        )


        # ----------------------------------------------------
        # ALL MANAGEMENT ALERTS TABLE
        # ----------------------------------------------------

        st.divider()

        st.subheader(
            "Management Alerts Generated"
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
            "The platform will match it against confirmed supplier "
            "names, facilities and network geographies."
        )


        # ----------------------------------------------------
        # EXAMPLE CASES
        # ----------------------------------------------------

        st.markdown("### Try an example")
        
        # Store the selected example in session state
        if "new_event_input" not in st.session_state:
            st.session_state["new_event_input"] = ""
        
        # Display the examples as clickable boxes
        cols = st.columns(2)
        
        for i, (label, description) in enumerate(EXAMPLE_EVENTS):
        
            with cols[i % 2]:
        
                if st.button(
                    label,
                    key=f"example_event_{i}",
                    use_container_width=True
                ):
                    st.session_state["new_event_input"] = description
                    st.rerun()


        # ----------------------------------------------------
        # INPUT
        # ----------------------------------------------------

        event_text = st.text_area(
            "Event description",
            key="new_event_input",
            height=130,
            placeholder="Describe an external event..."
        )


        analyze = st.button(
            "Analyze Event",
            type="primary"
        )


        if analyze:

            if not event_text.strip():

                st.warning(
                    "Please enter an event description."
                )

            else:

                matches = match_new_event(
                    event_text
                )


                # =================================================
                # NO MATCH
                # =================================================

                if not matches:

                    st.warning(
                        "No confirmed supplier, facility or "
                        "network geography was identified."
                    )


                    show_risk_badge(
                        "Network Risk",
                        "LOW"
                    )


                    st.info(
                        "This is an **Unassessed External Exposure**. "
                        "The platform deliberately does not invent "
                        "a supplier relationship."
                    )


                    st.markdown(
                        "**Recommended Action:** "
                        "No confirmed network action. Verify the "
                        "event independently if it appears relevant "
                        "to NovaDrive's logistics or supply base."
                    )


                # =================================================
                # MATCH FOUND
                # =================================================

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


                    # ---------------------------------------------
                    # MATCH
                    # ---------------------------------------------

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


                    # ---------------------------------------------
                    # NETWORK GRAPH
                    # ---------------------------------------------

                    st.subheader(
                        "Network Impact"
                    )


                    show_network_graph(
                        highlighted_nodes=downstream_only,
                        selected_event_nodes=matched_suppliers
                    )


                    # ---------------------------------------------
                    # RISK ASSESSMENT
                    # ---------------------------------------------

                    st.divider()

                    st.subheader(
                        "Risk Assessment"
                    )


                    network_risk = calculate_network_impact_risk(
                        matched_suppliers,
                        downstream_only
                    )


                    risk_cols = st.columns(
                        2
                    )


                    with risk_cols[0]:

                        show_risk_badge(
                            "Event / Network Impact Risk",
                            network_risk
                        )


                    # If an established supplier-risk
                    # classification exists, show it separately.

                    known_risks = []

                    for supplier in matched_suppliers:

                        supplier_risk = get_supplier_risk(
                            supplier
                        )

                        if supplier_risk:

                            known_risks.append(
                                (
                                    supplier,
                                    supplier_risk
                                )
                            )


                    with risk_cols[1]:

                        if known_risks:

                            # Use highest known supplier risk
                            # for the headline badge.

                            rank = {
                                "LOW": 1,
                                "MEDIUM": 2,
                                "HIGH": 3,
                                "CRITICAL": 4
                            }

                            highest_supplier_risk = max(
                                known_risks,
                                key=lambda x:
                                rank.get(
                                    x[1],
                                    0
                                )
                            )[1]


                            show_risk_badge(
                                "Established Supplier Risk",
                                highest_supplier_risk
                            )

                        else:

                            st.markdown(
                                """
                                <div style="
                                    border-left: 7px solid #9CA3AF;
                                    background-color: #9CA3AF18;
                                    padding: 14px 18px;
                                    border-radius: 7px;
                                    margin-bottom: 12px;
                                ">
                                    <div style="
                                        font-size: 13px;
                                        color: #6B7280;
                                        margin-bottom: 4px;
                                    ">
                                        Established Supplier Risk
                                    </div>
                                    <div style="
                                        font-size: 25px;
                                        font-weight: 700;
                                        color: #6B7280;
                                    ">
                                        Not assessed
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )


                    st.caption(
                        "Event / Network Impact Risk reflects the "
                        "confirmed network exposure identified by "
                        "this event. Established Supplier Risk is "
                        "shown separately where an existing supplier "
                        "risk classification is available."
                    )


                    # ---------------------------------------------
                    # SUPPLIER RISK DETAILS
                    # ---------------------------------------------

                    if known_risks:

                        st.markdown(
                            "**Established supplier-risk classifications:**"
                        )

                        for supplier, risk in known_risks:

                            st.markdown(
                                f"- **{supplier}:** "
                                f"{risk}"
                            )


                    # ---------------------------------------------
                    # MANAGEMENT ACTION
                    # ---------------------------------------------

                    st.divider()

                    st.subheader(
                        "Recommended Management Action"
                    )


                    st.markdown(
                        get_recommended_action(
                            network_risk
                        )
                    )


                    # ---------------------------------------------
                    # IMPACT SUMMARY
                    # ---------------------------------------------

                    st.divider()

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


                    # ---------------------------------------------
                    # AFFECTED NETWORK
                    # ---------------------------------------------

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
