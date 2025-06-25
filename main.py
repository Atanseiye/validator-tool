import streamlit as st
import json
import os
import hashlib
import time
import matplotlib.pyplot as plt

# --- Paths ---
USERS_FILE = "config/users.json"
TASKS_FILE = "config/tasks.json"
PROCESSED_TASK_FOLDER = "processed_data"

# Track admin login state in session_state
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

# --- Utility Functions ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_json(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return {}

def save_json(data, file):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# --- Initialize Files ---
if not os.path.exists(USERS_FILE):
    save_json({}, USERS_FILE)
if not os.path.exists(TASKS_FILE):
    save_json({}, TASKS_FILE)

# --- Load Data ---
users = load_json(USERS_FILE)
tasks = load_json(TASKS_FILE)

# --- UI Config ---
st.set_page_config(page_title="Task Manager", layout="wide")
st.title("🔐 Task Manager with User Accounts")

# --- Handle Logout ---
if st.session_state.get("logout_triggered", False):
    with st.spinner("🔄 Logging out... Please wait"):
        time.sleep(1)
    st.session_state.clear()
    st.rerun()

# --- Tabs ---
tabs = st.tabs(["📝 Register", "🔑 Login & Task View", "👩‍💼 Admin Panel"])

# --- 1. Register Tab ---
with tabs[0]:
    st.header("Register a new user")
    new_username = st.text_input("Username")
    new_password = st.text_input("Password", type="password")
    if st.button("Register"):
        if new_username in users:
            st.error("Username already exists.")
        elif not new_username or not new_password:
            st.warning("Please fill in all fields.")
        else:
            users[new_username] = hash_password(new_password)
            save_json(users, USERS_FILE)
            st.success(f"User '{new_username}' registered!")

# --- 2. Login & Task View Tab ---
with tabs[1]:
    st.header("Login to view your tasks")

    # Finalize login on rerun
    if st.session_state.get("pending_login"):
        st.session_state["username"] = st.session_state.pop("username_pending")
        st.session_state["batch_number"] = st.session_state.pop("batch_number_pending")
        st.session_state["logged_in"] = True
        st.session_state.pop("pending_login")
        st.rerun()

    # Not logged in yet
    if not st.session_state.get("logged_in"):
        username = st.text_input("Username", key="user_name")
        password = st.text_input("Password", type="password", key="pass_word")

        if st.button("Login", key="login_button"):
            if username in users and hash_password(password) == users[username]:
                batch_list = tasks.get(username, [])
                batch_number = batch_list[-1] if batch_list else 0

                st.session_state["username_pending"] = username
                st.session_state["batch_number_pending"] = batch_number
                st.session_state["pending_login"] = True
                st.rerun()
            else:
                st.error("Invalid credentials.")

    # Logged-in section
    else:
        # st.success(f"Logged in as: {st.session_state['username']}")
        if st.button("🚪 Logout"):
            st.session_state["logout_triggered"] = True
            st.rerun()

        # Import task interface
        from taskManager.task import main as task_ui
        task_ui(st.session_state["username"])


# --- 3. Admin Panel Tab ---
with tabs[2]:
    st.header("Admin Panel - Assign or Reassign Tasks")

    if not st.session_state.admin_logged_in:
        admin_username = st.text_input("Admin Username", key="admin_user")
        admin_password = st.text_input("Admin Password", type="password", key="admin_pass")

        if st.button("Login as Admin"):
            if admin_username == "admin" and hash_password(admin_password) == users.get("admin", ""):
                st.session_state.admin_logged_in = True
                st.success("Admin logged in!")
            else:
                st.error("Invalid admin credentials.")

    if st.session_state.admin_logged_in:
        st.success("Admin logged in!")

        user_list = list(users.keys())
        if "admin" in user_list:
            user_list.remove("admin")

        # Display files in processed_task folder
        st.subheader("Processed Tasks")

        try:
            files = os.listdir(PROCESSED_TASK_FOLDER)
            files = [f for f in files if f.endswith(".csv") and os.path.isfile(os.path.join(PROCESSED_TASK_FOLDER, f))]

            if files:
                selected_file = st.selectbox("Select a processed CSV file to view and assign", files)

                if selected_file:
                    file_path = os.path.join(PROCESSED_TASK_FOLDER, selected_file)
                    with open(file_path, "r", encoding="utf-8") as f:
                        file_content = f.read()


                    # st.text_area("File Content", file_content, height=200, disabled=True)

                    assign_to = st.selectbox("Assign this task to", user_list)
                    if st.button("Assign Selected CSV as Task"):
                        tasks.setdefault(assign_to, []).append(selected_file)
                        save_json(tasks, TASKS_FILE)
                        st.success(f"Task `{selected_file}` assigned to {assign_to}")

            else:
                st.info("No CSV files found in the processed_task folder.")

        except FileNotFoundError:
            st.warning(f"Folder `{PROCESSED_TASK_FOLDER}` not found.")

        # Prepare Data
        st.subheader("Task Distribution Overview")
        if not tasks:
            st.warning("No tasks assigned yet.")
            st.stop()
        # Prepare Data for Plotting
        names = list(tasks.keys())
        task_counts = [len(task_list) for task_list in tasks.values()]
        total_tasks = sum(task_counts)

        # Display as Bar Chart
        fig, ax = plt.subplots()
        bars = ax.bar(names, task_counts, color='skyblue')

        ax.set_xticklabels(names, rotation=45, ha='right')

        ax.set_ylabel("Number of Tasks")
        ax.set_xlabel("Person")
        ax.set_title("Task Count per Person")
        ax.bar_label(bars)  # Display count on top of bars

        # Show Plot
        st.pyplot(fig)

        # Add Total Task Count in Legend
        ax.legend([f"Total Tasks: {total_tasks}"])
        
                # --- Backup Download Section ---
        st.markdown("---")
        st.subheader("🧰 Backup Current App State")

        import zipfile
        from io import BytesIO

        if st.button("📦 Download Backup (Full App State)"):
            backup_buffer = BytesIO()
            folders_to_include = [
                ("edit_states", "edit_states"),
                ("fetched_data", "fetched_data"),
                ("processed_data", "processed_data")
            ]
            files_to_include = [
                ("users.json", "users.json"),
                ("tasks.json", "tasks.json"),
                ("data/batch.json", "batch.json")
            ]

            with zipfile.ZipFile(backup_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                # Add files
                for file_path, arcname in files_to_include:
                    if os.path.exists(file_path):
                        zipf.write(file_path, arcname=arcname)

                # Add folders
                for folder_path, arc_root in folders_to_include:
                    if os.path.isdir(folder_path):
                        for root, _, files in os.walk(folder_path):
                            for file in files:
                                full_path = os.path.join(root, file)
                                arcname = os.path.join(arc_root, os.path.relpath(full_path, start=folder_path))
                                zipf.write(full_path, arcname=arcname)

            st.download_button(
                label="⬇️ Download ZIP Backup",
                data=backup_buffer.getvalue(),
                file_name="full_app_backup.zip",
                mime="application/zip"
            )


# --- End of Admin Panel Tab ---