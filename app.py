import streamlit as st
import pandas as pd
import os
try:
    import plotly.express as px
except:
    import plotly.express as px
    print("Plotly import workaround triggered")

st.set_page_config(page_title="AI Talent Dashboard", layout="wide")

# LOAD DATA
@st.cache_data
def load_data():
    try:
        employees_df = pd.read_csv("employees_rows.csv")
        competency_df = pd.read_csv("employee_competency_final.csv")
        strengths_df = pd.read_csv("strengths_rows.csv")

        print("CSV loaded successfully!",
              employees_df.shape, competency_df.shape, strengths_df.shape)

        return employees_df, competency_df, strengths_df

    except Exception as e:
        print("❌ Error loading CSV:", e)
        return None, None, None

employees_df, competency_df, strengths_df = load_data()

if employees_df is None:
    st.error("❌ Data gagal dimuat. Periksa file CSV di repo.")
    st.stop()

for df in [employees_df, competency_df, strengths_df]:
    df.columns = df.columns.str.strip()

if "final_competency_match" not in competency_df.columns:
    st.error("Kolom 'final_competency_match' tidak ada di competency CSV!")
    st.stop()

df = competency_df.merge(employees_df, on="employee_id", how="left")
if "key_strengths" in strengths_df.columns:
    df = df.merge(strengths_df[["employee_id", "key_strengths"]],
                  on="employee_id", how="left")
else:
    df["key_strengths"] = ""

df = df.sort_values("final_competency_match", ascending=False).reset_index(drop=True)

# App UI
st.title("AI Talent Competency Dashboard")
st.caption("Talent readiness & competency matching using AI strategic pillars.")


# TOP TALENT LEADERBOARD
st.subheader("Top Talent Leaderboard")

display_name = "fullname" if "fullname" in df.columns else "employee_id"

top_n = st.slider("Select Top N", 5, 100, 10)
top_df = df.head(top_n)

fig = px.bar(
    top_df,
    x=display_name,
    y="final_competency_match",
    text="final_competency_match",
    labels={"final_competency_match": "Final Score"},
)
fig.update_traces(textposition="outside")
fig.update_layout(xaxis_tickangle=30, height=420)

st.plotly_chart(fig, use_container_width=True)


# TALENT STRENGTH DETAILS
st.subheader("Candidate Strength Highlights")

selected = st.selectbox("Select employee:", df[display_name].tolist())
emp = df[df[display_name] == selected].iloc[0]

st.markdown(f"### {selected}")
st.markdown(f"**Final Score:** {emp['final_competency_match']:.2f}")

ks = emp.get("key_strengths", "")
if pd.notna(ks) and ks != "":
    st.markdown("**Strongest Pillars:**")
    for p in [x.strip() for x in ks.split(",") if x.strip()]:
        st.markdown(f"- **{p}**")

# SCORE DISTRIBUTION
st.write("---")
st.subheader("Score Distribution")

fig2 = px.histogram(df, x="final_competency_match", nbins=12)
st.plotly_chart(fig2, use_container_width=True)

st.caption("Final Dashboard • AI Talent Competency • 2025")
