from file_locations import umbrella_import, umbrella_logger
import json
import os
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
import time
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('expand_frame_repr', False)

start_time = time.time()


class Umbrella:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.auth_headers = {'Content-Type': 'application/x-www-form-urlencoded',
                             'Accept': 'application/json'}
        self.auth_url = 'https://api.umbrella.com/auth/v2/token'
        self.auth_data = {'grant_type': 'client_credentials'}
        self.destination_list_url = 'https://api.umbrella.com/policies/v2/destinationlists'
        self.access_token = self.pull_access_token()
        self.api_headers = {'Authorization': 'Bearer ' + self.access_token,
                            'Content-Type': 'application/json',
                            'Accept': 'application/json'
                            }
        self.umbrella_url = ''
        self.c2_data = '''
        {"name": "C2_Servers_Hunted_Blocklist", 
        "access": "block",
        "bundleTypeId": 1,
        "isGlobal": false}
        '''
        # Execute functions to delete, recreate, and update
        self.delete_specific_destination_list()
        self.create_umbrella_destination_list()
        self.add_umbrella_domains_urls()

    def pull_access_token(self):
        try:
            # Pull API Token with all the necessary fields
            response = requests.post(self.auth_url,
                                     headers=self.auth_headers,
                                     data=self.auth_data,
                                     auth=HTTPBasicAuth(username=self.username,
                                                        password=self.password))
            self.access_token = response.json()['access_token']
            umbrella_logger.info(f'Successfully pulled access_token!')
            return self.access_token
        except Exception as e:
            umbrella_logger.info(f'Failed to pull access_token!')
            umbrella_logger.info(f'Exception is {e}.')

    def pull_umbrella_url(self):
        # Get request to figure out what is the id of the destination list we want to delete
        request = requests.get(self.destination_list_url, headers=self.api_headers)

        # Slice for data field
        data = request.json()['data']

        # Import json into pandas
        df = pd.json_normalize(data)

        # Search for specific list. In this case 'C2_Servers_Hunted_Blocklist'
        df = df.loc[df['name'] == 'C2_Servers_Hunted_Blocklist']

        # Pull row id to insert into URL to delete
        id_ = df['id'][0]

        # URL with id
        self.umbrella_url = 'https://api.umbrella.com/policies/v2/destinationlists/' + str(id_)
        return self.umbrella_url

    def delete_specific_destination_list(self):
        """
        Delete the destination list. This will take two seconds vs looping through each destination and deleting.
        The latter will take 15 to 20 minutes. The downside to this approach is you must add the new list to each
        DNS zone.
        """
        try:

            request = requests.delete(self.pull_umbrella_url(), headers=self.api_headers)
            umbrella_logger.info(request.json())
            umbrella_logger.info(f'Successfully deleted C2_Servers_Hunted_Blocklist in Umbrella!')
            umbrella_logger.info(f'\n')
        except Exception as e:
            umbrella_logger.error(f'Failed to delete C2_Servers_Hunted_Blocklist in Umbrella.')
            umbrella_logger.error(f'Error is {e}')
            umbrella_logger.info(f'\n')

    def create_umbrella_destination_list(self):
        """
        Create the new destination list in Umbrella
        """
        try:
            request = requests.post(self.destination_list_url, headers=self.api_headers, data=self.c2_data)
            umbrella_logger.info(request.json())
            umbrella_logger.info(f'Successfully created C2_Servers_Hunted_Blocklist in Umbrella!')
            umbrella_logger.info(f'\n')
        except Exception as e:
            umbrella_logger.error(f'Failed to create C2_Servers_Hunted_Blocklist in Umbrella.')
            umbrella_logger.error(f'Error is {e}')
            umbrella_logger.info(f'\n')

    def add_umbrella_domains_urls(self):
        """
        Add the destinations into the destination list
        """
        try:
            # This will hit production!
            url = str(self.pull_umbrella_url()) + '/destinations'
            # Iterate over df and push each row into blocklist
            umbrella_df = pd.read_csv(umbrella_import, header=0)
            for index, row in enumerate(umbrella_df['hostnames'].items()):
                data = [{'destination': row[1]}]
                data = json.dumps(data)
                requests.post(url, headers=self.api_headers, data=data)
            umbrella_logger.info(f"Script took {((time.time() - start_time) / 60):.3f} minutes to run in its entirety.")
            umbrella_logger.info(f'Successfully imported all domains into C2_Servers_Hunted_Blocklist')

        except Exception as e:
            umbrella_logger.error(f'Failed to import data into C2_Servers_Hunted_Blocklist')
            umbrella_logger.error(f'Error is {e}')
            umbrella_logger.info(f'\n')
            umbrella_logger.info(f"Script took {((time.time() - start_time) / 60):.3f} minutes to run in its entirety.")


if __name__ == '__main__':
    Umbrella(username='', password='')
