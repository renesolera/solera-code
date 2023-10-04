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

# Variables for Weather Data
weather_Server = 'DESKTOP-EQPBGR1'
weather_Database = 'soleradb'
weather_username = 'soleras_first_pc'
weather_password = 'ABC1234D'
weather_Driver = 'ODBC Driver 17 for SQL Server'
weather_table_name = 'weather'
weather_pk_column_name = 'Time'
weather_tmp_dir_path = "C:/Users/Soleras_First_PC/Documents/PowerBI Project/tmp_weather"
weather_data_dir_path = "C:/Users/Soleras_First_PC/Downloads"

# Variables for Pyro Data
pyro_Server = 'DESKTOP-EQPBGR1'
pyro_Database = 'soleradb'
pyro_username = 'soleras_first_pc'
pyro_password = 'ABC1234D'
pyro_Driver = 'ODBC Driver 17 for SQL Server'
pyro_table_name = 'pyro'
pyro_pk_column_name = 'Time'
pyro_tmp_dir_path = "C:/Users/Soleras_First_PC/Documents/PowerBI Project/tmp_pyro"
pyro_data_dir_path  = "C:/Users/Soleras_First_PC/Documents/PowerBI Project/pyro_source"
    
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

### Data cleaning for Weather Data

# Grab files
weather_data_files = [f for f in os.listdir(weather_data_dir_path) if '.csv' in f.lower()]
weather_new_file = weather_data_files[-1]  # use 0 for first, use -1 for last

# Search for files matching the pattern 'YYYY-MM-DD_YYYY-MM-DD' in the directory
weather_data_files = glob.glob(os.path.join(weather_data_dir_path, '*_*'))

# Sort the files based on their modified time (newest first)
weather_data_files.sort(key=os.path.getmtime, reverse=True)

