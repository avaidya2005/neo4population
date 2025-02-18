import pandas as pd
import ast
from neo4j import GraphDatabase
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO)

# Define the URI and credentials for your Neo4j database
uri = "neo4j://127.0.0.1:7687"
username = "neo4j"
password = "neo4j123"

# Create a Neo4j driver instance
driver = GraphDatabase.driver(uri, auth=(username, password))

def create_team_id(team_members, factory, location):
    # Correct potential JSON format issues
    try:
        team_members_list = json.loads(team_members.replace("'", '"'))
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return None
    
    # Get the name of the first member
    first_member_name = team_members_list[0]['Name']
    
    # Extract the segment before the second underscore
    team_id_segment = first_member_name.split('_')[0] + '_' + first_member_name.split('_')[1]
    
    # Create a unique team ID
    team_id = f"{location}_{factory}_{team_id_segment}"
    return team_id

# Function to execute batched queries
def execute_batch_queries(batch_queries):
    with driver.session() as session:
        with session.begin_transaction() as tx:
            for q in batch_queries:
                tx.run(q['query'], q['parameters'])

# Step 1: Read the CSV file
df = pd.read_csv("datafiles/small_data_set.csv")

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

df = pd.read_csv("datafiles/small_data_set.csv")
df = df.fillna('')

df['unique_machine_id'] = df['Location'] + '-' + df['Factory'].astype(str) + '-' + df['Machine Type']  # Create a unique machine ID
df['Team Id'] = df.apply(lambda row: create_team_id(row['Team Members'], row['Factory'], row['Location']), axis=1)
df['Team Id'].to_csv('datafiles/team_ids.csv', index=False)
node_queries = []
for index, row in df.iterrows():
    node_queries.append({
        'query': """
            MERGE (l:Location {name: $location})
            MERGE (f:Factory {name: $factory, location: $location})
            MERGE (m:Machine {machine_id: $unique_machine_id, machine_type: $machine_type, machine_age: $machine_age, utilization: $utilization, downtime: $downtime})
            MERGE (b:Batch {batch_id: $batch, date: date($date), quality: $quality, defect_rate: $defect_rate, production_volume: $production_volume, cycle_time: $cycle_time, temperature: $temperature, pressure: $pressure, chemical_ratio: $chemical_ratio, mixing_speed: $mixing_speed, safety_incidents: $saftey_incidents})
            MERGE (s:Shift {shift_id: $shift_id})
            MERGE (p:Product {product_category: $product_category, market_demand: $market_demand_index})
            MERGE (su:Supplier {supplier_name: $supplier_name, delays: $supplier_delays, material_quality: $raw_material_quality})
            MERGE (mt:Metrics {metrics_id: $metrics_id, energy_consumption: $energy_consumption, co2_emissions: $co2_emissions, waste_generated: $waste_generated, cost_of_downtime: $cost_of_downtime, revenue: $revenue, profit_margin: $profit_margin});

        """,
        'parameters': {
            'metrics_id': row['unique_machine_id'] + '-' + row['Batch'],
            'profit_margin': row['Profit Margin (%)'],
            'revenue': row['Revenue ($)'],
            'cost_of_downtime': row['Cost of Downtime ($)'],
            'waste_generated': row['Waste Generated (kg)'],
            'co2_emissions': row['CO2 Emissions (kg)'],
            'energy_consumption': row['Energy Consumption (kWh)'],
            'market_demand_index': row['Market Demand Index'],
            'supplier_delays': row['Supplier Delays (days)'],
            'raw_material_quality': row['Raw Material Quality'],
            'shift_id' : row['Shift'],
            'factory': row['Factory'],
            'location': row['Location'],
            'unique_machine_id': row['unique_machine_id'],
            'machine_type': row['Machine Type'],
            'machine_age': row['Machine Age (years)'],
            'utilization': row['Machine Utilization (%)'],
            'downtime': row['Cost of Downtime ($)'],
            'batch': row['Batch'],
            'date' :row['Date'],
            'quality': row['Batch Quality (Pass %)'],
            'defect_rate': row['Defect Rate (%)'],
            'production_volume': row['Production Volume (units)'],
            'cycle_time' : row['Cycle Time (minutes)'],
            'temperature' : row['Temperature (C)'],
            'pressure' : row['Pressure (psi)'],
            'chemical_ratio': row['Chemical Ratio'],
            'mixing_speed' : row['Mixing Speed (RPM)'],
            'saftey_incidents' : row['Safety Incidents (count)'],
            'product_category': row['Product Category'],
            'supplier_name': row['Supplier']
        }
    })

