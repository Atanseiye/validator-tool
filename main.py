import streamlit as st
import json
import os
import hashlib
import time

# --- Paths ---
USERS_FILE = "users.json"
TASKS_FILE = "tasks.json"

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
        from task import main as task_ui
        task_ui(st.session_state["username"])


# --- 3. Admin Panel Tab ---
with tabs[2]:
    st.header("Admin Panel - Assign Tasks")

    admin_username = st.text_input("Admin Username", key="admin_user")
    admin_password = st.text_input("Admin Password", type="password", key="admin_pass")

    if st.button("Login as Admin"):
        if admin_username == "admin" and hash_password(admin_password) == users.get("admin", ""):
            st.success("Admin logged in!")

            user_list = list(users.keys())
            if "admin" in user_list:
                user_list.remove("admin")

            selected_user = st.selectbox("Select user to assign task", user_list)
            new_task = st.text_area("Enter the task")

            if st.button("Assign Task"):
                if new_task.strip():
                    tasks.setdefault(selected_user, []).append(new_task.strip())
                    save_json(tasks, TASKS_FILE)
                    st.success(f"Task assigned to {selected_user}")
                else:
                    st.warning("Task cannot be empty.")
        else:
            st.error("Invalid admin credentials.")
