import streamlit as st
from d3b_redcap_api.redcap import REDCapStudy
import sys
import xlsxwriter
import arrow
import pandas
import base64
from io import BytesIO
import re

st.set_page_config(
    page_title="REDCap Patient Last Seen Report",
    page_icon="💎",
    layout="centered",
    initial_sidebar_state="expanded",
)


@st.cache(ttl=600, show_spinner=False)
def get_date_fields(api_token):
    r = REDCapStudy("https://redcap.chop.edu/api/", api_token)
    with st.spinner("Fetching project metadata..."):
        date_fields = sorted(
            f["field_name"]
            for f in r.get_data_dictionary()
            if "date" in f["text_validation_type_or_show_slider_number"]
        )
    return date_fields


@st.cache(ttl=600, show_spinner=False)
def get_records(api_token, date_fields):
    r = REDCapStudy("https://redcap.chop.edu/api/", api_token)
    with st.spinner("Fetching project records..."):
        return r.get_records(fields=date_fields)


@st.cache(ttl=600, show_spinner=False)
def filter_dates(records, chosen_date_fields):
    values = {}
    for rec in records:
        if rec["field_name"] in chosen_date_fields:
            values.setdefault(rec["record"], set()).add(rec["value"])
    dates = {k: sorted(v)[-1] for k, v in values.items()}
    return dates


st.markdown(
    "This program finds the most recent date for each subject "
    "selected from one or more date fields and compares that with "
    "today's date to indicate how long it has been since the "
    "subject's most recent visit."
)

api_token = st.sidebar.text_input("Project API Token")

if st.sidebar.button("Reload"):
    st.caching.clear_cache()

if not api_token:
    st.stop()

date_fields = get_date_fields(api_token)
records = get_records(api_token, date_fields)


chosen_date_fields_1 = st.sidebar.multiselect(
    "Choose one or more fields to find the most recent date from:", date_fields
)
st.sidebar.text("OR (don't do both)")
chosen_date_fields_2 = st.sidebar.text_input(
    "Type/paste them here separated by commas like asdf_hjkl,asdf_hjkl,asdf_hjkl"
)
chosen_date_fields_2 = re.sub(r"[^\w\s,]", "", chosen_date_fields_2)

chosen_date_fields = [
    v.strip() for v in chosen_date_fields_2.split(",") if v
] or chosen_date_fields_1

if not chosen_date_fields:
    st.info("Please choose one or more date fields to use in the sidebar on the left.")
    st.stop()

dates = filter_dates(records, chosen_date_fields)

if not dates:
    st.stop()

today = arrow.now()
table_header = ["Subject", "Date Last Seen", "Days Ago"]
table = []
for i in sorted(dates.items(), key=lambda i: i[1]):
    then = arrow.get(i[1])
    days_ago = (today - then).days
    table.append(dict(zip(table_header, [i[0], i[1], days_ago])))

df = (
    pandas.DataFrame(table)
    .sort_values(by="Days Ago", kind="mergesort", key=lambda col: col >= 0)
    .reset_index(drop=True)
)
df.index = df.index + 1

msg = f"Using fields: [{', '.join(chosen_date_fields)}]"

year_sum = sum(df["Days Ago"] > 365)
future_sum = sum(df["Days Ago"] < 0)
msg += f"  \nLast seen more than a year ago:  {year_sum}"
if future_sum > 0:
    msg += f"  \nLast seen IN THE FUTURE???:      {future_sum}"

st.text(msg)


def color_days(s):
    if s["Days Ago"] < 0:
        return ["background-color: #FFDDDD"] * len(s)
    elif s["Days Ago"] > 365:
        return ["background-color: #D2EFFF"] * len(s)
    else:
        return [""] * len(s)


df = df.style.apply(color_days, axis=1)


def to_excel(df):
    output = BytesIO()
    writer = pandas.ExcelWriter(output, engine="xlsxwriter")
    df.to_excel(writer, index=False)
    writer.save()
    return output.getvalue()


button_css = """
<style>
.btn {
  border: 1px solid DodgerBlue;
  color: DodgerBlue;
  padding: 12px 30px;
  cursor: pointer;
  font-size: 18px;
  border-radius:5px;
  text-decoration: none;
}

.btn:hover {
  background-color: RoyalBlue;
  color: White;
}
</style>
"""

st.markdown(button_css, unsafe_allow_html=True)
b64 = base64.b64encode(to_excel(df)).decode()
download_link = f'<a class="btn" target="_blank" href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="Report.xlsx">Download this table as "Report.xlsx"</a>'
st.markdown(download_link, unsafe_allow_html=True)

st.table(df)
