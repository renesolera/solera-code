# -*- coding: utf-8 -*-
"""
Created on Thu Mar 16 10:42:04 2023

@author: E. Robertson

Revision History:
Author     Date          Version     Description
EAR        03/19/2023    1.0.0       Initial release
EAR        03/20/2023    1.1.0       Added heartbeat, debug motor control, print measured and target data when 'targeting'
EAR        04/11/2023    1.2.0       Added means to set true AZ angle on device. 
EAR        04/22/2023    1.2.5       Added decimal support for angles, log to txt file, wake function. 
EAR        04/22/2023    1.3.0       Updated serial comms.  
EAR        06/28/2023    2.0.0       Added wifi comms  
EAR        08/02/2023    2.1.0       Updated polling frequency. 
 
"""
import sys
from pysolar.solar import *
import datetime
from tkinter import *
import time
import serial
import schedule
import os.path
import urllib.request
import http
from urllib.error import HTTPError
from urllib.error import URLError
from socket import timeout

global ser, connected, main_loop_running, txt_az_degree, txt_ze_degree, txt_long, txt_lat, longitude, latitude, timezone, base_url, COMMS_TYPE, COMMS_SERIAL, COMMS_WIFI, track_freq, target_job
COMMS_SERIAL = 0
COMMS_WIFI = 1
COMMS_TYPE = COMMS_WIFI
track_freq = 60 #60 seconds tracking frequency


connected = 0
main_loop_running = 1
#EROB#base_url = "http://192.168.1.184/"
base_url = "http://10.1.10.58/"#SOLERA#

longitude = -80.18
latitude = 25.77
timezone = -5

root = Tk()
root.title("Dual Axis Tracker")
root.geometry('500x400')

if COMMS_TYPE==COMMS_SERIAL:
    lbl_com = Label(root, text="COM Port: ")
    lbl_com.grid()

    txt_com = Entry(root, width=10)
    txt_com.grid(column=1, row=0)
    txt_com.insert(0, "COM11")
elif COMMS_TYPE==COMMS_WIFI:
    lbl_com = Label(root, text="Server: ")
    lbl_com.grid()
    
lbl_general = Label(root, text="")
lbl_general.grid(column=0, row=4)

dt_now = datetime.datetime.now()
log_folder = 'C:/Users/Soleras_First_PC/Desktop/python/Log_Files' #SOLERA#
#EROB#log_folder = 'C:/Users/earob/Documents/py_temp/Log_Files'
log_filename = os.path.join(log_folder,dt_now.strftime("%Y-%m-%d-%H-%M") + '_' + 'python_log.txt')
print('Data logging')
print(dt_now)

#added by Sushrut
log_folder_dashboard = 'C:/Users/Soleras_First_PC/Desktop/python/Log_Files/Dashboard Log' #SOLERA#
#EROB#log_folder_dashboard = 'C:/Users/earob/Documents/py_temp/Log_Files/Dashboard Log'
log_filename_db = os.path.join(log_folder_dashboard,dt_now.strftime("%Y-%m-%d") + '_' + 'dishstatus_log.txt')

#filename edited by Sushrut
with open(log_filename, 'a') as file:
    file.write(dt_now.strftime("%Y-%m-%d-%H-%M"))
    file.write('\nprogram start\n')
    file.close()
with open(log_filename_db, 'a') as file1:
    file.close()

def post_data(payload):
    global base_url
    post_url = base_url + payload
    try:
        url = post_url
        response = urllib.request.urlopen(url, timeout=10).read().decode('utf-8')
        return response
    except HTTPError as error:
        print('HTTP Error: Data not retrieved because %s\nURL: %s', error, url)
        return 0
    except URLError as error:
        if isinstance(error.reason, timeout):
            print('Timeout Error: Data not retrieved because %s\nURL: %s', error, url)
        else:
            print('URL Error: Data not retrieved because %s\nURL: %s', error, url)
        return 0
    except http.client.HTTPException as e:
        try: 
            temp= str(e)
        except:
            print("http client response not able to be a string")
            temp = e
        return temp
    else:
        print('Access successful.')
        
