"""
Python-PlentyMarkets-API-interface.

Interface to the resources from PlentyMarkets(https://www.plentymarkets.eu)

Copyright (C) 2021  Sebastian Fricke, Panasiam

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
from pathlib import Path
import time
from typing import Dict, List, Union
import requests
import simplejson
import gnupg
import logging
import tqdm
import pandas
from collections import defaultdict
from datetime import datetime, timezone, date, timedelta
from json.decoder import JSONDecodeError

import plenty_api.keyring
import plenty_api.utils as utils
from plenty_api.constants import (
    IMPORT_ORDER_DATE_TYPES, ORDER_TYPES, VALID_LANGUAGES, DUMPABLE_CONTENT_TYPES
)


class PlentyApi():
    """
    Provide specified routines to access data from PlentyMarkets
    over the RestAPI.

    Public methods:
        GET REQUESTS
        **plenty_api_get_pending_redistribution**

        **plenty_api_get_pending_reorder**

        **plenty_api_get_orders_by_date**

        **plenty_api_get_attributes**

        **plenty_api_get_vat_id_mappings**

        **plenty_api_get_price_configuration**

        **plenty_api_get_manufacturers**

        **plenty_api_get_referrers**

        **plenty_api_get_items**

        **plenty_api_get_variations**

        **plenty_api_get_stock**

        **plenty_api_get_storagelocations**

        **plenty_api_get_variation_stock_batches**

        **plenty_api_get_variation_warehouses**

        **plenty_api_get_contacts**

        **plenty_api_get_property_names**

        **plenty_api_get_property_selections**

        **plenty_api_get_property_selection_names**

        **plenty_api_get_shipping_pallets**

        **plenty_api_get_shipping_package_items**

        **plenty_api_get_shipping_packages_for_order**

        **plenty_api_dump_bi_raw_file**

        **plenty_api_get_bi_raw_files**

        **plenty_api_get_amazon_product_types**

        POST REQUESTS
        **plenty_api_set_image_availability**

        **plenty_api_create_items**

        **plenty_api_create_variations**

        **plenty_api_create_attribute**

        **plenty_api_create_attribute_names**

        **plenty_api_create_attribute_values**

        **plenty_api_create_attribute_value_names**

        **plenty_api_create_redistribution**

        **plenty_api_create_reorder**

        **plenty_api_create_transaction**

        **plenty_api_create_booking**

        **plenty_api_create_property_selection_name**

        PUT REQUESTS

        **plenty_api_update_redistribution**

        **plenty_api_book_incoming_items**

        **plenty_api_book_outgoing_items**

        **plenty_api_update_property_selection_name**
    """

    def __init__(self, base_url: str, login_method: str = 'keyring',
                 login_data: dict = None, data_format: str = 'json',
                 debug: bool = False):
        """
        Initialize the object and directly authenticate to the API to get
        the bearer token.

        Parameter:
            base_url    [str]   -   Base URL to the PlentyMarkets API
                                    Endpoint, format:
                                    [https://{name}.plentymarkets-cloud01.com]
        OPTIONAL
            login_method[str]   -   Choose the login method from a variety of
                                    options:
                                        [keyring, direct, gpg_encrypted,
                                         plain_text, azure_credential]
            login_data  [dict]  -   Elements for the specific login method
            data_format [str]   -   Output format of the response
            debug       [bool]  -   Print out additional information about the
                                    request URL and parameters
        """
        self.url = base_url
        self.keyring = plenty_api.keyring.CredentialManager()
        if debug:
            logging.basicConfig(level=logging.DEBUG)
        self.data_format = data_format.lower()
        if data_format.lower() not in ['json', 'dataframe']:
            self.data_format = 'json'
        self.creds = {'Authorization': ''}
        logged_in = self.__authenticate(
            login_method=login_method, login_data=login_data)
        if not logged_in:
            raise RuntimeError('Authentication failed')

        self.cli_progress_bar = False

    def __authenticate(self, login_method: str, login_data: dict) -> bool:
        """
        Get the bearer token from the PlentyMarkets API.
        There are five possible methods:
            + Enter credentials once and keep the username and the password
              within a keyring ('keyring')

            + Enter the username and password directly ('direct')

            + Provide username as an argument and get the password
              from a GnuPG encrypted file at a specified path.
              ('gpg_encrypted')

            + Provide username and the password as arguments ('plain_text')

            + Provide the identifier for a azure cloud credential instance
              ('azure_credential')

        Parameter:
            login_method    [str]       -   Name of the login method
            login_data      [dict]      -   Elements of the specific login
                                            method

        Return:
                        [bool]
        """
        if login_method not in ['keyring', 'direct', 'gpg_encrypted',
                                'plain_text', 'azure_credential']:
            raise utils.InvalidLoginAttempt(
                reason=f"invalid login method {login_method}")
        token = ''
        decrypt_pw = None

        if login_method == 'keyring':
            creds = self.keyring.get_credentials()
            if not creds:
                creds = utils.new_keyring_creds(keyring=self.keyring)
        elif login_method == 'direct':
            creds = utils.get_temp_creds()
        elif login_method == 'plain_text':
            if not all(key in login_data for key in ['user', 'password']):
                raise utils.InvalidLoginAttempt(
                    reason="Missing login data for the `plain_text` login "
                    "method, user and password required as keys in the "
                    "`login_data` dictionary."
                )
            creds = {'username': login_data['user'],
                     'password': login_data['password']}
        elif login_method == 'gpg_encrypted':
            if not all(key in login_data for key in ['user', 'file_path']):
                raise utils.InvalidLoginAttempt(
                    reason="Missing login data for the `gpg_encrypted` "
                    "login method, user and file_path required as keys in the"
                    " `login_data` dictionary."
                )
            gpg = gnupg.GPG()
            try:
                with open(login_data['file_path'], 'rb') as pw_file:
                    decrypt_pw = gpg.decrypt_file(pw_file)
            except FileNotFoundError as err:
                logging.error("Login to API failed: Provided gpg file is not "
                              f"valid\n=> {err}")
                return False
            if not decrypt_pw:
                logging.error("Login to API failed: Decryption of password"
                              " file failed.")
                return False
            password = decrypt_pw.data.decode('utf-8').strip('\n')
            creds = {'username': login_data['user'], 'password': password}
        elif login_method == 'azure_credential':
            try:
                import automationassets
            except ModuleNotFoundError as err:
                raise utils.InvalidLoginAttempt(
                    reason="Login method `azure_credential` can only be used "
                    "from an Azure cloud instance with prepared Python SDK"
                ) from err
            if 'credential_identifier' not in login_data:
                raise utils.InvalidLoginAttempt(
                    reason=str("Missing login data for the `azure_credential` "
                               "login method, credential_identifier required "
                               "as a key in the `login_data` dictionary.")
                )
            creds = automationassets.get_automation_credential(
                login_data['credential_identifier'])

        endpoint = self.url + '/rest/login'
        response = requests.post(endpoint, params=creds)
        if response.status_code == 403:
            logging.error(
                "Login to API failed: your account is locked\n"
                "unlock @ Setup->settings->accounts->{user}->unlock login"
            )
        try:
            token = utils.build_login_token(response_json=response.json())
        except JSONDecodeError:
            logging.error(
                "Plentymarkets API refuses to grant a login token."
                "(Possible reason: Too many users logged in)"
            )
            return False
        except KeyError:
            try:
                if (
                    response.json()['error'] == 'invalid_credentials'
                    and login_data == 'keyring'
                ):
                    logging.error(
                        "Wrong credentials: Please enter valid credentials."
                    )
                    creds = utils.update_keyring_creds(keyring=self.keyring)
                    response = requests.post(endpoint, params=creds)
                    token = utils.build_login_token(
                        response_json=response.json())
                else:
                    logging.error("Login to API failed: login token retrieval "
                                  f"was unsuccessful.\nstatus:{response}")
                    return False
            except KeyError:
                logging.error("Login to API failed: login token retrieval was "
                              f"unsuccessful.\nstatus:{response}")
                try:
                    logging.debug(f"{response.json()}")
                except Exception as err:
                    logging.error("Login to API failed: Could not read the "
                                  f"response: {err}")
                    return False
        if not token:
            return False

        self.creds['Authorization'] = token
        return True

    def __plenty_api_request(self,
                             method: str,
                             domain: str,
                             query: dict = None,
                             data: dict = None,
                             path: str = '') -> dict:
        """
        Make a request to the PlentyMarkets API.

        Parameter:
            method      [str]   -   GET/POST
            domain      [str]   -   Orders/Items...
        (Optional)
            query       [dict]  -   Additional options for the request
            data        [dict]  -   Data body for post requests
        """
        route = ''
        endpoint = ''
        raw_response = {}
        response = {}

        route = utils.get_route(domain=domain)
        endpoint = utils.build_endpoint(url=self.url, route=route, path=path)
        logging.debug(f"Endpoint: {endpoint}")
        if query:
            logging.debug(f"Params: {query}")
        while True:
            if method.lower() == 'get':
                raw_response = requests.get(endpoint, headers=self.creds,
                                            params=query)

            if method.lower() == 'post':
                raw_response = requests.post(endpoint, headers=self.creds,
                                             params=query, json=data)

            if method.lower() == 'put':
                raw_response = requests.put(endpoint, headers=self.creds,
                                            params=query, json=data)

            if raw_response.status_code != 429:
                break
            logging.warning(
                "API:Request throttled, limit for subscription reached"
            )
            time.sleep(3)

        logging.debug(f"request url: {raw_response.request.url}")

        # if the response is a file, return raw content, so it can be written to a file
        if raw_response.headers['Content-Type'] in DUMPABLE_CONTENT_TYPES:
            return raw_response.content

        try:
            response = raw_response.json()
        except simplejson.errors.JSONDecodeError:
            logging.error(f"No response for request {method} at {endpoint}")
            return None

        if isinstance(response, dict) and 'error' in response.keys():
            logging.error(f"Request failed:\n{response['error']['message']}")

        return response

# GET REQUESTS

    def __repeat_get_request_for_all_records(self,
                                             domain: str,
                                             query: dict,
                                             path: str = '') -> dict:
        """
        Collect data records from multiple API requests in a single JSON
        data structure.

        Parameter:
            domain      [str]   -   Orders/Items/..
            query       [dict]  -   Additional options for the request

        Return:
                        [dict]  -   API response in as javascript object
                                    notation
        """
        response = self.__plenty_api_request(method='get',
                                             domain=domain,
                                             path=path,
                                             query=query)
        if not response:
            return None

        if ((isinstance(response, dict) and 'error' in response.keys()) or
                isinstance(response, list)):
            return response

        page_info = utils.sniff_response_format(response=response, query=query)
        # Handle page slices (custom selection of pages)
        slice_start = ''
        slice_end = ''
        if 'pages' in query:
            pages = query['pages']
            slice_start = pages['start_page'] if 'start_page' in pages else ''
            slice_end = pages['end_page'] if 'end_page' in pages else ''
            logging.debug(f"Using page slice [{slice_start}:{slice_end}]")
        if slice_start and slice_start >= 2:
            entries = []
        else:
            entries = response[page_info['data']]

        if self.cli_progress_bar and page_info['last_page']:
            pbar = None
            if not page_info['end_condition'](response):
                pbar = tqdm.tqdm(desc=f'Plentymarkets {domain} request',
                                 total=response[page_info['last_page']])
        elif self.cli_progress_bar and not page_info['last_page']:
            logging.warn(f"Response for {domain} has no pagination, unable to detect the number of pages.")

        page = 1
        while not page_info['end_condition'](response):
            # Count from 1 onward if the response has no pagination
            if page_info['page']:
                page = response[page_info['page']] + 1
            else:
                page = page + 1
            query.update({'page': page})

            if slice_end and page > slice_end:
                # Skip requests for pages after the end of the slice
                break

            response = self.__plenty_api_request(method='get',
                                                 domain=domain,
                                                 path=path,
                                                 query=query)
            if not response:
                return None

            if isinstance(response, dict) and 'error' in response.keys():
                logging.error(f"subsequent {domain} API requests failed.")
                return response

            if slice_start and page < slice_start:
                # Skip pages before the beginning of the slice
                continue

            entries += response[page_info['data']]

            if self.cli_progress_bar:
                if pbar:
                    pbar.update(1)

        if self.cli_progress_bar and page_info['last_page']:
            if pbar:
                pbar.close()

        return entries

    def __plenty_api_generic_get(self,
                                 domain: str = '',
                                 path: str = '',
                                 refine: dict = None,
                                 additional: list = None,
                                 query: dict = None,
                                 lang: str = ''):
        """
        Generic wrapper for GET routes that includes basic checks, repeated
        requests and data type conversion.

        Parameters:
            domain      [str]   -   orders/items/...
            path        [str]   -   Addition to the domain for a specific route
            refine      [dict]  -   Apply filters to the request
            additional  [list]  -   Additional arguments for the query
            query       [dict]  -   Extra elements for the query
            lang        [str]   -   Language for the export

        Return:
                        [JSON(Dict) / DataFrame] <= self.data_format
        """
        query = utils.sanity_check_parameter(
            domain=domain, query=query, refine=refine,
            additional=additional,lang=lang)

        data = self.__repeat_get_request_for_all_records(
            domain=domain, path=path, query=query)

        return utils.transform_data_type(
            data=data, data_format=self.data_format)

    def __plenty_api_get_pending_non_sales_orders(self, refine: dict) -> list:
        """
        Get all non sales orders that have not been finished yet.
        (Redistributions or Reorders)
        Parameters:
            refine          [dict]      -   Refine arguments for the order
                                            search

        Return:
                        [JSON(Dict) / DataFrame] <= self.data_format
        """
        additional = ['orderItems.transactions']
        query = utils.sanity_check_parameter(domain='order',
                                             query=None,
                                             refine=refine,
                                             additional=additional)

        orders = self.__repeat_get_request_for_all_records(domain='orders',
                                                           query=query)
        if isinstance(orders, dict) and 'error' in orders.keys():
            logging.error("GET pending non sales orders failed with:\n"
                          f"{orders}")
            return None

        pending_list = []
        for order in orders:
            finished = False
            for event_date in order['dates']:
                if event_date['typeId'] == IMPORT_ORDER_DATE_TYPES['finish']:
                    finished = True
            if not finished:
                pending_list.append(order)
        orders = utils.transform_data_type(data=pending_list,
                                           data_format=self.data_format)

        return orders

    def plenty_api_dump_bi_raw_file(
        self, remote_files: Union[str, dict, list],
        download_directory: Path = Path('.')
    ) -> List[Union[Path, None]]:
        """
        Dumping BI raw data to file.

        Parameter:

            remote_files[str, dict, list]   -   BI files to download
                                                determines the path to the raw
                                                data this can be a string, a
                                                list of strings or a dict (e.g.
                                                the response from
                                                `plenty_api_get_bi_raw_files`)
        OPTIONAL
            download_directory  [Path]      -   Local filepath to store the data
                                                default is the current directory.
                                                Automatically created when not
                                                found.

        Return:
                                [list]      -   list of paths to downloaded files
        """
        if isinstance(remote_files, str):
            remote_files = [remote_files]

        response_list = []
        for remote_file in remote_files:
            remote_file_path_query = None
            # if a response from plenty_api_get_bi_raw_files was passed, extract path
            if isinstance(remote_file, dict) and 'path' in remote_file:
                remote_file_path_query = Path(remote_file['path'])

            if isinstance(remote_file, str):
                remote_file_path_query = Path(remote_file)

            if not remote_file_path_query:
                logging.warning(
                    f'validation error - invalid path query ({remote_file}) for'
                    'BI files. Required is either a single path, a list of'
                    'paths or a the response format of'
                    '`plenty_api_get_bi_raw_files`.'
                )
                response_list.append(None)
                continue
            response = self.__plenty_api_request(
                method='get', domain='bi_raw', path='/file',
                query={'path':remote_file_path_query}
            )
            if isinstance(response, bytes):
                download_directory.mkdir(parents=True, exist_ok=True)
                file_destination = download_directory / remote_file_path_query.name
                with open(file_destination, "wb") as requested_file:
                        requested_file.write(response)
                        response_list.append(file_destination)
            else:
                response_list.append(None)
                logging.error('Failed to fetch {}'.format(remote_file_path_query))
        return response_list

    def plenty_api_get_bi_raw_files(self, refine: dict = None, query: dict = None) -> list:
        """
        Get a list of BI-Rawdata files

        Parameters:
            refine              [dict]      -   Refine arguments for the BI
            query               [dict]      -   Query arguments e.g. page-slicing

        Return:
                        [JSON(Dict) / DataFrame] <= self.data_format
        """
        query = utils.sanity_check_parameter(domain='bi_raw',
                                             query=query,
                                             refine=refine,
                                             additional=None)

        # Prefer 100 items per page over the default of 20
        if 'itemsPerPage' not in query:
            query.update({'itemsPerPage':100})

        bi_files = self.__repeat_get_request_for_all_records(domain='bi_raw',
                                                             query=query)

        if isinstance(bi_files, dict) and 'error' in bi_files.keys():
            logging.error("GET BI-Rawfile list failed with:\n"
                          f"{bi_files}")
            return None

        bi_files = utils.transform_data_type(data=bi_files,
                                           data_format=self.data_format)

        return bi_files

    def plenty_api_get_pending_redistribution(
        self, order_id: int = 0, sender: int = 0, receiver: int = 0,
        shipping_packages: str = ''
    ) -> list:
        """
        Get all redistribution that have not been finished yet.
        Parameters:
        OPTIONAL
            order_id        [int]       -   Plentymarkets ID of a specific
                                            order
            sender          [int]       -   Plentymarkets ID of the sender
                                            warehouse
            receiver        [int]       -   Plentymarkets ID of the receiver
                                            warehouse
            shipping_packages [str]     -   Pull shipping packages for each
                                            order, valid values:
                                            [
                                                '' - empty, no pull,
                                                'minimal' - pull minimal info,
                                                'full' - pull all information
                                            ]

        Return:
                        [JSON(Dict) / DataFrame] <= self.data_format
        """
        assert shipping_packages in ['', 'minimal', 'full']
        refine = {'orderType': ORDER_TYPES['redistribution']}
        if order_id:
            refine.update({'orderIds': [order_id]})
        if sender:
            refine.update({'sender.warehouse': sender})
        if receiver:
            refine.update({'receiver.warehouse': receiver})
        orders = self.__plenty_api_get_pending_non_sales_orders(refine=refine)
        if shipping_packages != '':
            for order in orders:
                packages = self.plenty_api_get_shipping_packages_for_order(
                    order_id=order['id'], mode=shipping_packages)
                order['shippingPackages'] = packages
        return orders

    def plenty_api_get_pending_reorder(
        self, order_id: int = 0, sender: int = 0, receiver: int = 0
    ) -> list:
        """
        Get all reorders that have not been finished yet.
        Parameters:
        OPTIONAL
            order_id        [int]       -   Plentymarkets ID of a specific
                                            order
            sender          [int]       -   Plentymarkets ID of the sender
                                            contact
            receiver        [int]       -   Plentymarkets ID of the receiver
                                            warehouse

        Return:
                        [JSON(Dict) / DataFrame] <= self.data_format
        """
        refine = {'orderType': ORDER_TYPES['reorder']}
        if order_id:
            refine.update({'orderIds': [order_id]})
        if sender:
            refine.update({'sender.contact': sender})
        if receiver:
            refine.update({'receiver.warehouse': receiver})
        return self.__plenty_api_get_pending_non_sales_orders(refine=refine)

    def plenty_api_get_orders_by_date(self, start: str = '', end: str = '',
                                      date_type='creation', additional=None,
                                      refine=None):
        """
        Get all orders within a specific date range.

        Parameter:
            start       [str]   -   Start date
            end         [str]   -   End date
            date_type   [str]   -   Specify the type of date
                                    {Creation, Change, Payment, Delivery}
            additional  [list]  -   Additional arguments for the query as
                                    specified in the manual
            refine      [dict]  -   Apply filters to the request
                                    Example:
                                    {'orderType': '1,4', referrerId: '1'}
                                    Restrict the request to order types:
                                        1 and 4 (sales orders and refund)
                                    And restrict it to only orders from the
                                    referrer with id '1'

        Return:
                        [JSON(Dict) / DataFrame] <= self.data_format
        """
        if not start:
            start = (date.today() - timedelta(days=1)).isoformat()
        if not end:
            end = date.today().isoformat()
        date_range = utils.build_date_range(start=start, end=end)
        if not date_range:
            logging.error(f"Invalid range {start} -> {end}")
            return None

        if not utils.check_date_range(date_range=date_range):
            logging.error(f"{date_range['start']} -> {date_range['end']}")
            return None

        query = utils.build_query_date(date_range=date_range,
                                       date_type=date_type)
        if not query:
            return None

        query = utils.sanity_check_parameter(domain='order',
                                             query=query,
                                             refine=refine,
                                             additional=additional)

        orders = self.__repeat_get_request_for_all_records(domain='orders',
                                                           query=query)
        if isinstance(orders, dict) and 'error' in orders.keys():
            logging.error(f"GET orders by date failed with:\n{orders}")
            return None

        orders = utils.transform_data_type(data=orders,
                                           data_format=self.data_format)

        return orders

    def plenty_api_get_attributes(self,
                                  additional: list = None,
                                  last_update: str = '',
                                  variation_map: bool = False):
        """
        List all attributes from PlentyMarkets, this will fetch the basic
        attribute structures, so if you require an attribute value use:
        additional=['values'].
        The option variation_map performs an additional request to
        /rest/items/variations in order to map variation IDs to attribute
        values.

        Parameter:
            additional  [list]  -   Add additional elements to the response
                                    data
                                    Viable options:
                                    ['values', 'names', 'maps']
            last_update [str]   -   Date of the last update given as one
                                    of the following formats:
                                        YYYY-MM-DDTHH:MM:SS+UTC-OFFSET
                                        attributes-MM-DDTHH:MM
                                        YYYY-MM-DD
            variation_map[bool]-   Fetch all variations and add a list of
                                    variations, where the attribute value
                                    matches to the corresponding attribute
                                    value

        Return:
                        [JSON(Dict) / DataFrame] <= self.data_format
        """
        attributes = None
        query = {}

        query = utils.sanity_check_parameter(domain='attribute',
                                             query=query,
                                             additional=additional)

        if last_update:
            query.update({'updatedAt': last_update})

        # variation_map was given but the required '&with=values' query is
        # missing, we assume the desired request was to be made with values
        if variation_map:
            if not additional:
                query.update({'with': 'values'})
            if additional:
                if 'values' not in additional:
                    query.update({'with': 'values'})

        attributes = self.__repeat_get_request_for_all_records(
            domain='attributes', query=query)
        if isinstance(attributes, dict) and 'error' in attributes.keys():
            logging.error(f"GET attributes failed with:\n{attributes}")
            return None

        if variation_map:
            variation = self.plenty_api_get_variations(
                additional=['variationAttributeValues'])
            attributes = utils.attribute_variation_mapping(
                variation=variation, attribute=attributes)

        attributes = utils.transform_data_type(data=attributes,
                                               data_format=self.data_format)

        return attributes

    def plenty_api_get_vat_id_mappings(self, subset: List[int] = None):
        """
        Get a mapping of all VAT configuration IDs to each country or
        if specified for a subset of countries.
        A VAT configuration is a combination of country, vat rates,
        restrictions and date range.

        Parameter:
            subset      [list]  -   restrict the mappings to only the given
                                    IDs (integer)
            You can locate these IDs in your Plenty- Markets system under:
            Setup-> Orders-> Shipping-> Settings-> Countries of delivery

        Return:
                        [JSON(Dict) / DataFrame] <= self.data_format
        """
        vat_data = self.__repeat_get_request_for_all_records(domain='vat',
                                                             query={})
        if isinstance(vat_data, dict) and 'error' in vat_data.keys():
            logging.error(f"GET VAT-configuration failed with:\n{vat_data}")
            return None

        vat_table = utils.create_vat_mapping(data=vat_data, subset=subset)

        vat_table = utils.transform_data_type(data=vat_table,
                                              data_format=self.data_format)
        return vat_table

    def plenty_api_get_price_configuration(self,
                                           minimal: bool = False,
                                           last_update: str = ''):
        """
        Fetch the price configuration from PlentyMarkets.

        Parameter:
            minimal     [bool]  -   reduce the response data to necessary IDs.
            last_update [str]   -   Date of the last update given as one of the
                                    following formats:
                                        YYYY-MM-DDTHH:MM:SS+UTC-OFFSET
                                        YYYY-MM-DDTHH:MM
                                        YYYY-MM-DD

        Result:
                        [JSON(Dict) / DataFrame] <= self.data_format
        """
        prices = None
        minimal_prices: list = []
        query = {}

        if last_update:
            # The documentation refers to Unix timestamps being a valid
            # format, but that is not the case within my tests.
            query.update({'updatedAt': last_update})

        prices = self.__repeat_get_request_for_all_records(
            domain='prices', query=query)
        if isinstance(prices, dict) and 'error' in prices.keys():
            logging.error(f"GET price-configuration failed with:\n{prices}")
            return None

        if not prices:
            return None

        if minimal:
            for price in prices:
                minimal_prices.append(
                    utils.shrink_price_configuration(data=price))
            prices = minimal_prices

        prices = utils.transform_data_type(data=prices,
                                           data_format=self.data_format)
        return prices

    def plenty_api_get_manufacturers(self,
                                     refine: dict = None,
                                     additional: list = None,
                                     last_update: str = ''):
        """
        Get a list of manufacturers (brands), which are setup on
        PlentyMarkets.

        Parameter:
            refine      [dict]  -   Apply a filter to the request
                                    The only viable option currently is:
                                    'name'
            additional  [list]  -   Add additional elements to the response
                                    data.
                                    Viable options currently:
                                    ['commisions', 'externals']
            last_update [str]   -   Date of the last update given as one of the
                                    following formats:
                                        YYYY-MM-DDTHH:MM:SS+UTC-OFFSET
                                        YYYY-MM-DDTHH:MM
                                        YYYY-MM-DD

        Return:
                        [JSON(Dict) / DataFrame] <= self.data_format
        """
        query = {}
        if last_update:
            query.update({'updatedAt': last_update})
        return self.__plenty_api_generic_get(domain='manufacturer',
                                             query=query,
                                             refine=refine,
                                             additional=additional)

    def plenty_api_get_referrers(self,
                                 column: str = ''):
        """
        Get a list of order referrers from PlentyMarkets.

        Even though the documentation claims that `columns` can work with an
        array of strings, it actually cannot query a subset of columns, as it
        will only use the last member of the array.
        To get all of the columns, leave @column empty.

        Parameter:
            OPTIONAL
            column      [str]   -   Name of the field from the referrer to be
                                    exported.

        Return:
                        [JSON(Dict) / DataFrame] <= self.data_format
        """
        # TODO actually only backendName, id and name are actually useful
        # because all other attributes are useless without identification
        valid_columns = ['backendName', 'id', 'isEditable', 'isFilterable',
                         'name', 'orderOwnderId', 'origin']
        query = {}
        if column and column not in valid_columns:
            logging.warning(f"Invalid column argument removed: {column}")
        elif column and column in valid_columns:
            query = {'columns': column}

        # This request doesn't export in form of pages
        referrers = self.__plenty_api_request(method='get',
                                              domain='referrer',
                                              query=query)
        if 'error' in {key for referrer in referrers for key in referrer}:
            logging.error(f"GET referrers failed with:\n{referrers}")
            return None

        referrers = utils.transform_data_type(data=referrers,
                                              data_format=self.data_format)

        return referrers

    def plenty_api_get_items(self,
                             refine: dict = None,
                             additional: list = None,
                             last_update: str = '',
                             lang: str = ''):
        """
        Get product data from PlentyMarkets.

        Parameter:
            refine      [dict]  -   Apply filters to the request
                                    Example:
                                    {'id': '12345', 'flagOne: '5'}
            additional  [list]  -   Add additional elements to the response
                                    data.
                                    Example:
                                    ['variations', 'itemImages']
            last_update [str]   -   Date of the last update given as one of the
                                    following formats:
                                        YYYY-MM-DDTHH:MM:SS+UTC-OFFSET
                                        YYYY-MM-DDTHH:MM
                                        YYYY-MM-DD
            lang        [str]   -   Provide the text within the data in one of
                                    the following languages:

            (plenty documentation: https://rb.gy/r6koft)

        Return:
                        [JSON(Dict) / DataFrame] <= self.data_format
        """
        query = {}
        if last_update:
            query.update({'updatedBetween': utils.date_to_timestamp(
                         date=last_update)})

        return self.__plenty_api_generic_get(domain='item',
                                             query=query,
                                             refine=refine,
                                             additional=additional,
                                             lang=lang)

    def plenty_api_get_variations(self,
                                  refine: dict = None,
                                  additional: list = None,
                                  lang: str = ''):
        """
        Get product data from PlentyMarkets.

        Parameter:
            refine      [dict]  -   Apply filters to the request
                                    Example:
                                    {'id': '2345', 'flagOne: '5'}
            additional  [list]  -   Add additional elements to the response
                                    data.
                                    Example:
                                    ['stock', 'images']
            lang        [str]   -   Provide the text within the data in one
                                    of the following languages:
                                    Example: 'de', 'en', etc.

            (plenty documentation: https://rb.gy/r6koft)

        Return:
                        [JSON(Dict) / DataFrame] <= self.data_format
        """
        query = {}

        return self.__plenty_api_generic_get(domain='variation',
                                             refine=refine,
                                             additional=additional,
                                             query=query,
                                             lang=lang)

    def plenty_api_get_stock(self, refine: dict = None):
        """
        Get stock data from PlentyMarkets.

        Parameter:
            refine      [dict]  -   Apply filters to the request
                                    Example:
                                    {'variationId': 2345}

        Return:
                        [JSON(Dict) / DataFrame] <= self.data_format
        """
        return self.__plenty_api_generic_get(domain='stockmanagement',
                                             refine=refine)

    def plenty_api_get_storagelocations(self,
                                        warehouse_id: int,
                                        refine: dict = None,
                                        additional: list = None):
        """
        Get storage location data from PlentyMarkets.

        Parameter:
            warehouse_id[int]   -   Plentymarkets ID of the target warehouse
            refine      [dict]  -   Apply filters to the request
                                    Example:
                                    {'variationId': 2345}
            additional  [list]  -   Add additional elements to the response
                                    data.
                                    Example:
                                    ['warehouseLocation']

        Return:
                        [JSON(Dict) / DataFrame] <= self.data_format
        """
        return self.__plenty_api_generic_get(
            domain='warehouses',
            path=f'/{warehouse_id}/stock/storageLocations',
            refine=refine,
            additional=additional)

    def plenty_api_get_variation_stock_batches(self, variation_id: int):
        """
        Get all storage locations from all available warehouses for the given
        variation.

        Parameter:
            variation_id[int]   -   Plentymarkets ID of the target variation

        Return:
                        [list]  -   list of storage locations ordered by the
                                    `bestBeforeDate`
        """
        # get all warehouses for this item
        refine = {'variationId': variation_id}

        # returns only locations with positive stock
        stock = self.plenty_api_get_stock(refine=refine)
        warehouses = [s['warehouseId'] for s in stock]

        # get storage data from everywhere
        storage_data = [location
                        for warehouse_id in warehouses
                        for location in self.plenty_api_get_storagelocations(
                        warehouse_id, refine=refine)]

        # return ordered by best before date (oldest first)
        return sorted(storage_data, key=lambda s: s['bestBeforeDate'])

    def plenty_api_get_variation_warehouses(self,
                                            item_id: int,
                                            variation_id: int) -> list:
        """
        Get all a list of warehouses, where the given variation is stored.

        Parameters:
            item_id     [int]   -   Plentymarkets ID of the item
                                    (variation container)
            variation_id[int]   -   Plentymarkets ID of the specific variation

        Return:
                        [JSON(Dict) / DataFrame] <= self.data_format
        """
        return self.__plenty_api_generic_get(
            domain='item',
            path=f'/{item_id}/variations/{variation_id}/variation_warehouses')

    def plenty_api_get_contacts(self,
                                refine: dict = None,
                                additional: list = None):
        """
        List all contacts on the Plentymarkets system.

        Parameter:
            refine      [dict]  -   Apply filters to the request
                                    Example:
                                    {'email': 'a@posteo.net', 'name': 'Thomas'}
            additional  [list]  -   Add additional elements to the response
                                    data.
                                    Example:
                                    ['addresses']

        Return:
                        [JSON(Dict) / DataFrame] <= self.data_format
        """
        return self.__plenty_api_generic_get(
            domain='contact',
            refine=refine,
            additional=additional)

    def plenty_api_get_property_names(
        self, property_id: Union[int, List[int]] = None,
        lang: Union[str, List[str]] = None
    ) -> Union[Dict[int, Dict[str, str]], pandas.DataFrame]:
        """
        Fetch a mapping of property IDs to one or more names in various
        languages.

        Parameters:
            property_id         [int/list]      -   Restrict the request to a
                                                    list of IDs or a single ID,
                                                    None indicates to pull all
            lang                [str/list]      -   Restrict the result data to
                                                    a list of languages or to a
                                                    single language,
                                                    None indicates to pull all.

        Returns:
                        [JSON(Dict) / DataFrame] <= self.data_format
        """
        assert isinstance(property_id, (int, list, type(None)))
        assert isinstance(lang, (str, list, type(None)))
        if isinstance(lang, str):
            lang = [lang]
        if lang:
            assert all(x in VALID_LANGUAGES for x in lang)

        domain = 'property'
        path = '/names'
        query = {}
        if isinstance(property_id, int):
            query.update({'propertyId': property_id})
        data = self.__repeat_get_request_for_all_records(
            domain=domain, path=path, query=query
        )
        if self.data_format == 'dataframe':
            processed_data = defaultdict(list)
        else:
            processed_data = defaultdict(dict)
        for prop in data:
            if (
                (lang and prop['lang'] not in lang) or
                (isinstance(property_id, list) and
                 prop['propertyId'] not in property_id)
            ):
                continue
            if self.data_format == 'dataframe':
                processed_data['property_id'].append(prop['propertyId'])
                processed_data['lang'].append(prop['lang'])
                processed_data['name'].append(prop['name'])
            else:
                processed_data[prop['propertyId']].update(
                    {prop['lang']: prop['name']}
                )
        if self.data_format == 'dataframe':
            dataframe = pandas.DataFrame.from_dict(processed_data)
            if len(dataframe.index) > 0:
                dataframe.sort_values(
                    ['property_id', 'lang'], inplace=True, ignore_index=True
                )
            return dataframe
        return dict(processed_data)

    def plenty_api_get_property_selections(self, refine: dict = None):
        """
        Get a mapping of selection IDs to the actual value in all available
        languages.

        Parameter:
            refine      [dict]  -   Apply filters to the request
                                    Example: {'propertyId': 123}

        Return:
                        [dict]  -   Mapping of all selection property values
        """
        domain = 'property'
        path = '/selections'

        query = utils.sanity_check_parameter(
            domain=domain, query=None, refine=refine,
            additional=None, lang='')

        data = self.__repeat_get_request_for_all_records(
            domain=domain, path=path, query=query)

        selection_map = defaultdict(lambda: defaultdict(dict))
        for selection in data:
            key = selection['propertyId']
            value_id = selection['id']
            for value in selection['relation']['relationValues']:
                selection_map[key][value_id][value['lang']] = value['value']

        df_data = []
        if self.data_format == 'dataframe':
            for property_id, selections in data.items():
                for selection_id, languages in selections.items():
                    for language, name in languages.items():
                        df_data.append([property_id, selection_id, language,
                                        name])
            columns = ['property_id', 'selection_id', 'language', 'name']
            return pandas.DataFrame(df_data, columns=columns)

        return dict(selection_map)

    def plenty_api_get_property_selection_names(self, selection_id: int):
        """
        Get all names for the specific selection Id.

        Parameter:
            selection_id        [int]   -   Selection Id which the names will
                                            be rturned for

        Return:
                        [JSON(Dict) / DataFrame] <= self.data_format
        """
        path = f"/selections/{selection_id}/names"
        data = self.__plenty_api_generic_get(domain='v2property', path=path)

        return data

    def plenty_api_get_shipping_pallets(self, order_id: int = 0):
        """
        Get shipping pallets from Plentymarkets, optionally from a specific
        order.

        Parameter:
        OPTIONAL
            order_id            [int]       -   ID of the order to pull
                                                shipping pallets from

        Return:
                        [JSON(Dict) / DataFrame] <= self.data_format
        """
        path = '/shipping/pallets'
        query = {} if not order_id else {'orderId': order_id}
        return self.__plenty_api_generic_get(
            domain='order', path=path, query=query)

    def plenty_api_get_shipping_package_items(self, package_id: int):
        """
        Get the content of a shipping package from Plentymarkets.

        Parameter:
            package_id          [int]       -   ID of the packae to pull
                                                items from

        Return:
                        [JSON(Dict) / DataFrame] <= self.data_format
        """
        path = f'/shipping/packages/{package_id}/items'
        orders = self.__repeat_get_request_for_all_records(
            domain='order', path=path, query={})
        return utils.transform_data_type(
            data=orders, data_format=self.data_format)

    def plenty_api_get_shipping_packages_for_order(self, order_id: int,
                                                   mode: str = 'full'):
        """
        Get the content of all shipping packages from a specific order.

        Parameter:
            order_id            [int]       -   ID of the order to pull
                                                shipping packages from
            mode                [str]       -   Summary format (minimal/full)
                                                default is full

        Return:
                        [JSON(Dict) / DataFrame] <= self.data_format
        """
        assert mode in ['minimal', 'full']
        pallets = self.plenty_api_get_shipping_pallets(order_id=order_id)
        package_responses = []
        for pallet in pallets:
            for package in pallet['packages']:
                package_response = self.plenty_api_get_shipping_package_items(
                    package_id=package['id'])
                package['content'] = package_response
                package_responses.append(package)

        return utils.summarize_shipment_packages(
            response=package_responses, mode=mode)

    def plenty_api_get_amazon_product_types(self):
        """
        Get a list of all available Amazon product types.

        Return:
                        [JSON(Dict) / DataFrame] <= self.data_format
        """
        return self.__plenty_api_generic_get(domain='pim',
                                             path='/amazon-product-types')

# POST REQUESTS

    def plenty_api_set_image_availability(self,
                                          item_id: str,
                                          image_id: str,
                                          target: dict) -> dict:
        """
        Create a marketplace availability for a specific item/image
        combiniation.

        Parameter:
            item_id     [str]   -   Item ID from PlentyMarkets
            image_id    [str]   -   Image ID from PlentyMarkets
            target      [dict]  -   ID of the specific:
                                        * marketplace
                                        * mandant (client)
                                        * listing
                                    together with a specifier



        Marketplace IDs: (@setup->orders->order origins)
        Mandant IDs: (@setup->client->{client}->settings[Plenty ID])

        Return:
                        [dict]
        """
        if not item_id or not image_id or not target:
            return {'error': 'missing_parameter'}

        target_name = ''
        target_id = ''
        for element in target:
            if element in ['marketplace', 'mandant', 'listing']:
                if target[element]:
                    target_name = element
                    target_id = target[element]
            else:
                logging.warning(f"{element} is not a valid target for the "
                                "image availability POST request.")

        if not target_name or not target_id:
            logging.error("Invalid target for availability configuration. "
                          f"Got: [{target}]")
            return {'error': 'invalid_target'}

        data = {
            "imageId": image_id,
            "type": target_name,
            "value": str(target_id)
        }
        path = str(f"/{item_id}/images/{image_id}/availabilities")

        response = self.__plenty_api_request(method="post",
                                             domain="items",
                                             path=path,
                                             data=data)

        return response

    def plenty_api_create_items(self, json: list) -> list:
        """
        Create one or more items at Plentymarkets.

        Parameter:
            json        [list]   -   Either a list of JSON objects or a single
                                     JSON, describing the items.

        Return:
                        [list]   -   Response objects if one or more should
                                     fail, the entry contains the error message
        """
        if isinstance(json, dict):
            json = [json]

        response = []
        for item in json:
            if not utils.sanity_check_json(route_name='items',
                                           json=item):
                response.append({'error': 'invalid_json'})
                continue
            response.append(self.__plenty_api_request(
                method="post", domain="items", data=item))
        return response

    def plenty_api_create_variations(self, item_id: int, json: list) -> list:
        """
        Create a variation for a specific item on Plentymarkets.

        Parameter:
            item_id     [int]    -   Add the variations to this item
            json        [list]   -   Either a list of JSON objects or a single
                                     JSON object describing a variation for an
                                     item.

        Return:
                        [list]   -   Response objects if one or more should
                                     fail, the entry contains the error
                                     message.
        """
        if not item_id:
            return [{'error': 'missing_parameter'}]

        if isinstance(json, dict):
            json = [json]

        path = str(f'/{item_id}/variations')

        response = []
        for variation in json:
            if not utils.sanity_check_json(route_name='variations',
                                        json=variation):
                response.append({'error': 'invalid_json'})
                continue
            response.append(self.__plenty_api_request(
                method="post", domain="items", path=path, data=variation))

        return response

    def plenty_api_create_attribute(self, json: dict) -> dict:
        """
        Create a new attribute on Plentymarkets.

        Parameter:
            json        [dict]  -   A single JSON object describing an
                                    attribute

        Return:
                        [dict]  -  Response object if the request should
                                   fail, the entry contains the error
                                   message.
        """
        if not utils.sanity_check_json(route_name='attributes',
                                    json=json):
            return {'error': 'invalid_json'}

        return self.__plenty_api_request(method="post", domain="attributes",
                                         data=json)

    def plenty_api_create_attribute_name(self, attribute_id: int,
                                         lang: str, name: str) -> dict:
        """
        Create an attribute name for a specific attribute.

        Parameter:
            attribute_id[str]   -   Attribute ID from PlentyMarkets
            lang        [str]   -   two letter abbreviation of a language
            name        [str]   -   The visible name of the attribute in
                                    the given language

        Return:
                        [dict]
        """
        if not attribute_id or not lang or not name:
            return [{'error': 'missing_parameter'}]

        path = str(f"/{attribute_id}/names")

        if utils.get_language(lang=lang) == 'INVALID_LANGUAGE':
            return {'error': 'invalid_language'}

        data = {
            'attributeId': attribute_id,
            'lang': lang,
            'name': name
        }

        return self.__plenty_api_request(method="post", domain="attributes",
                                         path=path, data=data)

    def plenty_api_create_attribute_values(self, attribute_id: int,
                                           json: list) -> dict:
        """
        Create one or more attribute values for a specific attribute.

        Parameter:
            attribute_id[str]   -   Attribute ID from PlentyMarkets
            json        [list]  -   Either a list of JSON objects or a
                                    single JSON object describing an
                                    attribute value for an attribute

        Return:
                        [list]
        """
        if not attribute_id:
            return [{'error': 'missing_parameter'}]

        if isinstance(json, dict):
            json = [json]

        path = str(f"/{attribute_id}/values")

        response = []
        for name in json:
            if not utils.sanity_check_json(route_name='attribute_values',
                                           json=name):
                response.append({'error': 'invalid_json'})
                continue

            response.append(self.__plenty_api_request(
                method="post", domain="attributes", path=path, data=name))

        return response

    def plenty_api_create_attribute_value_name(self, value_id: int,
                                               lang: str, name: str) -> dict:
        """
        Create an attribute value name for a specific attribute.

        Parameter:
            value_id    [str]   -   Attribute value ID from PlentyMarkets
            lang        [str]   -   two letter abbreviation of a language
            name        [str]   -   The visible name of the attribute in the
                                    given language

        Return:
                        [dict]
        """
        if not value_id or not lang or not name:
            return [{'error': 'missing_parameter'}]

        path = str(f"/attribute_values/{value_id}/names")

        if utils.get_language(lang=lang) == 'INVALID_LANGUAGE':
            return {'error': 'invalid_language'}

        data = {
            'valueId': value_id,
            'lang': lang,
            'name': name
        }

        return self.__plenty_api_request(method="post", domain="items",
                                         path=path, data=data)

    def plenty_api_create_redistribution(self, template: dict,
                                         book_out: bool = False) -> dict:
        """
        Create a new redistribution on Plentymarkets.

        The creation of a redistribution is split into multiple steps with the
        REST API, first the order has to be created, then the outgoing
        transaction have to be created and booked, before incoming transactions
        are created and booked.

        As soon as the order was initiated it cannot be changed/deleted anymore

        Parameter:
            template    [dict]  -   Describes the transactions between two
                                    warehouses
            book_out    [bool]  -   Book outgoing transaction directly

        Return:
                        [dict]
        """
        if not utils.validate_redistribution_template(template=template):
            return {'error': 'invalid_template'}

        redistribution_json = utils.build_import_json(
            template=template, sender_type='warehouse')
        response = self.__plenty_api_request(method="post",
                                             domain="redistribution",
                                             data=redistribution_json)

        (outgoing, incoming) = utils.build_redistribution_transactions(
            order=response, variations=template['variations'])

        if outgoing:
            for transaction in outgoing:
                transaction_response = self.plenty_api_create_transaction(
                    order_item_id=transaction['orderItemId'], json=transaction)
                if 'error' in transaction_response.keys():
                    logging.warning("transaction creation failed "
                                    f"({transaction_response})")

        if book_out:
            initiate_order_date = utils.build_date_update_json(
                date_type='initiate', date=datetime.now())
            self.plenty_api_update_redistribution(order_id=response['id'],
                                                  json=initiate_order_date)
            self.plenty_api_create_booking(order_id=response['id'])

        if incoming:
            for transaction in incoming:
                self.plenty_api_create_transaction(
                    order_item_id=transaction['orderItemId'], json=transaction)
            if book_out:
                self.plenty_api_create_booking(order_id=response['id'])
                finish_order_date = utils.build_date_update_json(
                    date_type='finish', date=datetime.now())
                self.plenty_api_update_redistribution(order_id=response['id'],
                                                      json=finish_order_date)

        return response

    def plenty_api_create_reorder(self, template):
        """
        Create a new reorder on Plentymarkets.

        This process is quite similar to the redistribution creation process,
        differences are that a reorder source is a contact instead of a
        warehouse and there are no outgoing transactions.

        Skip the automatic booking step for now as it doesn't seem to be useful
        for now.

        Parameter:
            template    [dict]  -   Describes the transactions between the
                                    sender contact and the receiver warehouse

        Return:
                        [dict]
        """
        reorder_json = utils.build_import_json(
            template=template, sender_type='contact')
        response = self.__plenty_api_request(method="post",
                                             domain="reorder",
                                             data=reorder_json)

        incoming = utils.build_reorder_transaction(
            order=response, variations=template['variations'])
        if incoming:
            for transaction in incoming:
                self.plenty_api_create_transaction(
                    order_item_id=transaction['orderItemId'], json=transaction)

        return response

    def plenty_api_create_transaction(self, order_item_id: int,
                                      json: dict) -> dict:
        """
        Create an outgoing or incoming transaction for an order.

        Parameter:
            order_item_id [int] -   ID of a single item (variation) within an
                                    order
            json        [dict]  -   single JSON object describing the
                                    transaction

        Return:
                        [dict]  -  Response object if the request should fail,
                                   the entry contains the error message.
        """
        if not order_item_id:
            return {'error': 'missing_parameter'}

        if not utils.sanity_check_json(route_name='transaction', json=json):
            return {'error': 'invalid_json'}

        path = str(f"/items/{order_item_id}/transactions")
        response = self.__plenty_api_request(method="post",
                                             domain="order",
                                             path=path,
                                             data=json)
        return response

    def plenty_api_create_booking(self, order_id: int,
                                  delivery_note: str = '') -> dict:
        """
        Execute all pending transactions within an order.

        This route handles outgoing and incoming transactions within an
        order (sales/redistribution/reorder/etc..). Which means it books
        out and books in.

        Parameter:
            order_id    [int]   -   ID of the order on Plentymarkets
            delivery_note [str] -   Identifier of the delivery note document,
                                    connected to the order

        Return:
                        [dict]  -  Response object if the request should
                                   fail, the entry contains the error message.
        """
        data = {}
        path = str(f"/{order_id}/booking")
        if delivery_note:
            data = {
                'deliveryNoteNumber': delivery_note
            }
        response = self.__plenty_api_request(method="post",
                                             domain="order",
                                             path=path,
                                             data=data)
        return response

    def plenty_api_create_property_selection(
        self, property_id: int, position: int, names: List[Dict[str, str]]
    ) -> dict:
        """
        Create a new selection value for a selection property with a variable
        amount of selection names.

        WARNING the Plentymarkets API will not detect duplicates.

        Parameters:
            property_id         [int]       -   Plentymarkets ID of the
                                                selection property
            position            [int]
            names               [list]      -   List of dictionaries for the
                                                selection, Example:
                                                [
                                                    {
                                                        'lang': 'de',
                                                        'name': 'Test',
                                                        'description': 'Woop'
                                                    }
                                                ]

        Returns:
                                [dict]      -   Response object if the request
                                                should fail, the entry contains
                                                the error message.
        """
        json = {
            'propertyId': property_id,
            'position': position,
            'names': names
        }
        path = "/selections"
        response = self.__plenty_api_request(method="post", path=path,
                                             domain="v2property", data=json)
        return response

    def plenty_api_create_property_selection_name(
        self, property_id: int, selection_id: int, lang: str, name: str
    ) -> dict:
        """
        Create a name in a specific language for a selection property.

        Parameter:
            property_id     [int]   -   Plentymarkets property Id which a new
                                        selection name will be created for
            lang            [str]   -   Initial language for selection creation
            name            [str]   -   Value of the selection name

        Return:
                            [dict]  -   Return the response object, in case the
                                        request fails return an error message
        """
        if not property_id or not lang or not name:
            return {'error': 'missing_parameter'}

        if utils.get_language(lang=lang) == 'INVALID_LANGUAGE':
            return {'error': 'invalid_language'}

        json = {
            'propertyId': property_id, 'selectionId': selection_id,
            'lang': lang, 'name': name
        }

        path = "/selections/names"
        response = self.__plenty_api_request(method="post", path=path,
                                             domain="v2property", data=json)
        return response

# PUT REQUESTS

    def plenty_api_update_redistribution(self, order_id: int,
                                         json: dict) -> dict:
        """
        Change certain attributes of a redistribution.

        Commonly used for changing certain event dates like:
            initiation, estimated delivery date and finish

        Parameter:
            order_id    [int]   -   ID of the order on Plentymarkets
            json        [dict]  -   single JSON object describing the update

        Return:
                        [dict]  -  Response object if the request should
                                   fail, the entry contains the error
                                   message.
        """
        if not order_id:
            return {'error': 'missing_parameter'}

        path = str(f"/{order_id}")
        response = self.__plenty_api_request(method="put",
                                             domain="redistribution",
                                             path=path,
                                             data=json)

        return response

    def plenty_api_book_incoming_items(self,
                                       item_id: int,
                                       variation_id: int,
                                       quantity: float,
                                       warehouse_id: int,
                                       location_id: int = 0,
                                       batch: str = None,
                                       best_before_date: str = None) -> dict:
        """
        Book a certain amount of stock of a specific variation into a location.

        If no stock location is given, this will book the stock into the
        standard location.
        The difference to the `plenty_api_create_booking` method is that the
        `plenty_api_create_booking` route needs existing transactions, while
        this method performs the booking directly.

        Parameters:
            item_id     [int]   -   Plentymarkets ID of the item
                                    (variation container)
            variation_id[int]   -   Plentymarkets ID of the specific variation
            quantity    [float] -   Amount to be booked into the location
            warehouse_id[int]   -   Plentymarkets ID of the target warehouse
            location_id [int]   -   Assigned ID for the storage location by
                                    default 0 (standard location)
            batch       [str]   -   Batch number that describes a specific
                                    group of products that are created within a
                                    limited time window
            best_before_date[str] -   Date at which a product loses guarantees
                                    for certain properties to be effective

        Return:
                        [dict]
        """
        # The REST API only accepts positive quantities for incoming bookings
        if quantity <= 0:
            return {'error': 'invalid_quantity'}

        data = {
            "warehouseId": warehouse_id,
            "storageLocationId": location_id,
            "deliveredAt": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"),
            "currency": "EUR",
            "quantity": quantity,
            "reasonId": 181,
        }

        if batch:
            data.update(batch=batch)
        if best_before_date:
            w3c_date = utils.parse_date(best_before_date)
            if w3c_date:
                data.update(bestBeforeDate=w3c_date)

        path = str(f"/{item_id}/variations/{variation_id}/stock/"
                   "bookIncomingItems")

        response = self.__plenty_api_request(method="put",
                                             domain="items",
                                             path=path,
                                             data=data)

        # TODO Error handling and introduce proper logging
        logging.debug(response)

        return response

    def plenty_api_book_outgoing_items(self,
                                       item_id: int,
                                       variation_id: int,
                                       quantity: float,
                                       warehouse_id: int,
                                       location_id: int = 0,
                                       batch: str = None,
                                       best_before_date: str = None):
        """
        Book a certain amount of stock of a specific variation from a location.

        If no stock location is given, this will book the stock from the
        standard location.
        The difference to the `plenty_api_create_booking` method is that the
        `plenty_api_create_booking` route needs existing transactions, while
        this method performs the booking directly.

        Parameters:
            item_id     [int]   -   Plentymarkets ID of the item
                                    (variation container)
            variation_id[int]   -   Plentymarkets ID of the specific variation
            quantity    [float] -   Amount to be booked into the location
            warehouse_id[int]   -   Plentymarkets ID of the target warehouse
            location_id [int]   -   Assigned ID for the storage location by
                                    default 0 (standard location)
            batch       [str]   -   Batch number that describes a specific
                                    group of products that are created within a
                                    limited time window
            best_before_date[str] -   Date at which a product loses guarantees
                                    for certain properties to be effective

        Return:
                        [dict]
        """
        # The REST API only accepts negative quantities for outgoing bookings
        if quantity >= 0:
            return {'error': 'invalid_quantity'}

        data = {
            "warehouseId": warehouse_id,
            "storageLocationId": location_id,
            "deliveredAt": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"),
            "currency": "EUR",
            "quantity": quantity,
            "reasonId": 201,
        }

        if batch:
            data.update(batch=batch)
        if best_before_date:
            w3c_date = utils.parse_date(best_before_date)
            if w3c_date:
                data.update(bestBeforeDate=w3c_date)

        path = str(f"/{item_id}/variations/{variation_id}/stock/"
                   "bookOutgoingItems")

        response = self.__plenty_api_request(method="put",
                                             domain="items",
                                             path=path,
                                             data=data)
        # TODO Error handling and introduce proper logging
        logging.debug(response)

        return response

    def plenty_api_update_property_selection_name(self, name_id: int,
                                                  name: str) -> dict:
        """
        Update the property selection name for the given name Id.

        Parameters:
            name_id         [int]   -   Id of the name value that will be
                                        changed
            name            [str]   -   New name value
        """
        if not name_id or not name:
            return {'error': 'missing_parameter'}

        json = {'name': name}

        path = f"/selections/names/{name_id}"
        response = self.__plenty_api_request(method="put", path=path,
                                             domain="v2property", data=json)
        return response
