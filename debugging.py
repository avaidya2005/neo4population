import pandas as pd

# Read the CSV file into a DataFrame
csv_file_path = 'datafiles/output_with_nodes.csv'  # Update with your actual file path
df = pd.read_csv(csv_file_path)

# Display the first few rows of the DataFrame
print("Initial DataFrame columns:", df.columns)
print("First few rows of the DataFrame:\n", df.head())

# Create a DataFrame with specific columns and include 'Team Id'
team_members = df[['Team Id', 'Name', 'Operator Experience (years)', 'Operator Training Level', 'Absenteeism Rate (%)']].drop_duplicates()
print("\nDataFrame with selected columns and Team Id:")
print(team_members.head())

# Count the number of unique team members
unique_team_members_count = team_members.drop_duplicates(subset='Name').shape[0]
print(f"Total unique team members: {unique_team_members_count}")

# Count the number of teams each member is associated with
team_counts = team_members.groupby('Name')['Team Id'].nunique()
print(f"Team associations per member:\n{team_counts}")

# Detailed view of members and their associated teams
print(f"Detailed view of team-member associations:\n{team_members}")

# Optional: Save the detailed team-member association to a new CSV file
team_members.to_csv('datafiles/detailed_team_members_with_ids.csv', index=False)
