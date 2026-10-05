# ============================================================
# NOVADRIVE — ALTERNATE SUPPLIER ENGINE
# ============================================================

import re
import json
import time
import requests
import pandas as pd

from bs4 import BeautifulSoup
from urllib.parse import urlparse
from ddgs import DDGS


# ============================================================
# FILES
# ============================================================

WORKBOOK = "data/NovaDrive_Point1_Network_Reconstruction.xlsx"
RISK_FILE = "data/novadrive_supplier_risk_scorecard.csv"


# ============================================================
# NORMALIZATION
# ============================================================

LEGAL_SUFFIXES = [
    "private limited",
    "private ltd",
    "pvt ltd",
    "pvt. ltd",
    "limited",
    "ltd",
    "incorporated",
    "inc",
    "corporation",
    "corp",
    "llc",
    "plc",
    "group"
]


def normalize_name(x):

    x = str(x).lower().strip()

    for suffix in LEGAL_SUFFIXES:
        x = re.sub(
            rf"\b{re.escape(suffix)}\b",
            "",
            x
        )

    x = re.sub(
        r"[^a-z0-9 ]",
        " ",
        x
    )

    x = re.sub(
        r"\s+",
        " ",
        x
    )

    return x.strip()


# ============================================================
# LOAD WORKBOOK
# ============================================================

def load_part4_data():

    components_df = pd.read_excel(
        WORKBOOK,
        sheet_name="Components Context"
    )

    relationships_df = pd.read_excel(
        WORKBOOK,
        sheet_name="Relationship Evidence"
    )

    risk_df = pd.read_csv(
        RISK_FILE
    )

    return (
        components_df,
        relationships_df,
        risk_df
    )


# ============================================================
# COMPONENT CONTEXT
# ============================================================

def build_component_context(
    components_df
):

    context = {}

    for _, row in components_df.iterrows():

        cid = str(
            row.get(
                "Component ID",
                row.get("Component", "")
            )
        ).strip()

        if not cid:
            continue

        # Support the actual workbook column names
        component = str(
            row.get(
                "Component",
                row.get(
                    "Component Name",
                    ""
                )
            )
        )

        description = str(
            row.get(
                "Description",
                row.get(
                    "Component Description",
                    ""
                )
            )
        )

        application = str(
            row.get(
                "Application / Use Case",
                row.get(
                    "Key application",
                    row.get(
                        "Application",
                        ""
                    )
                )
            )
        )

        products = str(
            row.get(
                "Products Using This Component",
                row.get(
                    "Products",
                    ""
                )
            )
        )

        context[cid] = {
            "component": component,
            "description": description,
            "application": application,
            "products": products
        }

    return context


# ============================================================
# COMPONENT ID EXTRACTION
# ============================================================

def extract_component_ids(
    text,
    component_ids
):

    text = str(text)

    found = []

    for cid in component_ids:

        if re.search(
            rf"\b{re.escape(cid)}\b",
            text,
            flags=re.I
        ):
            found.append(cid)

    return list(
        dict.fromkeys(found)
    )


# ============================================================
# INCUMBENT RELATIONSHIP EVIDENCE
# ============================================================

def get_incumbent_evidence(
    legal_name,
    relationships_df
):

    target = normalize_name(
        legal_name
    )

    rows = []

    for _, row in relationships_df.iterrows():

        text = " ".join(
            str(
                row.get(
                    col,
                    ""
                )
            )
            for col in relationships_df.columns
        )

        if target in normalize_name(text):

            rows.append({
                "Evidence ID":
                    row.get(
                        "Evidence ID",
                        ""
                    ),

                "Evidence Date":
                    row.get(
                        "Evidence Date",
                        ""
                    ),

                "Title / Parties":
                    row.get(
                        "Title / Parties",
                        ""
                    ),

                "Evidence Detail":
                    row.get(
                        "Evidence Detail",
                        ""
                    ),

                "Source Locator":
                    row.get(
                        "Source Locator",
                        ""
                    )
            })

    return pd.DataFrame(rows)


# ============================================================
# DERIVE ACTUAL SOURCING REQUIREMENT
# ============================================================

