import datetime
import shutil
import os
import pandas as pd
from sqlalchemy import create_engine, inspect
import psycopg2
import pyodbc
import re
import glob
from datetime import datetime

# Variables for Pyro Data
pyro_Server = 'DESKTOP-EQPBGR1'
pyro_Database = 'soleradb'
pyro_username = 'soleras_first_pc'
pyro_password = 'ABC1234D'
pyro_Driver = 'ODBC Driver 17 for SQL Server'
pyro_table_name = 'pyro'
pyro_pk_column_name = 'Time'
pyro_tmp_dir_path = "C:/Users/Soleras_First_PC/Documents/PowerBI Project/tmp_pyro"
pyro_data_dir_path = "C:/Users/Soleras_First_PC/Documents/PowerBI Project/pyro_source"

### Data cleaning for Pyro Data

# Grab files
pyro_data_files = [f for f in os.listdir(pyro_data_dir_path) if '.txt' in f.lower()]
pyro_new_file = pyro_data_files[-1]  # use 0 for first, use -1 for last

# Clean dir and move file
shutil.rmtree(pyro_tmp_dir_path, ignore_errors=True)
os.mkdir(pyro_tmp_dir_path)
pyro_dest = os.path.join(pyro_tmp_dir_path, pyro_new_file)
shutil.copy(os.path.join(pyro_data_dir_path, pyro_new_file), pyro_dest)
pyro_df = pd.read_csv(pyro_dest, sep=',', encoding='utf-8', encoding_errors='ignore')



# Combine Date and Time into datetime column
pyro_df['Datetime'] = pd.to_datetime(pyro_df['Date'] + ' ' + pyro_df['Time'], format='mixed')


# Drop the existing 'time' column
pyro_df = pyro_df.drop(columns=['Time'])
pyro_df = pyro_df.rename(columns={'Datetime': 'Time'})

pyro_df = pyro_df[['Time', 'Data']]

pyro_df[pyro_pk_column_name] = pd.to_datetime(pyro_df[pyro_pk_column_name], dayfirst=True).apply(lambda s: s.isoformat())
pyro_df.drop_duplicates(subset=[pyro_pk_column_name],keep='first',inplace=True)
pyro_df.to_csv(pyro_tmp_dir_path + '/' + pyro_new_file, index=False)

### SQL logic for Stirling Data

# Database connection
pyro_Database_con = f'mssql://@{pyro_Server}/{pyro_Database}?driver={pyro_Driver}'
pyro_engine = create_engine(pyro_Database_con)
pyro_con = pyro_engine.connect()

# Read existing data from the database
pyro_df = pd.read_sql_query(f"SELECT * FROM [{pyro_Database}].[dbo].[{pyro_table_name}]", pyro_con)

# Read new data from the CSV file
pyro_dp = pd.read_csv(pyro_tmp_dir_path + '/' + pyro_new_file)
pyro_dp.columns = [re.sub(r'[-\s/]+', '_', col.strip()).strip('_').replace('(', '').replace(')', '') for col in pyro_dp.columns]
pyro_dp.columns = [re.sub(r'[^a-zA-Z0-9_]', '', col) for col in pyro_dp.columns]

# Check if table exists
pyro_inspector = inspect(pyro_engine)
pyro_table_exists = pyro_inspector.has_table(pyro_table_name)
 
# Check for duplicates
pyro_existing_times_query = f"SELECT {pyro_pk_column_name} FROM {pyro_table_name}"
pyro_existing_times = pd.read_sql(pyro_existing_times_query, pyro_engine)

pyro_dp[pyro_pk_column_name] = pd.to_datetime(pyro_dp[pyro_pk_column_name])
min_date = pyro_dp[pyro_pk_column_name].min().date()
max_date = pyro_dp[pyro_pk_column_name].max().date()


pyro_dp[pyro_pk_column_name] = pd.to_datetime(pyro_dp[pyro_pk_column_name]).dt.strftime('%Y-%m-%d %H:%M:%S')

# Convert the primary key column values to match the database format
print(pyro_dp[pyro_pk_column_name])
# Filter out duplicates
pyro_dp_filtered = pyro_dp[~pyro_dp[pyro_pk_column_name].astype(str).isin(pyro_existing_times[pyro_pk_column_name].astype(str))]

# Ensure none of the column names end with an underscore
pyro_dp_filtered.columns = [col.rstrip('_') if col.endswith('_') else col for col in pyro_dp_filtered.columns]

# Write the DataFrame to the SQL table
pyro_dp_filtered.to_sql(pyro_table_name, pyro_engine, if_exists='append', index=False)


shutil.rmtree(pyro_data_dir_path, ignore_errors=True)
os.mkdir(pyro_data_dir_path)