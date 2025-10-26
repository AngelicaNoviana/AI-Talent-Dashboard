# app.py (robust version)
import streamlit as st
import pandas as pd
import os
try:
    import plotly.express as px
except:
    import plotly.express as px
    print("Plotly import workaround triggered")


st.set_page_config(page_title="AI Talent Dashboard", layout="wide")

# ----------------------------------------------------------
# LOAD DATA (robust)
# ----------------------------------------------------------
@st.cache_data
def load_data():
    # filenames you have in folder
    score_file = "employee_competency_final.csv"
    emp_file = "employees_rows.csv"
    str_file = "strengths_rows.csv"  # adjust if your file has slightly different name

    print("✅ CSV files loaded:", employees_df.shape, competency_df.shape, strengths_df.shape)
    print("Columns in employees_df:", employees_df.columns.tolist())
    print("Columns in competency_df:", competency_df.columns.tolist())
    print("Columns in strengths_df:", strengths_df.columns.tolist())


    # read safely (if file not found, raise friendly error)
    for f in [score_file, emp_file]:
        if not os.path.exists(f):
            raise FileNotFoundError(f"File not found: {f}. Pastikan CSV ada di folder yang sama dengan app.py")

    df_score = pd.read_csv(score_file)
    df_emp = pd.read_csv(emp_file)

    # strengths file is optional, try to load
    if os.path.exists(str_file):
        df_str = pd.read_csv(str_file)
    else:
        df_str = pd.DataFrame(columns=["employee_id"])  # empty DF as fallback

    # standardize column names (strip spaces)
    df_score.columns = df_score.columns.str.strip()
    df_emp.columns = df_emp.columns.str.strip()
    df_str.columns = df_str.columns.str.strip()

    # ensure employee_id column exists in all (or rename common variants)
    # possible variants mapping
    def ensure_col(df, possible_names, canonical):
        for n in possible_names:
            if n in df.columns:
                if n != canonical:
                    df = df.rename(columns={n: canonical})
                return df
        return df

    df_score = ensure_col(df_score, ["employee_id", "employee id", "emp_id", "id"], "employee_id")
    df_emp = ensure_col(df_emp, ["employee_id", "employee id", "emp_id", "id"], "employee_id")
    df_str = ensure_col(df_str, ["employee_id", "employee id", "emp_id", "id"], "employee_id")

    # merge left (score is driver)
    df = df_score.merge(df_emp, on="employee_id", how="left")

    # merge strengths if there is any plausible column for pillars
    # normalize possible strengths column names to "key_strengths"
    possible_strength_cols = ["key_strengths", "top_pillars", "key_strength", "strengths", "top_strengths", "top_pillars"]
    found = None
    for c in possible_strength_cols:
        if c in df_str.columns:
            df_str = df_str.rename(columns={c: "key_strengths"})
            found = "key_strengths"
            break

    # if df_str has 'employee_id' and 'key_strengths' after rename, merge
    if "employee_id" in df_str.columns and "key_strengths" in df_str.columns:
        df = df.merge(df_str[["employee_id", "key_strengths"]], on="employee_id", how="left")
    else:
        # no strengths file or column available — create empty key_strengths
        df["key_strengths"] = None

    # sort by final score if column exists, else fallback to other name
    score_col = None
    for c in ["final_competency_match", "final_score", "final_competency_score", "final_match"]:
        if c in df.columns:
            score_col = c
            break
    if score_col is None:
        raise KeyError("Tidak menemukan kolom skor akhir (final_competency_match). Periksa nama kolom di CSV 'employee_competency_final.csv'.")
    # ensure numeric
    df[score_col] = pd.to_numeric(df[score_col], errors="coerce")
    df = df.sort_values(score_col, ascending=False).reset_index(drop=True)
    # unify name used later
    df = df.rename(columns={score_col: "final_competency_match"})

    return df

# load dataframe
df = load_data()

st.title("🤖 AI Talent Competency Dashboard")
st.caption("Talent readiness & competency matching using AI strategic pillars.")

# ----------------------------------------------------------
# TOP TALENT LEADERBOARD
# ----------------------------------------------------------
st.subheader("🏆 Top Talent Leaderboard")

top_n = st.number_input("Show top N (for chart)", min_value=5, max_value=100, value=10, step=1)
top_df = df.head(int(top_n))

fig = px.bar(
    top_df,
    x="fullname" if "fullname" in top_df.columns else "employee_id",
    y="final_competency_match",
    text="final_competency_match",
    labels={"fullname": "Employee", "final_competency_match": "Final Score"}
)
fig.update_traces(textposition="outside")
fig.update_layout(xaxis_tickangle=30, height=400)

st.plotly_chart(fig, use_container_width=True)

# ----------------------------------------------------------
# KEY STRENGTHS PER TALENT (robust handling)
# ----------------------------------------------------------
st.subheader("💡 Candidate Strength Highlights")

# dropdown shows fullname if available
display_name_col = "fullname" if "fullname" in df.columns else "employee_id"
selected = st.selectbox("Select employee:", df[display_name_col].tolist())

# get employee row
emp_row = df[df[display_name_col] == selected].iloc[0]

# safe access final score
final_score = emp_row.get("final_competency_match", None)
st.markdown(f"### {selected}")
if final_score is not None and not pd.isna(final_score):
    st.markdown(f"**Final Score:** {final_score:.2f}")
else:
    st.markdown("**Final Score:** -")

# Try to get key_strengths column — many possible names handled earlier; final column is 'key_strengths'
ks = None
if "key_strengths" in df.columns and pd.notna(emp_row.get("key_strengths")):
    ks = str(emp_row.get("key_strengths")).strip()
    # sometimes stored as list-like string; normalize
    if ks.startswith("[") and ks.endswith("]"):
        ks = ks[1:-1]
elif "top_pillars" in df.columns and pd.notna(emp_row.get("top_pillars")):
    ks = str(emp_row.get("top_pillars")).strip()

# If still no ks, attempt to compute top 3 pillars from a per-employee competencies CSV if available
if not ks or ks == "None" or ks == "nan":
    # try to find a competencies file in cwd to compute top pillars
    # possible filenames
    comp_files = ["competencies_yearly.csv", "competencies.csv", "competencies_rows.csv", "competencies_years.csv"]
    comp_file_found = None
    for fname in comp_files:
        if os.path.exists(fname):
            comp_file_found = fname
            break

    if comp_file_found:
        # compute avg per pillar for this employee across years
        cdf = pd.read_csv(comp_file_found)
        cdf.columns = cdf.columns.str.strip()
        # ensure employee_id and pillar_code and score exist
        if set(["employee_id", "pillar_code", "score"]).issubset(cdf.columns):
            sub = cdf[cdf["employee_id"] == emp_row["employee_id"]]
            if not sub.empty:
                agg = sub.groupby("pillar_code", as_index=False)["score"].mean()
                agg = agg.sort_values("score", ascending=False).head(3)
                ks = ", ".join(agg["pillar_code"].astype(str).tolist())
    # if cannot compute ks, fallback to empty
    if not ks or ks in ("None", "nan"):
        ks = ""

# display pillars
if ks:
    st.markdown("✅ **Strongest Pillars:**")
    for p in [x.strip() for x in ks.split(",") if x.strip()]:
        st.markdown(f"- **{p}**")

# ----------------------------------------------------------
# SCORE DISTRIBUTION
# ----------------------------------------------------------
st.write("---")
st.subheader("📊 Score Distribution")

fig2 = px.histogram(df, x="final_competency_match", nbins=15)
st.plotly_chart(fig2, use_container_width=True)

st.caption("Final Dashboard")


