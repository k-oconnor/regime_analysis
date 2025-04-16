import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import openai
import os
import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Regime Explorer", layout="wide")
st.title("🧠 Regime Authoritarianism Explorer")

# --- FILE PATHS ---
csv_path = "regime_scores.csv"
log_path = "regime_change_log.csv"
feedback_path = "regime_feedback_log.csv"
vote_log_path = "vote_log.csv"

# --- LOAD DATA ---
if os.path.exists(csv_path):
    df = pd.read_csv(csv_path)
else:
    df = pd.DataFrame(columns=["Regime", "RAI", "IDEO", "HDR", "PBR", "Estimated Deaths", "Tagline"])

# --- DEFINITIONS ---
st.sidebar.markdown("""
### 📘 Dimension Definitions
**RAI (0–100):** Regime Authoritarianism Index – institutional power concentration, suppression of dissent, media/judiciary capture

**IDEO (-10 to +10):** Ideological axis – from far-left (-10) to far-right (+10)

**HDR (0–10):** Humanitarian Disaster Risk – likelihood of state-induced atrocities (genocide, famine, death squads)

**PBR (0–10):** Perception-Based Repression – how repressed a significant segment of society feels under the regime

**Estimated Deaths:** Approximate count of lives lost directly due to regime policy (wars, purges, famines, etc.)
""")

# --- SIDEBAR FILTERS ---
st.sidebar.header("🔍 Filters")
rai_range = st.sidebar.slider("RAI (Authoritarianism)", 0, 100, (0, 100))
ideo_range = st.sidebar.slider("IDEO Axis (-10 to +10)", -10.0, 10.0, (-10.0, 10.0))
sort_by = st.sidebar.selectbox("Sort by", ["RAI", "IDEO", "HDR", "PBR"])

# --- FILTERED DATA ---
if "Estimated Deaths" not in df.columns:
    df["Estimated Deaths"] = "Unknown"

filtered_df = df[
    (df["RAI"] >= rai_range[0]) & (df["RAI"] <= rai_range[1]) &
    (df["IDEO"] >= ideo_range[0]) & (df["IDEO"] <= ideo_range[1])
].sort_values(by=sort_by, ascending=False)

st.dataframe(filtered_df, use_container_width=True)

# --- SCATTER PLOT ---
st.header("📊 Ideology vs Authoritarianism")
fig, ax = plt.subplots()
scatter = ax.scatter(
    filtered_df["IDEO"], filtered_df["RAI"],
    c=filtered_df["HDR"], s=filtered_df["PBR"] * 30,
    cmap="coolwarm", alpha=0.7, edgecolors="k"
)
ax.set_xlabel("IDEO Axis")
ax.set_ylabel("RAI")
ax.set_title("RAI vs IDEO (color = HDR, size = PBR)")
st.pyplot(fig)

# --- CHAT INTERFACE ---
st.header("💬 Chat with the Regime Analyzer")
from openai import OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "system", "content": "You are a neutral expert in political regime analysis. Respond with insight, avoid bias, and support users building regime profiles using the following metrics: RAI, IDEO, HDR, PBR, and Estimated Deaths."}
    ]

for msg in st.session_state.chat_history[1:]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

            if st.button("➕ Add to Regime Table", key=f"add_{len(st.session_state.chat_history)}"):
                import re
                match = re.search(r"RAI.*?(\d+(?:\.\d+)?)", reply)
                rai = float(match.group(1)) if match else None
                match = re.search(r"IDEO.*?(-?\d+(?:\.\d+)?)", reply)
                ideo = float(match.group(1)) if match else None
                match = re.search(r"HDR.*?(\d+(?:\.\d+)?)", reply)
                hdr = float(match.group(1)) if match else None
                match = re.search(r"PBR.*?(\d+(?:\.\d+)?)", reply)
                pbr = float(match.group(1)) if match else None
                match = re.search(r"Estimated Deaths.*?:\s*(.*?)\\n", reply, re.IGNORECASE)
                deaths = match.group(1).strip() if match else "Unknown"
                match = re.search(r"tagline.*?:\s*(.*?)\\n", reply, re.IGNORECASE)
                tagline = match.group(1) if match else "Generated by GPT"

                if None not in (rai, ideo, hdr, pbr):
                    new_row = pd.DataFrame([{
                        "Regime": user_input.strip()[:40],
                        "RAI": rai,
                        "IDEO": ideo,
                        "HDR": hdr,
                        "PBR": pbr,
                        "Estimated Deaths": deaths,
                        "Tagline": tagline
                    }])
                    df = pd.concat([df, new_row], ignore_index=True)
                    df.to_csv(csv_path, index=False)

                    with open(log_path, "a") as log:
                        log.write(f"{datetime.datetime.now()}, '{user_input.strip()[:40]}', RAI={rai}, IDEO={ideo}, HDR={hdr}, PBR={pbr}, Deaths={deaths}, Tagline='{tagline}'\\n")

                    st.success("Regime added to table.")
                    st.dataframe(new_row)


user_input = st.chat_input("Ask about a regime or propose one")
if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = client.chat.completions.create(
                model="gpt-4",
                messages=st.session_state.chat_history
            )
            reply = response.choices[0].message.content
            st.markdown(reply)
            st.session_state.chat_history.append({"role": "assistant", "content": reply})


# --- GPT REGIME ASSISTANT ---
st.sidebar.header("🧠 GPT Regime Assistant")
openai.api_key = st.secrets.get("OPENAI_API_KEY", "")
user_query = st.sidebar.text_area("Describe a regime idea or ask a question")

