import streamlit as st
import pandas as pd
import openai
from io import StringIO

# Streamlit UI
st.title("🧪 Test Data Generator")

# Load API key from Streamlit secrets
try:
    openai.api_key = st.secrets["openai_api_key"]
except:
    st.error("Please add your OpenAI API key to Streamlit secrets under 'openai_api_key'.")

# Function to infer schema from uploaded CSV
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

# Sidebar: choose input method
mode = st.sidebar.radio("Input method", ["Upload CSV", "Manual schema"])

if mode == "Upload CSV":
    uploaded_file = st.sidebar.file_uploader("Upload a CSV file", type="csv")
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.write("### Preview of your data")
        st.dataframe(df.head())
        schema = infer_schema_from_csv(df)
        st.write("### Inferred schema:")
        for col, typ in schema:
            st.write(f"- **{col}**: {typ}")
else:
    st.sidebar.write("Enter one column per line in the format `column_name:type`")
    text = st.sidebar.text_area("Schema definition", "name:string\nage:integer\nsalary:float")
    schema = []
    for line in text.splitlines():
        if ":" in line:
            col, typ = line.split(":", 1)
            schema.append((col.strip(), typ.strip()))

# Select number of records
target_rows = st.slider("Number of records to generate", min_value=1, max_value=1000, value=10)

# Generate button
generate = st.button("Generate Test Data")

if generate:
    if not schema:
        st.error("No schema defined. Please upload a CSV or enter a schema manually.")
    else:
        # Build prompt
        schema_desc = ", ".join([f"{col} as {typ}" for col, typ in schema])
        prompt = f"Generate {target_rows} rows of realistic test data in CSV format with the following columns: {schema_desc}."

        # Call OpenAI using new v1 interface
        with st.spinner("Generating data..."):
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1500
            )
        content = response.choices[0].message.content.strip()

        # Display and allow download
        st.write("### Generated Data Preview")
        try:
            gen_df = pd.read_csv(StringIO(content))
            st.dataframe(gen_df)
        except Exception as e:
            st.error("Error parsing generated CSV: " + str(e))

        st.download_button(
            label="Download CSV",
            data=content,
            file_name="test_data.csv",
            mime="text/csv"
        )
