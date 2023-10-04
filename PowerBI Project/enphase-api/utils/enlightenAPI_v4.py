import datetime
import json
import requests
from base64 import b64encode
from datetime import date

class enlightenAPI_v4:

    def __assert_success(self, res, exit_on_failure = True):
        '''
        Determine if the web request was successful (HTTP 200)
            Returns:
                If exit_on_failure, returned whether the web request was successful
        '''
        if res.status_code != 200:
            dl.error("Server Responded: " + str(res.status_code) + " - " + res.text)
            if exit_on_failure:
                quit()
            else:
                return False
        return True

    def __log_time(self):
        return datetime.datetime.now().strftime('%Y-%m-%d %I:%M:%S') + ": "

    def fetch_systems(self):
        '''
        Run the enlighten API Fetch Systems route
            Returns:
                Returns a list of systems for which the user can make API requests. By default, systems are returned in batches of 10. The maximum size is 100.
        '''
        url = f'{self.config["api_url"]}api/v4/systems/?key={self.config["app_api_key"]}'
        response = requests.get(url, headers={'Authorization': 'Bearer ' + self.config["access_token"]})
        self.__assert_success(response)
        result = json.loads(result.text)
        return result

    def __refresh_access_token(self):
        '''
        Refresh the access_token (1 day expiration) using the refresh_token (1 week expiration) using the steps detailed 
        at: https://developer-v4.enphase.com/docs/quickstart.html#step_10.
        This will override the current self.config and save the new config to local disk to ensure we have the latest access
        and refresh tokens for the next use.
        
        Note: It's unclear from the Enlighten API docs how to refresh the refresh_token once it expires. If the refresh_token expires 
        we're unable to call this route. Generating an access/refresh token via the API (https://developer-v4.enphase.com/docs/quickstart.html#step_8) 
        seems to only be usable once per app auth_code.
            Returns:
                The full web request result of the token refresh
        '''
        print(self.__log_time() + "Refreshing access_token...")
        url = f'{self.config["api_url"]}/oauth/token?grant_type=refresh_token&refresh_token={self.config["refresh_token"]}'
        # Enlighten API v4 Quickstart says this should be a GET request, but that seems to be incorrect. POST works.
        response = requests.post(url, auth=(self.config['app_client_id'], self.config['app_client_secret']))
        refresh_successful = self.__assert_success(response, False)
        if not refresh_successful:
            print("Unable to refresh access_token. Please set a new access_token and refresh_token in the enlighten_v4_config.json. Quitting...")
            quit()

        result = json.loads(response.text)
        
        self.config['access_token'] = result['access_token']
        self.config['refresh_token'] = result['refresh_token']

        with open('enlighten_v4_config.json', 'w') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=4)

        return result

    def production_meter_readings(self):
        '''
        Returns the last known reading of each production meter on the system as of the requested time, 
        regardless of whether the meter is currently in service or retired.
        Read_at is the time at which the reading was taken, and is always less than or equal to the requested end_at. 
        Commonly, the reading will be within 30 minutes of the requested end_at. 
        However, larger deltas can occur and do not necessarily mean there is a problem with the meter or the system. 
        Systems that are configured to report infrequently can show large deltas on all meters, especially when end_at is close to the current time. 
        Meters that have been retired from a system will show an end_at that doesn’t change, and that eventually is far away from the current time.
        '''
        print(self.__log_time() + "Pulling EnlightenAPI production_meter_readings summary...")
        url = f'{self.config["api_url"]}api/v4/systems/{self.config["system_id"]}/production_meter_readings?key={self.config["app_api_key"]}'
        response = requests.get(url, headers={'Authorization': 'Bearer ' + self.config["access_token"]})
        self.__assert_success(response)
        result = json.loads(response.text)
        return result

    def __init__(self, config):
        '''
        Initialize the englightAPI class
            Parameters:
                The API configuration (as a dictionary). Must contain api_url, api_key, and secrets
        '''
        self.config = config

        # It seems the v4 API allows you to only call the OAuth POST route with grant_type=authorization_code a SINGLE time for a auth_code.
        # So we need to make sure those already exist.
        if not self.config["access_token"] or not self.config["refresh_token"]:
            print('Error: access_token or refresh_token not set in the enlighten_v4_config.json')
            quit()

        # Refresh and save out the new config with the refreshed access_token/refresh_token
        self.__refresh_access_token()