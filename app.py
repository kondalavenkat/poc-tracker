import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime
from io import BytesIO
import os
import time
from pathlib import Path
from streamlit_autorefresh import st_autorefresh

# ──────────────────────────────────────────────
#  CONFIG
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="PoC Command Center",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
* { font-family: 'Inter', sans-serif; }

.kpi-card {
    background: linear-gradient(135deg, #1e2030 0%, #272b40 100%);
    border: 1px solid #363b54;
    border-radius: 16px;
    padding: 20px 18px;
    text-align: center;
    transition: transform 0.2s, box-shadow 0.2s;
}
.kpi-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(108,99,255,.25);
}
.kpi-number {
    font-size: 2.4rem;
    font-weight: 800;
    background: linear-gradient(135deg, #6C63FF, #48C9B0);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1.1;
}
.kpi-label {
    font-size: 0.85rem;
    color: #9CA3AF;
    margin-top: 6px;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 600;
}

.badge {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.5px;
}
.badge-completed   { background: #064e3b; color: #6ee7b7; }
.badge-wip         { background: #1e3a5f; color: #60a5fa; }
.badge-no          { background: #3b3520; color: #fcd34d; }

.progress-outer {
    background: #1f2235;
    border-radius: 10px;
    height: 14px;
    overflow: hidden;
    width: 100%;
}
.progress-inner {
    height: 100%;
    border-radius: 10px;
    transition: width 0.6s ease;
}

.alert-box {
    background: linear-gradient(135deg, #4a1d1d, #3b1515);
    border-left: 4px solid #ef4444;
    border-radius: 8px;
    padding: 12px 18px;
    margin-bottom: 8px;
    color: #fca5a5;
    font-size: 0.9rem;
}

.section-header {
    font-size: 1.15rem;
    font-weight: 700;
    color: #e2e8f0;
    margin: 24px 0 12px 0;
    display: flex;
    align-items: center;
    gap: 8px;
}

.detail-card {
    background: linear-gradient(135deg, #1e2030 0%, #272b40 100%);
    border: 1px solid #363b54;
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 12px;
}
.detail-card h2 { color: #6C63FF; margin: 0 0 16px 0; }
.detail-card p  { color: #d1d5db; margin: 6px 0; }
.detail-label   { color: #9CA3AF; font-weight: 600; }

.tool-tag {
    display: inline-block;
    background: #2d2f4e;
    border: 1px solid #4a4d6e;
    color: #a5b4fc;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    margin: 2px 3px;
    font-weight: 500;
}

.challenge-box {
    background: #1f1520;
    border-left: 4px solid #f59e0b;
    border-radius: 8px;
    padding: 10px 16px;
    color: #fcd34d;
    font-size: 0.88rem;
    margin-top: 8px;
}

footer { visibility: hidden; }
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #13152a 0%, #1a1d32 100%);
}
</style>
""", unsafe_allow_html=True)

# ── Auto-refresh every 30 seconds ─────────────
refresh_count = st_autorefresh(interval=30_000, limit=None, key="live_refresh")

# ──────────────────────────────────────────────
#  DATA
# ──────────────────────────────────────────────
DATA_PATH = Path(__file__).parent / "poc_data.csv"

# Ensure CSV exists so Cloud deployment doesn't crash
if not DATA_PATH.exists():
    empty_df = pd.DataFrame(columns=[
        "POC Name", "Tools & Requirements", "Completion %", 
        "Status", "Expected End Date", "Recent Comments", "Challenges"
    ])
    empty_df.to_csv(DATA_PATH, index=False)

@st.cache_data(ttl=15)  # Cache data for 15s, then re-read from disk
def load_data_cached():
    return load_data()

def load_data():
    df = pd.read_csv(DATA_PATH, parse_dates=["Expected End Date"])
    df["Completion %"] = df["Completion %"].astype(int)
    df["Challenges"] = df["Challenges"].fillna("")
    df["Recent Comments"] = df["Recent Comments"].fillna("")
    return df

def save_data(dataframe):
    dataframe.to_csv(DATA_PATH, index=False)

# ── Hidden changelog (backend only) ──────────
CHANGELOG_PATH = Path(__file__).parent / "changelog.csv"

def log_change(action, poc_name, details=""):
    """Silently records every change to data/changelog.csv. Not visible on dashboard."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = pd.DataFrame([{
        "Timestamp": timestamp,
        "Action": action,
        "POC Name": poc_name,
        "Details": details,
    }])
    if CHANGELOG_PATH.exists():
        entry.to_csv(CHANGELOG_PATH, mode="a", header=False, index=False)
    else:
        entry.to_csv(CHANGELOG_PATH, index=False)

df = load_data_cached()
today = pd.Timestamp(datetime.now().date())

# ──────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────
STATUS_COLORS = {
    "Completed": "#10b981",
    "WIP": "#3b82f6",
    "NO": "#f59e0b",
}

def status_badge(s):
    cls = {"Completed": "badge-completed", "WIP": "badge-wip", "NO": "badge-no"}.get(s, "")
    label = {"NO": "Not Started"}.get(s, s)
    return f'<span class="badge {cls}">{label}</span>'

def progress_html(pct):
    c = "#10b981" if pct >= 80 else "#3b82f6" if pct >= 50 else "#f59e0b" if pct >= 25 else "#ef4444"
    return f'<div class="progress-outer"><div class="progress-inner" style="width:{pct}%;background:linear-gradient(90deg,{c}cc,{c});"></div></div>'

def kpi(number, label):
    return f'<div class="kpi-card"><div class="kpi-number">{number}</div><div class="kpi-label">{label}</div></div>'

def tool_tags(tools_str):
    return " ".join(f'<span class="tool-tag">{t.strip()}</span>' for t in str(tools_str).split(";") if t.strip())

def get_delayed(data):
    d = data[(data["Status"] != "Completed") & (data["Expected End Date"] < today)]
    return [(r["POC Name"], (today - r["Expected End Date"]).days) for _, r in d.iterrows()]

# ──────────────────────────────────────────────
#  SIDEBAR
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚀 PoC Command Center")
    st.markdown("---")
    page = st.radio("Navigate", [
        "📊 Overview",
        "📈 Progress Tracker",
        "🔍 PoC Details",
        "✏️ Manage PoCs",
    ], label_visibility="collapsed")
    st.markdown("---")
    st.markdown("### 🔧 Filters")
    statuses = df["Status"].unique().tolist()
    sel_status = st.multiselect("Status", statuses, default=statuses)
    search = st.text_input("🔎 Search PoC", "")
    st.markdown("---")
    st.markdown(f"🔄 **Last Refreshed**")
    st.caption(f"{datetime.now().strftime('%I:%M:%S %p')}")
    st.markdown("<small style='color:#6b7280;'>Auto-refreshes every 30s</small>", unsafe_allow_html=True)

fdf = df[df["Status"].isin(sel_status)].copy()
if search:
    fdf = fdf[fdf["POC Name"].str.contains(search, case=False)]

# ──────────────────────────────────────────────
#  📊 OVERVIEW
# ──────────────────────────────────────────────
if page == "📊 Overview":
    st.markdown("# 📊 PoC Command Center")
    st.markdown("")

    # ── Live KPI Panel (auto-updates every 30s independently) ──
    @st.fragment(run_every="30s")
    def live_kpi_panel():
        live_df = load_data()  # Always get fresh data
        live_fdf = live_df[live_df["Status"].isin(sel_status)].copy()
        if search:
            live_fdf = live_fdf[live_fdf["POC Name"].str.contains(search, case=False)]

        total = len(live_fdf)
        completed = len(live_fdf[live_fdf["Status"] == "Completed"])
        wip = len(live_fdf[live_fdf["Status"] == "WIP"])
        not_started = len(live_fdf[live_fdf["Status"] == "NO"])
        avg_pct = int(live_fdf["Completion %"].mean()) if total else 0

        c1, c2, c3, c4, c5 = st.columns(5)
        for col, (n, l) in zip([c1, c2, c3, c4, c5], [
            (total, "Total PoCs"), (completed, "Completed"), (wip, "WIP"),
            (not_started, "Not Started"), (f"{avg_pct}%", "Avg Completion"),
        ]):
            col.markdown(kpi(n, l), unsafe_allow_html=True)

        # Live pulse indicator
        st.caption(f"🟢 Live — Last synced: {datetime.now().strftime('%I:%M:%S %p')}")

    live_kpi_panel()

    st.markdown("")

    # Alerts
    delayed = get_delayed(fdf)
    if delayed:
        st.markdown('<div class="section-header">🚨 Delayed PoCs</div>', unsafe_allow_html=True)
        for name, days in delayed:
            st.markdown(f'<div class="alert-box">⚠️ <strong>{name}</strong> delayed by <strong>{days} day{"s" if days!=1 else ""}</strong></div>', unsafe_allow_html=True)
        st.markdown("")

    left, right = st.columns([1, 1.6])

    with left:
        st.markdown('<div class="section-header">🍩 Status Distribution</div>', unsafe_allow_html=True)
        sc = fdf["Status"].value_counts().reset_index()
        sc.columns = ["Status", "Count"]
        fig = px.pie(sc, values="Count", names="Status", hole=0.55, color="Status",
                     color_discrete_map=STATUS_COLORS)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          font_color="#e2e8f0", margin=dict(t=20,b=20,l=20,r=20),
                          legend=dict(orientation="h", y=-0.1), height=340)
        fig.update_traces(textinfo="label+value", textfont_size=13)
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown('<div class="section-header">📊 Completion by PoC</div>', unsafe_allow_html=True)
        bar_df = fdf[["POC Name", "Completion %", "Status"]].sort_values("Completion %", ascending=True)
        fig2 = px.bar(bar_df, x="Completion %", y="POC Name", orientation="h",
                      color="Status", color_discrete_map=STATUS_COLORS, text="Completion %")
        fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                           font_color="#e2e8f0", margin=dict(t=20,b=20,l=20,r=20),
                           xaxis_title="", yaxis_title="", showlegend=False, height=340)
        fig2.update_traces(texttemplate="%{text}%", textposition="outside")
        st.plotly_chart(fig2, use_container_width=True)


# ──────────────────────────────────────────────
#  📈 PROGRESS TRACKER
# ──────────────────────────────────────────────
elif page == "📈 Progress Tracker":
    st.markdown("# 📈 Progress Tracker")
    st.markdown("")

    buf = BytesIO()
    fdf.to_excel(buf, index=False, engine="openpyxl")
    st.download_button("📥 Export to Excel", data=buf.getvalue(),
                       file_name="poc_tracker.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.markdown("")

    # Header
    h1, h2, h3, h4, h5 = st.columns([2.5, 3, 1.2, 3, 1])
    h1.markdown("**PoC Name**")
    h2.markdown("**Tools & Requirements**")
    h3.markdown("**Status**")
    h4.markdown("**Progress**")
    h5.markdown("**%**")
    st.markdown("---")

    for _, row in fdf.iterrows():
        c1, c2, c3, c4, c5 = st.columns([2.5, 3, 1.2, 3, 1])
        c1.markdown(f"**{row['POC Name']}**")
        c2.markdown(tool_tags(row["Tools & Requirements"]), unsafe_allow_html=True)
        c3.markdown(status_badge(row["Status"]), unsafe_allow_html=True)
        c4.markdown(progress_html(row["Completion %"]), unsafe_allow_html=True)
        c5.markdown(f"**{row['Completion %']}%**")

        # Show recent comments as a subtle line
        if row["Recent Comments"]:
            st.caption(f"💬 {row['Recent Comments']}")
        st.markdown("---")




# ──────────────────────────────────────────────
#  🔍 POC DETAILS
# ──────────────────────────────────────────────
elif page == "🔍 PoC Details":
    st.markdown("# 🔍 PoC Details")
    st.markdown("")

    names = fdf["POC Name"].tolist()
    if not names:
        st.info("No PoCs match your filters.")
    else:
        selected = st.selectbox("Select a PoC", names)
        row = fdf[fdf["POC Name"] == selected].iloc[0]

        st.markdown("")
        left, right = st.columns(2)

        with left:
            st.markdown(f"""
            <div class="detail-card">
                <h2>🧪 {row['POC Name']}</h2>
                <p><span class="detail-label">📌 Status:</span> {status_badge(row['Status'])}</p>
                <p><span class="detail-label">📅 Expected End:</span> {row['Expected End Date'].strftime('%b %d, %Y')}</p>
                <p class="detail-label" style="margin-top:14px;">🛠️ Tools & Requirements</p>
                <p>{tool_tags(row['Tools & Requirements'])}</p>
            </div>
            """, unsafe_allow_html=True)

        with right:
            st.markdown(f"""
            <div class="detail-card">
                <h3 style="color:#e2e8f0; margin:0 0 12px 0;">Completion</h3>
                <div class="kpi-number" style="font-size:3.5rem; margin-bottom:10px;">{row['Completion %']}%</div>
                {progress_html(row['Completion %'])}
                <h3 style="color:#e2e8f0; margin:20px 0 8px 0;">💬 Recent Comments</h3>
                <p style="color:#9CA3AF;">{row['Recent Comments'] if row['Recent Comments'] else 'No comments yet'}</p>
            </div>
            """, unsafe_allow_html=True)

        # Challenges
        if row["Challenges"] and row["Challenges"] != "None":
            st.markdown(f"""
            <div class="challenge-box">
                ⚡ <strong>Challenge:</strong> {row['Challenges']}
            </div>
            """, unsafe_allow_html=True)




# ──────────────────────────────────────────────
#  ✏️ MANAGE POCS
# ──────────────────────────────────────────────
elif page == "✏️ Manage PoCs":
    st.markdown("# ✏️ Manage PoCs")
    st.markdown("")

    tab_add, tab_edit, tab_delete = st.tabs(["➕ Add New PoC", "📝 Edit Existing", "🗑️ Delete"])

    # ── ADD NEW POC ───────────────────────────
    with tab_add:
        st.markdown('<div class="section-header">➕ Add a New PoC</div>', unsafe_allow_html=True)
        with st.form("add_poc_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_name = st.text_input("PoC Name *")
                new_tools = st.text_input("Tools & Requirements", placeholder="Python; LangChain; GPT-4")
                new_status = st.selectbox("Status", ["WIP", "Completed", "NO"])
            with col2:
                new_completion = st.slider("Completion %", 0, 100, 0)
                new_end = st.date_input("Expected End Date", value=date(2026, 3, 20))
                new_challenges = st.text_input("Challenges", placeholder="Any blockers?")
            new_comments = st.text_area("Recent Comments", placeholder="Latest update...")

            submitted = st.form_submit_button("✅ Add PoC", use_container_width=True)
            if submitted:
                if not new_name.strip():
                    st.error("❌ PoC Name is required!")
                elif new_name.strip() in df["POC Name"].values:
                    st.error(f"❌ '{new_name.strip()}' already exists!")
                else:
                    with st.status(f"Adding **{new_name.strip()}**...", expanded=True) as op_status:
                        st.write("📋 Validating data...")
                        time.sleep(0.3)
                        new_row = pd.DataFrame([{
                            "POC Name": new_name.strip(),
                            "Tools & Requirements": new_tools,
                            "Completion %": new_completion,
                            "Status": new_status,
                            "Expected End Date": pd.Timestamp(new_end),
                            "Recent Comments": new_comments,
                            "Challenges": new_challenges,
                        }])
                        st.write("💾 Saving to database...")
                        updated_df = pd.concat([df, new_row], ignore_index=True)
                        save_data(updated_df)
                        st.write("📝 Recording changelog...")
                        log_change("ADDED", new_name.strip(), f"Status={new_status}, Completion={new_completion}%, Tools={new_tools}")
                        time.sleep(0.3)
                        st.cache_data.clear()
                        op_status.update(label=f"✅ **{new_name.strip()}** added successfully!", state="complete")
                    time.sleep(1)
                    st.rerun()

    # ── EDIT EXISTING POC ─────────────────────
    with tab_edit:
        st.markdown('<div class="section-header">📝 Edit an Existing PoC</div>', unsafe_allow_html=True)
        edit_names = df["POC Name"].tolist()
        if not edit_names:
            st.info("No PoCs to edit.")
        else:
            edit_selected = st.selectbox("Select PoC to edit", edit_names, key="edit_select")
            row = df[df["POC Name"] == edit_selected].iloc[0]
            idx = df[df["POC Name"] == edit_selected].index[0]

            with st.form("edit_poc_form"):
                col1, col2 = st.columns(2)
                with col1:
                    edit_tools = st.text_input("Tools & Requirements", value=row["Tools & Requirements"])
                    edit_status = st.selectbox("Status", ["WIP", "Completed", "NO"],
                                               index=["WIP", "Completed", "NO"].index(row["Status"]))
                    edit_completion = st.slider("Completion %", 0, 100, int(row["Completion %"]))
                with col2:
                    edit_end = st.date_input("Expected End Date", value=row["Expected End Date"].date())
                    edit_challenges = st.text_input("Challenges", value=row["Challenges"])
                edit_comments = st.text_area("Recent Comments", value=row["Recent Comments"])

                save_btn = st.form_submit_button("💾 Save Changes", use_container_width=True)
                if save_btn:
                    with st.status(f"Saving changes to **{edit_selected}**...", expanded=True) as op_status:
                        st.write("🔍 Detecting changes...")
                        time.sleep(0.3)
                        # Build change details for log
                        changes = []
                        if edit_tools != row["Tools & Requirements"]: changes.append(f"Tools: {row['Tools & Requirements']} → {edit_tools}")
                        if edit_status != row["Status"]: changes.append(f"Status: {row['Status']} → {edit_status}")
                        if edit_completion != int(row["Completion %"]): changes.append(f"Completion: {row['Completion %']}% → {edit_completion}%")
                        if str(edit_end) != str(row["Expected End Date"].date()): changes.append(f"End Date: {row['Expected End Date'].date()} → {edit_end}")
                        if edit_challenges != row["Challenges"]: changes.append(f"Challenges updated")
                        if edit_comments != row["Recent Comments"]: changes.append(f"Comments updated")

                        if changes:
                            for c in changes:
                                st.write(f"  ➜ {c}")
                        else:
                            st.write("  ℹ️ No fields changed")

                        st.write("💾 Saving to database...")
                        df.at[idx, "Tools & Requirements"] = edit_tools
                        df.at[idx, "Status"] = edit_status
                        df.at[idx, "Completion %"] = edit_completion
                        df.at[idx, "Expected End Date"] = pd.Timestamp(edit_end)
                        df.at[idx, "Challenges"] = edit_challenges
                        df.at[idx, "Recent Comments"] = edit_comments
                        save_data(df)
                        st.write("📝 Recording changelog...")
                        log_change("EDITED", edit_selected, " | ".join(changes) if changes else "No fields changed")
                        time.sleep(0.3)
                        st.cache_data.clear()
                        op_status.update(label=f"✅ **{edit_selected}** updated — {len(changes)} change(s)!", state="complete")
                    time.sleep(1)
                    st.rerun()

    # ── DELETE POC ────────────────────────────
    with tab_delete:
        st.markdown('<div class="section-header">🗑️ Delete a PoC</div>', unsafe_allow_html=True)
        del_names = df["POC Name"].tolist()
        if not del_names:
            st.info("No PoCs to delete.")
        else:
            del_selected = st.selectbox("Select PoC to delete", del_names, key="del_select")
            del_row = df[df["POC Name"] == del_selected].iloc[0]

            st.markdown(f"""
            <div class="detail-card" style="border-color:#ef4444;">
                <h3 style="color:#ef4444; margin:0 0 8px 0;">⚠️ You are about to delete:</h3>
                <p><strong>{del_row['POC Name']}</strong> — {del_row['Status']} — {del_row['Completion %']}%</p>
                <p style="color:#9CA3AF; font-size:0.85rem;">💬 {del_row['Recent Comments']}</p>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🗑️ Confirm Delete", type="primary", use_container_width=True):
                with st.status(f"Deleting **{del_selected}**...", expanded=True) as op_status:
                    st.write("🗑️ Removing from database...")
                    time.sleep(0.3)
                    updated_df = df[df["POC Name"] != del_selected].reset_index(drop=True)
                    save_data(updated_df)
                    st.write("📝 Recording changelog...")
                    log_change("DELETED", del_selected, f"Was {del_row['Status']} at {del_row['Completion %']}%")
                    time.sleep(0.3)
                    st.cache_data.clear()
                    op_status.update(label=f"🗑️ **{del_selected}** deleted!", state="complete")
                time.sleep(1)
                st.rerun()
