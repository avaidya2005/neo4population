import pandas as pd
import ast
from neo4j import GraphDatabase
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

# Define the URI and credentials for your Neo4j database
uri = "neo4j://localhost:7687"
username = "neo4j"
password = "neo4j123"

# Create a Neo4j driver instance
driver = GraphDatabase.driver(uri, auth=(username, password))

# Function to execute batched queries
def execute_batch_queries(batch_queries):
    with driver.session() as session:
        with session.begin_transaction() as tx:
            for q in batch_queries:
                tx.run(q['query'], q['parameters'])

# Step 1: Read the CSV file
df = pd.read_csv("datafiles/LargeDataSet.csv")

# Step 2: Parse the `Team Members` column with `ast.literal_eval`,
# and add `Factory`, `Location`, and distinct `ID`
def parse_team_members(row):
    def get_name_part(name):
        parts = name.split('_')
        return '_'.join(parts[:2])  # Take parts before the second underscore

    try:
        team_members = ast.literal_eval(row['Team Members'])
        nodes = []
        for member in team_members:
            name_part = get_name_part(member['Name'])
            id = f"{row['Location']}_{row['Factory']}_{name_part}"
            nodes.append({
                'Team Id': id,
                'Name': member['Name'],
                'Factory': row['Factory'],
                'Location': row['Location'],
                'Operator Experience (years)': member['Operator Experience (years)'],
                'Operator Training Level': member['Operator Training Level'],
                'Absenteeism Rate (%)': member['Absenteeism Rate (%)']
            })
        return nodes
    except (ValueError, SyntaxError) as e:
        print(f"Error parsing row {row.name}: {e}")
        return []

# Apply the function to each row and create a dataframe of nodes
df['Team Member Nodes'] = df.apply(parse_team_members, axis=1)

# Display the new dataframe with team member nodes
teamMemberNodes = df['Team Member Nodes'].explode().apply(pd.Series).drop_duplicates()

# Optionally, save the updated dataframe to a new CSV file
output_csv_path = "datafiles/output_with_nodes.csv"
teamMemberNodes.to_csv(output_csv_path, index=False)

# Read the new CSV file into a DataFrame for Neo4j insertion
df = pd.read_csv(output_csv_path)

# Replace NaN values with a default value (e.g., empty string)
df = df.fillna('')

# Create Team nodes
team_queries = []
for index, row in df.iterrows():
    team_queries.append({
        'query': """
            MERGE (t:Team {
                id: $id,
                factory: $factory,
                location: $location
            })
        """,
        'parameters': {
            'id': row['Team Id'],
            'factory': row['Factory'],
            'location': row['Location']
        }
    })
execute_batch_queries(team_queries)

# Create Member nodes and relationships to Teams
member_queries = []
for index, row in df.iterrows():
    member_queries.append({
        'query': """
            MATCH (t:Team {id: $team_id})
            MERGE (m:Member {
                name: $name,
                experience: $experience,
                trainingLevel: $trainingLevel,
                absenteeismRate: $absenteeismRate,
                factory: $factory,
                location: $location
            })
            MERGE (t)-[:HAS_MEMBER]->(m)
        """,
        'parameters': {
            'team_id': row['Team Id'],
            'name': row['Name'],
            'experience': row['Operator Experience (years)'],
            'trainingLevel': row['Operator Training Level'],
            'absenteeismRate': row['Absenteeism Rate (%)'],
            'factory': row['Factory'],
            'location': row['Location']
        }
    })

df = pd.read_csv("datafiles/LargeDataSet.csv")
df = df.fillna('')
unique_dates = df['Date'].unique()
date_queries = []
for date in unique_dates:
    date_queries.append({
        'query': """
            MERGE (d:Date {date: date($date)})
        """,
        'parameters': {
            'date': date
        }
    })

df['unique_machine_id'] = df['Location'] + '-' + df['Factory'].astype(str) + '-' + df['Machine Type']  # Create a unique machine ID

node_queries = []
for index, row in df.iterrows():
    node_queries.append({
        'query': """
            MERGE (f:Factory {factory_id: $factory, location: $location})
            MERGE (m:Machine {machine_id: $unique_machine_id, machine_type: $machine_type, machine_age: $machine_age})
            MERGE (:Product {product_category: $product_category})
            MERGE (:Supplier {supplier_name: $supplier_name})

        """,
        'parameters': {
            'factory': row['Factory'],
            'location': row['Location'],
            'unique_machine_id': row['unique_machine_id'],
            'machine_type': row['Machine Type'],
            'machine_age': row['Machine Age (years)'],
            'product_category': row['Product Category'],
            'supplier_name': row['Supplier']
        }
    })


machine_queries = []
for index, row in df.iterrows():
    machine_queries.append({
        'query': """
            MATCH (f:Factory {factory_id: $factory, location: $location})
            MERGE (m:Machine {machine_id: $unique_machine_id})
            MERGE (f)-[:HAS_MACHINE]->(m)
        """,
        'parameters': {
            'factory': row['Factory'],
            'location': row['Location'],
            'unique_machine_id': row['unique_machine_id'],
        }
    })

# Create OPERATED_ON relationships
operated_on_queries = []
for index, row in df.iterrows():
    operated_on_queries.append({
        'query': """
            MATCH (f:Factory {factory_id: $factory, location: $location})
            MATCH (d:Date {date: date($date)})
            MERGE (f)-[r:OPERATED_ON {production_volume: $production_volume, revenue: $revenue, profit_margin: $profit_margin, market_demand_index: $market_demand_index, shift: $shifts}]->(d)
        """,
        'parameters': {
            'factory': row['Factory'],
            'location': row['Location'],
            'date': row['Date'],
            'production_volume': row['Production Volume (units)'],
            'revenue': row['Revenue ($)'],
            'profit_margin': row['Profit Margin (%)'],
            'market_demand_index': row['Market Demand Index'],
            'shifts': row['Shift']
        }
    })

execute_batch_queries(date_queries)    
execute_batch_queries(member_queries)
execute_batch_queries(node_queries)
execute_batch_queries(machine_queries)
execute_batch_queries(operated_on_queries)


# Close the driver connection
driver.close()