def read_data_board():
    global base_url
    read_board_url = base_url + "data"
    
    try:
        url = read_board_url
        response = urllib.request.urlopen(url, timeout=10).read().decode('utf-8')
        return response
    except HTTPError as error:
        print('HTTP Error: Data of not retrieved because ', error, '\nURL: ', url)
        return 0
    except URLError as error:
        if isinstance(error.reason, timeout):
            print('Timeout Error: Data not retrieved because %s\nURL: %s', error, url)
        else:
            print('URL Error: Data not retrieved because %s\nURL: %s', error, url)
        return 0
    except http.client.HTTPException as e:
        try: 
            temp= str(e)
        except:
            print("http client response not able to be a string")
            temp = e
        return temp
    else:
        print('Access successful.')
    
    
def server_heartbeat():
    global base_url
    
    try:
        url = base_url + "wf_hb"
        response = urllib.request.urlopen(url, timeout=10).read().decode('utf-8')
        return response
    except HTTPError as error:
        print('HTTP Error: Data not retrieved because %s\nURL: %s', error, url)
        return 0
    except URLError as error:
        if isinstance(error.reason, timeout):
            print('Timeout Error: Data not retrieved because %s\nURL: %s', error, url)
        else:
            print('URL Error: Data not retrieved because %s\nURL: %s', error, url)
        return 0
    except http.client.HTTPException as e:
        try: 
            temp= str(e)
        except:
            print("http client response not able to be a string")
            temp = e
        return temp
    else:
        print('Access successful.')
    
def read_Arduino_wifi():
    global file
    #todo: add HB failure to arduino code. 
    board_message = read_data_board()
    if type(board_message)!=str:
        print(board_message)
        return
    if board_message=="no_data":
        print("no_data...")
        return
    else:
        print(board_message)
        try:
            #filename edited by Sushrut
            dt_now = datetime.datetime.now()
            with open(log_filename, 'a') as file:
                file.write(dt_now.strftime("%Y-%m-%d-%H-%M-%S"))
                file.write("\n")
                file.write(board_message)
                file.write("\n")
                file.close()
        except Exception as e:
            print("logging issue:")
            print(e)
            file.close()     
        try:
            dt_now = datetime.datetime.now()
            temp = board_message
            data_points = board_message.count('gyro')
            if "gyro" in temp:
                temp2 = temp.split("gyro:")[1]
                if data_points == 1:
                    temp = temp2.split("\n")[0]
                elif data_points == 2:
                    temp = temp2 + "\n" + temp.split("gyro:")[2].split("\n")[0]
                elif data_points >= 3:
                    temp = temp2
                with open(log_filename_db, 'a') as file1:
                     file1.write(dt_now.strftime("%Y-%m-%d-%H-%M-%S"))
                     file1.write(" : ")
                     file1.write(temp)
                     file1.close()
        except Exception as e:
            print("file1 write fail:")
            print(e)  
    

def read_Arduino_serial():
    global ser, file

    if(ser.inWaiting() > 0):
        val = ser.read(ser.inWaiting())
        if("HB fail" in val.decode('utf-8')):
            stop_motors()
        try:
            print((val.decode('utf-8')))
        except:
            print("fail to decode message")
            
        try:
            #filename edited by Sushrut
            dt_now = datetime.datetime.now()
            with open(log_filename, 'a') as file:
                file.write(dt_now.strftime("%Y-%m-%d-%H-%M-%S"))
                file.write("\n")
                file.write((val.decode('utf-8')))
                file.write("\n")
                file.close()
        except Exception as e:
            print("logging issue:")
            print(e)
            file.close()     
        try:
            dt_now = datetime.datetime.now()
            temp = val.decode('utf-8')
            if "gyro" in temp:
                temp2 = temp.split("gyro:")[1]
                temp = temp2.split("\n")[0]
                with open(log_filename_db, 'a') as file1:
                     file1.write(dt_now.strftime("%Y-%m-%d-%H-%M-%S"))
                     file1.write(" : ")
                     file1.write(temp)
                     file1.close()
        except Exception as e:
            print("file1 write fail:")
            print(e)
            