if weather_data_files:
  weather_new_file = os.path.basename(weather_data_files[0])
  # Clean dir and move file
  shutil.rmtree(weather_tmp_dir_path)
  os.mkdir(weather_tmp_dir_path)
  weather_dest = weather_tmp_dir_path + '/' + weather_new_file
  shutil.copy(weather_data_dir_path + '/' + weather_new_file, weather_dest)
  weather_df = pd.read_csv(weather_tmp_dir_path + '/' + weather_new_file, skiprows=[1])

  # Data manipulation

  # Parse the date string
  weather_df[weather_pk_column_name] = pd.to_datetime(weather_df[weather_pk_column_name], format='mixed')
  weather_df.to_csv(weather_tmp_dir_path + '/' + weather_new_file, index=False)

  # Database connection
  weather_Database_con = f'mssql://@{weather_Server}/{weather_Database}?driver={weather_Driver}'
  weather_engine = create_engine(weather_Database_con)
  weather_con = weather_engine.connect()

  # Read existing data from the database
  weather_df = pd.read_sql_query(f"SELECT * FROM [{weather_Database}].[dbo].[{weather_table_name}]", weather_con)

  # Read new data from the CSV file
  weather_dp = pd.read_csv(weather_tmp_dir_path + '/' + weather_new_file)

  # Data manipulation
  # Rename the columns in the DataFrame
  weather_dp.rename(columns={
    'Time': 'Time',
    'Barometric pressure (Absolute)': 'Barometric_pressure_Absolute',
    'Barometric Pressure (Relative)': 'Barometric_Pressure_Relative',
    'Indoor temperature': 'Indoor_temperature',
    'Indoor humidity': 'Indoor_humidity',
    'Outdoor temperature': 'Outdoor_temperature',
    'Outdoor humidity': 'Outdoor_humidity',
    'Dew Point': 'Dew_Point',
    'Heat Index': 'Heat_Index',
    'Wind Chill': 'Wind_Chill',
    'Feels Like': 'Feels_Like',
    'Wind Direction': 'Wind_Direction',
    'Wind speed': 'Wind_speed',
    '10 min AVG': '_10_min_AVG',
    'Wind gust': 'Wind_gust',
    'Rain rate': 'Rain_rate',
    'Hourly rainfall': 'Hourly_rainfall',
    'Daily rainfall': 'Daily_rainfall',
    'UV index': 'UV_index',
    'Light intensity': 'Light_intensity',
    'CH1 temperature': 'CH1_temperature',
    'CH1 humidity': 'CH1_humidity',
    'CH1 Dew Point': 'CH1_Dew_Point',
    'CH1 Heat Index': 'CH1_Heat_Index',
    'CH2 temperature': 'CH2_temperature',
    'CH2 humidity': 'CH2_humidity',
    'CH2 Dew Point': 'CH2_Dew_Point',
    'CH2 Heat Index': 'CH2_Heat_Index',
    'CH3 temperature': 'CH3_temperature',
    'CH3 humidity': 'CH3_humidity',
    'CH3 Dew Point': 'CH3_Dew_Point',
    'CH3 Heat Index': 'CH3_Heat_Index',
    'CH4 temperature': 'CH4_temperature',
    'CH4 humidity': 'CH4_humidity',
    'CH4 Dew Point': 'CH4_Dew_Point',
    'CH4 Heat Index': 'CH4_Heat_Index',
    'CH5 temperature': 'CH5_temperature',
    'CH5 humidity': 'CH5_humidity',
    'CH5 Dew Point': 'CH5_Dew_Point',
    'CH5 Heat Index': 'CH5_Heat_Index',
    'CH6 temperature': 'CH6_temperature',
    'CH6 humidity': 'CH6_humidity',
    'CH6 Dew Point': 'CH6_Dew_Point',
    'CH6 Heat Index': 'CH6_Heat_Index',
    'CH7 temperature': 'CH7_temperature',
    'CH7 humidity': 'CH7_humidity',
    'CH7 Dew Point': 'CH7_Dew_Point',
    'CH7 Heat Index': 'CH7_Heat_Index',
    'Last strike': 'Last_strike',
    'Lightning distance': 'Lightning_distance',
    'Lightning hourly count': 'Lightning_hourly_count',
    'Lightning total in 5 minutes': 'Lightning_total_in_5_minutes',
    'Lightning total in 30 minutes': 'Lightning_total_in_30_minutes',
    'Lightning total in 1 hour': 'Lightning_total_in_1_hour',
    'Lightning total in 1 day': 'Lightning_total_in_1_day',
    'Water Leakage CH1': 'Water_Leakage_CH1',
    'Water Leakage CH2': 'Water_Leakage_CH2',
    'Water Leakage CH3': 'Water_Leakage_CH3',
    'Water Leakage CH4': 'Water_Leakage_CH4',
    'Water Leakage CH5': 'Water_Leakage_CH5',
    'Water Leakage CH6': 'Water_Leakage_CH6',
    'Water Leakage CH7': 'Water_Leakage_CH7',
    'CO CH1': 'CO_CH1',
    'CO Sensor battery CH1': 'CO_Sensor_battery_CH1',
    'PM2.5 CH1': 'PM2_5_CH1',
    'PM10 CH1': 'PM10_CH1',
    'PM sensor CH1 battery': 'PM_sensor_CH1_battery',
    'PM sensor CH1 connect': 'PM_sensor_CH1_connect',
    'PM 2.5 CH1 AQI': 'PM_2_5_CH1_AQI',
    'PM 10 CH1 AQI': 'PM_10_CH1_AQI',
    'PM2.5 CH2': 'PM2_5_CH2',
    'PM10 CH2': 'PM10_CH2',
    'PM sensor CH2 battery': 'PM_sensor_CH2_battery',
    'PM sensor CH2 connect': 'PM_sensor_CH2_connect',
    'PM 2.5 CH2 AQI': 'PM_2_5_CH2_AQI',
    'PM 10 CH2 AQI': 'PM_10_CH2_AQI',
    'PM2.5 CH3': 'PM2_5_CH3',
    'PM10 CH3': 'PM10_CH3',
    'PM sensor CH3 battery': 'PM_sensor_CH3_battery',
    'PM sensor CH3 connect': 'PM_sensor_CH3_connect',
    'PM 2.5 CH3 AQI': 'PM_2_5_CH3_AQI',
    'PM 10 CH3 AQI': 'PM_10_CH3_AQI',
    'PM2.5 CH4': 'PM2_5_CH4',
    'PM10 CH4': 'PM10_CH4',
    'PM sensor CH4 battery': 'PM_sensor_CH4_battery',
    'PM sensor CH4 connect': 'PM_sensor_CH4_connect',
    'PM 2.5 CH4 AQI': 'PM_2_5_CH4_AQI',
    'PM 10 CH4 AQI': 'PM_10_CH4_AQI',
    'HCHO': 'HCHO',
    'HCHO+VOC Sensor battery': 'HCHO_VOC_Sensor_battery',
    'CO₂': 'CO',
    'CO₂ Sensor Battery': 'CO_Sensor_Battery'
  }, inplace = True)

  # Replace "---" with null values
  weather_dp.replace('---', pd.NA, inplace=True)

  # Check if table exists
  weather_inspector = inspect(weather_engine)
  weather_table_exists = weather_inspector.has_table(weather_table_name)

  if weather_table_exists:
    # Check for duplicates
    weather_existing_times_query = f"SELECT {weather_pk_column_name} FROM {weather_table_name}"
    weather_existing_times = pd.read_sql(weather_existing_times_query, weather_engine)

    # Filter out duplicates
    weather_dp_filtered = weather_dp[~weather_dp[weather_pk_column_name].astype(str).isin(weather_existing_times[weather_pk_column_name].astype(str))]
  else:
    weather_dp_filtered = weather_dp

  # Ensure none of the column names end with an underscore
  weather_dp_filtered.columns = [col.rstrip('_') if col.endswith('_') else col for col in weather_dp_filtered.columns]

  # Write the DataFrame to the SQL table
  weather_dp_filtered.to_sql(weather_table_name, weather_engine, if_exists='append', index=False)
