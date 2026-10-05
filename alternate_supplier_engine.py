# ============================================================
# NOVADRIVE — ALTERNATE SUPPLIER ENGINE
# Precomputed recommendation version
# ============================================================

import os
import pandas as pd


# ============================================================
# CONFIG
# ============================================================

# The Excel file should be placed in the same repository under:
# data/alternate_supplier_recommendations.xlsx

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ALTERNATE_FILE = os.path.join(
    BASE_DIR,
    "data",
    "alternate_supplier_recommendations_clean.xlsx"
)


# ============================================================
# LOAD PRECOMPUTED RESULTS
# ============================================================

def load_alternate_supplier_data():

    if not os.path.exists(ALTERNATE_FILE):
        raise FileNotFoundError(
            f"Alternate supplier file not found: {ALTERNATE_FILE}"
        )

    df = pd.read_excel(ALTERNATE_FILE)

    # Clean column names
    df.columns = [
        str(col).strip()
        for col in df.columns
    ]

    # Numeric fields
    numeric_columns = [
        "Technical Fit",
        "Application Fit",
        "Manufacturing Footprint",
        "Industry / Scale",
        "Fitment Score"
    ]

    for col in numeric_columns:

        if col in df.columns:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

    # Clean incumbent supplier names
    if "Incumbent Supplier" in df.columns:

        df["Incumbent Supplier"] = (
            df["Incumbent Supplier"]
            .astype(str)
            .str.strip()
        )

    # Clean alternate supplier names
    if "Alternate Supplier" in df.columns:

        df["Alternate Supplier"] = (
            df["Alternate Supplier"]
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

    # Remove common legal suffixes so that:
    #
    # "Boreal Power Systems"
    #
    # and
    #
    # "Boreal Power Systems Ltd."
    #
    # still match.

    suffixes = [
        " private limited",
        " pvt ltd",
        " pvt. ltd.",
        " private ltd",
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

            name = name[:-len(suffix)].strip()
            break

    return name


# ============================================================
# FIND ALTERNATE SUPPLIERS
# ============================================================

def find_alternates(
    supplier_name,
    risk_category=None,
    max_candidates=8
):
    """
    Return precomputed alternate suppliers for the selected
    NovaDrive incumbent supplier.

    The function intentionally keeps the same interface as
    the previous live-search engine so the Streamlit dashboard
    does not need to change.
    """

    # --------------------------------------------------------
    # Load precomputed dataset
    # --------------------------------------------------------

    df = load_alternate_supplier_data()

    if df.empty:
        return pd.DataFrame()


    # --------------------------------------------------------
    # Match incumbent supplier
    # --------------------------------------------------------

    target = normalize_supplier_name(
        supplier_name
    )

    df["_normalized_incumbent"] = (
        df["Incumbent Supplier"]
        .apply(normalize_supplier_name)
    )

    matches = df[
        df["_normalized_incumbent"] == target
    ].copy()


    # --------------------------------------------------------
    # If exact normalized match fails, try substring match
    # --------------------------------------------------------

    if matches.empty:

        supplier_text = str(
            supplier_name
        ).strip().lower()

        matches = df[
            df["Incumbent Supplier"]
            .astype(str)
            .str.lower()
            .str.contains(
                supplier_text,
                regex=False,
                na=False
            )
        ].copy()


    # --------------------------------------------------------
    # Nothing found
    # --------------------------------------------------------

    if matches.empty:

        return pd.DataFrame()


    # --------------------------------------------------------
    # Risk category
    #
    # We deliberately DO NOT filter recommendations based
    # on risk category.
    #
    # The Excel already contains the correct recommendation
    # set for every incumbent supplier.
    # --------------------------------------------------------


    # --------------------------------------------------------
    # Sort by fitment score
    # --------------------------------------------------------

    if "Fitment Score" in matches.columns:

        matches["Fitment Score"] = pd.to_numeric(
            matches["Fitment Score"],
            errors="coerce"
        )

        matches = matches.sort_values(
            by="Fitment Score",
            ascending=False,
            na_position="last"
        )


    # --------------------------------------------------------
    # Remove duplicate alternate suppliers
    #
    # This prevents the same company appearing multiple
    # times if it was found for multiple component records.
    # --------------------------------------------------------

    if "Alternate Supplier" in matches.columns:

        matches = matches.drop_duplicates(
            subset=["Alternate Supplier"],
            keep="first"
        )


    # --------------------------------------------------------
    # Return requested number of candidates
    # --------------------------------------------------------

    matches = matches.head(
        max_candidates
    ).copy()


    # --------------------------------------------------------
    # Remove helper column
    # --------------------------------------------------------

    if "_normalized_incumbent" in matches.columns:

        matches = matches.drop(
            columns=["_normalized_incumbent"]
        )


    # --------------------------------------------------------
    # Make sure expected dashboard columns exist
    # --------------------------------------------------------

    expected_columns = [

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
        "Evidence",
        "Source Date",
        "Source URL",
        "Qualification Next Step"

    ]

    for col in expected_columns:

        if col not in matches.columns:

            matches[col] = ""


    # --------------------------------------------------------
    # Return in the same column structure
    # --------------------------------------------------------

    return matches[expected_columns].reset_index(
        drop=True
    )


# ============================================================
# OPTIONAL ALIAS
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