def send_target_data():
    global ser, longitude, latitude, COMMS_TYPE, COMMS_SERIAL, COMMS_WIFI
    day_of_year = datetime.datetime.now().timetuple().tm_yday
    hour = datetime.datetime.now().hour
    minute = datetime.datetime.now().minute
    second = datetime.datetime.now().second
    tz = time.timezone if (time.localtime().tm_isdst == 0) else time.altzone
    tz_offset = round(tz/60/60*-1)
    string_ser = str(day_of_year)+","+str(hour)+"," + \
        str(minute)+","+str(second)+","+str(tz_offset)+",\n"

    # send azi and zen angles direct...
    date = datetime.datetime.now(datetime.timezone.utc)
    ze = get_altitude(latitude, longitude, date)
    az = (get_azimuth(latitude, longitude, date))
    dec_ze = ("%.2f" % round(ze, 2))
    dec_az = ("%.2f" % round(az, 2))
    #elevation, azimuth
    string_ser = (dec_ze)+","+(dec_az)
    print("Target updated.")
    dt_now = datetime.datetime.now()
    print(dt_now)
    
    if COMMS_TYPE==COMMS_SERIAL: 
        header = "abab"
        payload_class = 0 #target data
        payload = dec_ze+","+dec_az
        payload_len = len(dec_ze)+len(dec_az)+1
        send_data = bytearray(header, 'utf-8')
        send_data.append(payload_class)
        send_data.append(payload_len)
        byte_arr = bytearray(payload, 'utf-8')
        send_data = send_data + (byte_arr)
        ser.write(send_data)
    elif COMMS_TYPE==COMMS_WIFI: 
        payload_class = "0," #target data
        payload = dec_ze+","+dec_az
        send_data = payload_class+payload
        post_data(str(send_data))


def connect():
    global ser, COMMS_TYPE, COMMS_SERIAL, COMMS_WIFI
    lbl_com.configure(text="Checking...")
    schedule.clear()
    if COMMS_TYPE==COMMS_SERIAL: 
        try:
            ser = serial.Serial(txt_com.get(), 9600, timeout=1)
            # If device connects, go on:
            lbl_com.configure(text="Connected.")
            device_connected()
            schedule.every(30).seconds.do(heartbeat)
        except serial.SerialException as e:
            lbl_com.configure(text="COM Port: ")
            lbl_general.configure(text="Failed to connect!")
    elif COMMS_TYPE==COMMS_WIFI:
        try:
            one = server_heartbeat()
            if one=="wfm_hb":
                # If device connects, go on:
                lbl_com.configure(text="Connected.")
                lbl_general.configure(text="")
                device_connected()
                schedule.every(5).seconds.do(heartbeat)
            else:
                lbl_com.configure(text="Not Connected.")
        except:
            lbl_general.configure(text="Failed to connect!\nCheck server.")
                
            
            
    


btn_com = Button(root, text="Connect", fg="black", command=connect)
btn_com.grid(column=2, row=0)


def tracking():
    global ser, COMMS_TYPE, COMMS_SERIAL, COMMS_WIFI, track_freq, target_job
    lbl_general.configure(text="Tracking...")
    if COMMS_TYPE==COMMS_SERIAL:
        header = "abab"
        payload_class = 1 #target data
        payload = "t"
        payload_len = 1
        send_data = bytearray(header, 'utf-8')
        send_data.append(payload_class)
        send_data.append(payload_len)
        byte_arr = bytearray(payload, 'utf-8')
        send_data = send_data + (byte_arr)
        ser.write(send_data)
    elif COMMS_TYPE==COMMS_WIFI:
        payload = "1,t"
        post_data(payload)
        
    time.sleep(2) #edited by Sushrut
    send_target_data()
    try: 
        schedule.cancel_job(target_job)
    except:
        print("target_job not yet defined")
    target_job = schedule.every(60).seconds.do(send_target_data) #edited by Sushrut
    print("Measured\t\t\t\t\tTarget")
    print("Pitch,   Roll,    Yaw,    Pitch,   Roll")
    
    #filename changed by Sushrut
    with open(log_filename, 'a') as file:
        file.write(dt_now.strftime("%Y-%m-%d-%H-%M"))
        file.write("Measured\t\t\t\t\tTarget\n")
        file.write("Pitch,   Roll,    Yaw,    Pitch,   Roll\n")
        file.close()
    # with open(log_filename_db, 'a') as file1:
    #      file1.write("Start tracking\n")
    #      file1.close()  


