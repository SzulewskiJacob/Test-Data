import streamlit as st
import pandas as pd
import openai
from io import StringIO

# --- Page setup ---
st.set_page_config(layout="wide")
st.title("🧪 Test Data Generator")

# --- Load API key ---
try:
    openai.api_key = st.secrets["openai_api_key"]
except:
    st.error("Please add your OpenAI API key to Streamlit secrets under 'openai_api_key'.")
    st.stop()

# --- Helper: infer schema from DataFrame ---
def infer_schema_from_csv(df: pd.DataFrame):
    schema = []
    for col, dtype in df.dtypes.items():
        if pd.api.types.is_integer_dtype(dtype):
            schema.append((col, "integer"))
        elif pd.api.types.is_float_dtype(dtype):
            schema.append((col, "float"))
        elif pd.api.types.is_bool_dtype(dtype):
            schema.append((col, "boolean"))
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            schema.append((col, "date"))
        else:
            schema.append((col, "string"))
    return schema

# --- Session state for manual schema fields ---
if "schema_fields" not in st.session_state:
    st.session_state.schema_fields = [{"name": "column_1", "type": "string"}]

# --- Main controls ---
mode = st.radio("Input method", ["Upload CSV", "Manual schema"])
target_rows = st.slider("Number of records to generate", min_value=1, max_value=1000, value=10)
generate = st.button("Generate Test Data")

# --- Grey panel for schema controls ---
st.markdown(
    """
    <div style='background-color:#f0f2f6; padding:16px; border-radius:8px; margin-top:16px;'>
    """, unsafe_allow_html=True
)
schema = []

if mode == "Upload CSV":
    st.header("Upload CSV to Infer Schema")
    uploaded_file = st.file_uploader("Upload a CSV file", type="csv")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.subheader("Preview")
        st.dataframe(df.head(), use_container_width=True)
        schema = infer_schema_from_csv(df)
        st.subheader("Inferred Schema")
        for col, typ in schema:
            st.write(f"- **{col}**: {typ}")

elif mode == "Manual schema":
    st.header("Define Schema Manually")
    remove_index = None
    for i, field in enumerate(st.session_state.schema_fields):
        cols = st.columns([0.5, 3, 1])
        if cols[0].button("🗑️", key=f"remove_{i}"):
            remove_index = i
        name = cols[1].text_input("Field name", value=field["name"], key=f"name_{i}")
        dtype = cols[2].selectbox("Type", ["string", "integer", "float", "boolean", "date"],
                                 index=["string", "integer", "float", "boolean", "date"].index(field["type"]),
                                 key=f"type_{i}")
        st.session_state.schema_fields[i]["name"] = name
        st.session_state.schema_fields[i]["type"] = dtype
    if remove_index is not None:
        st.session_state.schema_fields.pop(remove_index)
        st.experimental_rerun()
    if st.button("Add Field"):
        count = len(st.session_state.schema_fields) + 1
        st.session_state.schema_fields.append({"name": f"column_{count}", "type": "string"})
        st.experimental_rerun()
    schema = [(f["name"], f["type"]) for f in st.session_state.schema_fields]

st.markdown("</div>", unsafe_allow_html=True)

# --- Generate and display results ---
if generate:
    if not schema or any(col.strip() == "" for col, _ in schema):
        st.error("Please ensure you have defined a valid schema before generating.")
    else:
        desc = ", ".join([f"{col} as {typ}" for col, typ in schema])
        prompt = f"Generate {target_rows} rows of realistic test data in CSV format with the following columns: {desc}."
        with st.spinner("Generating..."):
            resp = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=target_rows * len(schema) * 20
            )
        content = resp.choices[0].message.content.strip()
        st.subheader("Generated Data Preview")
        try:
            gen_df = pd.read_csv(StringIO(content))
            st.dataframe(gen_df, use_container_width=True)
        except Exception as e:
            st.error(f"Error parsing generated CSV: {e}")
        st.download_button(
            label="Download CSV",
            data=content,
            file_name="test_data.csv",
            mime="text/csv"
        )
