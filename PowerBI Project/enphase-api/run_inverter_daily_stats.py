import datetime
import pandas as pd
import json
from utils.enlightenAPI_v4 import enlightenAPI_v4
import shutil
import os
from sqlalchemy import create_engine, inspect
import psycopg2
import pyodbc
import re
import glob

# Variables for enphase Data
enphase_Server = 'DESKTOP-EQPBGR1'
enphase_Database = 'soleradb'
enphase_username = 'soleras_first_pc'
enphase_password = 'ABC1234D'
enphase_Driver = 'ODBC Driver 17 for SQL Server'
enphase_table_name = 'enphase'
enphase_pk_column_name = 'Time'

# Load the user config
with open('enlighten_v4_config.json') as config_file:
    config = json.load(config_file)

print(f'Beginning EnlightenAPI pull for System ID: {config["system_id"]}')
api = enlightenAPI_v4(config)

# Get the inverter data from the enlighten API
production_meter_readings = api.production_meter_readings()

# Extract the relevant information
meter_reading = production_meter_readings['meter_readings'][0]
value = meter_reading['value']
read_at = datetime.datetime.fromtimestamp(meter_reading['read_at'])

# Create DataFrame
data = {'power_produced': [value], 'Time': [read_at]}
df = pd.DataFrame(data)

### SQL logic for enphase Data

# Database connection
enphase_Database_con = f'mssql://@{enphase_Server}/{enphase_Database}?driver={enphase_Driver}'
enphase_engine = create_engine(enphase_Database_con)
enphase_con = enphase_engine.connect()

# Read existing data from the database
enphase_df = pd.read_sql_query(f"SELECT * FROM [{enphase_Database}].[dbo].[{enphase_table_name}]", enphase_con)

# Now 'latest_row' is a pandas Series object representing the latest row in the table
latest_row = enphase_df.sort_values('Time', ascending=False).iloc[0]

# Get the last power reading from the database
# last_power_reading = enphase_df['power_produced'].iloc[-1]

# Calculate the difference
# current_power_reading = df['power_produced'].iloc[0]
power_difference = meter_reading['value'] - latest_row['power_produced']

print(f"Last Power Reading: {latest_row['power_produced']}")
print(f"Current Power Reading: {meter_reading['value']}")
print(f"Power Difference: {power_difference}")

# Update DataFrame
data = {'power_produced': [value], 'Time': [read_at], 'power_produced_latest': [power_difference]}
df = pd.DataFrame(data)

# Write the DataFrame to the SQL table
df.to_sql(enphase_table_name, enphase_engine, if_exists='append', index=False)