def zeroing():
    global ser, COMMS_TYPE, COMMS_SERIAL, COMMS_WIFI, target_job
    lbl_general.configure(text="Zeroing...")
    if COMMS_TYPE==COMMS_SERIAL:
        header = "abab"
        payload_class = 1 #target data
        payload = "z"
        payload_len = 1
        send_data = bytearray(header, 'utf-8')
        send_data.append(payload_class)
        send_data.append(payload_len)
        byte_arr = bytearray(payload, 'utf-8')
        send_data = send_data + (byte_arr)
        ser.write(send_data)
    elif COMMS_TYPE==COMMS_WIFI:
        payload = "1,z"
        post_data(payload)

    try: 
        schedule.cancel_job(target_job)
    except:
        print("target_job not yet defined")


def storing():
    global ser, COMMS_TYPE, COMMS_SERIAL, COMMS_WIFI, target_job
    lbl_general.configure(text="Stowing...")
    if COMMS_TYPE==COMMS_SERIAL:
        header = "abab"
        payload_class = 1 #target data
        payload = "s"
        payload_len = 1
        send_data = bytearray(header, 'utf-8')
        send_data.append(payload_class)
        send_data.append(payload_len)
        byte_arr = bytearray(payload, 'utf-8')
        send_data = send_data + (byte_arr)
        ser.write(send_data)
    elif COMMS_TYPE==COMMS_WIFI:
        payload = "1,s"
        post_data(payload)

    try: 
        schedule.cancel_job(target_job)
    except:
        print("target_job not yet defined")
    

def wakeup_fx():
    global ser, COMMS_TYPE, COMMS_SERIAL, COMMS_WIFI, target_job
    lbl_general.configure(text="Waking...")
    if COMMS_TYPE==COMMS_SERIAL:
        header = "abab"
        payload_class = 1 #target data
        payload = "w"
        payload_len = 1
        send_data = bytearray(header, 'utf-8')
        send_data.append(payload_class)
        send_data.append(payload_len)
        byte_arr = bytearray(payload, 'utf-8')
        send_data = send_data + (byte_arr)
        ser.write(send_data)
    elif COMMS_TYPE==COMMS_WIFI:
        payload = "1,w"
        post_data(payload)

    try: 
        schedule.cancel_job(target_job)
    except:
        print("target_job not yet defined")


def stop_motors():
    global ser, COMMS_TYPE, COMMS_SERIAL, COMMS_WIFI, target_job
    lbl_general.configure(text="Motor stopped")
    if COMMS_TYPE==COMMS_SERIAL:
        header = "abab"
        payload_class = 1 #target data
        payload = "a"
        payload_len = 1
        send_data = bytearray(header, 'utf-8')
        send_data.append(payload_class)
        send_data.append(payload_len)
        byte_arr = bytearray(payload, 'utf-8')
        send_data = send_data + (byte_arr)
        ser.write(send_data)
    elif COMMS_TYPE==COMMS_WIFI:
        payload = "1,a"
        post_data(payload)

    try: 
        schedule.cancel_job(target_job)
    except:
        print("target_job not yet defined")
    

def az_pos():
    global ser, COMMS_TYPE, COMMS_SERIAL, COMMS_WIFI, target_job
    lbl_general.configure(text="AZ positive...")
    if COMMS_TYPE==COMMS_SERIAL:
        header = "abab"
        payload_class = 1 #target data
        payload = "b"
        payload_len = 1
        send_data = bytearray(header, 'utf-8')
        send_data.append(payload_class)
        send_data.append(payload_len)
        byte_arr = bytearray(payload, 'utf-8')
        send_data = send_data + (byte_arr)
        ser.write(send_data)
    elif COMMS_TYPE==COMMS_WIFI:
        payload = "1,b"
        post_data(payload)

    try: 
        schedule.cancel_job(target_job)
    except:
        print("target_job not yet defined")


def az_neg():
    global ser, COMMS_TYPE, COMMS_SERIAL, COMMS_WIFI, target_job
    lbl_general.configure(text="AZ negative...")
    if COMMS_TYPE==COMMS_SERIAL:
        header = "abab"
        payload_class = 1 #target data
        payload = "c"
        payload_len = 1
        send_data = bytearray(header, 'utf-8')
        send_data.append(payload_class)
        send_data.append(payload_len)
        byte_arr = bytearray(payload, 'utf-8')
        send_data = send_data + (byte_arr)
        ser.write(send_data)
    elif COMMS_TYPE==COMMS_WIFI:
        payload = "1,c"
        post_data(payload)

    try: 
        schedule.cancel_job(target_job)
    except:
        print("target_job not yet defined")