else:
    print("No weather data files found.")

### Data cleaning for Pyro Data

# Grab files
pyro_data_files = [f for f in os.listdir(pyro_data_dir_path) if '.txt' in f.lower()]
pyro_new_file = pyro_data_files[-1]  # use 0 for first, use -1 for last

# Clean dir and move file
shutil.rmtree(pyro_tmp_dir_path)
os.mkdir(pyro_tmp_dir_path)
pyro_dest = pyro_tmp_dir_path + '/' + pyro_new_file
shutil.copy(pyro_data_dir_path + '/' + pyro_new_file, pyro_dest)
pyro_df = pd.read_csv(pyro_tmp_dir_path + '/' + pyro_new_file, sep=',', encoding='utf-8', encoding_errors='ignore')

# Data manipulation

pyro_df['DateTime'] = pyro_df.apply(lambda s: s['Date'] + ' ' +s['Time'],axis = 1)
pyro_df.rename(columns={'DateTime':'Time'})
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

if pyro_table_exists:
  # Check for duplicates
  pyro_existing_times_query = f"SELECT {pyro_pk_column_name} FROM {pyro_table_name}"
  pyro_existing_times = pd.read_sql(pyro_existing_times_query, pyro_engine)

  # Convert the primary key column values to match the database format
  pyro_dp[pyro_pk_column_name] = pd.to_datetime(pyro_dp[pyro_pk_column_name]).dt.strftime('%Y-%m-%d %H:%M:%S')

  # Filter out duplicates
  pyro_dp_filtered = pyro_dp[~pyro_dp[pyro_pk_column_name].astype(str).isin(pyro_existing_times[pyro_pk_column_name].astype(str))]
else:
  pyro_dp_filtered = pyro_dp

# Ensure none of the column names end with an underscore
pyro_dp_filtered.columns = [col.rstrip('_') if col.endswith('_') else col for col in pyro_dp_filtered.columns]

# Write the DataFrame to the SQL table
pyro_dp_filtered.to_sql(pyro_table_name, pyro_engine, if_exists='append', index=False)



#DAQ1---------------------------------------------------------

# Variables for daq1 Data
daq1_Server = 'DESKTOP-EQPBGR1'
daq1_Database = 'soleradb'
daq1_username = 'soleras_first_pc'
daq1_password = 'ABC1234D'
daq1_Driver = 'ODBC Driver 17 for SQL Server'
daq1_table_name = 'daq1'
daq1_pk_column_name = 'Time'
daq1_tmp_dir_path = "C:/Users/Soleras_First_PC/Documents/PowerBI Project/tmp_daq"
daq1_data_dir_path = "C:/Users/Soleras_First_PC/Documents/PowerBI Project/daq_data"

### Data cleaning for daq1 Data

