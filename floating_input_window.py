import tkinter as tk
import os
import streamlit as st

# Cluster map data
cluster_map = {
    "Cluster 1 - Oriental": ["Roxas", "San Vicente", "Araceli", "Dumaran"],
    "Cluster 2 - Del Norte": ["Taytay", "El Nido", "Coron", "Linapacan"],
    "Cluster 3 - Occidental": ["Narra", "Quezon", "Rizal"],
    "Cluster 4 - Del Sur": ["Espanola", "Brooke's Point", "Bataraza", "Balabac"],
    "PCAT - Cuyo": ["Cuyo", "PCAT"]
}

def create_floating_input_window():
    # Function to save text manually when the button is pressed
    def save_text():
        current_text = entry.get("1.0", "end-1c")
        try:
            with open("voucher_input.txt", "w") as f:
                f.write(current_text)
            update_status("Saved Successfully", "green")
        except Exception as e:
            update_status("Save failed", "red")
        
        # Count the number of entries after saving
        entry_count = len(current_text.splitlines())
        update_status(f"Saved {entry_count} entries", "green")

    # Function to trigger the rerun of Streamlit
    def manual_submit():
        save_text()  # Save the text before triggering the rerun
        with open("trigger.txt", "w") as f:
            f.write(str(os.urandom(8)))  # Random content to trigger change

    # Update the status message
    def update_status(message, color):
        status_label.config(text=message, fg=color)

    # Auto-fill suggestions based on typed text for the active line
    def on_key_release(event):
        typed_text = entry.get("1.0", "end-1c")
        active_line = entry.index(tk.INSERT).split('.')[0]  # Get the current active line number
        current_line = entry.get(f"{active_line}.0", f"{active_line}.end")

        matching_towns = []

        # Search through the cluster_map for matching towns
        for cluster, towns in cluster_map.items():
            matching_towns += [town for town in towns if town.lower().startswith(current_line.lower())]

        # Clear the previous suggestions
        listbox.delete(0, tk.END)

        if current_line:
            for town in matching_towns:
                listbox.insert(tk.END, town)
            listbox.place(x=entry.winfo_x(), y=entry.winfo_y() + entry.winfo_height())  # Position below the text box
        else:
            listbox.place_forget()  # Hide the suggestions when the input is empty

    def on_listbox_select(event):
        selected_town = listbox.get(listbox.curselection())
        active_line = entry.index(tk.INSERT).split('.')[0]  # Get the current active line number
        entry.delete(f"{active_line}.0", f"{active_line}.end")
        entry.insert(f"{active_line}.0", selected_town)
        listbox.place_forget()  # Hide the suggestions after selection

    # Handle the Tab key to auto-complete the text for the active line
    def on_tab_key(event):
        # If there's a suggestion, complete the text for the current line
        if listbox.size() > 0:
            selected_town = listbox.get(0)  # Get the first suggestion
            active_line = entry.index(tk.INSERT).split('.')[0]  # Get the current active line number
            entry.delete(f"{active_line}.0", f"{active_line}.end")
            entry.insert(f"{active_line}.0", selected_town)
            listbox.place_forget()  # Hide the suggestions after auto-completion

    # Handle the Enter key to move to the next line
    def on_enter_key(event):
        entry.insert(tk.INSERT, "\n")  # Move to the next line and allow auto-fill to start for that line
        on_key_release(event)  # Trigger the auto-fill for the new line

    # Initialize tkinter window
    root = tk.Tk()
    root.geometry("300x280+500+300")
    root.title("Voucher Input")
    root.resizable(True, True)

    # Text box for input
    entry = tk.Text(root, height=10, width=60)
    entry.pack(padx=10, pady=(10, 5), expand=True, fill="both")
    entry.bind("<KeyRelease>", on_key_release)  # Bind the key release event to show suggestions
    entry.bind("<Tab>", on_tab_key)  # Bind the Tab key event for auto-completion
    entry.bind("<Return>", on_enter_key)  # Bind the Enter key to move to the next line

    # Listbox for showing auto-fill suggestions
    listbox = tk.Listbox(root, height=5)
    listbox.bind("<Double-1>", on_listbox_select)  # Select item from listbox on double click

    # Status label to display messages
    status_label = tk.Label(root, text="", font=("Arial", 16))
    status_label.pack()

    # Button frame for placing buttons
    button_frame = tk.Frame(root)
    button_frame.pack(pady=(0, 10))

    # Button to trigger the rerun of Streamlit
    submit_btn = tk.Button(button_frame, text="Rerun Streamlit", command=manual_submit)
    submit_btn.pack(side="left", padx=5)

    # Button to clear the input text
    clear_btn = tk.Button(button_frame, text="Clear", command=lambda: entry.delete("1.0", tk.END))
    clear_btn.pack(side="left", padx=5)

    root.lift()
    root.attributes("-topmost", True)
    root.mainloop()

create_floating_input_window()