def ze_pos():
    global ser, COMMS_TYPE, COMMS_SERIAL, COMMS_WIFI, target_job
    lbl_general.configure(text="ZE positive...")
    if COMMS_TYPE==COMMS_SERIAL:
        header = "abab"
        payload_class = 1 #target data
        payload = "d"
        payload_len = 1
        send_data = bytearray(header, 'utf-8')
        send_data.append(payload_class)
        send_data.append(payload_len)
        byte_arr = bytearray(payload, 'utf-8')
        send_data = send_data + (byte_arr)
        ser.write(send_data)
    elif COMMS_TYPE==COMMS_WIFI:
        payload = "1,d"
        post_data(payload)

    try: 
        schedule.cancel_job(target_job)
    except:
        print("target_job not yet defined")


def ze_neg():
    global ser, COMMS_TYPE, COMMS_SERIAL, COMMS_WIFI, target_job
    lbl_general.configure(text="ZE negative...")
    if COMMS_TYPE==COMMS_SERIAL:
        header = "abab"
        payload_class = 1 #target data
        payload = "e"
        payload_len = 1
        send_data = bytearray(header, 'utf-8')
        send_data.append(payload_class)
        send_data.append(payload_len)
        byte_arr = bytearray(payload, 'utf-8')
        send_data = send_data + (byte_arr)
        ser.write(send_data)
    elif COMMS_TYPE==COMMS_WIFI:
        payload = "1,e"
        post_data(payload)

    try: 
        schedule.cancel_job(target_job)
    except:
        print("target_job not yet defined")


def heartbeat():
    global ser, COMMS_TYPE, COMMS_SERIAL, COMMS_WIFI
    if COMMS_TYPE==COMMS_SERIAL:
        header = "abab"
        payload_class = 4 #target data
        payload = "q"
        payload_len = 1
        send_data = bytearray(header, 'utf-8')
        send_data.append(payload_class)
        send_data.append(payload_len)
        byte_arr = bytearray(payload, 'utf-8')
        send_data = send_data + (byte_arr)
        ser.write(send_data)
    elif COMMS_TYPE==COMMS_WIFI:
        payload = "4,q" #target data
        post_data(payload)

def device_connected():
    global connected, txt_az_degree, txt_ze_degree, txt_lat, txt_long, latitude, longitude, COMMS_TYPE, COMMS_SERIAL, COMMS_WIFI
    connected = 1
    btn_track = Button(root, text="Run tracking program.",
                       fg='black', command=tracking)
    btn_track.grid(column=0, row=1)
    btn_zero = Button(root, text="Run zeroing program.",
                      fg='black', command=zeroing)
    btn_zero.grid(column=0, row=2)
    btn_store = Button(root, text="Run stow program.",
                       fg='black', command=storing)
    btn_store.grid(column=0, row=3)

    btn_stop = Button(root, text="Stop motors.",
                      fg='black', command=stop_motors)
    btn_stop.grid(column=0, row=5)
    btn_az_pos = Button(root, text="Test AZ positive.",
                        fg='black', command=az_pos)
    btn_az_pos.grid(column=0, row=6)
    btn_az_neg = Button(root, text="Test AZ negative.",
                        fg='black', command=az_neg)
    btn_az_neg.grid(column=1, row=6)
    btn_ze_pos = Button(root, text="Test ZE positive.",
                        fg='black', command=ze_pos)
    btn_ze_pos.grid(column=0, row=7)
    btn_ze_neg = Button(root, text="Test ZE negative.",
                        fg='black', command=ze_neg)
    btn_ze_neg.grid(column=1, row=7)

    btn_update_az_degress = Button(
        root, text="Update azimuth angle.", fg='black', command=update_az_degrees)
    btn_update_az_degress.grid(column=0, row=9)
    txt_az_degree = Entry(root, width=10)
    txt_az_degree.insert(0, "0")
    txt_az_degree.grid(column=1, row=9)

    btn_update_ze_degress = Button(
        root, text="Update zenith angle.", fg='black', command=update_ze_degrees)
    btn_update_ze_degress.grid(column=0, row=10)
    txt_ze_degree = Entry(root, width=10)
    txt_ze_degree.insert(0, "0")
    txt_ze_degree.grid(column=1, row=10)

    btn_update_lat = Button(root, text="Update latitude.",
                            fg='black', command=update_latitude)
    btn_update_lat.grid(column=0, row=11)
    txt_lat = Entry(root, width=10)
    txt_lat.insert(0, str(latitude))
    txt_lat.grid(column=1, row=11)

    btn_update_long = Button(
        root, text="Update longitude.", fg='black', command=update_longitude)
    btn_update_long.grid(column=0, row=12)
    txt_long = Entry(root, width=10)
    txt_long.insert(0, str(longitude))
    txt_long.grid(column=1, row=12)

    btn_wakeup = Button(root, text="Wakeup.", fg='black', command=wakeup_fx)
    btn_wakeup.grid(column=0, row=13)

    if COMMS_TYPE==COMMS_SERIAL:
        schedule.every(1).seconds.do(read_Arduino_serial)
    elif COMMS_TYPE==COMMS_WIFI:
        schedule.every(1).seconds.do(read_Arduino_wifi)


