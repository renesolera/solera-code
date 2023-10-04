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

# Variables for dish Data
dish_Server = 'DESKTOP-EQPBGR1'
dish_Database = 'soleradb'
dish_username = 'soleras_first_pc'
dish_password = 'ABC1234D'
dish_Driver = 'ODBC Driver 17 for SQL Server'
dish_table_name = 'dish_status'
dish_pk_column_name = 'Time'
dish_tmp_dir_path = "C:/Users/Soleras_First_PC/Documents/PowerBI Project/tmp_dish"
dish_data_dir_path  = "C:/Users/Soleras_First_PC/Documents/PowerBI Project/dish_source"

# Grab files
dish_data_files = [f for f in os.listdir(dish_data_dir_path) if '.txt' in f.lower()]
dish_new_file = dish_data_files[-1]  # use 0 for first, use -1 for last

# Clean dir and move file
shutil.rmtree(dish_tmp_dir_path)
os.mkdir(dish_tmp_dir_path)
dish_dest = dish_tmp_dir_path + '/' + dish_new_file
shutil.copy(dish_data_dir_path + '/' + dish_new_file, dish_dest)
dish_df = pd.read_csv(dish_tmp_dir_path + '/' + dish_new_file,
                   sep='\t',  
                   engine='python',
                   encoding='utf-8',
                   encoding_errors='ignore',
                   header=None,
                   skiprows=0)

# Data manipulation
columns_to_check = [1, 2, 3, 4, 5]
dish_df = dish_df[0].str.split(r'[,;:]+', expand=True)
dish_df = dish_df.dropna(axis=1, how='any')
dish_df = dish_df[dish_df[columns_to_check].apply(lambda row: pd.to_numeric(row, errors='coerce').notna().all(), axis=1)]
dish_df.columns =  [dish_pk_column_name, 'current_elevation_angle', 'current_azimuth_angle','remove', 'sun_elevation_angle', 'sun_azimuth_angle']
dish_df[dish_pk_column_name] = dish_df[dish_pk_column_name].str.strip()
dish_df[dish_pk_column_name] = dish_df[dish_pk_column_name].apply(lambda s: datetime.strptime(s, '%Y-%m-%d-%H-%M-%S'))
dish_df= dish_df[[dish_pk_column_name, 'current_elevation_angle', 'current_azimuth_angle','sun_elevation_angle', 'sun_azimuth_angle']]

dish_df.drop_duplicates(subset=[dish_pk_column_name],keep='first',inplace=True)
dish_df.to_csv(dish_tmp_dir_path + '/' + dish_new_file, index=False)


### SQL logic for Stirling Data

# Database connection
dish_Database_con = f'mssql://@{dish_Server}/{dish_Database}?driver={dish_Driver}'
dish_engine = create_engine(dish_Database_con)
dish_con = dish_engine.connect()

# Read existing data from the database
dish_df = pd.read_sql_query(f"SELECT * FROM [{dish_Database}].[dbo].[{dish_table_name}]", dish_con)

# Read new data from the CSV file
dish_dp = pd.read_csv(dish_tmp_dir_path + '/' + dish_new_file)
dish_dp.columns = [re.sub(r'[-\s/]+', '_', col.strip()).strip('_').replace('(', '').replace(')', '') for col in dish_dp.columns]
dish_dp.columns = [re.sub(r'[^a-zA-Z0-9_]', '', col) for col in dish_dp.columns]

# Check if table exists
dish_inspector = inspect(dish_engine)
dish_table_exists = dish_inspector.has_table(dish_table_name)

if dish_table_exists:
  # Check for duplicates
  dish_existing_times_query = f"SELECT {dish_pk_column_name} FROM {dish_table_name}"
  dish_existing_times = pd.read_sql(dish_existing_times_query, dish_engine)

  # Convert the primary key column values to match the database format
  dish_dp[dish_pk_column_name] = pd.to_datetime(dish_dp[dish_pk_column_name]).dt.strftime('%Y-%m-%d %H:%M:%S')

  # Filter out duplicates
  dish_dp_filtered = dish_dp[~dish_dp[dish_pk_column_name].astype(str).isin(dish_existing_times[dish_pk_column_name].astype(str))]
else:
  dish_dp_filtered = dish_dp

# Ensure none of the column names end with an underscore
dish_dp_filtered.columns = [col.rstrip('_') if col.endswith('_') else col for col in dish_dp_filtered.columns]

# Write the DataFrame to the SQL table
dish_dp_filtered.to_sql(dish_table_name, dish_engine, if_exists='append', index=False)

