import streamlit as st
import pandas as pd
import plotly.express as px
import hashlib
import uuid
import os
import json
from datetime import datetime

# Create folders for data storage if they don't exist
os.makedirs("data", exist_ok=True)

# File paths
USERS_FILE = "data/users.json"
CANDIDATES_FILE = "data/candidates.json"
ELECTORAL_BOXES_FILE = "data/electoral_boxes.json"
VOTES_FILE = "data/votes.json"
VOTE_COUNTS_FILE = "data/vote_counts.json"

# Initialize data files if they don't exist
def initialize_data_files():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            # Create a default admin user
            default_admin = {
                "admin": {
                    "password": hashlib.sha256("admin123".encode()).hexdigest(),
                    "role": "admin",
                    "created_at": datetime.now().isoformat()
                }
            }
            json.dump(default_admin, f)
    
    if not os.path.exists(CANDIDATES_FILE):
        with open(CANDIDATES_FILE, "w") as f:
            json.dump({}, f)
    
    if not os.path.exists(ELECTORAL_BOXES_FILE):
        with open(ELECTORAL_BOXES_FILE, "w") as f:
            json.dump({}, f)
    
    if not os.path.exists(VOTES_FILE):
        with open(VOTES_FILE, "w") as f:
            json.dump({}, f)
            
    if not os.path.exists(VOTE_COUNTS_FILE):
        with open(VOTE_COUNTS_FILE, "w") as f:
            json.dump({}, f)

# Load data
def load_data(file_path):
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Save data
def save_data(data, file_path):
    with open(file_path, "w") as f:
        json.dump(data, f)

# Authentication functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate(username, password):
    users = load_data(USERS_FILE)
    if username in users and users[username]["password"] == hash_password(password):
        return users[username]["role"]
    return None

# Add user function
def add_user(username, password, role):
    users = load_data(USERS_FILE)
    if username in users:
        return False, "Username already exists"
    
    users[username] = {
        "password": hash_password(password),
        "role": role,
        "created_at": datetime.now().isoformat()
    }
    save_data(users, USERS_FILE)
    return True, "User added successfully"

# Add candidate function
def add_candidate(name, party):
    candidates = load_data(CANDIDATES_FILE)
    candidate_id = str(uuid.uuid4())
    candidates[candidate_id] = {
        "name": name,
        "party": party,
        "created_at": datetime.now().isoformat()
    }
    save_data(candidates, CANDIDATES_FILE)
    return True, "Candidate added successfully"

# Add electoral box function
def add_electoral_box(name, location, registered_voters):
    boxes = load_data(ELECTORAL_BOXES_FILE)
    box_id = str(uuid.uuid4())
    boxes[box_id] = {
        "name": name,
        "location": location,
        "registered_voters": registered_voters,
        "created_at": datetime.now().isoformat()
    }
    save_data(boxes, ELECTORAL_BOXES_FILE)
    return True, "Electoral box added successfully"

# Record a single vote
def record_single_vote(box_id, candidate_ids, counter_username):
    votes = load_data(VOTES_FILE)
    
    # Create a unique ID for this vote entry
    vote_id = str(uuid.uuid4())
    
    # Record the vote
    if box_id not in votes:
        votes[box_id] = {}
    
    votes[box_id][vote_id] = {
        "candidates": candidate_ids,
        "recorded_by": counter_username,
        "recorded_at": datetime.now().isoformat()
    }
    
    save_data(votes, VOTES_FILE)
    
    # Also update the vote counts for easier reporting
    vote_counts = load_data(VOTE_COUNTS_FILE)
    
    if box_id not in vote_counts:
        vote_counts[box_id] = {}
    
    for candidate_id in candidate_ids:
        if candidate_id not in vote_counts[box_id]:
            vote_counts[box_id][candidate_id] = 0
        vote_counts[box_id][candidate_id] += 1
    
    save_data(vote_counts, VOTE_COUNTS_FILE)
    
    return True

# Record invalid vote
def record_invalid_vote(box_id, counter_username):
    return record_single_vote(box_id, ["invalid"], counter_username)

# Get total votes by candidate
def get_total_votes():
    vote_counts = load_data(VOTE_COUNTS_FILE)
    candidates = load_data(CANDIDATES_FILE)
    
    # Initialize results dictionary
    results = {candidate_id: 0 for candidate_id in candidates}
    results["invalid"] = 0
    
    # Sum up all votes
    for box_id, box_votes in vote_counts.items():
        for candidate_id, count in box_votes.items():
            if candidate_id in results:
                results[candidate_id] += count
            elif candidate_id == "invalid":
                results["invalid"] += count
    
    return results

