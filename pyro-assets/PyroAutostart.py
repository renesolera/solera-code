# -*- coding: utf-8 -*-
"""
Created on Mon Sep 18 14:31:50 2023

pyautogui.moveTo(260, 2060, duration=2)
pyautogui.click()


pyautogui.moveTo(1752, 1850, duration=1)
pyautogui.click()
pyautogui.moveTo(1812, 1150, duration=1)
pyautogui.click()

time.sleep(820)


@author: Kyle Borot
"""


import pyautogui
from pywinauto.application import Application
import time
import datetime
from datetime import date, datetime



app = Application(backend='uia').start(r"C:\Program Files (x86)\Solar Light Co\PMA Organizer\PMAORG.exe").connect(title='Form1 - [Download Data]', timeout=100)


time.sleep(5)
pyautogui.moveTo(1752, 1850, duration=1)
pyautogui.click()
pyautogui.moveTo(1812, 1150, duration=1)
pyautogui.click()

time.sleep(400)



pyautogui.moveTo(260, 2060, duration=2)
pyautogui.click()

#Save as txt
pyautogui.moveTo(40, 40, duration=1)
pyautogui.click()
pyautogui.moveTo(40, 125, duration=1)
pyautogui.click()
today = datetime.today().strftime('%Y-%m-%d')
pyautogui.write(f'{today}.txt')  
pyautogui.moveTo(2200, 905, duration=2)
pyautogui.click()

#Save as CSV
pyautogui.moveTo(40, 40, duration=1)
pyautogui.click()
pyautogui.moveTo(40, 125, duration=1)
pyautogui.click()
pyautogui.write(f'{today}.txt') 
pyautogui.moveTo(2000, 955, duration=2)
pyautogui.click()
pyautogui.moveTo(2000, 995, duration=2)
pyautogui.click()
pyautogui.moveTo(2200, 905, duration=2)
pyautogui.click()


#pyautogui.moveTo(1800, 2175, duration=1)


#pyautogui.moveTo(80, 80, duration=1)
#pyauto.click()

