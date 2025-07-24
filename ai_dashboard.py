import streamlit as st
import pandas as pd
import plotly.express as px
import openai

st.set_page_config(layout="wide")
st.title("📊 AI-Powered Financial Dashboard Generator")

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file:
    excel = pd.ExcelFile(uploaded_file)
    sheet = st.selectbox("Select Sheet", excel.sheet_names)
    df = excel.parse(sheet)

    st.subheader("🔍 Data Preview")
    st.dataframe(df.head())

    date_cols = [col for col in df.columns if "date" in col.lower()]
    value_cols = [col for col in df.columns if df[col].dtype in [float, int] and df[col].nunique() > 10]
    group_cols = [col for col in df.columns if df[col].dtype == object and df[col].nunique() < 50]

    st.sidebar.header("🧠 Auto-Detected Columns")
    date_col = st.sidebar.selectbox("Select Date Column", date_cols)
    value_col = st.sidebar.selectbox("Select Value Column", value_cols)
    group_col = st.sidebar.selectbox("Select Grouping Column", group_cols)

    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df['Month'] = df[date_col].dt.to_period("M").astype(str)

    st.sidebar.header("🔎 Filters")
    unique_groups = df[group_col].dropna().unique()
    selected_groups = st.sidebar.multiselect(f"Filter by {group_col}", unique_groups, default=list(unique_groups))
    df_filtered = df[df[group_col].isin(selected_groups)]

    total = df_filtered[value_col].sum()
    monthly_summary = df_filtered.groupby("Month")[value_col].sum().reset_index()
    top_groups = df_filtered.groupby(group_col)[value_col].sum().reset_index().sort_values(value_col, ascending=False).head(10)

    col1, col2, col3 = st.columns(3)
    col1.metric("📈 Total", f"{total:,.2f}")
    col2.metric("📅 Months", df['Month'].nunique())
    col3.metric(f"🏷️ {group_col}s", len(unique_groups))

    st.subheader("📊 Monthly Trend")
    fig = px.bar(monthly_summary, x="Month", y=value_col, title="Monthly Total", height=400)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader(f"🏆 Top {group_col}s by {value_col}")
    fig2 = px.bar(top_groups, x=group_col, y=value_col, color=group_col, height=400)
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("💬 Ask Your Data")
    question = st.text_input("Ask a question about your financial data")

    if question:
        openai.api_key = st.secrets["OPENAI_API_KEY"]
        prompt = f"""
You are a financial data assistant. The dataframe 'df' has the following columns:
{', '.join(df.columns)}.

User question: "{question}"

Write Python pandas code to answer the question and visualize it using plotly.
Return ONLY the code.
"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            code = response.choices[0].message['content'].strip()
            st.code(code, language='python')
            exec(code)
        except Exception as e:
            st.error(f"❌ GPT failed: {str(e)}")

    st.subheader("📤 Download Summary")
    summary_csv = monthly_summary.to_csv(index=False).encode('utf-8')
    st.download_button("Download Monthly Summary CSV", summary_csv, "summary.csv", "text/csv")
