import os
import re
import json
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from ddgs import DDGS


WORKBOOK = "data/NovaDrive_Point1_Network_Reconstruction.xlsx"
RISK_FILE = "data/novadrive_supplier_risk_scorecard.csv"
OUTPUT = "data/novadrive_web_alternate_suppliers.csv"


xls = pd.ExcelFile(WORKBOOK)

components_df = pd.read_excel(
    WORKBOOK,
    sheet_name="Components Context"
)

relationships_df = pd.read_excel(
    WORKBOOK,
    sheet_name="Relationship Evidence"
)

risk_df = pd.read_csv(RISK_FILE)

print("Workbook:", WORKBOOK)
print("Components:", components_df.shape)
print("Relationships:", relationships_df.shape)
print("Risk scorecard:", risk_df.shape)


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


risk_df["normalized_name"] = (
    risk_df["Legal Name"]
    .apply(normalize_name)
)


component_context = {}

for _, row in components_df.iterrows():

    cid = str(
        row.get(
            "Component ID",
            row.get(
                "Component",
                ""
            )
        )
    ).strip()

    if not cid:
        continue

    component_context[cid] = {

        "component": str(
            row.get(
                "Component",
                ""
            )
        ),

        "description": str(
            row.get(
                "Description",
                ""
            )
        ),

        "application": str(
            row.get(
                "Application / Use Case",
                ""
            )
        ),

        "products": str(
            row.get(
                "Products Using This Component",
                ""
            )
        )
    }


print("\nCOMPONENT CONTEXT")

for k, v in component_context.items():

    print(
        k,
        "=>",
        v
    )


COMPONENT_IDS = set(
    component_context.keys()
)


def extract_component_ids(text):

    text = str(text)

    found = []

    for cid in COMPONENT_IDS:

        if re.search(
            rf"\b{re.escape(cid)}\b",
            text,
            flags=re.I
        ):

            found.append(cid)

    return list(
        dict.fromkeys(found)
    )


def get_incumbent_evidence(
    legal_name
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


def derive_sourcing_requirement(
    legal_name
):

    evidence = get_incumbent_evidence(
        legal_name
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

        title = str(
            row.get(
                "Title / Parties",
                ""
            )
        )

        detail = str(
            row.get(
                "Evidence Detail",
                ""
            )
        )

        all_text.append(title)
        all_text.append(detail)

    relationship_text = " ".join(
        all_text
    )

    component_ids = extract_component_ids(
        relationship_text
    )

    descriptions = []
    applications = []
    products = []

    for cid in component_ids:

        ctx = component_context.get(
            cid,
            {}
        )

        if ctx.get(
            "description"
        ):

            descriptions.append(
                ctx["description"]
            )

        if ctx.get(
            "application"
        ):

            applications.append(
                ctx["application"]
            )

        if ctx.get(
            "products"
        ):

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

        "components":
            component_ids,

        "relationship_text":
            relationship_text,

        "requirement":
            requirement,

        "applications":
            " ".join(applications),

        "products":
            " ".join(products)
    }


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
        dict.fromkeys(
            applications
        )
    )


priority_df = risk_df[
    risk_df["Risk_Category"].isin(
        [
            "HIGH",
            "CRITICAL"
        ]
    )
].copy()


print(
    "\nHIGH / CRITICAL SUPPLIERS"
)

print(
    priority_df[
        [
            "Legal Name",
            "Composite_Risk_Score",
            "Risk_Category"
        ]
    ].to_string(
        index=False
    )
)


HEADERS = {

    "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/154 Safari/537.36"
}


def fetch_page(url):

    try:

        r = requests.get(
            url,
            headers=HEADERS,
            timeout=12
        )

        if r.status_code >= 400:

            return None

        return r.text

    except Exception:

        return None


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

    "forbes.com"
]


def domain_is_blocked(url):

    domain = urlparse(
        url
    ).netloc.lower()

    return any(
        blocked in domain
        for blocked in BLOCKED_DOMAINS
    )


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
    url,
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

    jsonld = []

    for script in soup.find_all(
        "script",
        type="application/ld+json"
    ):

        try:

            data = json.loads(
                script.string or ""
            )

            if isinstance(
                data,
                list
            ):

                jsonld.extend(
                    data
                )

            else:

                jsonld.append(
                    data
                )

        except Exception:

            pass

    organization_name = ""

    for item in jsonld:

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

    return {

        "title":
            title,

        "description":
            meta_description,

        "text":
            text,

        "organization_name":
            organization_name
    }