# Calculate progress of counting
def get_counting_progress():
    boxes = load_data(ELECTORAL_BOXES_FILE)
    votes = load_data(VOTES_FILE)
    
    total_boxes = len(boxes)
    counted_boxes = sum(1 for box_id in votes if votes[box_id])
    
    if total_boxes == 0:
        return 0
    
    return (counted_boxes / total_boxes) * 100

# Admin dashboard
def admin_dashboard():
    st.title("Admin Dashboard")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Users", "Candidates", "Electoral Boxes", "Results"])
    
    with tab1:
        st.header("Add User")
        new_username = st.text_input("Username", key="new_user")
        new_password = st.text_input("Password", type="password", key="new_pass")
        new_role = st.selectbox("Role", ["admin", "counter", "public"])
        
        if st.button("Add User"):
            success, message = add_user(new_username, new_password, new_role)
            st.write(message)
        
        st.header("Existing Users")
        users = load_data(USERS_FILE)
        user_data = []
        for username, details in users.items():
            user_data.append({
                "Username": username,
                "Role": details["role"],
                "Created At": details["created_at"]
            })
        
        if user_data:
            st.dataframe(pd.DataFrame(user_data))
    
    with tab2:
        st.header("Add Candidate")
        candidate_name = st.text_input("Candidate Name")
        candidate_party = st.text_input("Party")
        
        if st.button("Add Candidate"):
            success, message = add_candidate(candidate_name, candidate_party)
            st.write(message)
        
        st.header("Existing Candidates")
        candidates = load_data(CANDIDATES_FILE)
        candidate_data = []
        for cid, details in candidates.items():
            candidate_data.append({
                "ID": cid,
                "Name": details["name"],
                "Party": details["party"]
            })
        
        if candidate_data:
            st.dataframe(pd.DataFrame(candidate_data))
    
    with tab3:
        st.header("Add Electoral Box")
        box_name = st.text_input("Box Name")
        box_location = st.text_input("Location")
        registered_voters = st.number_input("Registered Voters", min_value=0, value=0)
        
        if st.button("Add Electoral Box"):
            success, message = add_electoral_box(box_name, box_location, registered_voters)
            st.write(message)
        
        st.header("Existing Electoral Boxes")
        boxes = load_data(ELECTORAL_BOXES_FILE)
        box_data = []
        for bid, details in boxes.items():
            box_data.append({
                "ID": bid,
                "Name": details["name"],
                "Location": details["location"],
                "Registered Voters": details["registered_voters"]
            })
        
        if box_data:
            st.dataframe(pd.DataFrame(box_data))
    
    with tab4:
        display_results()

