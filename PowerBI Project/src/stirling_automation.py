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

# Variables for Stirling Data
stirling_Server = 'DESKTOP-EQPBGR1'
stirling_Database = 'soleradb'
stirling_username = 'soleras_first_pc'
stirling_password = 'ABC1234D'
stirling_Driver = 'ODBC Driver 17 for SQL Server'
stirling_table_name = 'stirling'
stirling_pk_column_name = 'Time'
stirling_tmp_dir_path = "C:/Users/Soleras_First_PC/Documents/PowerBI Project/tmp"
stirling_data_dir_path = "C:/STIRLING ENGINE DATA VIEWER v1.0.0.9/LOG"
    
### Data cleaning for Stirling Data

# Grab files
stirling_data_files = [f for f in os.listdir(stirling_data_dir_path) if '.tsv' in f.lower()]
stirling_new_file = stirling_data_files[-1]  # use 0 for first, use -1 for last

# Clean dir and move file
shutil.rmtree(stirling_tmp_dir_path)
os.mkdir(stirling_tmp_dir_path)
stirling_dest = stirling_tmp_dir_path + '/' + stirling_new_file
shutil.copy(stirling_data_dir_path + '/' + stirling_new_file, stirling_dest)
stirling_df = pd.read_csv(stirling_tmp_dir_path + '/' + stirling_new_file, sep='\t', encoding='utf-8', encoding_errors='ignore',skiprows=8)

# Data manipulation
stirling_df[stirling_pk_column_name] = pd.to_datetime(stirling_df[stirling_pk_column_name], dayfirst=True).apply(lambda s: s.isoformat())
stirling_df.drop_duplicates(subset=[stirling_pk_column_name],keep='first',inplace=True)
stirling_df.to_csv(stirling_tmp_dir_path + '/' + stirling_new_file, index=False)

### SQL logic for Stirling Data

# Database connection
stirling_Database_con = f'mssql://@{stirling_Server}/{stirling_Database}?driver={stirling_Driver}'
stirling_engine = create_engine(stirling_Database_con)
stirling_con = stirling_engine.connect()

# Read existing data from the database
stirling_df = pd.read_sql_query(f"SELECT * FROM [{stirling_Database}].[dbo].[{stirling_table_name}]", stirling_con)

# Read new data from the CSV file
stirling_dp = pd.read_csv(stirling_tmp_dir_path + '/' + stirling_new_file)
stirling_dp.columns = [re.sub(r'[-\s/]+', '_', col.strip()).strip('_').replace('(', '').replace(')', '') for col in stirling_dp.columns]
stirling_dp.columns = [re.sub(r'[^a-zA-Z0-9_]', '', col) for col in stirling_dp.columns]

# Check if table exists
stirling_inspector = inspect(stirling_engine)
stirling_table_exists = stirling_inspector.has_table(stirling_table_name)

if stirling_table_exists:
  # Check for duplicates
  stirling_existing_times_query = f"SELECT {stirling_pk_column_name} FROM {stirling_table_name}"
  stirling_existing_times = pd.read_sql(stirling_existing_times_query, stirling_engine)

  # Convert the primary key column values to match the database format
  stirling_dp[stirling_pk_column_name] = pd.to_datetime(stirling_dp[stirling_pk_column_name]).dt.strftime('%Y-%m-%d %H:%M:%S')

  # Filter out duplicates
  stirling_dp_filtered = stirling_dp[~stirling_dp[stirling_pk_column_name].astype(str).isin(stirling_existing_times[stirling_pk_column_name].astype(str))]
else:
  stirling_dp_filtered = stirling_dp

# Ensure none of the column names end with an underscore
stirling_dp_filtered.columns = [col.rstrip('_') if col.endswith('_') else col for col in stirling_dp_filtered.columns]

# Write the DataFrame to the SQL table
stirling_dp_filtered.to_sql(stirling_table_name, stirling_engine, if_exists='append', index=False)