def update_az_degrees():
    global ser, txt_az_degree, COMMS_TYPE, COMMS_SERIAL, COMMS_WIFI
    degrees = txt_az_degree.get()
    degrees_msg = str(degrees)
    try:
        temp = float(degrees)
        if(temp > 360 or temp < 0):
            print("Enter 0-360.")
        else:
            if COMMS_TYPE==COMMS_SERIAL:
                header = "abab"
                payload_class = 2 #target data
                payload = degrees_msg
                payload_len = len(degrees_msg)
                send_data = bytearray(header, 'utf-8')
                send_data.append(payload_class)
                send_data.append(payload_len)
                byte_arr = bytearray(payload, 'utf-8')
                send_data = send_data + (byte_arr)
                ser.write(send_data)
            elif COMMS_TYPE==COMMS_WIFI:
                payload_class = "2," #target data
                payload = degrees_msg
                send_data = payload_class + payload
                post_data(send_data)
    except:
        print("Incorrect format")
    print("Requesting Azimuth update to: ", degrees_msg)

def update_ze_degrees():
    global ser, txt_ze_degree, COMMS_TYPE, COMMS_SERIAL, COMMS_WIFI
    degrees = txt_ze_degree.get()
    degrees_msg = str(degrees)
    try:
        temp = float(degrees)
        if(temp > 360 or temp < 0):
            print("Enter 0-360.")
        else:
            if COMMS_TYPE==COMMS_SERIAL:
                header = "abab"
                payload_class = 3 #target data
                payload = degrees_msg
                payload_len = len(degrees_msg)
                send_data = bytearray(header, 'utf-8')
                send_data.append(payload_class)
                send_data.append(payload_len)
                byte_arr = bytearray(payload, 'utf-8')
                send_data = send_data + (byte_arr)
                ser.write(send_data)
            elif COMMS_TYPE==COMMS_WIFI:
                payload_class = "3," #target data
                payload = degrees_msg
                send_data = payload_class + degrees_msg
                post_data(send_data)

    except:
        print("Incorrect format")
    print("Requesting Zenith update to: ", degrees_msg)


def update_latitude():
    global txt_lat, latitude
    degrees = txt_lat.get()
    degrees_msg = "v"+str(degrees)
    latitude = float(degrees)
    print("latitude updated to: ", latitude)
    
    #filename changed by Sushrut
    with open(log_filename, 'a') as file:
        file.write("latitude updated to: ", str(latitude))
        file.write("\n")
        file.close()


def update_longitude():
    global txt_long, longitude
    degrees = txt_long.get()
    degrees_msg = "v"+str(degrees)
    longitude = float(degrees)
    print("longitude updated to: ", str(longitude))
    
    #filename changed by Sushrut
    with open(log_filename, 'a') as file:
        file.write("longitude updated to: ", longitude)
        file.write("\n")
        file.close()


def on_closing():
    global connected, ser, main_loop_running, COMMS_TYPE, COMMS_SERIAL, COMMS_WIFI
    if(connected == 1):
        if COMMS_TYPE==COMMS_SERIAL:
            ser.close()
    schedule.clear()
    print("closing...")    
    
    #filename edited by Sushrut
    with open(log_filename, 'a') as file:
        file.write("closing...\n")
        file.close()
    
    root.destroy()
    main_loop_running = 0


root.protocol("WM_DELETE_WINDOW", on_closing)
while main_loop_running == 1:
    schedule.run_pending()
    root.update_idletasks()
    root.update()