# Counter dashboard with improved vote entry interface
def counter_dashboard(username):
    st.title("Vote Counter Dashboard")
    
    # Get electoral boxes
    boxes = load_data(ELECTORAL_BOXES_FILE)
    candidates = load_data(CANDIDATES_FILE)
    
    if not boxes:
        st.warning("No electoral boxes have been created yet.")
        return

    if not candidates:
        st.warning("No candidates have been added yet.")
        return
    
    # Select box to count
    box_options = {f"{details['name']} ({details['location']})": bid for bid, details in boxes.items()}
    selected_box_name = st.selectbox("Select Electoral Box", list(box_options.keys()))
    selected_box_id = box_options[selected_box_name]
    
    # Get candidate information sorted by name
    candidate_info = []
    for cid, details in candidates.items():
        candidate_info.append({
            "id": cid,
            "name": details["name"],
            "party": details["party"]
        })
    
    # Sort candidates by name
    candidate_info = sorted(candidate_info, key=lambda x: x["name"])
    
    # Set up session state for tracking selections in current vote
    if "current_selections" not in st.session_state:
        st.session_state.current_selections = set()
    
    # Function to toggle candidate selection
    def toggle_candidate(candidate_id):
        if candidate_id in st.session_state.current_selections:
            st.session_state.current_selections.remove(candidate_id)
        else:
            st.session_state.current_selections.add(candidate_id)
    
    # Function to submit the current vote
    def submit_vote():
        if not st.session_state.current_selections:
            st.warning("No candidates selected. Please select at least one candidate or mark as invalid.")
            return
        
        record_single_vote(selected_box_id, list(st.session_state.current_selections), username)
        st.session_state.current_selections = set()
        st.success("Vote recorded successfully!")
        
        # Update the vote counts display
        vote_counts = load_data(VOTE_COUNTS_FILE)
        box_counts = vote_counts.get(selected_box_id, {})
        for i, candidate in enumerate(candidate_info):
            st.session_state[f"count_{candidate['id']}"] = box_counts.get(candidate["id"], 0)
        st.session_state[f"count_invalid"] = box_counts.get("invalid", 0)
        
        # Update total count
        total = sum(box_counts.values())
        st.session_state["total_count"] = total

    # Function to submit invalid vote
    def submit_invalid():
        record_invalid_vote(selected_box_id, username)
        st.session_state.current_selections = set()
        st.success("Invalid vote recorded!")
        
        # Update the invalid vote count display
        vote_counts = load_data(VOTE_COUNTS_FILE)
        box_counts = vote_counts.get(selected_box_id, {})
        st.session_state[f"count_invalid"] = box_counts.get("invalid", 0)
        
        # Update total count
        total = sum(box_counts.values())
        st.session_state["total_count"] = total
    
    # Function to clear selections
    def clear_selections():
        st.session_state.current_selections = set()
        st.success("Selections cleared!")
    
    # Display vote entry interface with buttons
    st.header("Quick Vote Entry")
    
    # Initialize counts in session state
    vote_counts = load_data(VOTE_COUNTS_FILE)
    box_counts = vote_counts.get(selected_box_id, {})
    
    if "total_count" not in st.session_state:
        st.session_state["total_count"] = sum(box_counts.values())
    
    # Display current vote count
    st.subheader(f"Total votes recorded: {st.session_state['total_count']}")
    
    # Display info about current selections
    if st.session_state.current_selections:
        selected_names = []
        for cid in st.session_state.current_selections:
            for candidate in candidate_info:
                if candidate["id"] == cid:
                    selected_names.append(f"{candidate['name']} ({candidate['party']})")
        
        st.write("Current selection:")
        for name in selected_names:
            st.markdown(f"- {name}")
    else:
        st.info("No candidates selected for current vote")
    
    # Create a grid layout for candidate buttons
    cols_per_row = 3
    
    # Initialize counts for each candidate
    for i, candidate in enumerate(candidate_info):
        if f"count_{candidate['id']}" not in st.session_state:
            st.session_state[f"count_{candidate['id']}"] = box_counts.get(candidate["id"], 0)
    
    if f"count_invalid" not in st.session_state:
        st.session_state[f"count_invalid"] = box_counts.get("invalid", 0)
    
    # Create rows of candidates
    for i in range(0, len(candidate_info), cols_per_row):
        cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            if i + j < len(candidate_info):
                candidate = candidate_info[i + j]
                with cols[j]:
                    # Determine button color based on selection state
                    button_key = f"candidate_{candidate['id']}"
                    is_selected = candidate["id"] in st.session_state.current_selections
                    button_label = f"{candidate['name']}\n({candidate['party']})\nCount: {st.session_state[f'count_{candidate['id']}']}"
                    
                    if is_selected:
                        st.button(
                            button_label, 
                            key=button_key, 
                            on_click=toggle_candidate,
                            args=(candidate["id"],),
                            type="primary"  # Highlight selected candidates
                        )
                    else:
                        st.button(
                            button_label, 
                            key=button_key, 
                            on_click=toggle_candidate,
                            args=(candidate["id"],)
                        )
    
    # Create action buttons for vote submission
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.button(
            "Submit Vote", 
            key="submit_vote",
            on_click=submit_vote,
            type="primary"
        )
    
    with col2:
        st.button(
            f"Submit Invalid Vote (Count: {st.session_state['count_invalid']})", 
            key="submit_invalid",
            on_click=submit_invalid
        )
    
    with col3:
        st.button(
            "Clear Selections", 
            key="clear_selections",
            on_click=clear_selections
        )
    
    # Show keyboard shortcuts instructions
    with st.expander("Keyboard Shortcuts"):
        st.markdown("""
        For faster vote entry, you can use keyboard shortcuts:
        - **Enter**: Submit the current vote
        - **Esc**: Clear all selections
        - **I**: Mark as invalid vote
        """)
        st.info("Note: Click anywhere on the page first to enable keyboard shortcuts")
    
    # Add JavaScript for keyboard shortcuts
    st.markdown("""
    <script>
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            document.querySelector('button[data-testid="submit_vote"]').click();
        } else if (e.key === 'Escape') {
            document.querySelector('button[data-testid="clear_selections"]').click();
        } else if (e.key === 'i' || e.key === 'I') {
            document.querySelector('button[data-testid="submit_invalid"]').click();
        }
    });
    </script>
    """, unsafe_allow_html=True)
    
    # Show current progress
    st.header("Counting Progress")
    progress = get_counting_progress()
    st.progress(progress / 100)
    st.write(f"{progress:.1f}% of electoral boxes counted")
    
    # Show current results for this electoral box
    st.header(f"Results for {selected_box_name}")
    box_results = []
    
    for candidate in candidate_info:
        count = box_counts.get(candidate["id"], 0)
        box_results.append({
            "Candidate": candidate["name"],
            "Party": candidate["party"],
            "Votes": count
        })
    
    # Add invalid votes
    box_results.append({
        "Candidate": "Invalid Votes",
        "Party": "N/A",
        "Votes": box_counts.get("invalid", 0)
    })
    
    if box_results:
        box_results_df = pd.DataFrame(box_results)
        st.dataframe(box_results_df)
        
        # Bar chart of results
        total_votes = sum(box_counts.values())
        if total_votes > 0:
            fig = px.bar(
                box_results_df, 
                x="Candidate", 
                y="Votes", 
                color="Party", 
                title=f"Vote Distribution for {selected_box_name}"
            )
            st.plotly_chart(fig)
    
    # Show overall results as well
    display_results()

