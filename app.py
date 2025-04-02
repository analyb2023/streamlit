import streamlit as st
import pandas as pd
import plotly.express as px
import hashlib
import uuid
import os
import json
from datetime import datetime
import time

# Create folders for data storage if they don't exist
os.makedirs("data", exist_ok=True)

# File paths
USERS_FILE = "data/users.json"
CANDIDATES_FILE = "data/candidates.json"
ELECTORAL_BOXES_FILE = "data/electoral_boxes.json"
VOTES_FILE = "data/votes.json"
VOTE_COUNTS_FILE = "data/vote_counts.json"
OFFLINE_VOTES_FILE = "data/offline_votes.json"

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
            
    if not os.path.exists(OFFLINE_VOTES_FILE):
        with open(OFFLINE_VOTES_FILE, "w") as f:
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

# Add candidate function with category
def add_candidate(name, party, category):
    candidates = load_data(CANDIDATES_FILE)
    candidate_id = str(uuid.uuid4())
    candidates[candidate_id] = {
        "name": name,
        "party": party,
        "category": category,
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

# Record a single vote (supports both online and offline storage)
def record_single_vote(box_id, candidate_ids, counter_username, offline_mode=False):
    vote_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    vote_data = {
        "candidates": candidate_ids,
        "recorded_by": counter_username,
        "recorded_at": timestamp
    }
    
    if offline_mode:
        # Store vote in offline storage
        offline_votes = load_data(OFFLINE_VOTES_FILE)
        if box_id not in offline_votes:
            offline_votes[box_id] = {}
        
        offline_votes[box_id][vote_id] = vote_data
        save_data(offline_votes, OFFLINE_VOTES_FILE)
        return True
    else:
        # Store vote in main storage
        votes = load_data(VOTES_FILE)
        if box_id not in votes:
            votes[box_id] = {}
        
        votes[box_id][vote_id] = vote_data
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
def record_invalid_vote(box_id, counter_username, offline_mode=False):
    return record_single_vote(box_id, ["invalid"], counter_username, offline_mode)

# Sync offline votes with the main system
def sync_offline_votes():
    offline_votes = load_data(OFFLINE_VOTES_FILE)
    if not offline_votes:
        return 0  # No votes to sync
    
    synced_count = 0
    
    for box_id, box_votes in offline_votes.items():
        for vote_id, vote_data in box_votes.items():
            # Get data from offline vote
            candidate_ids = vote_data["candidates"]
            counter_username = vote_data["recorded_by"]
            
            # Record in main system
            record_single_vote(box_id, candidate_ids, counter_username)
            synced_count += 1
    
    # Clear offline votes after successful sync
    save_data({}, OFFLINE_VOTES_FILE)
    
    return synced_count

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

# Get available categories from candidates
def get_categories():
    candidates = load_data(CANDIDATES_FILE)
    categories = set()
    
    for cid, details in candidates.items():
        if "category" in details:
            categories.add(details["category"])
    
    return sorted(list(categories))

# Admin dashboard
def admin_dashboard():
    st.title("Admin Dashboard")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Users", "Candidates", "Electoral Boxes", "Results", "Offline Votes"])
    
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
        # Add category field
        candidate_category = st.text_input("Category (e.g., President, Senator, Governor)")
        
        if st.button("Add Candidate"):
            if candidate_name and candidate_party and candidate_category:
                success, message = add_candidate(candidate_name, candidate_party, candidate_category)
                st.write(message)
            else:
                st.error("All fields are required")
        
        st.header("Existing Candidates")
        candidates = load_data(CANDIDATES_FILE)
        candidate_data = []
        for cid, details in candidates.items():
            candidate_data.append({
                "ID": cid,
                "Name": details["name"],
                "Party": details["party"],
                "Category": details.get("category", "Uncategorized")
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
    
    with tab5:
        st.header("Manage Offline Votes")
        
        # Show offline votes count
        offline_votes = load_data(OFFLINE_VOTES_FILE)
        offline_vote_count = sum(len(votes) for box_id, votes in offline_votes.items())
        
        st.write(f"Pending offline votes: {offline_vote_count}")
        
        if offline_vote_count > 0:
            if st.button("Sync Offline Votes"):
                synced = sync_offline_votes()
                st.success(f"Successfully synced {synced} votes!")
                # Force refresh
                st.rerun()
        
        # Show offline votes by box
        if offline_votes:
            st.subheader("Offline Votes by Electoral Box")
            offline_box_counts = {}
            
            for box_id, votes in offline_votes.items():
                # Get box name
                boxes = load_data(ELECTORAL_BOXES_FILE)
                box_name = f"Unknown Box ({box_id})"
                if box_id in boxes:
                    box_name = f"{boxes[box_id]['name']} ({boxes[box_id]['location']})"
                
                offline_box_counts[box_name] = len(votes)
            
            offline_box_df = pd.DataFrame([
                {"Electoral Box": box, "Pending Votes": count}
                for box, count in offline_box_counts.items()
            ])
            
            st.dataframe(offline_box_df)

# Counter dashboard with improved vote entry interface and offline support
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
    
    # Offline mode toggle
    offline_mode = st.toggle("Offline Mode", value=False, 
                            help="Enable if you're working without internet connection. Votes will be stored locally and synced later.")
    
    # If offline mode is active, show banner
    if offline_mode:
        st.warning("?? OFFLINE MODE ACTIVE: Votes will be stored locally and need to be synced later.", icon="??")
    
    # Select box to count
    box_options = {f"{details['name']} ({details['location']})": bid for bid, details in boxes.items()}
    selected_box_name = st.selectbox("Select Electoral Box", list(box_options.keys()))
    selected_box_id = box_options[selected_box_name]
    
    # Get candidate information and group by category
    candidate_by_category = {}
    for cid, details in candidates.items():
        category = details.get("category", "Uncategorized")
        if category not in candidate_by_category:
            candidate_by_category[category] = []
        
        candidate_by_category[category].append({
            "id": cid,
            "name": details["name"],
            "party": details["party"],
            "category": category
        })
    
    # Sort candidates by name within each category
    for category in candidate_by_category:
        candidate_by_category[category] = sorted(candidate_by_category[category], key=lambda x: x["name"])
    
    # Set up session state for tracking selections in current vote
    if "current_selections" not in st.session_state:
        st.session_state.current_selections = set()
    
    # Set up session state for selected category
    if "selected_category" not in st.session_state:
        categories = list(candidate_by_category.keys())
        st.session_state.selected_category = categories[0] if categories else None
    
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
        
        success = record_single_vote(selected_box_id, list(st.session_state.current_selections), username, offline_mode)
        if success:
            st.session_state.current_selections = set()
            
            if offline_mode:
                st.success("Vote recorded offline and will be synced later!")
            else:
                st.success("Vote recorded successfully!")
                
                # Update the vote counts display
                vote_counts = load_data(VOTE_COUNTS_FILE)
                box_counts = vote_counts.get(selected_box_id, {})
                
                # Update counts for all candidates
                for category in candidate_by_category:
                    for candidate in candidate_by_category[category]:
                        st.session_state[f"count_{candidate['id']}"] = box_counts.get(candidate["id"], 0)
                
                st.session_state[f"count_invalid"] = box_counts.get("invalid", 0)
                
                # Update total count
                total = sum(box_counts.values())
                st.session_state["total_count"] = total

    # Function to submit invalid vote
    def submit_invalid():
        success = record_invalid_vote(selected_box_id, username, offline_mode)
        if success:
            st.session_state.current_selections = set()
            
            if offline_mode:
                st.success("Invalid vote recorded offline and will be synced later!")
            else:
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
    
    # Sync offline votes function for counter
    def sync_votes_counter():
        synced = sync_offline_votes()
        st.success(f"Successfully synced {synced} votes!")
        # Force refresh
        st.rerun()
    
    # Display vote entry interface with buttons
    st.header("Quick Vote Entry")
    
    # Initialize counts in session state
    vote_counts = load_data(VOTE_COUNTS_FILE)
    box_counts = vote_counts.get(selected_box_id, {})
    
    if "total_count" not in st.session_state:
        st.session_state["total_count"] = sum(box_counts.values())
    
    # Display current vote count
    st.subheader(f"Total votes recorded: {st.session_state['total_count']}")
    
    # If there are offline votes and not in offline mode, show sync button
    offline_votes = load_data(OFFLINE_VOTES_FILE)
    offline_vote_count = sum(len(votes) for box_id, votes in offline_votes.items())
    
    if offline_vote_count > 0 and not offline_mode:
        st.warning(f"You have {offline_vote_count} pending offline votes that need syncing.")
        if st.button("Sync Offline Votes"):
            sync_votes_counter()
    
    # Display info about current selections
    if st.session_state.current_selections:
        selected_names = []
        for cid in st.session_state.current_selections:
            for category in candidate_by_category:
                for candidate in candidate_by_category[category]:
                    if candidate["id"] == cid:
                        selected_names.append(f"{candidate['name']} ({candidate['party']}) - {category}")
        
        st.write("Current selection:")
        for name in selected_names:
            st.markdown(f"- {name}")
    else:
        st.info("No candidates selected for current vote")
    
    # Category tabs
    category_tabs = st.tabs(list(candidate_by_category.keys()))
    
    # Initialize counts for each candidate
    for category in candidate_by_category:
        for candidate in candidate_by_category[category]:
            if f"count_{candidate['id']}" not in st.session_state:
                st.session_state[f"count_{candidate['id']}"] = box_counts.get(candidate["id"], 0)
    
    if f"count_invalid" not in st.session_state:
        st.session_state[f"count_invalid"] = box_counts.get("invalid", 0)
    
    # Create a grid layout for candidate buttons within each category tab
    cols_per_row = 3
    for i, category in enumerate(candidate_by_category):
        with category_tabs[i]:
            candidates_in_category = candidate_by_category[category]
            for j in range(0, len(candidates_in_category), cols_per_row):
                cols = st.columns(cols_per_row)
                for k in range(cols_per_row):
                    if j + k < len(candidates_in_category):
                        candidate = candidates_in_category[j + k]
                        with cols[k]:
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
    
    # Create tabs for each category in results
    result_categories = list(candidate_by_category.keys()) + ["Overall"]
    result_tabs = st.tabs(result_categories)
    
    # Initialize result data by category
    results_by_category = {category: [] for category in candidate_by_category}
    
    for category in candidate_by_category:
        for candidate in candidate_by_category[category]:
            count = box_counts.get(candidate["id"], 0)
            results_by_category[category].append({
                "Candidate": candidate["name"],
                "Party": candidate["party"],
                "Category": category,
                "Votes": count
            })
    
    # Add invalid votes to a general category
    invalid_votes = {
        "Candidate": "Invalid Votes",
        "Party": "N/A",
        "Category": "Invalid",
        "Votes": box_counts.get("invalid", 0)
    }
    
    # Display results by category
    for i, category in enumerate(candidate_by_category):
        with result_tabs[i]:
            if results_by_category[category]:
                category_df = pd.DataFrame(results_by_category[category])
                st.dataframe(category_df)
                
                # Bar chart of results for this category
                total_votes_category = sum(c["Votes"] for c in results_by_category[category])
                if total_votes_category > 0:
                    fig = px.bar(
                        category_df, 
                        x="Candidate", 
                        y="Votes", 
                        color="Party", 
                        title=f"{category} Vote Distribution for {selected_box_name}"
                    )
                    st.plotly_chart(fig)
            else:
                st.info(f"No votes recorded for {category} yet.")
    
    # Display overall results
    with result_tabs[-1]:
        # Combine all category results
        all_results = []
        for category in results_by_category:
            all_results.extend(results_by_category[category])
        
        # Add invalid votes
        all_results.append(invalid_votes)
        
        if all_results:
            all_results_df = pd.DataFrame(all_results)
            st.dataframe(all_results_df)
            
            # Bar chart of overall results
            total_votes = sum(r["Votes"] for r in all_results)
            if total_votes > 0:
                fig = px.bar(
                    all_results_df, 
                    x="Candidate", 
                    y="Votes", 
                    color="Category", 
                    title=f"Overall Vote Distribution for {selected_box_name}"
                )
                st.plotly_chart(fig)
        else:
            st.info("No votes recorded yet.")
    
    # Show overall results as well
    display_results()

# Display results and dashboard with category segregation
def display_results():
    st.header("Overall Election Results")
    
    # Get total votes by candidate
    results = get_total_votes()
    candidates = load_data(CANDIDATES_FILE)
    
    # Get categories and organize candidates by category
    candidates_by_category = {}
    for cid, details in candidates.items():
        category = details.get("category", "Uncategorized")
        if category not in candidates_by_category:
            candidates_by_category[category] = []
        
        candidates_by_category[category].append({
            "id": cid,
            "name": details["name"],
            "party": details["party"]
        })