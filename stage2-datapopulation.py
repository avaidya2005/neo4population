import pandas as pd
from neo4j import GraphDatabase
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

# Define the URI and credentials for your Neo4j database
uri = "neo4j://localhost:7687"
username = "neo4j"
password = "neo4j123"



#uri = "neo4j://172.104.129.10:7687"  # Default URI for Neo4j
#username = "neo4j"
#password = "neo4j123"

# Create a Neo4j driver instance
driver = GraphDatabase.driver(uri, auth=(username, password))



# Function to execute batched queries
def execute_batch_queries(batch_queries):
    with driver.session() as session:
        with session.begin_transaction() as tx:
            for q in batch_queries:
                tx.run(q['query'], q['parameters'])


# Read the CSV file into a DataFrame
csv_file_path = 'datafiles/data_rounded.csv'  # Update with your actual file path
#csv_file_path = '/home/dhani/form-factory/kg/scripts/data.csv'  # Update with your actual file path

df = pd.read_csv(csv_file_path)

# Replace NaN values with a default value (e.g., empty string)
df = df.fillna('')


df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')  # Convert date to the correct format
df['unique_machine_id'] = 'Machine-'+ df['Location'] + '-' + df['Factory'].astype(str) + '-' + df['Machine Type']  # Create a unique machine ID
df['operator_id'] = 'Operator-' + df['Location'] + '-' + df['Factory'].astype(str) + '-' + df['Operator Experience (years)'].astype(str)  # Create a unique operator ID
print(df.info())

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


factory_queries = []
for index, row in df.iterrows():
    factory_queries.append({
        'query': """
            MERGE (f:Factory {factory_id: $factory, location: $location})
            MERGE (m:Machine {machine_id: $unique_machine_id, machine_type: $machine_type, machine_age: $machine_age})
            MERGE (:Operator {operator_id: $operator_id, operator_experience: $operator_experience, operator_training_level: $operator_training_level})
            MERGE (:Product {product_category: $product_category})
            MERGE (:Supplier {supplier_name: $supplier_name})
            MERGE (:Defect {defect_root_cause: $defect_root_cause})
            MERGE (:RawMaterial {raw_material_quality: $raw_material_quality})


        """,
        'parameters': {
            'factory': row['Factory'],
            'location': row['Location'],
            'unique_machine_id': row['unique_machine_id'],
            'machine_type': row['Machine Type'],
            'machine_age': row['Machine Age (years)'],
            'operator_id':  row['operator_id'],
            'operator_experience': row['Operator Experience (years)'],
            'operator_training_level': row['Operator Training Level'],
            'product_category': row['Product Category'],
            'supplier_name': row['Supplier'],
            'defect_root_cause': row['Defect Root Cause'],
            'raw_material_quality': row['Raw Material Quality']
        }
    })

# Create Machine nodes and establish PART_OF relationships
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

# Create USED_ON relationships
used_on_queries = []
for index, row in df.iterrows():
    used_on_queries.append({
        'query': """
            MATCH (m:Machine {machine_id: $unique_machine_id})
            MATCH (d:Date {date: date($date)})
            MERGE (m)-[r:USED_ON {machine_utilization: $machine_utilization, machine_downtime: $machine_downtime, cycle_time: $cycle_time, 
                energy_consumption: $energy_consumption, co2_emissions: $co2_emissions, emission_limit_compliance: $emission_limit_compliance, 
                cost_of_downtime: $cost_of_downtime, breakdowns: $breakdowns, safety_incidents: $safety_incidents, defect_rate: $defect_rate, team_size: $team_size, absentialism: $absentialism }]->(d)
        """,
        'parameters': {
            'unique_machine_id': row['unique_machine_id'],
            'date': row['Date'], 
            'shift': row['Shift'],
            'factory': row['Factory'],
            'location': row['Location'],
            'machine_utilization': row['Machine Utilization (%)'],
            'machine_downtime': row['Machine Downtime (hours)'],
            'cycle_time': row['Cycle Time (minutes)'],
            'energy_consumption': row['Energy Consumption (kWh)'],
            'co2_emissions': row['CO2 Emissions (kg)'],
            'emission_limit_compliance': row['Emission Limit Compliance'],
            'cost_of_downtime': row['Cost of Downtime ($)'],
            'breakdowns': row['Breakdowns (count)'],
            'safety_incidents': row['Safety Incidents (count)'],
            'defect_rate': row['Defect Rate (%)'],
            'team_size': row['Team Size'],
            'absentialism': row['Absenteeism Rate (%)']
        }
    })

