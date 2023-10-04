import datetime
import shutil
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
import time

# Define the URLs and credentials
dashboard_url = 'https://proweatherlive.net/dashboard/'
email_address = 'jreudave@getsolera.com'
password = 'Vab15511111$$$$###@@'
delay = 25

# Set the path to the ChromeDriver executable
chrome_driver_path = "C:/Users/Soleras_First_PC/Documents/PowerBI Project/src/chromedriver_win32/chromedriver.exe"


# Set up the ChromeDriver service
service = Service(chrome_driver_path)

# Set up the webdriver with the ChromeDriver service
browser = webdriver.Chrome(service=service)
browser.get(dashboard_url)


try:
  # Wait for the email input field to be present
  myElem = WebDriverWait(browser, delay).until(EC.presence_of_element_located((By.ID, "input-62")))
  email = browser.find_element(By.ID, "input-62")
  email.send_keys(email_address, Keys.TAB)
  
  # Enter the password and submit the form
  password_field = browser.find_element(By.ID, "input-65")
  password_field.send_keys(password, Keys.TAB + Keys.TAB + Keys.ENTER)
except TimeoutException:
  print("Loading took too much time")

time.sleep(5)

# Perform the required actions on the webpage
browser.find_element(By.ID, "search").send_keys(Keys.TAB + Keys.TAB + Keys.ENTER + Keys.ARROW_DOWN + Keys.ARROW_DOWN + Keys.ARROW_DOWN + Keys.ARROW_DOWN + Keys.ARROW_DOWN + Keys.ARROW_DOWN + Keys.ARROW_DOWN + Keys.ENTER)
time.sleep(5)
browser.find_element(By.XPATH, '//span[text()="EXPORT DATA"]').click()
time.sleep(5)
browser.find_element(By.XPATH, '//*[@id="app"]/div[4]/div/div/div[2]/div/button[2]/span/div').click()
time.sleep(5)
