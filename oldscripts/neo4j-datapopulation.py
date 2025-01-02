import pandas as pd
from neo4j import GraphDatabase
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

# Define the URI and credentials for your Neo4j database
#uri = "neo4j://localhost:7687"
#username = "neo4j"
#password = "neo4j123"



uri = "neo4j://172.104.129.10:7687"  # Default URI for Neo4j
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


# Read the CSV file into a DataFrame
csv_file_path = 'datafiles/data_rounded.csv'  # Update with your actual file path
#csv_file_path = '/home/dhani/form-factory/kg/scripts/data.csv'  # Update with your actual file path

df = pd.read_csv(csv_file_path)

# Replace NaN values with a default value (e.g., empty string)
df = df.fillna('')

# Check DataFrame info
print(df.info())
print(df.head())

df['unique_factory_id'] = df['Factory']
df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')  # Convert date to the correct format

city_queries = []
for index, row in df.iterrows():
    city_queries.append({
        'query': """
            MERGE (c:Location {location: $location})
        """,
        'parameters': {
            'location': row['Location'],
        }
    })

factory_queries = []
for index, row in df.iterrows():
    factory_queries.append({
        'query': """
            MERGE (f:Factory {factory_id: $factory})
        """,
        'parameters': {
            'factory': row['unique_factory_id'],
        }
    })

# Create LOCATED_IN relationships

located_in_queries = []
for index, row in df.iterrows():
    located_in_queries.append({
        'query': """
            MATCH (f:Factory {factory_id: $factory})
            MATCH (l:Location {location: $location})

            MERGE (f)-[:LOCATED_IN]->(l)
        """,
        'parameters': {
             'factory': row['unique_factory_id'],
             'location': row['Location']
        }
    })


# Create Machine nodes and establish PART_OF relationships
machine_queries = []
for index, row in df.iterrows():
    machine_queries.append({
        'query': """
            MATCH (f:Factory {factory_id: $factory})
            MERGE (m:Machine {machine_id: $machine_type})
            MERGE (m)-[:PART_OF]->(f)
        """,
        'parameters': {
            'factory': row['unique_factory_id'],
            'machine_type': row['Machine Type'],
        }
    })

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

# Create Product nodes
product_queries = []
for index, row in df.iterrows():
    product_queries.append({
        'query': """
            MERGE (p:Product {product_category: $product_category})
        """,
        'parameters': {
            'product_category': row['Product Category']
        }
    })

# Create Supplier nodes
supplier_queries = []
for index, row in df.iterrows():
    supplier_queries.append({
        'query': """
            MERGE (s:Supplier {supplier_name: $supplier_name})
        """,
        'parameters': {
            'supplier_name': row['Supplier']
        }
    })

# Create Defect nodes
defect_queries = []
for index, row in df.iterrows():
    defect_queries.append({
        'query': """
            MERGE (d:Defect {defect_root_cause: $defect_root_cause})
        """,
        'parameters': {
            'defect_root_cause': row['Defect Root Cause']
        }
    })

# Create Shift nodes
unique_shifts = df['Shift'].unique()
shift_queries = []
for shift in unique_shifts:
    shift_queries.append({
        'query': """
            MERGE (s:Shift {shift: $shift})
        """,
        'parameters': {
            'shift': shift
        }
    })



# Create OPERATED_ON relationships
operated_on_queries = []
for index, row in df.iterrows():
    operated_on_queries.append({
        'query': """
            MATCH (f:Factory {factory_id: $factory})
            MATCH (d:Date {date: date($date)})
            MATCH (s:Shift {shift: $shift})
            MERGE (f)-[r:OPERATED_ON {location: $location, date: $date, shift: $shift}]->(d)
            ON CREATE SET r.production_volume = $production_volume, r.revenue = $revenue, 
                          r.profit_margin = $profit_margin, r.market_demand_index = $market_demand_index
            ON MATCH SET r.production_volume = $production_volume, r.revenue = $revenue, 
                         r.profit_margin = $profit_margin, r.market_demand_index = $market_demand_index
        """,
        'parameters': {
            'factory': row['Factory'],
            'location': row['Location'],
            'date': row['Date'],
            'production_volume': row['Production Volume (units)'],
            'revenue': row['Revenue ($)'],
            'profit_margin': row['Profit Margin (%)'],
            'market_demand_index': row['Market Demand Index'],
            'shift': row['Shift']
        }
    })

