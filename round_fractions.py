import pandas as pd

# Read the CSV file into a DataFrame
df = pd.read_csv('datafiles/subset.csv')

# Replace 'Factory ' with an empty string in the 'Factory' column to retain only numeric values 
df['Factory'] = df['Factory'].str.replace('Factory ', '').astype(int)


df.to_csv('datafiles/subset_cleaned.csv', index=False)