def derive_sourcing_requirement(
    legal_name,
    relationships_df,
    component_context
):

    evidence = get_incumbent_evidence(
        legal_name,
        relationships_df
    )

    if evidence.empty:

        return {
            "components": [],
            "relationship_text": "",
            "requirement": "",
            "applications": "",
            "products": ""
        }

    all_text = []

    for _, row in evidence.iterrows():

        all_text.append(
            str(
                row.get(
                    "Title / Parties",
                    ""
                )
            )
        )

        all_text.append(
            str(
                row.get(
                    "Evidence Detail",
                    ""
                )
            )
        )

    relationship_text = " ".join(
        all_text
    )

    component_ids = extract_component_ids(
        relationship_text,
        set(component_context.keys())
    )

    descriptions = []
    applications = []
    products = []

    for cid in component_ids:

        ctx = component_context.get(
            cid,
            {}
        )

        if ctx.get("description"):
            descriptions.append(
                ctx["description"]
            )

        if ctx.get("application"):
            applications.append(
                ctx["application"]
            )

        if ctx.get("products"):
            products.append(
                ctx["products"]
            )

    requirement = " ".join([
        relationship_text,
        " ".join(descriptions),
        " ".join(applications),
        " ".join(products)
    ])

    return {
        "components": component_ids,
        "relationship_text": relationship_text,
        "requirement": requirement,
        "applications": " ".join(applications),
        "products": " ".join(products)
    }


# ============================================================
# CAPABILITY
# ============================================================

def infer_capability(
    requirement
):

    text = requirement.lower()

    capability_rules = [

        (
            [
                "printed circuit",
                "pcb",
                "pcba",
                "control board",
                "control electronics",
                "printed circuit board"
            ],
            "industrial control PCB PCBA manufacturing"
        ),

        (
            [
                "battery monitoring",
                "battery management",
                "bms",
                "battery control",
                "energy storage electronics"
            ],
            "battery management system BMS battery monitoring electronics manufacturer"
        ),

        (
            [
                "dc-link capacitor",
                "film capacitor",
                "dielectric",
                "capacitor"
            ],
            "DC link film capacitor power electronics manufacturer"
        ),

        (
            [
                "silicon carbide",
                "sic",
                "sic semiconductor",
                "sic power"
            ],
            "silicon carbide SiC power semiconductor manufacturer industrial power electronics"
        ),

        (
            [
                "power assembly",
                "power module",
                "igbt",
                "power electronics",
                "power semiconductor"
            ],
            "IGBT SiC power module industrial power electronics manufacturer"
        ),

        (
            [
                "magnetic",
                "magnetics",
                "inductor",
                "transformer"
            ],
            "industrial power magnetics inductor transformer manufacturer"
        ),

        (
            [
                "copper foil",
                "foil"
            ],
            "copper foil manufacturer power electronics battery"
        ),

        (
            [
                "resin",
                "polymer",
                "encapsulation"
            ],
            "industrial electronic encapsulation resin polymer manufacturer"
        ),

        (
            [
                "ceramic"
            ],
            "industrial electronic ceramics power electronics manufacturer"
        ),

        (
            [
                "connector",
                "connectors"
            ],
            "industrial electrical connector manufacturer power electronics"
        ),

        (
            [
                "thermal",
                "heat sink",
                "thermal metal"
            ],
            "industrial thermal management heat sink manufacturer power electronics"
        )
    ]

    for keywords, capability in capability_rules:

        if any(
            k in text
            for k in keywords
        ):
            return capability

    return (
        "industrial power electronics "
        "component manufacturer"
    )


# ============================================================
# APPLICATION
# ============================================================

def infer_application(
    requirement
):

    text = requirement.lower()

    applications = []

    if any(
        x in text
        for x in [
            "industrial drive",
            "industrial drives",
            "inverter"
        ]
    ):
        applications.append(
            "industrial drives inverter"
        )

    if any(
        x in text
        for x in [
            "charging",
            "charger",
            "ev"
        ]
    ):
        applications.append(
            "EV charging power conversion"
        )

    if any(
        x in text
        for x in [
            "energy storage",
            "battery"
        ]
    ):
        applications.append(
            "energy storage battery systems"
        )

    if any(
        x in text
        for x in [
            "industrial electronics",
            "control"
        ]
    ):
        applications.append(
            "industrial control electronics"
        )

    if not applications:

        applications.append(
            "industrial power electronics"
        )

    return " ".join(
        dict.fromkeys(applications)
    )