# Create USED_ON relationships
used_on_queries = []
for index, row in df.iterrows():
    used_on_queries.append({
        'query': """
            MATCH (m:Machine {machine_id: $unique_machine_id})
            MATCH (d:Date {date: date($date)})
            MATCH (s:Shift {shift: $shift})
            MERGE (m)-[r:USED_ON {location: $location, factory: $factory, machine_utilization: $machine_utilization, machine_downtime: $machine_downtime, cycle_time: $cycle_time, 
                energy_consumption: $energy_consumption, co2_emissions: $co2_emissions, emission_limit_compliance: $emission_limit_compliance, 
                cost_of_downtime: $cost_of_downtime, breakdowns: $breakdowns, safety_incidents: $safety_incidents, defect_rate: $defect_rate}]->(d)
        """,
        'parameters': {
            'unique_machine_id': row['Machine Type'],
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
            'defect_rate': row['Defect Rate (%)']
        }
    })

# Create relationships as specified
product_date_relationships = []
product_supplier_relationships = []
machine_defect_date_relationships = []

for index, row in df.iterrows():
    product_date_relationships.append({
        'query': """
            MATCH (p:Product {product_category: $product_category})
            MATCH (d:Date {date: date($date)})
            MERGE (p)-[:PRODUCED_ON {batch_quality: $batch_quality, location: $location, factory: $factory, machine_id: $unique_machine_id}]->(d)
        """,
        'parameters': {
            'product_category': row['Product Category'],
            'date': row['Date'],
            'batch_quality': row['Batch Quality (Pass %)'],
            'factory': row['Factory'],
            'location': row['Location'],
            'unique_machine_id': row['Machine Type'],
        }
    })
    product_supplier_relationships.append({
        'query': """
            MATCH (p:Product {product_category: $product_category})
            MATCH (sup:Supplier {supplier_name: $supplier_name})
            MERGE (p)-[:SUPPLIED_BY {supplier_delays: $supplier_delays, raw_material_quality: $raw_material_quality, location: $location, factory: $factory, machine_id: $unique_machine_id}]->(sup)
        """,
        'parameters': {
            'product_category': row['Product Category'],
            'supplier_name': row['Supplier'],
            'supplier_delays': row['Supplier Delays (days)'],
            'raw_material_quality': row['Raw Material Quality'],
            'factory': row['Factory'],
            'location': row['Location'],
            'unique_machine_id': row['Machine Type'],
        }
    })
    machine_defect_date_relationships.append({
        'query': """
            MATCH (m:Machine {machine_id: $machine_id})
            MATCH (def:Defect {defect_root_cause: $defect_root_cause})
            MATCH (d:Date {date: date($date)})
            MERGE (m)-[:EXPERIENCED_DEFECT {location: $location, factory: $factory, machine_id: $machine_id, date: date($date)}]->(def)-[:ON]->(d)
        """,
        'parameters': {
            'machine_id': row['Machine Type'],
            'factory': row['Factory'],
            'location': row['Location'],            
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
            'unique_team_id': row['Location'] + '_' +   str(row['Factory']) +  '_' + row['Machine Type'],
            'factory': row['Factory'],
            'location': row['Location'],
            'machine_type': row['Machine Type'],
            'date': row['Date'] # Assuming 'Production Volume (units)' is the column name
        }
    })
 
execute_batch_queries(city_queries)
execute_batch_queries(factory_queries)

execute_batch_queries(located_in_queries)

execute_batch_queries(machine_queries)
execute_batch_queries(date_queries)
execute_batch_queries(product_queries)
execute_batch_queries(supplier_queries)
execute_batch_queries(defect_queries)
execute_batch_queries(shift_queries)
execute_batch_queries(operated_on_queries) 
execute_batch_queries(used_on_queries)


execute_batch_queries(product_date_relationships)
execute_batch_queries(product_supplier_relationships)
execute_batch_queries(machine_defect_date_relationships)
execute_batch_queries(team_queries)

# Close the driver connection
driver.close()
