import pandas as pd
from neo4j import GraphDatabase
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

# Define the URI and credentials for your Neo4j database
uri = "neo4j://localhost:7687"
username = "neo4j"
password = "neo4j123"

""" uri = "neo4j://172.104.129.10:7687"
username = "neo4j"
password = "neo4j123" """


# Create a Neo4j driver instance
driver = GraphDatabase.driver(uri, auth=(username, password))

# Define a function to run Cypher queries with error handling
def run_query(query, parameters=None):
    try:
        with driver.session() as session:
            result = session.run(query, parameters)
            return list(result)
    except Exception as e:
        logging.error(f"Error running query: {e}")
        return None

# Read the CSV file into a DataFrame
csv_file_path = 'C:/Development/workspace/kg-creations/datafiles/data_original.csv'  # Update with your actual file path
#csv_file_path = '/home/dhani/form-factory/kg/scripts/data.csv'  # Update with your actual file path

df = pd.read_csv(csv_file_path)

# Replace NaN values with a default value (e.g., empty string)
df = df.fillna('')

# Check DataFrame info
print(df.info())
print(df.head())

# Generate unique identifiers for factories and machines
df['unique_factory_id'] = df['Location'] + '_' + df['Factory']
df['unique_machine_id'] = df['unique_factory_id'] + '_' + df['Machine Type']
df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')  # Convert date to the correct format

# Create City nodes
unique_cities = df['Location'].unique()
city_queries = []
for city in unique_cities:
    city_queries.append({
        'query': """
            MERGE (c:City {name: $name})
        """,
        'parameters': {
            'name': city
        }
    })

# Create Factory nodes and establish LOCATED_IN relationships
factory_queries = []
unique_factories = df[['Location', 'unique_factory_id']].drop_duplicates()
for index, row in unique_factories.iterrows():
    factory_queries.append({
        'query': """
            MATCH (c:City {name: $location})
            MERGE (f:Factory {factory_id: $factory, location: $location})
            MERGE (f)-[:LOCATED_IN]->(c)
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
            MATCH (f:Factory {factory_id: $factory, location: $location})
            MERGE (m:Machine {machine_id: $unique_machine_id, type: $machine_type})
            MERGE (m)-[:PART_OF]->(f)
        """,
        'parameters': {
            'unique_machine_id': row['unique_machine_id'],
            'factory': row['unique_factory_id'],
            'location': row['Location'],
            'machine_type': row['Machine Type']
        }
    })

# Create Production Log nodes and establish LOGGED_BY relationships
production_log_queries = []
for index, row in df.iterrows():
    production_log_queries.append({
        'query': """
            MATCH (m:Machine {machine_id: $unique_machine_id})
            MERGE (p:ProductionLog {log_id: $unique_machine_id + '_' + $date, date: date($date), 
                utilization: $utilization, downtime: $downtime, maintenance_history: $maintenance_history, 
                age: $age, batch_quality: $batch_quality, cycle_time: $cycle_time, energy_consumption: $energy_consumption, 
                energy_efficiency: $energy_efficiency, co2_emissions: $co2_emissions, emission_compliance: $emission_compliance, 
                waste_generated: $waste_generated, water_usage: $water_usage, shift: $shift, operator_experience: $operator_experience, 
                team_size: $team_size, training_level: $training_level, absenteeism_rate: $absenteeism_rate, product_category: $product_category, 
                supplier: $supplier, supplier_delays: $supplier_delays, raw_material_quality: $raw_material_quality, market_demand: $market_demand, 
                downtime_cost: $downtime_cost, revenue: $revenue, profit_margin: $profit_margin, breakdowns: $breakdowns, safety_incidents: $safety_incidents, 
                defect_root_cause: $defect_root_cause, production_volume: $production_volume, defect_rate: $defect_rate})
            MERGE (p)-[:LOGGED_BY]->(m)
        """,
        'parameters': {
            'unique_machine_id': row['unique_machine_id'],
            'date': row['Date'],
            'utilization': row['Machine Utilization (%)'],
            'downtime': row['Machine Downtime (hours)'],
            'maintenance_history': row['Maintenance History'],
            'age': row['Machine Age (years)'],
            'batch_quality': row['Batch Quality (Pass %)'],
            'cycle_time': row['Cycle Time (minutes)'],
            'energy_consumption': row['Energy Consumption (kWh)'],
            'energy_efficiency': row['Energy Efficiency Rating'],
            'co2_emissions': row['CO2 Emissions (kg)'],
            'emission_compliance': row['Emission Limit Compliance'],
            'waste_generated': row['Waste Generated (kg)'],
            'water_usage': row['Water Usage (liters)'],
            'shift': row['Shift'],
            'operator_experience': row['Operator Experience (years)'],
            'team_size': row['Team Size'],
            'training_level': row['Operator Training Level'],
            'absenteeism_rate': row['Absenteeism Rate (%)'],
            'product_category': row['Product Category'],
            'supplier': row['Supplier'],
            'supplier_delays': row['Supplier Delays (days)'],
            'raw_material_quality': row['Raw Material Quality'],
            'market_demand': row['Market Demand Index'],
            'downtime_cost': row['Cost of Downtime ($)'],
            'revenue': row['Revenue ($)'],
            'profit_margin': row['Profit Margin (%)'],
            'breakdowns': row['Breakdowns (count)'],
            'safety_incidents': row['Safety Incidents (count)'],
            'defect_root_cause': row['Defect Root Cause'],
            'production_volume': row['Production Volume (units)'],
            'defect_rate': row['Defect Rate (%)']
        }
    })

# Function to execute batched queries
def execute_batch_queries(batch_queries):
    with driver.session() as session:
        with session.begin_transaction() as tx:
            for q in batch_queries:
                tx.run(q['query'], q['parameters'])

# Execute batched queries in transactions
execute_batch_queries(city_queries)
execute_batch_queries(factory_queries)
execute_batch_queries(machine_queries)
execute_batch_queries(production_log_queries)

print("City, Factory, Machine, and ProductionLog nodes created successfully with unique identifiers, attributes, and relationships!")

# Close the driver connection
driver.close()
