# ============================================================
# NOVADRIVE — ALTERNATE SUPPLIER ENGINE
# PRECOMPUTED DATASET VERSION
# ============================================================

import os
import glob
import pandas as pd


# ============================================================
# PATH
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


# ============================================================
# REQUIRED COLUMNS
# ============================================================

REQUIRED_COLUMNS = [
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


# ============================================================
# FIND THE CORRECT EXCEL FILE
# ============================================================

def find_data_file():

    preferred_files = [
        os.path.join(
            DATA_DIR,
            "novadrive_alternate_supplier_recommendations_clean.xlsx"
        ),
        os.path.join(
            DATA_DIR,
            "novadrive_alternate_supplier_recommendations_clean(1).xlsx"
        ),
        os.path.join(
            DATA_DIR,
            "alternate_supplier_recommendations.xlsx"
        ),
        os.path.join(
            DATA_DIR,
            "alternate_supplier_recommendations_clean.xlsx"
        )
    ]

    # First check known filenames
    for path in preferred_files:

        if os.path.exists(path):
            return path

    # Then search for any alternate-supplier Excel file
    candidates = glob.glob(
        os.path.join(
            DATA_DIR,
            "*alternate*.xlsx"
        )
    )

    if candidates:
        return candidates[0]

    raise FileNotFoundError(
        "No alternate-supplier Excel file found in data/."
    )


# ============================================================
# LOAD EXCEL — ROBUST TO SHEET NAME
# ============================================================

def load_excel_data():

    excel_file = find_data_file()

    # Read workbook sheet names
    excel_file_obj = pd.ExcelFile(excel_file)

    sheet_names = excel_file_obj.sheet_names

    # Prefer the intended sheet
    if "Alternate Suppliers" in sheet_names:

        df = pd.read_excel(
            excel_file,
            sheet_name="Alternate Suppliers"
        )

    else:

        # Some uploaded versions use Sheet1.
        # Use the first sheet if it contains the required
        # alternate-supplier columns.

        df = None

        for sheet in sheet_names:

            candidate = pd.read_excel(
                excel_file,
                sheet_name=sheet
            )

            candidate_columns = set(
                str(c).strip()
                for c in candidate.columns
            )

            if (
                "Incumbent Supplier" in candidate_columns
                and
                "Alternate Supplier" in candidate_columns
                and
                "Risk Category" in candidate_columns
            ):

                df = candidate
                break

        if df is None:

            raise ValueError(
                "The Excel file was found, but no sheet containing "
                "the alternate-supplier dataset could be identified."
            )

    # Clean column names
    df.columns = [
        str(c).strip()
        for c in df.columns
    ]

    return df


# ============================================================
# LOAD + CLEAN DATA
# ============================================================

def load_alternate_supplier_data():

    df = load_excel_data()

    # --------------------------------------------------------
    # Normalize Risk Category
    # --------------------------------------------------------

    if "Risk Category" in df.columns:

        df["Risk Category"] = (
            df["Risk Category"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

    # --------------------------------------------------------
    # ONLY USE HIGH / CRITICAL
    # --------------------------------------------------------

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
    # Text columns
    # --------------------------------------------------------

    text_columns = [
        "Incumbent Supplier",
        "Risk Category",
        "Component ID",
        "Component",
        "Relationship-Based Requirement",
        "Alternate Supplier",
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

    # --------------------------------------------------------
    # Add columns expected by dashboard if absent
    # --------------------------------------------------------

    if "Supplier Risk" not in df.columns:

        df["Supplier Risk"] = (
            "Not assessed — diligence required"
        )

    if "Supplier Risk Score" not in df.columns:

        df["Supplier Risk Score"] = pd.NA

    # --------------------------------------------------------
    # Remove obviously empty supplier rows
    # --------------------------------------------------------

    df = df[
        df["Alternate Supplier"]
        .astype(str)
        .str.strip()
        .ne("")
    ].copy()

    return df.reset_index(drop=True)


# ============================================================
# NORMALIZE SUPPLIER NAME
# ============================================================

def normalize_supplier_name(name):

    if name is None:
        return ""

    name = str(name).strip().lower()

    # Remove punctuation
    name = (
        name
        .replace(",", " ")
        .replace(".", " ")
    )

    # Normalize whitespace
    name = " ".join(
        name.split()
    )

    suffixes = [
        "private limited",
        "private ltd",
        "pvt ltd",
        "limited",
        "ltd",
        "llc",
        "incorporated",
        "inc",
        "corporation",
        "corp"
    ]

    for suffix in suffixes:

        if name.endswith(
            " " + suffix
        ):

            name = name[
                :-(len(suffix) + 1)
            ].strip()

            break

    return name


# ============================================================
# FIND ALTERNATES
# ============================================================

def find_alternates(
    supplier_name,
    risk_category=None,
    max_candidates=8
):

    # --------------------------------------------------------
    # Load precomputed dataset
    # --------------------------------------------------------

    df = load_alternate_supplier_data()

    if df.empty:

        return pd.DataFrame()


    # --------------------------------------------------------
    # Normalize names
    # --------------------------------------------------------

    target = normalize_supplier_name(
        supplier_name
    )

    df["_normalized_incumbent"] = (
        df["Incumbent Supplier"]
        .apply(normalize_supplier_name)
    )


    # --------------------------------------------------------
    # Exact match
    # --------------------------------------------------------

    results = df[
        df["_normalized_incumbent"] == target
    ].copy()


    # --------------------------------------------------------
    # Fallback partial match
    # --------------------------------------------------------

    if results.empty:

        target_words = [
            word
            for word in target.split()
            if len(word) >= 4
        ]

        if target_words:

            scores = []

            for _, row in df.iterrows():

                incumbent = row[
                    "_normalized_incumbent"
                ]

                matched = sum(
                    word in incumbent
                    for word in target_words
                )

                scores.append(
                    matched
                )

            df["_match_score"] = scores

            results = df[
                df["_match_score"] > 0
            ].copy()

            if not results.empty:

                results = results.sort_values(
                    "_match_score",
                    ascending=False
                )

                # Only retain reasonably strong matches
                results = results[
                    results["_match_score"]
                    >= max(
                        1,
                        len(target_words) // 2
                    )
                ]


    # --------------------------------------------------------
    # No match
    # --------------------------------------------------------

    if results.empty:

        return pd.DataFrame()


    # --------------------------------------------------------
    # Sort by fitment
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

    results = results.drop_duplicates(
        subset=["Alternate Supplier"],
        keep="first"
    )


    # --------------------------------------------------------
    # Limit results
    # --------------------------------------------------------

    results = results.head(
        max_candidates
    ).copy()


    # --------------------------------------------------------
    # Remove helper columns
    # --------------------------------------------------------

    helper_columns = [
        "_normalized_incumbent",
        "_match_score"
    ]

    for column in helper_columns:

        if column in results.columns:

            results = results.drop(
                columns=[column]
            )


    # --------------------------------------------------------
    # Guarantee dashboard columns
    # --------------------------------------------------------

    for column in REQUIRED_COLUMNS:

        if column not in results.columns:

            results[column] = ""


    # --------------------------------------------------------
    # Final column order
    # --------------------------------------------------------

    final_columns = REQUIRED_COLUMNS + [
        "Supplier Risk",
        "Supplier Risk Score"
    ]

    results = results[
        [
            column
            for column in final_columns
            if column in results.columns
        ]
    ].reset_index(
        drop=True
    )


    return results


# ============================================================
# COMPATIBILITY ALIAS
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
