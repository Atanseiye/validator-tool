import streamlit as st
import pandas as pd
import shutil
import subprocess
import os
import json
from pathlib import Path

# ─── CONFIGURATION ────────────────────────────────────────────────────────────

ACCURATE_DIR = Path('processed_data')
REJECTED_DIR = Path('rejected_data')

TASKS_FILE = "tasks.json"
USERS_FILE = "users.json"
BATCH_NUMBER = Path('data/batch.json')


# ─── UTILITY FUNCTIONS ────────────────────────────────────────────────────────

def ensure_dirs():
    for d in (ACCURATE_DIR, REJECTED_DIR):
        d.mkdir(parents=True, exist_ok=True)


def move_file(src_path: Path, dest_folder: Path):
    dest_path = dest_folder / src_path.name
    shutil.move(str(src_path), str(dest_path))


def read_batch_number():
    if not os.path.exists(BATCH_NUMBER):
        with open(BATCH_NUMBER, "w") as f:
            json.dump({"batch_number": 0}, f)
        return 0
    with open(BATCH_NUMBER, "r") as f:
        return json.load(f)["batch_number"]


def write_batch_number(number):
    with open(BATCH_NUMBER, "w") as f:
        json.dump({"batch_number": number}, f)


def write_task(username, batch_number):
    tasks = {}
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, "r") as f:
            tasks = json.load(f)

    for user_batches in tasks.values():
        if batch_number in user_batches:
            return False

    user_batches = tasks.get(username, [])
    user_batches.append(batch_number)
    tasks[username] = user_batches

    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=4)

    return True


def remove_last_task(username):
    if not os.path.exists(TASKS_FILE):
        return

    with open(TASKS_FILE, "r") as f:
        tasks = json.load(f)

    if username in tasks and tasks[username]:
        tasks[username].pop()

    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=4)


# ─── MAIN STREAMLIT APP ───────────────────────────────────────────────────────

def main(username):
    if not username:
        st.error("No username provided.")
        return

    PAIRS_DIR = Path(f'fetched_data/{username}')
    PAIRS_DIR.mkdir(parents=True, exist_ok=True)
    ensure_dirs()

    if "action_pending" in st.session_state and st.session_state["action_pending"]:
        if "locked_file" in st.session_state:
            selected_path = PAIRS_DIR / st.session_state.locked_file
            action = st.session_state.pop("action_pending")
            target_dir = ACCURATE_DIR if action == "accept" else REJECTED_DIR
            try:
                move_file(selected_path, target_dir)
                msg = "Accepted" if action == "accept" else "Rejected"
                st.success(f"{msg}: `{selected_path.name}` → {target_dir.name}/")
                st.session_state.pop("locked_file", None)
                st.rerun()
            except Exception as e:
                st.error(f"Error moving file: {e}")
                return

    csv_files = sorted(PAIRS_DIR.glob("*.csv"))
    if len(csv_files) == 0:
        batch_number = read_batch_number()
        try:
            subprocess.run(
                ["python", "data/process.py", "--batch_number", str(batch_number), "--username", username],
                check=True
            )
            write_task(username, batch_number)
            write_batch_number(batch_number + 1)
            csv_files = sorted(PAIRS_DIR.glob("*.csv"))
        except subprocess.CalledProcessError:
            if batch_number == 0:
                st.error("You data have been loaded and fetched but we are unable to access it at the moment. Kindly log out and log in back.")
                return
            write_batch_number(batch_number)
            remove_last_task(username)
            st.error(f"Failed to fetch data for batch {batch_number}.")
            return

    st.sidebar.header("Select a CSV to View")
    filenames = [p.name for p in csv_files]

    if "locked_file" not in st.session_state:
        st.session_state.locked_file = filenames[0] if filenames else None

    default_index = filenames.index(st.session_state.locked_file) if st.session_state.locked_file in filenames else 0
    choice = st.sidebar.selectbox("CSV file:", filenames, index=default_index)

    if choice != st.session_state.locked_file:
        st.session_state.locked_file = choice

    selected_path = PAIRS_DIR / st.session_state.locked_file
    edited_log_file = PAIRS_DIR / f".edited_log_{choice}.json"

    st.success(f"Welcome, {username}!")
    st.subheader(f"🖊️ Editing Preview: `{choice}`")

    try:
        df = pd.read_csv(selected_path, encoding="utf-8-sig")[['yoruba_text', 'english_text']]
    except Exception as e:
        st.error(f"Failed to read `{choice}`:\n{e}")
        return

    # Load previous edits
    previous_edits = []
    if edited_log_file.exists():
        with open(edited_log_file) as f:
            previous_edits = [tuple(e) for e in json.load(f)]

    edited_df = st.data_editor(
        df,
        use_container_width=True,
        height=500,
        key="edited_df"
    )

    if st.button("💾 Save Edits"):
        try:
            changed_cells = []
            for row in range(len(df)):
                for col in ['yoruba_text', 'english_text']:
                    if df.at[row, col] != edited_df.at[row, col]:
                        changed_cells.append((row, col))

            edited_df.to_csv(selected_path, index=False, encoding="utf-8-sig")

            all_edited = set(previous_edits + changed_cells)
            with open(edited_log_file, "w") as f:
                json.dump(list(all_edited), f)

            st.success(f"Edits saved. {len(changed_cells)} cells changed and logged.")

        except Exception as e:
            st.error(f"Failed to save edits: {e}")

    # Optional: show highlighted changes
    if edited_log_file.exists() and st.checkbox("👁️ View Highlighted Changes"):
        with open(edited_log_file) as f:
            highlight_cells = set(tuple(x) for x in json.load(f))

        def highlight(val, row_idx, col_name):
            return "background-color: yellow" if (row_idx, col_name) in highlight_cells else ""

        styled_df = df.style.apply(
            lambda row: [highlight(val, row.name, col) for col, val in row.items()],
            axis=1
        )
        st.dataframe(styled_df, use_container_width=True, height=500)

    with open(selected_path, "rb") as f:
        st.download_button("📥 Download CSV", f, file_name=choice, mime="text/csv")

    st.markdown("---")
    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("✅ Accept"):
            st.session_state.action_pending = "accept"
            st.rerun()

    with col2:
        if st.button("Next"):
            batch_number = read_batch_number()
            write_batch_number(batch_number + 1)
            write_task(username, batch_number)

            try:
                subprocess.run(
                    ["python", "data/process.py", "--batch_number", str(batch_number), "--username", username],
                    check=True
                )
                st.success(f"Fetched batch {batch_number} for {username}")
                st.rerun()
            except subprocess.CalledProcessError:
                write_batch_number(batch_number)
                remove_last_task(username)
                st.error(f"Failed to fetch batch {batch_number}")


# ─── CLI Entry Point (Optional for Script Use) ────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=False)
    parser.add_argument("--batch_number", required=False, type=int, default=0)
    args = parser.parse_args()

    st.session_state["username"] = args.username or "cli_user"
    st.session_state["batch_number"] = args.batch_number

    main(st.session_state["username"])
