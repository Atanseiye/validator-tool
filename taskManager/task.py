import streamlit as st
import pandas as pd
import shutil
from pathlib import Path
import json
import subprocess
import os
from config.auth import upload_file
import argparse
import hashlib

# ─── UTILITY FUNCTIONS ─────────────────────────────────────────────────────
def get_next_batch_number():
    """Get next available global batch number"""
    with open(BATCH_FILE, "r") as f:
        return json.load(f)["batch_number"]

def increment_batch_number():
    """Increment the global batch number"""
    with open(BATCH_FILE, "r") as f:
        batch_data = json.load(f)
        current_batch = batch_data["batch_number"]
        batch_data["batch_number"] = current_batch + 1
        
    with open(BATCH_FILE, "w") as f:
        json.dump(batch_data, f)

def assign_batch_to_user(username, batch_number):
    """Assign batch to user in tasks.json"""
    tasks = {}
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, "r") as f:
            tasks = json.load(f)
    
    user_tasks = tasks.get(username, [])
    if batch_number not in user_tasks:
        user_tasks.append(batch_number)
        tasks[username] = user_tasks
        
        with open(TASKS_FILE, "w") as f:
            json.dump(tasks, f, indent=4)
        return True
    return False

def remove_last_batch_from_user(username):
    """Remove last batch assignment from user in tasks.json"""
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, "r") as f:
            tasks = json.load(f)
            
        if username in tasks and tasks[username]:
            removed_batch = tasks[username].pop()
            
            with open(TASKS_FILE, "w") as f:
                json.dump(tasks, f, indent=4)
            return removed_batch
    return None

def move_file(src_path: Path, dest_folder: Path):
    """Move file and upload to Google Drive"""
    dest_path = dest_folder / src_path.name
    shutil.move(str(src_path), str(dest_path))
    upload_file(dest_path, f"{dest_folder.name}/{dest_path.name}")

def get_edit_state_file(csv_path):
    """Get path to edit state file for a CSV"""
    file_hash = hashlib.md5(str(csv_path).encode()).hexdigest()
    return EDIT_STATE_DIR / f"{file_hash}.json"

def load_edit_state(csv_path):
    """Load edit state from JSON file"""
    state_file = get_edit_state_file(csv_path)
    if state_file.exists():
        with open(state_file, "r") as f:
            return json.load(f)
    return {}

def save_edit_state(csv_path, edited_df, original_df):
    """Save edited cells to JSON file"""
    state_file = get_edit_state_file(csv_path)
    edited_cells = {}
    
    # Compare each cell to find edits
    for col in edited_df.columns:
        for idx in edited_df.index:
            original_val = original_df.at[idx, col]
            edited_val = edited_df.at[idx, col]
            
            # Handle NaN values properly
            if pd.isna(original_val) and pd.isna(edited_val):
                continue
            if original_val != edited_val:
                if col not in edited_cells:
                    edited_cells[col] = []
                edited_cells[col].append(int(idx))
    
    with open(state_file, "w") as f:
        json.dump(edited_cells, f, indent=2)

def highlight_edited_cells(df, edit_state):
    """Apply highlighting to edited cells - FIXED VERSION"""
    # Create a DataFrame of styles with the same index and columns
    styles_df = pd.DataFrame('', index=df.index, columns=df.columns)
    
    # Apply highlighting to edited cells
    for col in edit_state:
        if col in df.columns:
            for idx in edit_state[col]:
                if idx in df.index:
                    styles_df.at[idx, col] = 'background-color: #FFD700'
    
    return styles_df

