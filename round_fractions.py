import pandas as pd
import numpy as np

# Read the CSV file into a DataFrame
df = pd.read_csv('datafiles/data_original.csv')

# List of columns with large fractional values to be rounded
columns_to_round = [
    'Machine Utilization (%)', 'Machine Downtime (hours)', 'Batch Quality (Pass %)',
    'Cycle Time (minutes)', 'Energy Consumption (kWh)', 'CO2 Emissions (kg)',
    'Waste Generated (kg)', 'Water Usage (liters)', 'Absenteeism Rate (%)',
    'Market Demand Index', 'Cost of Downtime ($)', 'Revenue ($)', 'Profit Margin (%)',
    'Defect Rate (%)'
]

experience_mapping = { 'Beginner': 3, 'Intermediate': 5, 'Advanced': 8 }

# Round the values in the specified columns to two decimal places
df[columns_to_round] = df[columns_to_round].round(2)

df['Operator Experience (years)'] = df['Operator Experience (years)'].round()
df['Operator Experience (years)'] = df['Operator Training Level'].map(experience_mapping)
# Replace 'Factory ' with an empty string in the 'Factory' column to retain only numeric values 
df['Factory'] = df['Factory'].str.replace('Factory ', '').astype(int)


for index, row in df.iterrows():
    if row['Location'] == 'City A' and row['Machine Type'] == 'Type A':
        df.at[index, 'Machine Age (years)'] = 7
    elif row['Location'] == 'City A' and row['Machine Type'] == 'Type B':
        df.at[index, 'Machine Age (years)'] = 5  
    elif row['Location'] == 'City A' and row['Machine Type'] == 'Type C': 
        df.at[index, 'Machine Age (years)'] = 3

    elif row['Location'] == 'City B' and row['Machine Type'] == 'Type A':
        df.at[index, 'Machine Age (years)'] = 8
    elif row['Location'] == 'City B' and row['Machine Type'] == 'Type B':
        df.at[index, 'Machine Age (years)'] = 6  
    elif row['Location'] == 'City B' and row['Machine Type'] == 'Type C': 
        df.at[index, 'Machine Age (years)'] = 4

    elif row['Location'] == 'City C' and row['Machine Type'] == 'Type A':
        df.at[index, 'Machine Age (years)'] = 9
    elif row['Location'] == 'City C' and row['Machine Type'] == 'Type B':
        df.at[index, 'Machine Age (years)'] = 7  
    elif row['Location'] == 'City C' and row['Machine Type'] == 'Type C': 
        df.at[index, 'Machine Age (years)'] = 4

    elif row['Location'] == 'City D' and row['Machine Type'] == 'Type A':
        df.at[index, 'Machine Age (years)'] = 7
    elif row['Location'] == 'City D' and row['Machine Type'] == 'Type B':
        df.at[index, 'Machine Age (years)'] = 6  
    elif row['Location'] == 'City D' and row['Machine Type'] == 'Type C': 
        df.at[index, 'Machine Age (years)'] = 5

    elif row['Location'] == 'City E' and row['Machine Type'] == 'Type A':
        df.at[index, 'Machine Age (years)'] = 8
    elif row['Location'] == 'City E' and row['Machine Type'] == 'Type B':
        df.at[index, 'Machine Age (years)'] = 3 
    elif row['Location'] == 'City E' and row['Machine Type'] == 'Type C': 
        df.at[index, 'Machine Age (years)'] = 4

# Save the modified DataFrame back to a CSV file
df.to_csv('datafiles/data_rounded.csv', index=False)