# Display results and dashboard
def display_results():
    st.header("Overall Election Results")
    
    # Get total votes by candidate
    results = get_total_votes()
    candidates = load_data(CANDIDATES_FILE)
    
    # Prepare data for visualization
    result_data = []
    for cid, votes in results.items():
        if cid == "invalid":
            name = "Invalid Votes"
            party = "N/A"
        else:
            if cid in candidates:
                name = candidates[cid]["name"]
                party = candidates[cid]["party"]
            else:
                continue
        
        result_data.append({
            "Candidate": name,
            "Party": party,
            "Votes": votes
        })
    
    # Display results table
    if result_data:
        result_df = pd.DataFrame(result_data)
        st.dataframe(result_df)
        
        # Bar chart of results
        if sum(results.values()) > 0:  # Only show chart if there are votes
            fig = px.bar(
                result_df, 
                x="Candidate", 
                y="Votes", 
                color="Party", 
                title="Overall Vote Distribution"
            )
            st.plotly_chart(fig)
            
            # Pie chart for percentage distribution
            fig2 = px.pie(
                result_df, 
                values="Votes", 
                names="Candidate",
                title="Vote Share by Candidate",
                hover_data=["Party"]
            )
            st.plotly_chart(fig2)
    else:
        st.info("No votes recorded yet.")
    
    # Counting progress
    progress = get_counting_progress()
    st.write(f"Counting Progress: {progress:.1f}%")

# Public dashboard
def public_dashboard():
    st.title("Election Results - Public View")
    display_results()

# Main app
def main():
    # Initialize data files
    initialize_data_files()
    
    # Set page config
    st.set_page_config(
        page_title="Election Results Management System",
        page_icon="???",
        layout="wide"
    )
    
    # Add custom CSS for improved button styling
    st.markdown("""
    <style>
    .stButton button {
        height: 100px;
        white-space: pre-wrap;
        word-wrap: break-word;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Session state initialization
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.role = None
    
    # Sidebar for authentication
    with st.sidebar:
        st.title("Election Management")
        
        if st.session_state.authenticated:
            st.write(f"Logged in as: {st.session_state.username}")
            st.write(f"Role: {st.session_state.role}")
            
            if st.button("Logout"):
                st.session_state.authenticated = False
                st.session_state.username = None
                st.session_state.role = None
                st.rerun()
        else:
            st.header("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.button("Login"):
                role = authenticate(username, password)
                if role:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.role = role
                    st.success(f"Logged in as {role}")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
    
    # Main content based on authentication state and role
    if st.session_state.authenticated:
        if st.session_state.role == "admin":
            admin_dashboard()
        elif st.session_state.role == "counter":
            counter_dashboard(st.session_state.username)
        else:  # public or any other role
            public_dashboard()
    else:
        # If not authenticated, show public dashboard only
        public_dashboard()

if __name__ == "__main__":
    main()