""" 
operates_in_queries = []
for index, row in df.iterrows():
    operates_in_queries.append({
        'query': """
            MATCH (f:Factory {name: $factory, location: $location}), (l:Location {name: 'Location A'})
            CREATE (f)-[:OPERATES_IN]->(l);
        """,
        'parameters': {
            'factory': row['Factory'],
            'location': row['Location'],
        }
    })

# Create USES relationships
# Factory uses a machine
uses_queries = []
for index, row in df.iterrows():
    uses_queries.append({
        'query': """
            MATCH (f:Factory {factory_id: $factory, location: $location})
            MATCH (m:Machine {machine_id: $unique_machine_id})
            MERGE (f)-[r:USES]->(m)
        """,
        'parameters': {
            'factory': row['Factory'],
            'location': row['Location'],
            'unique_machine_id': row['unique_machine_id'],
        }
    })

# Create PRODUCES relationships
# Machine produces a batch
produces_queries = []
for index, row in df.iterrows():
    produces_queries.append({
        'query': """
            MATCH (m:Machine {machine_id: $unique_machine_id})
            MATCH (b:Batch {batch_id: $batch_id})
            CREATE (m)-[:PRODUCES]->(b);
        """,
        'parameters': {
            'unique_machine_id': row['unique_machine_id'],
            'batch_id': row['Batch']
        }
    })
    
# HAS_SHIFT queries
# Batch has a shift
has_shift_queries = []
for index, row in df.iterrows():
    has_shift_queries.append({
        'query': """
            MATCH (b:Batch {batch_id: $batch_id})
            MATCH (s:Shift {shift_id: $shift_id})
            CREATE (b)-[:HAS_SHIFT]->(s);
        """,
        'parameters': {
            'batch_id': row['Batch'],
            'shift_id': row['Shift']
        }
    })

#Shift has a team which operates
#HAS_TEAM queries

has_team_queries = []

for index, row in df.iterrows():
    has_team_queries.append({
        'query': """
            MATCH (t:Team {id: $id})
            MATCH (s:Shift {shift_id: $shift_id})
            MERGE (s)-[:HAS_TEAM]->(t)
        """,
        'parameters': {
            'id': row['Team Id'],
            'shift_id': row['Shift']
        }
    })

#Supplier supplies to a factory    
# SUPPLIES queries

supplies_queries = []
for index, row in df.iterrows():
    has_team_queries.append({
        'query': """
            MATCH (s:Supplier {name: $name})
            MATCH (f:Factory {name: $factory, location: $location})
            MERGE (s)-[:SUPPLIES]->(f)
        """,
        'parameters': {
            'name': row['Supplier'],
            'factory': row['Factory'],
            'location': row['Location']
        }
    })

# Batch belongs to a product
# BELONGS_TO relationship queries

belongs_to_queries = []

for index, row in df.iterrows():
    belongs_to_queries.append({
        'query': """
            MATCH (b:Batch {batch_id: $batch_id})
            MATCH (p:Product {product_category: $product_category})
            MERGE (b)-[:BELONGS_TO]->(p)
        """,
        'parameters': {
            'batch_id': row['Batch'],
            'product_category': row['Product Category']
        }
    })

# Batch has metrics
# HAS_METRICS relationship queries

has_metrics_queries = []

for index, row in df.iterrows():
    belongs_to_queries.append({
        'query': """
            MATCH (b:Batch {batch_id: $batch_id})
            MATCH (m:Metric {metrics_id: $metrics_id})
            MERGE (b)-[:BELONGS_TO]->(p)
        """,
        'parameters': {
            'batch_id': row['Batch'],
            'metrics_id': row['unique_machine_id'] + '-' + row['Batch'],
        }
    })

 """
execute_batch_queries(team_queries)
print('Team nodes created')
execute_batch_queries(member_queries)
print('Member nodes created')
execute_batch_queries(node_queries)
print('Node relationships created')
execute_batch_queries(operates_in_queries)
print('Operates in relationships created')
execute_batch_queries(uses_queries)
print('Uses relationships created')
execute_batch_queries(produces_queries)
print('Produces relationships created')
execute_batch_queries(has_shift_queries)
print('Has shift relationships created')
execute_batch_queries(has_team_queries)
print('Has team relationships created')
execute_batch_queries(supplies_queries)
print('Supplies relationships created')
execute_batch_queries(belongs_to_queries)
print('Belongs to relationships created')
execute_batch_queries(has_metrics_queries)
print('Has metrics relationships created')

df[['Team Id', 'unique_machine_id', 'Date']].to_csv('datafiles/relationships.csv', index=False)
# Close the driver connection
driver.close()
