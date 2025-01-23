import json
import pandas as pd

# Sample data
data = [
  {"Factory": 1, "Date": "2020-01-01", "Location": "Location A", "Team Members": "[{'Name': 'Member_0_0'}, {'Name': 'Member_0_1'}, {'Name': 'Member_0_2'}, {'Name': 'Member_0_3'}]"},
  {"Factory": 1, "Date": "2020-01-01", "Location": "Location A", "Team Members": "[{'Name': 'Member_1_0'}, {'Name': 'Member_1_1'}, {'Name': 'Member_1_2'}, {'Name': 'Member_1_3'}]"},
  {"Factory": 1, "Date": "2020-01-01", "Location": "Location A", "Team Members": "[{'Name': 'Member_2_0'}, {'Name': 'Member_2_1'}, {'Name': 'Member_2_2'}, {'Name': 'Member_2_3'}]"},
  {"Factory": 1, "Date": "2020-01-02", "Location": "Location A", "Team Members": "[{'Name': 'Member_3_0'}, {'Name': 'Member_3_1'}, {'Name': 'Member_3_2'}, {'Name': 'Member_3_3'}]"}
]

# Convert to DataFrame
df = pd.DataFrame(data)

# Extract parts before second underscore and create Team ID
def create_team_id(team_members_json, factory, location):
    # Replace single quotes with double quotes
    json_string = team_members_json.replace("'", '"')
    # Parse JSON
    team_members = json.loads(json_string)
    team_ids = []
    for member in team_members:
        part_before_second_underscore = '_'.join(member['Name'].split('_')[:2])
        team_ids.append(f"Factory{factory}_{location}_{part_before_second_underscore}")
    return team_ids

# Create Team IDs without modifying Member Names
df['Team ID'] = df.apply(lambda row: create_team_id(row['Team Members'], row['Factory'], row['Location']), axis=1)

# Explode the 'Team ID' list into individual rows
df = df.explode('Team ID').reset_index(drop=True)

# Display the DataFrame
print(df[['Factory', 'Date', 'Location', 'Team ID']])
