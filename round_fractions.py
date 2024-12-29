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

# Round the values in the specified columns to two decimal places
df[columns_to_round] = df[columns_to_round].round(2)

df['Operator Experience (years)'] = df['Operator Experience (years)'].round()

# Replace 'Factory ' with an empty string in the 'Factory' column to retain only numeric values 
df['Factory'] = df['Factory'].str.replace('Factory ', '').astype(int)

# Save the modified DataFrame back to a CSV file
df.to_csv('datafiles/data_rounded.csv', index=False)

