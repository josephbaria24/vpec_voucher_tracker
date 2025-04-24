import streamlit as st
import pandas as pd
import re
from datetime import datetime
from supabase import create_client, Client
import os
import calendar 
import pytz
import tkinter as tk

# Supabase credentials
SUPABASE_URL = "https://ibromwvqvxxmkphxpiae.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imlicm9td3Zxdnh4bWtwaHhwaWFlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUzOTQ4MTIsImV4cCI6MjA2MDk3MDgxMn0.pbyVSPnzsC80cI-LLatV2OTojLa1u8hZzOvm5TjddZA"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ------------------ Cluster Setup ------------------
cluster_map = {
    "Cluster 1 - Oriental": ["Roxas", "San Vicente", "Araceli", "Dumaran"],
    "Cluster 2 - Del Norte": ["Taytay", "El Nido", "Coron", "Linapacan"],
    "Cluster 3 - Occidental": ["Narra", "Quezon", "Rizal"],
    "Cluster 4 - Del Sur": ["Espanola", "Brooke's Point", "Bataraza", "Balabac"],
    "PCAT - Cuyo": ["Cuyo", "PCAT"]
}

# Get current date in Philippines timezone
ph_tz = pytz.timezone("Asia/Manila")
now_ph = datetime.now(ph_tz)

# Reverse map (add PCAT - Cuyo here)
campus_to_cluster = {}
for cluster, campuses in cluster_map.items():
    for campus in campuses:
        campus_to_cluster[campus.lower()] = cluster

# ------------------ Utility Functions ------------------

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

def reset_all_counts():
    for cluster in cluster_map.keys():
        supabase.table("cluster_counts").update({"count": 0}).eq("cluster", cluster).execute()

def find_cluster(text):
    for campus in campus_to_cluster:
        if re.search(rf"\b{re.escape(campus)}\b", text, re.IGNORECASE):
            return campus_to_cluster[campus]
    return "Unknown"

# ------------------ New Function to Get Vouchers by Date ------------------
def get_voucher_logs_by_date(year=None, month=None):
    query = supabase.table("voucher_logs").select("*")
    if year:
        query = query.gte("timestamp", f"{year}-01-01").lte("timestamp", f"{year}-12-31")
    if month and year:
        last_day = calendar.monthrange(year, month)[1]  # Get correct number of days in the month
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
                # Ensure the campus name exists in the dictionary before incrementing
                if campus_name in counts[cluster]:
                    counts[cluster][campus_name] += 1
                else:
                    # If the campus name is not found, initialize it with 1
                    counts[cluster][campus_name] = 1
                break
    return counts



# ------------------ Streamlit UI ------------------

st.set_page_config(layout="centered")
st.title("📋 VPEC Voucher Monitor")

cluster_counts = get_cluster_counts()

# Sidebar with counts and dropdowns

with st.sidebar:
    st.header("📅 Filter by Date")

    # Automatically set the current year to the default year
    selected_year = st.selectbox("Select Year", options=list(range(2023, now_ph.year + 1)), index=list(range(2023, now_ph.year + 1)).index(now_ph.year))

    # List of months for the dropdown
    month_names = ["All", "January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]

    # Automatically set the current month as the default
    selected_month_name = st.selectbox("Select Month", options=month_names, index=now_ph.month)  # now_ph.month gives current month as 1-12

    if selected_month_name == "All":
        logs = get_voucher_logs_by_date(year=selected_year)
    else:
        month_number = month_names.index(selected_month_name)  # January = 1, etc.
        logs = get_voucher_logs_by_date(year=selected_year, month=month_number)


    cluster_campus_counts = count_vouchers_by_cluster_and_campus(logs)

    st.header("📊 Voucher Clusters")
    for cluster, campus_counts in cluster_campus_counts.items():
        total = sum(campus_counts.values())
        with st.expander(f"{cluster} ({total} vouchers)"):

            # Make sure PCAT is handled here as well
            for campus, count in campus_counts.items():
                if count > 0:
                    st.markdown(f"- **{campus}**: {count}")


# Input section
st.subheader("📥 Add Vouchers")

# Check if the file exists
input_file_path = "voucher_input.txt"
input_text = ""
if os.path.exists(input_file_path):
    with open(input_file_path, "r") as file:
        input_text = file.read().strip()

# Prevent submitting empty content
if input_text:
    last_input = st.session_state.get("last_input", "")
    
    # Always process if there's new content in file (ignore session cache if file is not empty)
    if input_text != last_input:
        st.session_state["last_input"] = input_text

        # Start processing immediately (auto-submit)
        lines = input_text.split('\n')
        categorized = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for line in lines:
            if not line.strip():
                continue
            cluster = find_cluster(line)
            if cluster != "Unknown":
                update_cluster_count(cluster)
                categorized.append((cluster, line, timestamp))

                # Insert into Supabase
                supabase.table("voucher_logs").insert({
                    "cluster": cluster,
                    "text": line,
                    "timestamp": timestamp
                }).execute()

        # Empty the file after reading to prevent re-submission
        with open(input_file_path, "w") as f:
            f.write("")

        st.success("✅ Vouchers added and categorized automatically!")
        st.write("### 📄 Categorized Vouchers")
        for cluster, line, date in categorized:
            st.write(f"➡️ **{cluster}**: {line} _(added on {date})_")