def verify_supplier_page(
    url,
    title,
    description,
    text
):

    domain = urlparse(
        url
    ).netloc.lower()

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

    if domain_is_blocked(url):

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

    if not strong_sentence:

        return False

    return True


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

    return domain.split(
        "."
    )[0].title()


def technical_fit(
    requirement,
    page_text
):

    req = requirement.lower()

    page = page_text.lower()

    capability_keywords = [

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
        for x in capability_keywords
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

        keywords.append(
            "industrial"
        )

    if "drive" in app:

        keywords.append(
            "drive"
        )

    if "inverter" in app:

        keywords.append(
            "inverter"
        )

    if "charging" in app:

        keywords.append(
            "charging"
        )

    if "energy storage" in app:

        keywords.append(
            "energy storage"
        )

    if "battery" in app:

        keywords.append(
            "battery"
        )

    if "control" in app:

        keywords.append(
            "control"
        )

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

        s = sentence.strip()

        if len(s) < 40:

            continue

        words = set(
            re.findall(
                r"[a-zA-Z]{4,}",
                s.lower()
            )
        )

        score = len(
            words &
            requirement_words
        )

        if score > best_score:

            best_score = score

            best = s

    return best[:900]


def search_web(
    query,
    max_results=8
):

    try:

        with DDGS() as ddgs:

            results = list(
                ddgs.text(
                    query,
                    max_results=max_results
                )
            )

            # IMPORTANT:
            # DDGS can return unexpected values.
            # Only pass dictionary results
            # to the sourcing pipeline.

            return [
                result
                for result in results
                if isinstance(
                    result,
                    dict
                )
            ]

    except Exception as e:

        print(
            "Search error:",
            e
        )

        return []


def find_alternates(
    legal_name,
    risk_category=None,
    max_candidates=8
):

    sourcing = derive_sourcing_requirement(
        legal_name
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

    print("\n")

    print(
        "=" * 110
    )

    print(
        "INCUMBENT:",
        legal_name
    )

    print(
        "COMPONENTS:",
        components
    )

    print(
        "CAPABILITY:",
        capability
    )

    print(
        "APPLICATION:",
        application
    )

    print(
        "=" * 110
    )

    queries = [

        f'"{capability}" manufacturer "{application}"',

        f'{capability} manufacturer {application}',

        f'"{capability}" supplier {application}'
    ]

    candidates = []

    seen_urls = set()

    for query in queries:

        print(
            "\nSEARCH:",
            query
        )

        results = search_web(
            query,
            max_results=8
        )

        print(
            "Raw results:",
            len(results)
        )

        for result in results:

            # Foolproof protection against:
            # "string indices must be integers, not 'str'"

            if not isinstance(
                result,
                dict
            ):

                continue

            url = result.get(
                "href",
                result.get(
                    "url",
                    ""
                )
            )

            if not isinstance(
                url,
                str
            ):

                continue

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
                url,
                html
            )

            verified = verify_supplier_page(
                url,
                info["title"],
                info["description"],
                info["text"]
            )

            if not verified:

                continue

            company = extract_company_name(
                info["title"],
                info["organization_name"],
                url
            )

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

            evidence = get_evidence_snippet(
                info["text"],
                requirement
            )

            candidates.append({

                "Incumbent Supplier":
                    legal_name,

                "Risk Category":
                    risk_category,

                "Component ID":
                    ", ".join(
                        components
                    ),

                "Component":
                    "; ".join(

                        component_context[c][
                            "component"
                        ]

                        for c in components

                        if c in component_context
                    ),

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
                    "Not assessed — diligence required",

                "Supplier Risk Score":
                    None,

                "Evidence":
                    evidence,

                "Source Date":
                    "",

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

            print(
                "  ✓ VERIFIED:",
                company,
                "|",
                info["title"],
                "|",
                urlparse(
                    url
                ).netloc
            )

    result_df = pd.DataFrame(
        candidates
    )

    if not result_df.empty:

        result_df = result_df.drop_duplicates(
            subset=[
                "Incumbent Supplier",
                "Alternate Supplier",
                "Source URL"
            ]
        )

        result_df = result_df.sort_values(
            "Fitment Score",
            ascending=False
        )

        if max_candidates is not None:

            try:

                limit = int(
                    max_candidates
                )

                if limit > 0:

                    result_df = result_df.head(
                        limit
                    )

            except (
                TypeError,
                ValueError
            ):

                pass

    return result_df.reset_index(
        drop=True
    )
