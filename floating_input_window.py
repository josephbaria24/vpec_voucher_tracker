import tkinter as tk
import os
import streamlit as st


def create_floating_input_window():
    def save_text():
        current_text = entry.get("1.0", "end-1c")
        if current_text != save_text.last_text:
            try:
                with open("voucher_input.txt", "w") as f:
                    f.write(current_text)
                save_text.last_text = current_text
                update_status("Auto-saved", "green")
            except Exception as e:
                update_status("Auto-save failed", "red")
        root.after(1000, save_text)

    def manual_submit():
        current_text = entry.get("1.0", "end-1c")
        try:
            # Save to file before clearing
            with open("voucher_input.txt", "w") as f:
                f.write(current_text)
            
            # Update the session state to reflect the new input
            save_text.last_text = current_text
            st.session_state["last_input"] = current_text  # Update session state for Streamlit

            update_status("Submit successful", "green")

            # Clear the text input after the save
            entry.delete("1.0", "end")  # ✅ Clear the text input on success

        except Exception as e:
            update_status("Submit failed", "red")

    def update_status(message, color):
        status_label.config(text=message, fg=color)

    save_text.last_text = ""

    root = tk.Tk()
    root.geometry("500x280+500+300")
    root.title("Voucher Input")
    root.resizable(True, True)

    entry = tk.Text(root, height=10, width=60)
    entry.pack(padx=10, pady=(10, 5), expand=True, fill="both")

    # Status label
    status_label = tk.Label(root, text="", font=("Arial", 10))
    status_label.pack()

    # Buttons Frame
    button_frame = tk.Frame(root)
    button_frame.pack(pady=(0, 10))

    submit_btn = tk.Button(button_frame, text="Submit", command=manual_submit)
    submit_btn.pack(side="left", padx=5)

    close_btn = tk.Button(button_frame, text="Close", command=root.destroy)
    close_btn.pack(side="left", padx=5)

    # Start the loop and keep on top
    root.after(1000, save_text)
    root.lift()
    root.attributes("-topmost", True)
    root.mainloop()

# Launch the floating window
create_floating_input_window()
