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

daq1_data_files = [f for f in os.listdir(daq1_data_dir_path)]
if len(daq1_data_files) == 0:
    print("No files found in the directory.")
    # Handle the case where there are no files in the directory
else:
    # Grab files
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
daq2_data_files = [f for f in os.listdir(daq2_data_dir_path)]
if len(daq2_data_files) == 0:
    print("No files found in the directory.")
    # Handle the case where there are no files in the directory
else:
    # Grab files
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

### Data cleaning for daq2 Data
daq3_data_files = [f for f in os.listdir(daq3_data_dir_path)]
if len(daq3_data_files) == 0:
    print("No files found in the directory.")
    # Handle the case where there are no files in the directory
else:
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

# Construct the complete path to the folder to delete
folder_path = os.path.join(daq1_data_dir_path, daq1_data_files)

# Remove the folder and its contents
shutil.rmtree(folder_path)