import streamlit as st

st.set_page_config(
    page_title="NovaDrive CRO Dashboard",
    page_icon="🏭",
    layout="wide"
)

st.title("NovaDrive CRO Dashboard")
st.caption("Supplier Network & Risk Intelligence")

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Go to",
    [
        "Executive Overview",
        "Supplier Network",
        "Risk Assessment",
        "Events & Alerts",
        "Alternate Suppliers"
    ]
)

if page == "Executive Overview":
    st.header("Executive Overview")
    st.info("Dashboard overview coming next.")

elif page == "Supplier Network":
    st.header("Supplier Network")

elif page == "Risk Assessment":
    st.header("Risk Assessment")

elif page == "Events & Alerts":
    st.header("Events & Alerts")

elif page == "Alternate Suppliers":
    st.header("Alternate Suppliers")
    st.info("Alternate supplier analysis will be added after Part 4.")