# Grab files
daq1_data_files = [f for f in os.listdir(daq1_data_dir_path)]
daq1_data_files = daq1_data_dir_path + '/' + daq1_data_files[0]

daq1_new_file = glob.glob(os.path.join(daq1_data_files, "DAQ1*"))
tmp_file_name = glob.glob(os.path.join(daq1_data_files, "DAQ1*"))[0].split("\\")[-1]
daq1_new_file = daq1_new_file[0].replace("\\", "/")
# daq1_data_files = [f for f in os.listdir(daq1_data_files) if '.csv' in f.lower()]
# daq1_new_file = daq1_data_files[-1]  # use 0 for first, use -1 for last


# Clean dir and move file
shutil.rmtree(daq1_tmp_dir_path)
os.mkdir(daq1_tmp_dir_path)
daq1_dest = daq1_tmp_dir_path + '/' + tmp_file_name
shutil.copy(daq1_new_file, daq1_dest)
daq1_df = pd.read_csv(daq1_tmp_dir_path + '/' + tmp_file_name,
                    sep=',',  
                   engine='python',
                   encoding='utf-8',
                   encoding_errors='ignore',
                   header=0,
                   skiprows=6,
                usecols=range(1,10))

# Data manipulation
daq1_df.rename(columns={'Date/Time':daq1_pk_column_name},inplace=True)
daq1_df[daq1_pk_column_name] = pd.to_datetime(daq1_df[daq1_pk_column_name],format='mixed')
daq1_df.drop_duplicates(subset=[daq1_pk_column_name],keep='first',inplace=True)
daq1_df.to_csv(daq1_tmp_dir_path + '/' + tmp_file_name, index=False)

### SQL logic for daq1 Data

# Database connection
daq1_Database_con = f'mssql://@{daq1_Server}/{daq1_Database}?driver={daq1_Driver}'
daq1_engine = create_engine(daq1_Database_con)
daq1_con = daq1_engine.connect()

# Read existing data from the database
daq1_df = pd.read_sql_query(f"SELECT * FROM [{daq1_Database}].[dbo].[{daq1_table_name}]", daq1_con)

# Read new data from the CSV file
daq1_dp = pd.read_csv(daq1_tmp_dir_path + '/' + tmp_file_name)
daq1_dp.columns = [re.sub(r'[-\s/]+', '_', col.strip()).strip('_').replace('(', '').replace(')', '') for col in daq1_dp.columns]
daq1_dp.columns = [re.sub(r'[^a-zA-Z0-9_]', '', col) for col in daq1_dp.columns]

# Check if table exists
daq1_inspector = inspect(daq1_engine)
daq1_table_exists = daq1_inspector.has_table(daq1_table_name)

if daq1_table_exists:
  # Check for duplicates
  daq1_existing_times_query = f"SELECT {daq1_pk_column_name} FROM {daq1_table_name}"
  daq1_existing_times = pd.read_sql(daq1_existing_times_query, daq1_engine)

  # Convert the primary key column values to match the database format
  daq1_dp[daq1_pk_column_name] = pd.to_datetime(daq1_dp[daq1_pk_column_name]).dt.strftime('%Y-%m-%d %H:%M:%S')

  # Filter out duplicates
  daq1_dp_filtered = daq1_dp[~daq1_dp[daq1_pk_column_name].astype(str).isin(daq1_existing_times[daq1_pk_column_name].astype(str))]
else:
  daq1_dp_filtered = daq1_dp

# Ensure none of the column names end with an underscore
daq1_dp_filtered.columns = [col.rstrip('_') if col.endswith('_') else col for col in daq1_dp_filtered.columns]

# Write the DataFrame to the SQL table
daq1_dp_filtered.to_sql(daq1_table_name, daq1_engine, if_exists='append', index=False)




#----------------------------------------------------------------------

#DAQ2
# Variables for daq2 Data
daq2_Server = 'DESKTOP-EQPBGR1'
daq2_Database = 'soleradb'
daq2_username = 'soleras_first_pc'
daq2_password = 'ABC1234D'
daq2_Driver = 'ODBC Driver 17 for SQL Server'
daq2_table_name = 'daq2'
daq2_pk_column_name = 'Time'
daq2_tmp_dir_path = "C:/Users/Soleras_First_PC/Documents/PowerBI Project/tmp_daq"
daq2_data_dir_path = "C:/Users/Soleras_First_PC/Documents/PowerBI Project/daq_data"