# ─── MAIN APPLICATION ──────────────────────────────────────────────────────
def main(username):
    """Main task UI function - takes username as parameter"""
    # Initialize paths based on username
    PAIRS_DIR = Path(f'fetched_data/{username}')
    ACCURATE_DIR = Path('processed_data')
    REJECTED_DIR = Path('rejected_data')
    EDIT_STATE_DIR = Path("edit_states")
    
    # Ensure directories exist
    for path in [PAIRS_DIR, ACCURATE_DIR, REJECTED_DIR, EDIT_STATE_DIR]:
        path.mkdir(parents=True, exist_ok=True)

    # Initialize session state variables
    if "view_highlighted" not in st.session_state:
        st.session_state.view_highlighted = False
    if "current_file" not in st.session_state:
        st.session_state.current_file = None
    if "original_df" not in st.session_state:
        st.session_state.original_df = None

    # Handle pending file actions
    if "action_pending" in st.session_state:
        if "locked_file" in st.session_state:
            selected_path = PAIRS_DIR / st.session_state.locked_file
            action = st.session_state.pop("action_pending")
            
            if action == "accept":
                move_file(selected_path, ACCURATE_DIR)
                st.success(f"Accepted and uploaded: {selected_path.name}")
            elif action == "reject":
                move_file(selected_path, REJECTED_DIR)
                st.success(f"Rejected and uploaded: {selected_path.name}")
            
            # Clean up edit state
            state_file = get_edit_state_file(selected_path)
            if state_file.exists():
                state_file.unlink()
                
            st.session_state.pop("locked_file", None)
            st.rerun()

    def fetch_next_batch():
        """Fetch new batch of data with error handling"""
        batch_number = get_next_batch_number()
        
        # Reserve batch number immediately
        increment_batch_number()
        
        try:
            result = subprocess.run(
                ["python", "data/process.py", "--batch_number", str(batch_number), "--username", username],
                check=True,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                # Record assignment to user
                assign_batch_to_user(username, batch_number)
                return True, f"Batch {batch_number} fetched successfully!"
            else:
                # Return batch number to pool
                removed = remove_last_batch_from_user(username)
                st.warning(f"Reverted batch assignment for {username}: {removed}")
                return False, f"Error fetching batch: {result.stderr}"
        except subprocess.CalledProcessError as e:
            # Return batch number to pool
            removed = remove_last_batch_from_user(username)
            st.warning(f"Reverted batch assignment for {username}: {removed}")
            return False, f"Process failed: {e.stderr}"

    # Fetch initial data if needed
    csv_files = list(PAIRS_DIR.glob("*.csv"))
    if not csv_files:
        success, msg = fetch_next_batch()
        if not success:
            st.error(f"Data fetch failed: {msg}")
            return
        csv_files = list(PAIRS_DIR.glob("*.csv"))

    # File selection interface
    filenames = sorted(f.name for f in csv_files)
    if not filenames:
        st.warning("No CSV files available. Try fetching a new batch.")
        return
        
    if "locked_file" not in st.session_state or st.session_state.locked_file not in filenames:
        st.session_state.locked_file = filenames[0]

    selected_name = st.sidebar.selectbox(
        "Select CSV:",
        filenames,
        index=filenames.index(st.session_state.locked_file)
    )
    st.session_state.locked_file = selected_name
    file_path = PAIRS_DIR / selected_name

    # Main interface
    st.title(f"Bilingual Data Editor - {username}")
    st.subheader(f"Editing: {selected_name}")
    
    try:
        # Load CSV file
        df = pd.read_csv(file_path, encoding="utf-8-sig")[['yoruba_text', 'english_text']]
        
        # Initialize state when file changes
        if st.session_state.current_file != file_path:
            st.session_state.original_df = df.copy()
            st.session_state.current_df = df.copy()
            st.session_state.current_file = file_path
            st.session_state.edit_state = load_edit_state(file_path)
            st.session_state.view_highlighted = False
        
        # Toggle between edit and view modes
        view_mode = st.radio(
            "View Mode:",
            ["✏️ Edit Mode", "👁️ View Highlighted Changes"],
            index=1 if st.session_state.view_highlighted else 0
        )
        st.session_state.view_highlighted = (view_mode == "👁️ View Highlighted Changes")
        
        # Load edit state for this file
        edit_state = st.session_state.edit_state
        
        if st.session_state.view_highlighted:
            # Show read-only highlighted view
            st.info("Showing previously edited cells. Switch to Edit Mode to make changes.")
            
            # Apply highlighting
            styles_df = highlight_edited_cells(st.session_state.current_df, edit_state)
            
            # Create a styled DataFrame
            def apply_style(row):
                styles = []
                for col in row.index:
                    style = styles_df.at[row.name, col]
                    styles.append(style if style else '')
                return styles
            
            styled_df = st.session_state.current_df.style.apply(apply_style, axis=1)
            
            st.dataframe(
                styled_df,
                use_container_width=True,
                height=500
            )
        else:
            # Show editable data editor
            st.session_state.current_df = st.data_editor(
                st.session_state.current_df,
                use_container_width=True,
                height=500,
                key=f"editor_{file_path.name}"
            )
            
            # Save button
            if st.button("💾 Save Edits", help="Save changes to local file and update edit tracking"):
                # Save to CSV
                st.session_state.current_df.to_csv(file_path, index=False, encoding="utf-8-sig")
                
                # Update edit state
                save_edit_state(
                    file_path, 
                    st.session_state.current_df,
                    st.session_state.original_df
                )
                st.session_state.edit_state = load_edit_state(file_path)
                st.session_state.original_df = st.session_state.current_df.copy()
                st.success("Edits saved and highlighted!")
        
        # Download button
        with open(file_path, "rb") as f:
            st.download_button(
                "📥 Download CSV",
                f,
                file_name=selected_name,
                mime="text/csv",
                help="Download current version of CSV"
            )
        
        st.markdown("---")
        
        # File actions
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("✅ Accept", help="Accept file and move to processed folder"):
                st.session_state.action_pending = "accept"
        with col2:
            if st.button("❌ Reject", help="Reject file and move to rejected folder"):
                st.session_state.action_pending = "reject"
        with col3:
            if st.button("⏭️ Next Batch", help="Fetch next batch without processing current"):
                success, msg = fetch_next_batch()
                if success:
                    st.success(msg)
                    # Reset file state
                    st.session_state.pop("locked_file", None)
                    st.session_state.pop("original_df", None)
                    st.session_state.pop("current_file", None)
                    st.rerun()
                else:
                    st.error(msg)
                    
    except Exception as e:
        st.error(f"File error: {str(e)}")
        import traceback
        st.error(traceback.format_exc())

# ─── GLOBAL CONFIGURATION ──────────────────────────────────────────────────
# Defined outside of main to be accessible by utility functions
TASKS_FILE = "config/tasks.json"
BATCH_FILE = Path('data/batch.json')
EDIT_STATE_DIR = Path("edit_states")

# Initialize files if not exist
if not BATCH_FILE.exists():
    BATCH_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(BATCH_FILE, "w") as f:
        json.dump({"batch_number": 0}, f)

if not os.path.exists(TASKS_FILE):
    with open(TASKS_FILE, "w") as f:
        json.dump({}, f)

# ─── COMMAND LINE SUPPORT ──────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True, help="Username for task assignment")
    args = parser.parse_args()
    
    # For CLI usage, set session state if needed
    if "username" not in st.session_state:
        st.session_state.username = args.username
        
    main(args.username)