# -*- coding: utf-8 -*-
"""
Created on Tue Sep 19 16:00:11 2023
@author: SushrutBapat
"""

#https://proweatherlive.net/api/weatherMetrics/export?device=6410af8cb94a3b0007c62053&startTime=2023-09-10T04%3A00%3A00.000Z&endTime=2023-09-16T03%3A59%3A59.999Z&format=csv&units%5B0%5D%5Btype%5D=direction&units%5B0%5D%5Bunit%5D=m&units%5B1%5D%5Btype%5D=distance&units%5B1%5D%5Bunit%5D=km&units%5B2%5D%5Btype%5D=temperature&units%5B2%5D%5Bunit%5D=%C2%B0F&units%5B3%5D%5Btype%5D=baroPressure&units%5B3%5D%5Bunit%5D=hPa&units%5B4%5D%5Btype%5D=windSpeed&units%5B4%5D%5Bunit%5D=mph&units%5B5%5D%5Btype%5D=windDirection&units%5B5%5D%5Bunit%5D=360%C2%B0&units%5B6%5D%5Btype%5D=rain&units%5B6%5D%5Bunit%5D=in&units%5B7%5D%5Btype%5D=lightIntensity&units%5B7%5D%5Bunit%5D=W%2Fm%C2%B2&units%5B8%5D%5Btype%5D=hcho&units%5B8%5D%5Bunit%5D=ppb&units%5B9%5D%5Btype%5D=coco2&units%5B9%5D%5Bunit%5D=ppm&%24accessToken=eyJhbGciOiJIUzI1NiIsInR5cCI6ImFjY2VzcyIsInR5cGUiOiJhY2Nlc3MifQ.eyJ1c2VySWQiOiI2NDBhMzk2MWI5NGEzYjAwMDdhZmI4YjkiLCJpYXQiOjE2OTUxNTE4MzUsImV4cCI6MTcwMjkyNzgzNSwiYXVkIjoiaHR0cHM6Ly9wcm93ZWF0aGVybGl2ZS5uZXQiLCJpc3MiOiJmZWF0aGVycyIsInN1YiI6ImFub255bW91cyIsImp0aSI6IjdmMmRiZGJkLTgzNDMtNDZmNC1iMTRlLWFiOTc5YTFjZGI2YyJ9.6LU_Y949LFpj6-0mpIXtm8b19idVgDWJ-kHwLfbEr_M&locale=en

import pyautogui
from pywinauto.application import Application
import time
import datetime
from datetime import date, datetime, timedelta



app = Application().start('C:\Program Files\Google\Chrome\Application\Chrome.exe --force-renderer-accessibility')

yesterday = date.today() - timedelta(days=1)
today = date.today() + timedelta(days=1)

time.sleep(3)


pyautogui.write(f'https://proweatherlive.net/api/weatherMetrics/export?device=6410af8cb94a3b0007c62053&startTime={yesterday}T04%3A00%3A00.000Z&endTime={today}T03%3A59%3A59.999Z&format=csv&units%5B0%5D%5Btype%5D=direction&units%5B0%5D%5Bunit%5D=m&units%5B1%5D%5Btype%5D=distance&units%5B1%5D%5Bunit%5D=km&units%5B2%5D%5Btype%5D=temperature&units%5B2%5D%5Bunit%5D=%C2%B0F&units%5B3%5D%5Btype%5D=baroPressure&units%5B3%5D%5Bunit%5D=hPa&units%5B4%5D%5Btype%5D=windSpeed&units%5B4%5D%5Bunit%5D=mph&units%5B5%5D%5Btype%5D=windDirection&units%5B5%5D%5Bunit%5D=360%C2%B0&units%5B6%5D%5Btype%5D=rain&units%5B6%5D%5Bunit%5D=in&units%5B7%5D%5Btype%5D=lightIntensity&units%5B7%5D%5Bunit%5D=W%2Fm%C2%B2&units%5B8%5D%5Btype%5D=hcho&units%5B8%5D%5Bunit%5D=ppb&units%5B9%5D%5Btype%5D=coco2&units%5B9%5D%5Bunit%5D=ppm&%24accessToken=eyJhbGciOiJIUzI1NiIsInR5cCI6ImFjY2VzcyIsInR5cGUiOiJhY2Nlc3MifQ.eyJ1c2VySWQiOiI2NDBhMzk2MWI5NGEzYjAwMDdhZmI4YjkiLCJpYXQiOjE2OTUxNTE4MzUsImV4cCI6MTcwMjkyNzgzNSwiYXVkIjoiaHR0cHM6Ly9wcm93ZWF0aGVybGl2ZS5uZXQiLCJpc3MiOiJmZWF0aGVycyIsInN1YiI6ImFub255bW91cyIsImp0aSI6IjdmMmRiZGJkLTgzNDMtNDZmNC1iMTRlLWFiOTc5YTFjZGI2YyJ9.6LU_Y949LFpj6-0mpIXtm8b19idVgDWJ-kHwLfbEr_M&locale=en')  
pyautogui.press('enter')