### Data cleaning for daq2 Data

# Grab files
daq2_data_files = [f for f in os.listdir(daq2_data_dir_path)]
daq2_data_files = daq2_data_dir_path + '/' + daq2_data_files[0]

daq2_new_file = glob.glob(os.path.join(daq2_data_files, "DAQ 2*"))
tmp_file_name = glob.glob(os.path.join(daq2_data_files, "DAQ 2*"))[0].split("\\")[-1]
daq2_new_file = daq2_new_file[0].replace("\\", "/")
# daq2_data_files = [f for f in os.listdir(daq2_data_files) if '.csv' in f.lower()]
# daq2_new_file = daq2_data_files[-1]  # use 0 for first, use -1 for last


# Clean dir and move file
shutil.rmtree(daq2_tmp_dir_path)
os.mkdir(daq2_tmp_dir_path)
daq2_dest = daq2_tmp_dir_path + '/' + tmp_file_name
shutil.copy(daq2_new_file, daq2_dest)
daq2_df = pd.read_csv(daq2_tmp_dir_path + '/' + tmp_file_name,
                    sep=',',  
                   engine='python',
                   encoding='utf-8',
                   encoding_errors='ignore',
                   header=0,
                   skiprows=6,
                usecols=range(1,10))

# Data manipulation
daq2_df.rename(columns={'Date/Time':daq2_pk_column_name},inplace=True)
daq2_df[daq2_pk_column_name] = pd.to_datetime(daq2_df[daq2_pk_column_name],format='mixed')
daq2_df.drop_duplicates(subset=[daq2_pk_column_name],keep='first',inplace=True)
daq2_df.to_csv(daq2_tmp_dir_path + '/' + tmp_file_name, index=False)

### SQL logic for daq2 Data

# Database connection
daq2_Database_con = f'mssql://@{daq2_Server}/{daq2_Database}?driver={daq2_Driver}'
daq2_engine = create_engine(daq2_Database_con)
daq2_con = daq2_engine.connect()

# Read existing data from the database
daq2_df = pd.read_sql_query(f"SELECT * FROM [{daq2_Database}].[dbo].[{daq2_table_name}]", daq2_con)

# Read new data from the CSV file
daq2_dp = pd.read_csv(daq2_tmp_dir_path + '/' + tmp_file_name)
daq2_dp.columns = [re.sub(r'[-\s/]+', '_', col.strip()).strip('_').replace('(', '').replace(')', '') for col in daq2_dp.columns]
daq2_dp.columns = [re.sub(r'[^a-zA-Z0-9_]', '', col) for col in daq2_dp.columns]

# Check if table exists
daq2_inspector = inspect(daq2_engine)
daq2_table_exists = daq2_inspector.has_table(daq2_table_name)

if daq2_table_exists:
  # Check for duplicates
  daq2_existing_times_query = f"SELECT {daq2_pk_column_name} FROM {daq2_table_name}"
  daq2_existing_times = pd.read_sql(daq2_existing_times_query, daq2_engine)

  # Convert the primary key column values to match the database format
  daq2_dp[daq2_pk_column_name] = pd.to_datetime(daq2_dp[daq2_pk_column_name]).dt.strftime('%Y-%m-%d %H:%M:%S')

  # Filter out duplicates
  daq2_dp_filtered = daq2_dp[~daq2_dp[daq2_pk_column_name].astype(str).isin(daq2_existing_times[daq2_pk_column_name].astype(str))]
else:
  daq2_dp_filtered = daq2_dp

# Ensure none of the column names end with an underscore
daq2_dp_filtered.columns = [col.rstrip('_') if col.endswith('_') else col for col in daq2_dp_filtered.columns]

# Write the DataFrame to the SQL table
daq2_dp_filtered.to_sql(daq2_table_name, daq2_engine, if_exists='append', index=False)

#------------------------------------------------------------------