# ============================================================
# PAGE FETCHING
# ============================================================

HEADERS = {
    "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/154 Safari/537.36"
}


def fetch_page(url):

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=12
        )

        if response.status_code >= 400:
            return None

        return response.text

    except Exception:

        return None


# ============================================================
# DOMAIN FILTER
# ============================================================

BLOCKED_DOMAINS = [

    "wikipedia.org",
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "youtube.com",
    "twitter.com",
    "x.com",

    "marketresearch.com",
    "grandviewresearch.com",
    "marketsandmarkets.com",
    "fortunebusinessinsights.com",
    "mordorintelligence.com",

    "crunchbase.com",
    "zoominfo.com",
    "apollo.io",

    "globalelectrics.com",
    "yellowpages.com",

    "eventbrite.com",
    "10times.com",

    "reuters.com",
    "bloomberg.com",
    "forbes.com",

    "live5news.com",
    "postandcourier.com",
    "magdir.com"
]


def domain_is_blocked(url):

    domain = urlparse(
        url
    ).netloc.lower()

    return any(
        blocked in domain
        for blocked in BLOCKED_DOMAINS
    )


# ============================================================
# VERIFICATION
# ============================================================

SUPPLIER_TERMS = [
    "manufacturer",
    "manufactures",
    "manufacturing",
    "supplier",
    "supplies",
    "producer",
    "production",
    "factory",
    "fabrication"
]

PRODUCT_TERMS = [
    "product",
    "products",
    "module",
    "assembly",
    "component",
    "pcb",
    "pcba",
    "capacitor",
    "semiconductor",
    "power electronics",
    "igbt",
    "sic",
    "battery",
    "connector",
    "magnetic",
    "transformer",
    "inductor",
    "resin",
    "ceramic",
    "foil"
]

BAD_PAGE_TERMS = [
    "conference",
    "webinar",
    "summit",
    "expo",
    "event",
    "agenda",
    "speaker",
    "market report",
    "market research",
    "top 10",
    "ranking",
    "wikipedia"
]