operated_queries = []

for index, row in df.iterrows():
    operated_queries.append({
        'query': """
            MATCH (o:Operator {operator_id: $operator_id})
            MATCH (m:Machine {machine_id: $unique_machine_id})
            MATCH (d:Date {date: date($date)})
            CREATE (o)-[:OPERATED]->(m)-[:ON]->(d)
        """,
        'parameters': {
            'unique_machine_id': row['unique_machine_id'],
            'date': row['Date'], 
            'operator_id': row['operator_id']
        }
    })

# Create relationships as specified
product_date_relationships = []
product_raw_material_date_relationships = []
raw_material_supplier_relationships = []
machine_defect_date_relationships = []

for index, row in df.iterrows():
    product_date_relationships.append({
        'query': """
            MATCH (p:Product {product_category: $product_category})
            MATCH (d:Date {date: date($date)})
            MERGE (p)-[:PRODUCED_ON {batch_quality: $batch_quality}]->(d)
        """,
        'parameters': {
            'product_category': row['Product Category'],
            'date': row['Date'],
            'batch_quality': row['Batch Quality (Pass %)']
        }
    })

for index, row in df.iterrows():
    raw_material_supplier_relationships.append({
        'query': """
            MATCH (r:RawMaterial {raw_material_quality: $raw_material_quality})
            MATCH (sup:Supplier {supplier_name: $supplier_name})
            MATCH (d:Date {date: date($date)})
            MERGE (r)-[:SUPPLIED_BY {supplier_delays: $supplier_delays}]->(sup)-[:ON]->(d)
        """,
        'parameters': {
            'raw_material_quality': row['Raw Material Quality'],
            'supplier_name': row['Supplier'],
            'supplier_delays': row['Supplier Delays (days)'],
            'date': row['Date']
        }
    })

for index, row in df.iterrows():
    product_raw_material_date_relationships.append({
        'query': """
            MATCH (p:Product {product_category: $product_category})
            MATCH (r:RawMaterial {raw_material_quality: $raw_material_quality})
            MATCH (d:Date {date: date($date)})
            MERGE (p)-[:PRODUCED_USING ]->(r)-[:ON]->(d)
        """,
        'parameters': {
            'raw_material_quality': row['Raw Material Quality'],
            'product_category': row['Product Category'],
            'date': row['Date']
        }
    })

    machine_defect_date_relationships.append({
        'query': """
            MATCH (m:Machine {machine_id: $machine_id})
            MATCH (def:Defect {defect_root_cause: $defect_root_cause})
            MATCH (d:Date {date: date($date)})
            MERGE (m)-[:EXPERIENCED_DEFECT]->(def)-[:ON]->(d)
        """,
        'parameters': {
            'machine_id': row['unique_machine_id'],
            'defect_root_cause': row['Defect Root Cause'],
            'date': row['Date']
        }
    })
# Create Team nodes and relationships
team_queries = []

for index, row in df.iterrows():
    team_queries.append({
        'query': """
            MERGE (t:Team {team_id: $unique_team_id, factory: $factory, location: $location, machine_type: $machine_type})
            MERGE (m:Machine {machine_id: $machine_type})
            MERGE (t)-[:WORKS_ON {date: date($date)}]->(m)
        """,
        'parameters': {
            'unique_team_id': row['Location'] + '-' +   str(row['Factory']) +  '-' + row['Machine Type'],
            'factory': row['Factory'],
            'location': row['Location'],
            'machine_type': row['Machine Type'],
            'date': row['Date'] # Assuming 'Production Volume (units)' is the column name
        }
    })


execute_batch_queries(date_queries)
execute_batch_queries(factory_queries)
execute_batch_queries(machine_queries)
execute_batch_queries(operated_on_queries) 
execute_batch_queries(used_on_queries)
execute_batch_queries(operated_queries) 
execute_batch_queries(product_date_relationships)
execute_batch_queries(raw_material_supplier_relationships)
execute_batch_queries(product_raw_material_date_relationships)
execute_batch_queries(machine_defect_date_relationships)

# Close the driver connection
driver.close()
