import pandas as pd
import ast
from neo4j import GraphDatabase
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO)

# Define the URI and credentials for your Neo4j database
uri = "neo4j://172.104.129.10:7787"
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
df['Team Id'] = df.apply(lambda row: create_team_id(row['Team Members'], row['Factory'], row['Location']), axis=1)
df['Team Id'].to_csv('datafiles/team_ids.csv', index=False)
node_queries = []
for index, row in df.iterrows():
    node_queries.append({
        'query': """
            MERGE (f:Factory {factory_id: $factory, location: $location})
            MERGE (m:Machine {machine_id: $unique_machine_id, machine_type: $machine_type, machine_age: $machine_age})
            MERGE (:Product {product_category: $product_category})
            MERGE (:Supplier {supplier_name: $supplier_name})
            MERGE (:RawMaterial {raw_material_quality: $raw_material_quality})

        """,
        'parameters': {
            'factory': row['Factory'],
            'location': row['Location'],
            'unique_machine_id': row['unique_machine_id'],
            'machine_type': row['Machine Type'],
            'machine_age': row['Machine Age (years)'],
            'product_category': row['Product Category'],
            'supplier_name': row['Supplier'],
            'raw_material_quality': row['Raw Material Quality']

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
            MERGE (f)-[r:OPERATED_ON {shift: $shifts}]->(d)
        """,
        'parameters': {
            'factory': row['Factory'],
            'location': row['Location'],
            'date': row['Date'],
            'shifts': row['Shift']
        }
    })

# Create USED_ON relationships

used_on_queries = []
for index, row in df.iterrows():
    used_on_queries.append({
        'query': """
            MATCH (m:Machine {machine_id: $unique_machine_id})
            MATCH (d:Date {date: date($date)})
            MERGE (m)-[r:USED_ON {
                shift: $shifts, machine_utilization: $machine_utilization, cycle_time: $cycle_time, energy_consumption: $energy_consumption, 
                co2_emissions: $co2_emissions,emission_limit_compliance: $emission_limit_compliance, cost_of_downtime: $cost_of_downtime,
                breakdowns: $breakdowns, safety_incidents: $safety_incidents, defect_rate: $defect_rate, energy_efficiency_rating: $energy_efficiency_rating, 
                waste_generated: $waste_generated, water_usage: $water_usage, temperature: $temperature, pressure: $pressure, chemical_ratio: $chemical_ratio,
                mixing_speed: $mixing_speed, production_volume: $production_volume, revenue: $revenue, profit_margin: $profit_margin, market_demand_index: $market_demand_index
                }]->(d)
        """,
        'parameters': {
            'unique_machine_id': row['unique_machine_id'],
            'date': row['Date'],
            'shifts': row['Shift'],
            'machine_utilization': row['Machine Utilization (%)'],
            'cycle_time': row['Cycle Time (minutes)'],
            'energy_consumption': row['Energy Consumption (kWh)'],
            'co2_emissions': row['CO2 Emissions (kg)'],
            'emission_limit_compliance': row['Emission Limit Compliance'],
            'cost_of_downtime': row['Cost of Downtime ($)'],
            'breakdowns': row['Breakdowns (count)'],
            'safety_incidents': row['Safety Incidents (count)'],
            'defect_rate': row['Defect Rate (%)'],
            'energy_efficiency_rating': row['Energy Efficiency Rating'],
            'waste_generated': row['Waste Generated (kg)'],
            'water_usage': row['Water Usage (liters)'],
            'temperature': row['Temperature (C)'],
            'pressure': row['Pressure (psi)'],
            'chemical_ratio': row['Chemical Ratio'],
            'mixing_speed': row['Mixing Speed (RPM)'],
            'production_volume': row['Production Volume (units)'],
            'revenue': row['Revenue ($)'],
            'profit_margin': row['Profit Margin (%)'],
            'market_demand_index': row['Market Demand Index']
        }
    })
    
# USED_BY_TEAM queries
used_by_team_queries = []
for index, row in df.iterrows():
    used_by_team_queries.append({
        'query': """
            MATCH (m:Machine {machine_id: $unique_machine_id})
            MATCH (t:Team {id: $id})
            MERGE (m)-[r:USED_BY_TEAM {
                shift: $shift, 
                date: date($date), 
                average_operator_training_level: $average_operator_training_level, 
                average_absentialism: $average_absentialism, 
                average_operator_experience: $average_operator_experience}]->(t)
        """,
        'parameters': {
            'unique_machine_id': row['unique_machine_id'],
            'id': row['Team Id'],
            'shift': row['Shift'],
            'date': row['Date'],
            'average_operator_training_level': row['Operator Training Level'],
            'average_absentialism': row['Absenteeism Rate (%)'],
            'average_operator_experience': row['Operator Experience (years)']

        }
    })


product_date_relationships = []
product_raw_material_date_relationships = []
raw_material_supplier_relationships = []

for index, row in df.iterrows():
    product_date_relationships.append({
        'query': """
            MATCH (p:Product {product_category: $product_category})
            MATCH (d:Date {date: date($date)})
            MERGE (p)-[:PRODUCED_ON {batch: $batch, batch_quality: $batch_quality}]->(d)
        """,
        'parameters': {
            'product_category': row['Product Category'],
            'date': row['Date'],
            'batch_quality': row['Batch Quality (Pass %)'],
            'batch': row['Batch']
        }
    })

for index, row in df.iterrows():
    raw_material_supplier_relationships.append({
        'query': """
            MATCH (r:RawMaterial {raw_material_quality: $raw_material_quality})
            MATCH (sup:Supplier {supplier_name: $supplier_name})
            MERGE (r)-[:SUPPLIED_BY {date: date($date), shift: $shift, supplier_delays: $supplier_delays}]->(sup)
        """,
        'parameters': {
            'raw_material_quality': row['Raw Material Quality'],
            'supplier_name': row['Supplier'],
            'supplier_delays': row['Supplier Delays (days)'],
            'date': row['Date'],
            'shift': row['Shift']
        }
    })

for index, row in df.iterrows():
    product_raw_material_date_relationships.append({
        'query': """
            MATCH (p:Product {product_category: $product_category})
            MATCH (r:RawMaterial {raw_material_quality: $raw_material_quality})
            MERGE (p)-[:PRODUCED_USING{date: date($date), shift: $shift, batch: $batch, batch_quality: $batch_quality} ]->(r)
        """,
        'parameters': {
            'raw_material_quality': row['Raw Material Quality'],
            'product_category': row['Product Category'],
            'date': row['Date'],
            'shift': row['Shift'],
            'batch_quality': row['Batch Quality (Pass %)'],
            'batch': row['Batch']
        }
    })
execute_batch_queries(team_queries)
execute_batch_queries(date_queries)    
execute_batch_queries(member_queries)
execute_batch_queries(node_queries)
execute_batch_queries(machine_queries)
execute_batch_queries(operated_on_queries)
execute_batch_queries(used_on_queries)
execute_batch_queries(used_by_team_queries)
execute_batch_queries(product_date_relationships)
execute_batch_queries  (product_raw_material_date_relationships)
execute_batch_queries(raw_material_supplier_relationships)

df[['Team Id', 'unique_machine_id', 'Date']].to_csv('datafiles/relationships.csv', index=False)
# Close the driver connection
driver.close()
