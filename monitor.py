import streamlit as st
import pandas as pd
import re
from datetime import datetime
from supabase import create_client, Client
import os
import calendar
import pytz
import hashlib
import matplotlib.pyplot as plt

# --- Auto-refresh if trigger.txt changes ---
def hash_file(filepath):
    with open(filepath, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

trigger_path = "trigger.txt"
trigger_hash = hash_file(trigger_path) if os.path.exists(trigger_path) else ""
last_trigger_hash = st.session_state.get("last_trigger_hash", "")

if trigger_hash != last_trigger_hash:
    st.session_state["last_trigger_hash"] = trigger_hash
    # Removed st.rerun(), session state should handle updates without rerun

# Supabase credentials
SUPABASE_URL = "https://ibromwvqvxxmkphxpiae.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imlicm9td3Zxdnh4bWtwaHhwaWFlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUzOTQ4MTIsImV4cCI6MjA2MDk3MDgxMn0.pbyVSPnzsC80cI-LLatV2OTojLa1u8hZzOvm5TjddZA"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Cluster setup ---
cluster_map = {
    "Cluster 1 - Oriental": ["Roxas", "San Vicente", "Araceli", "Dumaran"],
    "Cluster 2 - Del Norte": ["Taytay", "El Nido", "Coron", "Linapacan"],
    "Cluster 3 - Occidental": ["Narra", "Quezon", "Rizal"],
    "Cluster 4 - Del Sur": ["Espanola", "Brooke's Point", "Bataraza", "Balabac"],
    "PCAT - Cuyo": ["Cuyo", "PCAT"]
}

ph_tz = pytz.timezone("Asia/Manila")
now_ph = datetime.now(ph_tz)

# Reverse map
campus_to_cluster = {}
for cluster, campuses in cluster_map.items():
    for campus in campuses:
        campus_to_cluster[campus.lower()] = cluster

# --- Utility functions ---
def get_cluster_counts():
    result = supabase.table("cluster_counts").select("*").execute()
    if result.data:
        return {row["cluster"]: row["count"] for row in result.data}
    return {cluster: 0 for cluster in cluster_map.keys()}

def update_cluster_count(cluster):
    result = supabase.table("cluster_counts").select("*").eq("cluster", cluster).execute()
    if result.data:
        current = result.data[0]
        new_count = current["count"] + 1
        supabase.table("cluster_counts").update({"count": new_count}).eq("cluster", cluster).execute()
    else:
        supabase.table("cluster_counts").insert({"cluster": cluster, "count": 1}).execute()

def find_cluster(text):
    for campus in campus_to_cluster:
        if re.search(rf"\b{re.escape(campus)}\b", text, re.IGNORECASE):
            return campus_to_cluster[campus]
    return "Unknown"

def get_voucher_logs_by_date(year=None, month=None):
    query = supabase.table("voucher_logs").select("*")
    if year:
        query = query.gte("timestamp", f"{year}-01-01").lte("timestamp", f"{year}-12-31")
    if month and year:
        last_day = calendar.monthrange(year, month)[1]
        query = query.gte("timestamp", f"{year}-{month:02d}-01").lte("timestamp", f"{year}-{month:02d}-{last_day}")
    result = query.execute()
    return result.data if result.data else []

def count_vouchers_by_cluster_and_campus(voucher_logs):
    counts = {cluster: {campus: 0 for campus in campuses} for cluster, campuses in cluster_map.items()}
    for entry in voucher_logs:
        text = entry.get("text", "")
        for campus in campus_to_cluster:
            campus_name = campus.title() if campus != "pcat" else "PCAT - Cuyo"
            if re.search(rf"\b{re.escape(campus)}\b", text, re.IGNORECASE):
                cluster = campus_to_cluster[campus]
                if campus_name in counts[cluster]:
                    counts[cluster][campus_name] += 1
                else:
                    counts[cluster][campus_name] = 1
                break
    return counts

# --- Streamlit UI ---
st.set_page_config(
    page_title="VPEC Voucher Tracker",
    page_icon="favicon.ico",
    layout="wide"
)
st.title("📋 VPEC Voucher Monitor")

# --- State tracking for navigation ---
if 'view_vouchers' not in st.session_state:
    st.session_state['view_vouchers'] = False

# --- "View All Voucher" Button ---
view_voucher_button = st.button("🔎 View All Vouchers")

if view_voucher_button:
    # Set session state to navigate to the vouchers page
    st.session_state['view_vouchers'] = True

# --- Sidebar: Filter by Date ---
with st.sidebar:
    st.header("📅 Filter by Date")
    selected_year = st.selectbox("Select Year", options=list(range(2023, now_ph.year + 1)), index=list(range(2023, now_ph.year + 1)).index(now_ph.year))
    month_names = ["All", "January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]
    selected_month_name = st.selectbox("Select Month", options=month_names, index=now_ph.month)

    if selected_month_name == "All":
        logs = get_voucher_logs_by_date(year=selected_year)
    else:
        month_number = month_names.index(selected_month_name)
        logs = get_voucher_logs_by_date(year=selected_year, month=month_number)

    cluster_campus_counts = count_vouchers_by_cluster_and_campus(logs)

    st.header("📊 Voucher Clusters")
    for cluster, campus_counts in cluster_campus_counts.items():
        total = sum(campus_counts.values())
        with st.expander(f"{cluster} ({total} vouchers)") :
            for campus, count in campus_counts.items():
                if count > 0:
                    st.markdown(f"- **{campus}**: {count}")

# --- Input Section and Chart in a Row ---
if not st.session_state['view_vouchers']:
    # Create two columns for the layout
    left_col, right_col = st.columns([1, 1])
    
    # Left column: Add Voucher form
    with left_col:
        st.subheader("📥 Add Voucher")

        # Dropdown for campus selection
        all_campuses = [campus for campuses in cluster_map.values() for campus in campuses]
        selected_campus = st.selectbox("Select Campus:", options=sorted(all_campuses))

        # Text input for transaction number
        transaction_number = st.text_input("Enter Transaction Number:")

        # Optional date input (default to today)
        selected_date = st.date_input("Select Date (optional):", value=now_ph.date())

        submit = st.button("Submit Voucher")

        if submit:
            if selected_campus and transaction_number.strip():
                # Use selected date or fallback to current date
                if selected_date:
                    timestamp = datetime.combine(selected_date, now_ph.time()).strftime("%Y-%m-%d %H:%M:%S")
                else:
                    timestamp = datetime.now(ph_tz).strftime("%Y-%m-%d %H:%M:%S")

                cluster = campus_to_cluster.get(selected_campus.lower(), "Unknown")
                voucher_text = f"{selected_campus} - {transaction_number}"

                if cluster != "Unknown":
                    update_cluster_count(cluster)

                    # Insert into Supabase
                    supabase.table("voucher_logs").insert({
                        "cluster": cluster,
                        "text": voucher_text,
                        "timestamp": timestamp
                    }).execute()

                    st.success("✅ Voucher added successfully!")
                    st.write("### 📄 Voucher Details")
                    st.write(f"➡️ **{cluster}**: {voucher_text} _(added on {timestamp})_")
                else:
                    st.error("❌ Unable to determine cluster for selected campus.")
            else:
                st.warning("⚠️ Please select a campus and enter a transaction number before submitting.")
    
    # Right column: Voucher Trends chart
    with right_col:
        st.subheader("📊 Voucher Trends")
        
        # Get actual data from Supabase/selected filters for the chart
        # Use the filtered logs or get all data if needed
        if selected_month_name == "All":
            chart_logs = get_voucher_logs_by_date(year=selected_year)
        else:
            month_number = month_names.index(selected_month_name)
            chart_logs = get_voucher_logs_by_date(year=selected_year, month=month_number)
        
        # Count vouchers per cluster for the radar chart
        cluster_counts = {}
        for log in chart_logs:
            cluster = log.get("cluster", "Unknown")
            if cluster not in cluster_counts:
                cluster_counts[cluster] = 0
            cluster_counts[cluster] += 1
        
        # Prepare data for radar chart
        labels = list(cluster_map.keys())  # Get all cluster names
        values = [cluster_counts.get(cluster, 0) for cluster in labels]  # Get counts, default 0 if no data
        
        # Create a figure and axes explicitly for radar chart
        fig, ax = plt.subplots(figsize=(6, 4), subplot_kw=dict(polar=True))
        
        # Number of variables
        N = len(labels)
        
        # What will be the angle of each axis in the plot
        angles = [n / float(N) * 2 * 3.14159 for n in range(N)]
        angles += angles[:1]  # Close the loop
        
        # Values need to be repeated to close the loop as well
        values_for_plot = values.copy()
        values_for_plot += values_for_plot[:1]
        
        # Draw the chart
        ax.plot(angles, values_for_plot, linewidth=1, linestyle='solid')
        ax.fill(angles, values_for_plot, alpha=0.1)
        
        # Fix axis to go in the right order and start at 12 o'clock
        ax.set_theta_offset(3.14159 / 2)
        ax.set_theta_direction(-1)
        
        # Set labels and ticks - using shortened cluster names for better readability
        short_labels = [label.split(' - ')[0] if ' - ' in label else label for label in labels]
        plt.xticks(angles[:-1], short_labels)
        
        # Calculate appropriate y-ticks based on actual data
        max_value = max(values) if values else 10
        y_ticks = [int(max_value * i / 5) for i in range(1, 6)]
        
        # Draw y-axis labels
        ax.set_rlabel_position(0)
        plt.yticks(y_ticks, color="grey", size=7)
        plt.ylim(0, max_value * 1.2)  # Set y limit with some headroom
        
        # Add title
        plt.title("Voucher Distribution by Cluster", size=11, y=1.1)
        
        # Display the plot using st.pyplot() with the figure
        st.pyplot(fig)


# --- Cluster and Voucher Management Section ---
if st.session_state['view_vouchers']:
    st.title("🗂️ Cluster and Voucher Management")

    # --- "Back to Home" Button ---
    if st.button("🏠 Back to Home"):
        st.session_state['view_vouchers'] = False  # Go back to the voucher input section
        st.rerun()
    
    # Fetch all voucher logs
    all_vouchers = supabase.table("voucher_logs").select("*").order("timestamp", desc=True).execute()
    vouchers_data = all_vouchers.data if all_vouchers.data else []

    # Organize vouchers by cluster
    cluster_vouchers = {}
    for voucher in vouchers_data:
        cluster_name = voucher.get("cluster", "Unknown")
        if cluster_name not in cluster_vouchers:
            cluster_vouchers[cluster_name] = []
        cluster_vouchers[cluster_name].append(voucher)

    # Create two sections: one for vouchers, one for chart
    col1, col2 = st.columns([2, 1])

    # Left column: Voucher and cluster data
    with col1:
        st.subheader("📊 Clusters Overview")

        for cluster_name, vouchers in cluster_vouchers.items():
            with st.expander(f"{cluster_name} ({len(vouchers)} vouchers)") :
                for voucher in vouchers:
                    col1, col2, col3 = st.columns([5, 2, 2])
                    with col1:
                        st.markdown(f"**{voucher['text']}**  \n`{voucher['timestamp']}`")
                    with col2:
                        if st.button("✏️ Edit", key=f"edit_button_{voucher['id']}"):
                            # Handle editing logic here
                            pass
                    with col3:
                        if st.button("🗑️ Delete", key=f"delete_button_{voucher['id']}"):
                            supabase.table("voucher_logs").delete().eq("id", voucher['id']).execute()
                            st.error("Deleted successfully!")