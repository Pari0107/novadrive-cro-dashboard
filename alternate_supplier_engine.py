# ============================================================
# NOVADRIVE — ALTERNATE SUPPLIER ENGINE
# PRECOMPUTED EXCEL VERSION
# ============================================================

import os
import glob
import pandas as pd


# ============================================================
# FIND THE EXCEL FILE
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


POSSIBLE_FILES = [
    os.path.join(
        BASE_DIR,
        "data",
        "novadrive_alternate_supplier_recommendations_clean.xlsx"
    ),

    os.path.join(
        BASE_DIR,
        "data",
        "novadrive_alternate_supplier_recommendations_clean(1).xlsx"
    ),

    os.path.join(
        BASE_DIR,
        "data",
        "alternate_supplier_recommendations.xlsx"
    ),

    os.path.join(
        BASE_DIR,
        "data",
        "alternate_supplier_recommendations_clean.xlsx"
    ),
]


def get_excel_file():

    for path in POSSIBLE_FILES:

        if os.path.exists(path):
            return path

    # Last-resort search for any Excel file containing
    # "alternate" in the data folder.

    data_folder = os.path.join(
        BASE_DIR,
        "data"
    )

    candidates = glob.glob(
        os.path.join(
            data_folder,
            "*alternate*.xlsx"
        )
    )

    if candidates:
        return candidates[0]

    raise FileNotFoundError(
        "Alternate supplier Excel file was not found in the data folder."
    )


# ============================================================
# LOAD DATA
# ============================================================

def load_alternate_supplier_data():

    excel_file = get_excel_file()

    df = pd.read_excel(
        excel_file,
        sheet_name="Alternate Suppliers"
    )

    # Clean column names
    df.columns = [
        str(c).strip()
        for c in df.columns
    ]

    # --------------------------------------------------------
    # Keep ONLY HIGH / CRITICAL supplier recommendations
    # --------------------------------------------------------

    if "Risk Category" in df.columns:

        df["Risk Category"] = (
            df["Risk Category"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        df = df[
            df["Risk Category"].isin(
                ["HIGH", "CRITICAL"]
            )
        ].copy()

    # --------------------------------------------------------
    # Numeric columns
    # --------------------------------------------------------

    numeric_columns = [
        "Technical Fit",
        "Application Fit",
        "Manufacturing Footprint",
        "Industry / Scale",
        "Fitment Score",
        "Supplier Risk Score"
    ]

    for column in numeric_columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    # --------------------------------------------------------
    # Clean text fields
    # --------------------------------------------------------

    text_columns = [
        "Incumbent Supplier",
        "Alternate Supplier",
        "Component ID",
        "Component",
        "Risk Category",
        "Supplier Verification",
        "Evidence",
        "Source Date",
        "Source URL",
        "Qualification Next Step"
    ]

    for column in text_columns:

        if column in df.columns:

            df[column] = (
                df[column]
                .fillna("")
                .astype(str)
                .str.strip()
            )

    return df


# ============================================================
# SUPPLIER NAME NORMALISATION
# ============================================================

def normalize_supplier_name(name):

    if name is None:
        return ""

    name = str(name).strip().lower()

    suffixes = [
        " private limited",
        " private ltd",
        " pvt ltd",
        " pvt. ltd.",
        " limited",
        " ltd.",
        " ltd",
        " llc",
        " inc.",
        " inc",
        " corporation",
        " corp.",
        " corp"
    ]

    for suffix in suffixes:

        if name.endswith(suffix):

            name = name[
                :-len(suffix)
            ].strip()

            break

    return name


# ============================================================
# MAIN FUNCTION
# ============================================================

def find_alternates(
    supplier_name,
    risk_category=None,
    max_candidates=8
):
    """
    Returns precomputed alternate suppliers from the Excel
    dataset.

    This deliberately keeps the same function signature as
    the previous live-search engine so app.py does not need
    to change.
    """

    # --------------------------------------------------------
    # Load precomputed dataset
    # --------------------------------------------------------

    df = load_alternate_supplier_data()

    if df.empty:

        return pd.DataFrame()


    # --------------------------------------------------------
    # Normalise selected supplier
    # --------------------------------------------------------

    target = normalize_supplier_name(
        supplier_name
    )


    df["_supplier_normalized"] = (
        df["Incumbent Supplier"]
        .apply(normalize_supplier_name)
    )


    # --------------------------------------------------------
    # Exact supplier match
    # --------------------------------------------------------

    results = df[
        df["_supplier_normalized"] == target
    ].copy()


    # --------------------------------------------------------
    # Fallback matching
    # --------------------------------------------------------

    if results.empty:

        target_words = [
            word
            for word in target.split()
            if len(word) > 2
        ]

        if target_words:

            mask = pd.Series(
                True,
                index=df.index
            )

            for word in target_words:

                mask = (
                    mask
                    &
                    df["_supplier_normalized"]
                    .str.contains(
                        word,
                        regex=False,
                        na=False
                    )
                )

            results = df[
                mask
            ].copy()


    # --------------------------------------------------------
    # No recommendations
    # --------------------------------------------------------

    if results.empty:

        return pd.DataFrame()


    # --------------------------------------------------------
    # Sort by fitment score
    # --------------------------------------------------------

    if "Fitment Score" in results.columns:

        results = results.sort_values(
            "Fitment Score",
            ascending=False,
            na_position="last"
        )


    # --------------------------------------------------------
    # Remove duplicate alternate suppliers
    # --------------------------------------------------------

    if "Alternate Supplier" in results.columns:

        results = results.drop_duplicates(
            subset=["Alternate Supplier"],
            keep="first"
        )


    # --------------------------------------------------------
    # Return top candidates
    # --------------------------------------------------------

    results = results.head(
        max_candidates
    ).copy()


    # --------------------------------------------------------
    # Remove helper column
    # --------------------------------------------------------

    if "_supplier_normalized" in results.columns:

        results = results.drop(
            columns=["_supplier_normalized"]
        )


    # --------------------------------------------------------
    # Guarantee dashboard columns
    # --------------------------------------------------------

    required_columns = [

        "Incumbent Supplier",
        "Risk Category",
        "Component ID",
        "Component",
        "Relationship-Based Requirement",
        "Alternate Supplier",
        "Supplier Verification",
        "Technical Fit",
        "Application Fit",
        "Manufacturing Footprint",
        "Industry / Scale",
        "Fitment Score",
        "Supplier Risk",
        "Supplier Risk Score",
        "Evidence",
        "Source Date",
        "Source URL",
        "Qualification Next Step"

    ]


    for column in required_columns:

        if column not in results.columns:

            results[column] = ""


    # --------------------------------------------------------
    # Final column order
    # --------------------------------------------------------

    results = results[
        required_columns
    ].reset_index(
        drop=True
    )


    return results


# ============================================================
# ALIAS
# ============================================================

def get_alternate_suppliers(
    supplier_name,
    risk_category=None,
    max_candidates=8
):

    return find_alternates(
        supplier_name,
        risk_category,
        max_candidates
    )