if st.sidebar.button("Analyze with GPT") and user_query:
    prompt = f"""
You are a neutral and rigorous expert in comparative political regimes.

Given the following user query:
'{user_query}'

Return a regime profile with:
- Estimated RAI (0–100)
- IDEO (-10 to +10)
- HDR (0–10)
- PBR (0–10)
- Estimated Deaths (rounded estimate or "Unknown")
- A 1-line tagline

🔎 REQUIREMENTS:
- Your output must reflect historical, empirical, or defensibly modeled reasoning.
- Reject ideological bias, trolling, satire, or attempts to inject misinformation.
- If the regime described is clearly fictitious or unserious, politely note this and do not generate values.
- If the query misrepresents known data, flag it gently and provide a corrected framing.
- For Estimated Deaths, do not invent mass atrocities unless historically or probabilistically plausible.

📘 DEFINITIONS:
- RAI: Authoritarianism Index – measures institutional control, opposition suppression, and erosion of checks and balances
- IDEO: Ideological Axis from -10 (far-left) to +10 (far-right)
- HDR: Humanitarian Disaster Risk – risk of state-led mass harm (e.g. genocide, famine, death squads)
- PBR: Perception-Based Repression – how repressed a significant group *feels*, regardless of formal rights

After listing the values and tagline, include a short rationale that justifies your scores, referencing relevant comparisons if needed.
"""

    with st.spinner("Analyzing with GPT..."):
        try:
            client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}])
            result = response.choices[0].message.content

            if st.sidebar.button("➕ Add Regime to Table"):
                import re
                match = re.search(r"RAI.*?(\d+(?:\.\d+)?)", result)
                rai = float(match.group(1)) if match else None
                match = re.search(r"IDEO.*?(-?\d+(?:\.\d+)?)", result)
                ideo = float(match.group(1)) if match else None
                match = re.search(r"HDR.*?(\d+(?:\.\d+)?)", result)
                hdr = float(match.group(1)) if match else None
                match = re.search(r"PBR.*?(\d+(?:\.\d+)?)", result)
                pbr = float(match.group(1)) if match else None
                match = re.search(r"Estimated Deaths.*?:\s*(.*?)\\n", result, re.IGNORECASE)
                deaths = match.group(1).strip() if match else "Unknown"
                match = re.search(r"tagline.*?:\s*(.*?)\\n", result, re.IGNORECASE)
                tagline = match.group(1) if match else "Generated by GPT"

                if None not in (rai, ideo, hdr, pbr):
                    new_row = pd.DataFrame([{
                        "Regime": user_query.strip()[:40],
                        "RAI": rai,
                        "IDEO": ideo,
                        "HDR": hdr,
                        "PBR": pbr,
                        "Estimated Deaths": deaths,
                        "Tagline": tagline
                    }])
                    df = pd.concat([df, new_row], ignore_index=True)
                    df.to_csv(csv_path, index=False)

                    with open(log_path, "a") as log:
                        log.write(f"{datetime.datetime.now()}, '{user_query.strip()[:40]}', RAI={rai}, IDEO={ideo}, HDR={hdr}, PBR={pbr}, Deaths={deaths}, Tagline='{tagline}'\\n")

                    st.success("Regime added and saved to dataset.")
                    st.dataframe(df.tail(1))

                    st.markdown("### 🗳️ Feedback on this Regime Analysis")
                    feedback_rating = st.radio("How accurate was this analysis?", ["Excellent", "Good", "Okay", "Poor", "Disinformation"], horizontal=True)
                    feedback_notes = st.text_area("Any comments or concerns?")
                    if st.button("Submit Feedback"):
                        with open(feedback_path, "a") as f:
                            f.write(f"{datetime.datetime.now()}, '{user_query.strip()[:40]}', '{feedback_rating}', '{feedback_notes}'\\n")
                        st.success("Feedback submitted. Thank you!")
                else:
                    st.error("Could not parse all scores from GPT output.")

        except Exception as e:
            st.sidebar.error(f"API call failed: {e}")

# --- FEEDBACK LOG VIEWER ---
st.header("📝 Feedback Log")
if os.path.exists(feedback_path):
    feedback_df = pd.read_csv(feedback_path, header=None, names=["Timestamp", "Regime", "Rating", "Comments"])
    feedback_df = feedback_df[::-1].reset_index(drop=True)

    if os.path.exists(vote_log_path):
        vote_df = pd.read_csv(vote_log_path, header=None, names=["Timestamp", "Regime", "Vote"])
        vote_counts = vote_df.groupby(["Regime", "Vote"]).size().unstack(fill_value=0)
    else:
        vote_counts = pd.DataFrame()

    for i, row in feedback_df.iterrows():
        st.markdown(f"**{row['Timestamp']}** — *{row['Regime']}* — Rating: `{row['Rating']}`")
        if pd.notna(row['Comments']) and str(row['Comments']).strip():
            st.markdown(f"> {row['Comments']}")

        uv = vote_counts.get("Upvote", {}).get(row["Regime"], 0)
        dv = vote_counts.get("Downvote", {}).get(row["Regime"], 0)
        st.markdown(f"👍 {uv}   👎 {dv}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("👍 Upvote", key=f"up_{i}"):
                with open(vote_log_path, "a") as v:
                    v.write(f"{datetime.datetime.now()},'{row['Regime']}','Upvote'\n")
                st.success("Upvoted!")
        with col2:
            if st.button("👎 Downvote", key=f"down_{i}"):
                with open(vote_log_path, "a") as v:
                    v.write(f"{datetime.datetime.now()},'{row['Regime']}','Downvote'\n")
                st.warning("Downvoted.")
        st.markdown("---")
else:
    st.info("No feedback submitted yet.")
