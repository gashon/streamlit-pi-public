import os
import subprocess
from datetime import datetime
import json

import streamlit as st

# Set the title of the app
# st.title("Video Compare App with Sorted Prompts")
# st.set_page_config(page_title="Video Compare App", layout="wide")

st.set_page_config(page_title="Video Compare App", layout="wide")

def format_json_display(raw_prompt):
    try:
        # Try parsing and pretty-printing as JSON
        obj = json.loads(raw_prompt)
        pretty = json.dumps(obj, indent=2)
        return f"```json\n{pretty}\n```"
    except Exception:
        # Fallback: force line breaks at commas if not parseable
        safe_prompt = raw_prompt.replace(",", ",\n")
        return f"```text\n{safe_prompt}\n```"


# # CSS TO MAKE VIDES SMALLER
# custom_css = """
# <style>
#
# html {
#     background: whitesmoke !important;
# }
#
# .stElementContainer {
# display: flex;
# justify-content: center;
# align-items: center;
#
# }
#     .stVideo {
#         max-width: 400px !important;
#         margin: 0 auto;
#     }
# </style>
# """
# st.markdown(custom_css, unsafe_allow_html=True)


# Function to load prompts from a file
def load_prompts(prompt_file_path):
    if os.path.exists(prompt_file_path):
        with open(prompt_file_path, "r") as f:
            prompts = f.read()
        if "-------" in prompts:
            return prompts.split("-------")
        else:
            return prompts.split("\n")
    else:
        return None


# Function to sort video files based on their numeric ID (e.g., fileXXX.mp4)
def sort_videos_by_id(video_files):
    def extract_id(video_file):
        try:
            return int(video_file.replace("video", "").replace(".mp4", ""))
        except ValueError:
            return float("inf")  # Place invalid files at the end

    return sorted(video_files, key=extract_id)


# Function to get git commit date for a directory
def get_git_commit_date(directory_path):
    """Get the last commit date for files in a directory using git log."""
    try:
        # Use git log to find the last commit that modified files in this directory
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ci", "--", directory_path],
            capture_output=True,
            text=True,
            cwd="."
        )
        if result.returncode == 0 and result.stdout.strip():
            # Parse the git date format: "2025-05-26 02:59:55 -0700"
            date_str = result.stdout.strip().split()[0]  # Get just the date part
            return datetime.strptime(date_str, "%Y-%m-%d")
        else:
            # Fallback to current date if git fails
            return datetime.now()
    except Exception:
        # Fallback to current date if git command fails
        return datetime.now()


# Function to format category name for display
def format_category_display(category_name):
    # Extract date from git commit history
    category_path = os.path.join(video_dir, category_name)
    commit_date = get_git_commit_date(category_path)
    date_str = commit_date.strftime("[%b %d]").lower()

    # Replace hyphens with spaces in the category name and convert to lowercase
    display_name = " ".join(category_name.split("-")).lower()

    return f"{date_str} {display_name}"


# Get the list of category folders in the 'video' directory
video_dir = "video"
categories = sorted(
    [d for d in os.listdir(video_dir) if os.path.isdir(os.path.join(video_dir, d))],
    key=lambda d: get_git_commit_date(os.path.join(video_dir, d)),
    reverse=True,
)

# Create a mapping of display names to actual folder names
category_display_map = {format_category_display(cat): cat for cat in categories}
category_display_names = list(category_display_map.keys())

# Retrieve the "category" value from query params
selected_category_from_query = st.query_params.get("category", None)

# If there are no categories, display a message
if not categories:
    st.error("No categories found in the 'video' directory.")
else:
    st.markdown("# pi-vid-eval compare")
    # Determine default index for selectbox if the query param matches a category
    default_index = 0
    if selected_category_from_query in categories:
        # Find the display name for the query parameter
        selected_display = next(
            (
                disp
                for disp, cat in category_display_map.items()
                if cat == selected_category_from_query
            ),
            category_display_names[0],
        )
        default_index = category_display_names.index(selected_display)

    # Let the user select a category
    selected_display = st.selectbox(
        "Select a Category", category_display_names, index=default_index
    )

    # Get the actual folder name from the display name
    selected_category = category_display_map[selected_display]

    # Update the query parameter to reflect the current selection
    # Writing directly to st.query_params automatically updates the URL.
    st.query_params["category"] = selected_category

    category_path = os.path.join(video_dir, selected_category)

    # Load prompts from the selected category folder
    prompt_file_path = os.path.join(category_path, "prompt.txt")
    prompts = load_prompts(prompt_file_path)

    if prompts is None:
        st.error(f"No prompt.txt file found in '{selected_category}'.")
    else:
        # Get the list of subfolders in the selected category
        subfolders = [
            d
            for d in os.listdir(category_path)
            if os.path.isdir(os.path.join(category_path, d))
        ]

        if len(subfolders) < 1:
            st.error(
                f"At least one subfolder is required for comparison in '{selected_category}'."
            )
        else:
            # Display prompts and corresponding videos for each pair of subfolders
            subfolder_paths = [os.path.join(category_path, sf) for sf in subfolders]
            subfolder_videos = [
                sort_videos_by_id(
                    [f for f in os.listdir(path) if f.lower().endswith(".mp4")]
                )
                for path in subfolder_paths
            ]

            max_videos = max(len(videos) for videos in subfolder_videos)

            for video_idx in range(max_videos):
                if len(subfolders) == 1:
                    # For single folder, wrap all content in centered narrow container
                    _, center_col, _ = st.columns([1, 2, 1])
                    with center_col:
                        # Display video number
                        st.markdown(f"### Video {video_idx + 1}")

                        # Display the corresponding prompt
                        prompt = (
                            format_json_display(prompts[video_idx])
                            if 0 <= video_idx < len(prompts)
                            else "No prompt available"
                        )
                        st.markdown(f"{prompt}")

                        # Display folder name
                        st.markdown(f"#### {subfolders[0]}")

                        # Display video
                        videos = subfolder_videos[0]
                        if video_idx < len(videos):
                            video_file = videos[video_idx]
                            video_path = os.path.join(subfolder_paths[0], video_file)
                            st.video(video_path)
                            st.caption(video_file)
                        else:
                            st.warning("No video available")

                        # Add a separator between video sets
                        st.markdown("---")
                else:
                    # For multiple folders, use full width layout
                    # Display video number
                    st.markdown(f"### Video {video_idx + 1}")

                    # Display the corresponding prompt
                    prompt = (
                        format_json_display(prompts[video_idx])
                        if 0 <= video_idx < len(prompts)
                        else "No prompt available"
                    )

                    formatted_prompt = format_json_display(prompt)
                    #st.markdown(formatted_prompt)

                    # Display folder names in columns
                    folder_cols = st.columns(len(subfolders))
                    for col_idx, subfolder in enumerate(subfolders):
                        with folder_cols[col_idx]:
                            st.markdown(f"#### {subfolder}")

                    # Create one row for each set of videos
                    video_cols = st.columns(len(subfolders))
                    # Display each model's video in its own column
                    for col_idx, videos in enumerate(subfolder_videos):
                        with video_cols[col_idx]:
                            if video_idx < len(videos):
                                video_file = videos[video_idx]
                                video_path = os.path.join(
                                    subfolder_paths[col_idx], video_file
                                )
                                st.video(video_path)
                                st.caption(video_file)
                            else:
                                st.warning("No video available")

                    # Add a separator between video sets
                    st.markdown("---")