def extract_page_info(
    html
):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    title = (
        soup.title.get_text(
            " ",
            strip=True
        )
        if soup.title
        else ""
    )

    meta_description = ""

    meta = soup.find(
        "meta",
        attrs={
            "name": "description"
        }
    )

    if meta:

        meta_description = meta.get(
            "content",
            ""
        )

    text = soup.get_text(
        " ",
        strip=True
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    organization_name = ""

    for script in soup.find_all(
        "script",
        type="application/ld+json"
    ):

        try:

            data = json.loads(
                script.string or ""
            )

            items = (
                data
                if isinstance(data, list)
                else [data]
            )

            for item in items:

                if not isinstance(
                    item,
                    dict
                ):
                    continue

                typ = str(
                    item.get(
                        "@type",
                        ""
                    )
                ).lower()

                if typ in [
                    "organization",
                    "corporation",
                    "localbusiness"
                ]:

                    organization_name = str(
                        item.get(
                            "name",
                            ""
                        )
                    ).strip()

                    if organization_name:
                        break

        except Exception:
            pass

    return {
        "title": title,
        "description": meta_description,
        "text": text,
        "organization_name": organization_name
    }


def verify_supplier_page(
    url,
    title,
    description,
    text
):

    if domain_is_blocked(url):
        return False

    combined = (
        title + " " +
        description + " " +
        text[:30000]
    ).lower()

    bad_hits = sum(
        1
        for term in BAD_PAGE_TERMS
        if term in combined
    )

    if bad_hits >= 2:
        return False

    supplier_hits = sum(
        1
        for term in SUPPLIER_TERMS
        if term in combined
    )

    if supplier_hits < 2:
        return False

    product_hits = sum(
        1
        for term in PRODUCT_TERMS
        if term in combined
    )

    if product_hits < 2:
        return False

    sentences = re.split(
        r"[.!?]",
        text
    )

    strong_sentence = False

    for sentence in sentences:

        s = sentence.lower()

        has_supplier = any(
            term in s
            for term in SUPPLIER_TERMS
        )

        has_product = any(
            term in s
            for term in PRODUCT_TERMS
        )

        if (
            has_supplier
            and
            has_product
        ):

            strong_sentence = True
            break

    return strong_sentence


# ============================================================
# COMPANY NAME
# ============================================================

def extract_company_name(
    title,
    organization_name,
    url
):

    if organization_name:
        return organization_name

    if "|" in title:

        parts = [
            x.strip()
            for x in title.split("|")
            if x.strip()
        ]

        if len(parts) >= 2:
            return parts[-1]

    if " - " in title:

        parts = [
            x.strip()
            for x in title.split(" - ")
            if x.strip()
        ]

        if len(parts) >= 2:
            return parts[-1]

    domain = urlparse(
        url
    ).netloc.lower()

    domain = domain.replace(
        "www.",
        ""
    )

    return domain.split(".")[0].title()


# ============================================================
# FITMENT
# ============================================================

def technical_fit(
    requirement,
    page_text
):

    req = requirement.lower()
    page = page_text.lower()

    keywords = [
        "pcb",
        "pcba",
        "control board",
        "battery",
        "bms",
        "capacitor",
        "power module",
        "power electronics",
        "igbt",
        "sic",
        "semiconductor",
        "magnetic",
        "transformer",
        "inductor",
        "connector",
        "resin",
        "polymer",
        "ceramic",
        "copper foil",
        "thermal"
    ]

    relevant = [
        x
        for x in keywords
        if x in req
    ]

    if not relevant:
        return 50

    matches = [
        x
        for x in relevant
        if x in page
    ]

    return round(
        50 +
        50 * len(matches) /
        len(relevant),
        1
    )


def application_fit(
    application,
    page_text
):

    app = application.lower()
    page = page_text.lower()

    keywords = []

    if "industrial" in app:
        keywords.append("industrial")

    if "drive" in app:
        keywords.append("drive")

    if "inverter" in app:
        keywords.append("inverter")

    if "charging" in app:
        keywords.append("charging")

    if "energy storage" in app:
        keywords.append("energy storage")

    if "battery" in app:
        keywords.append("battery")

    if "control" in app:
        keywords.append("control")

    if not keywords:
        return 60

    matches = [
        x
        for x in keywords
        if x in page
    ]

    return round(
        50 +
        50 * len(matches) /
        len(keywords),
        1
    )


def manufacturing_fit(
    page_text
):

    page = page_text.lower()

    terms = [
        "manufacturing",
        "factory",
        "production",
        "facility",
        "plant",
        "assembly"
    ]

    hits = sum(
        1
        for x in terms
        if x in page
    )

    if hits >= 4:
        return 80

    if hits >= 2:
        return 65

    return 40


def scale_fit(
    page_text
):

    page = page_text.lower()

    terms = [
        "global",
        "international",
        "million",
        "billion",
        "factory",
        "production",
        "high volume",
        "large scale"
    ]

    hits = sum(
        1
        for x in terms
        if x in page
    )

    if hits >= 4:
        return 70

    if hits >= 2:
        return 50

    return 30


def fitment_score(
    tech,
    app,
    manufacturing,
    scale
):

    return round(
        0.40 * tech +
        0.30 * app +
        0.20 * manufacturing +
        0.10 * scale,
        1
    )


# ============================================================
# EVIDENCE
# ============================================================

def get_evidence_snippet(
    text,
    requirement
):

    sentences = re.split(
        r"[.!?]",
        text
    )

    requirement_words = set(
        re.findall(
            r"[a-zA-Z]{4,}",
            requirement.lower()
        )
    )

    best = ""
    best_score = 0

    for sentence in sentences:

        sentence = sentence.strip()

        if len(sentence) < 40:
            continue

        words = set(
            re.findall(
                r"[a-zA-Z]{4,}",
                sentence.lower()
            )
        )

        score = len(
            words &
            requirement_words
        )

        if score > best_score:

            best_score = score
            best = sentence

    return best[:900]


# ============================================================
# SUPPLIER RISK
# ============================================================

def get_existing_supplier_risk(
    candidate,
    risk_df
):

    candidate_norm = normalize_name(
        candidate
    )

    for _, row in risk_df.iterrows():

        existing = normalize_name(
            row.get(
                "Legal Name",
                ""
            )
        )

        if (
            existing == candidate_norm
            or
            existing in candidate_norm
            or
            candidate_norm in existing
        ):

            return (
                row.get(
                    "Risk_Category",
                    "Unknown"
                ),
                row.get(
                    "Composite_Risk_Score",
                    None
                )
            )

    return (
        "Not assessed — diligence required",
        None
    )


# ============================================================
# WEB SEARCH
# ============================================================

def search_web(
    query,
    max_results=8
):

    try:

        with DDGS() as ddgs:

            return list(
                ddgs.text(
                    query,
                    max_results=max_results
                )
            )

    except Exception:

        return []


# ============================================================
# MAIN FUNCTION
# ============================================================

def find_alternates(
    legal_name,
    risk_category=None,
    max_candidates=8
):

    components_df, relationships_df, risk_df = (
        load_part4_data()
    )

    component_context = build_component_context(
        components_df
    )

    sourcing = derive_sourcing_requirement(
        legal_name,
        relationships_df,
        component_context
    )

    components = sourcing[
        "components"
    ]

    requirement = sourcing[
        "requirement"
    ]

    capability = infer_capability(
        requirement
    )

    application = infer_application(
        requirement
    )

    queries = [

        f'"{capability}" manufacturer "{application}"',

        f'{capability} manufacturer {application}',

        f'"{capability}" supplier {application}'
    ]

    candidates = []

    seen_urls = set()
    seen_companies = set()

    for query in queries:

        results = search_web(
            query,
            max_results=8
        )

        for result in results:

            url = result.get(
                "href",
                result.get(
                    "url",
                    ""
                )
            )

            if not url:
                continue

            if url in seen_urls:
                continue

            seen_urls.add(url)

            html = fetch_page(
                url
            )

            if not html:
                continue

            info = extract_page_info(
                html
            )

            if not verify_supplier_page(
                url,
                info["title"],
                info["description"],
                info["text"]
            ):
                continue

            company = extract_company_name(
                info["title"],
                info["organization_name"],
                url
            )

            company_norm = normalize_name(
                company
            )

            # Don't return same company repeatedly
            if company_norm in seen_companies:
                continue

            # Don't recommend incumbent itself
            incumbent_norm = normalize_name(
                legal_name
            )

            if (
                company_norm == incumbent_norm
                or
                company_norm in incumbent_norm
                or
                incumbent_norm in company_norm
            ):
                continue

            tech = technical_fit(
                requirement,
                info["text"]
            )

            app = application_fit(
                application,
                info["text"]
            )

            mfg = manufacturing_fit(
                info["text"]
            )

            scale = scale_fit(
                info["text"]
            )

            score = fitment_score(
                tech,
                app,
                mfg,
                scale
            )

            supplier_risk, supplier_risk_score = (
                get_existing_supplier_risk(
                    company,
                    risk_df
                )
            )

            evidence = get_evidence_snippet(
                info["text"],
                requirement
            )

            candidates.append({

                "Incumbent Supplier":
                    legal_name,

                "Risk Category":
                    risk_category or "—",

                "Component ID":
                    ", ".join(
                        components
                    ),

                "Component":
                    "; ".join(
                        component_context[c]["component"]
                        for c in components
                        if c in component_context
                        and component_context[c]["component"]
                        and component_context[c]["component"]
                        != "nan"
                    ),

                "Required Capability":
                    capability,

                "Application":
                    application,

                "Relationship-Based Requirement":
                    requirement[:1500],

                "Alternate Supplier":
                    company,

                "Supplier Verification":
                    "VERIFIED",

                "Technical Fit":
                    tech,

                "Application Fit":
                    app,

                "Manufacturing Footprint":
                    mfg,

                "Industry / Scale":
                    scale,

                "Fitment Score":
                    score,

                "Supplier Risk":
                    supplier_risk,

                "Supplier Risk Score":
                    supplier_risk_score,

                "Evidence":
                    evidence,

                "Source URL":
                    url,

                "Qualification Next Step":
                    (
                        "Validate technical specifications, "
                        "manufacturing capability, quality "
                        "certifications, capacity, lead time, "
                        "and NovaDrive qualification requirements."
                    )
            })

            seen_companies.add(
                company_norm
            )

            if len(candidates) >= max_candidates:
                return pd.DataFrame(
                    sorted(
                        candidates,
                        key=lambda x:
                        x["Fitment Score"],
                        reverse=True
                    )
                )

            time.sleep(0.25)

    return pd.DataFrame(
        sorted(
            candidates,
            key=lambda x:
            x["Fitment Score"],
            reverse=True
        )
    )