#DAQ3
# Variables for daq3 Data
daq3_Server = 'DESKTOP-EQPBGR1'
daq3_Database = 'soleradb'
daq3_username = 'soleras_first_pc'
daq3_password = 'ABC1234D'
daq3_Driver = 'ODBC Driver 17 for SQL Server'
daq3_table_name = 'daq3'
daq3_pk_column_name = 'Time'
daq3_tmp_dir_path = "C:/Users/Soleras_First_PC/Documents/PowerBI Project/tmp_daq"
daq3_data_dir_path = "C:/Users/Soleras_First_PC/Documents/PowerBI Project/daq_data"

### Data cleaning for daq3 Data

# Grab files
daq3_data_files = [f for f in os.listdir(daq3_data_dir_path)]
daq3_data_files = daq3_data_dir_path + '/' + daq3_data_files[0]

daq3_new_file = glob.glob(os.path.join(daq3_data_files, "DAQ 3*"))
tmp_file_name = glob.glob(os.path.join(daq3_data_files, "DAQ 3*"))[0].split("\\")[-1]
daq3_new_file = daq3_new_file[0].replace("\\", "/")
# daq3_data_files = [f for f in os.listdir(daq3_data_files) if '.csv' in f.lower()]
# daq3_new_file = daq3_data_files[-1]  # use 0 for first, use -1 for last


# Clean dir and move file
shutil.rmtree(daq3_tmp_dir_path)
os.mkdir(daq3_tmp_dir_path)
daq3_dest = daq3_tmp_dir_path + '/' + tmp_file_name
shutil.copy(daq3_new_file, daq3_dest)
daq3_df = pd.read_csv(daq3_tmp_dir_path + '/' + tmp_file_name,
                    sep=',',  
                   engine='python',
                   encoding='utf-8',
                   encoding_errors='ignore',
                   header=0,
                   skiprows=6,
                usecols=range(1,10))

# Data manipulation
daq3_df.rename(columns={'Date/Time':daq3_pk_column_name},inplace=True)
daq3_df[daq3_pk_column_name] = pd.to_datetime(daq3_df[daq3_pk_column_name],format='mixed')
daq3_df.drop_duplicates(subset=[daq3_pk_column_name],keep='first',inplace=True)
daq3_df.to_csv(daq3_tmp_dir_path + '/' + tmp_file_name, index=False)

### SQL logic for daq3 Data

# Database connection
daq3_Database_con = f'mssql://@{daq3_Server}/{daq3_Database}?driver={daq3_Driver}'
daq3_engine = create_engine(daq3_Database_con)
daq3_con = daq3_engine.connect()

# Read existing data from the database
daq3_df = pd.read_sql_query(f"SELECT * FROM [{daq3_Database}].[dbo].[{daq3_table_name}]", daq3_con)

# Read new data from the CSV file
daq3_dp = pd.read_csv(daq3_tmp_dir_path + '/' + tmp_file_name)
daq3_dp.columns = [re.sub(r'[-\s/]+', '_', col.strip()).strip('_').replace('(', '').replace(')', '') for col in daq3_dp.columns]
daq3_dp.columns = [re.sub(r'[^a-zA-Z0-9_]', '', col) for col in daq3_dp.columns]

# Check if table exists
daq3_inspector = inspect(daq3_engine)
daq3_table_exists = daq3_inspector.has_table(daq3_table_name)

if daq3_table_exists:
  # Check for duplicates
  daq3_existing_times_query = f"SELECT {daq3_pk_column_name} FROM {daq3_table_name}"
  daq3_existing_times = pd.read_sql(daq3_existing_times_query, daq3_engine)

  # Convert the primary key column values to match the database format
  daq3_dp[daq3_pk_column_name] = pd.to_datetime(daq3_dp[daq3_pk_column_name]).dt.strftime('%Y-%m-%d %H:%M:%S')

  # Filter out duplicates
  daq3_dp_filtered = daq3_dp[~daq3_dp[daq3_pk_column_name].astype(str).isin(daq3_existing_times[daq3_pk_column_name].astype(str))]
else:
  daq3_dp_filtered = daq3_dp

# Ensure none of the column names end with an underscore
daq3_dp_filtered.columns = [col.rstrip('_') if col.endswith('_') else col for col in daq3_dp_filtered.columns]

# Write the DataFrame to the SQL table
daq3_dp_filtered.to_sql(daq3_table_name, daq3_engine, if_exists='append', index=False)


#-------------------------------------------------------------------------

#Dish Status ----------------------------------------------------------------

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

#-----------------------------------------------------------------------------------