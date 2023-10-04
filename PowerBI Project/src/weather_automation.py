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
