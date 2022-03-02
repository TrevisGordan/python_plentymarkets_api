# Python PlentyMarkets API interface

## Reference

- [Login](#login)
    + [GPG encrypted password file workflow](#gpg_workflow)
- [GET-Requests](#get-requests)
    + [Order related data](#get-order-section)
        * [get pending reorders](#get-pending-reorders)
        * [get pending redistributions](#get-pending-redistributions)
        * [get orders by date](#get-orders-by-date)
        * [get shipping pallets](#get-pallets)
        * [get shipping package items](#get-package-items)
        * [get shipping packages for order](#get-packages-for-order)
    + [get referrers](#get-referrers)
    + [Item related data](#get-items-section)
        * [get items](#get-items)
        * [get variations](#get-variations)
        * [get attributes](#get-attributes)
        * [get prices](#get-prices)
        * [get manufacturers](#get-manufacturers)
        * [get property names](#get-property-names)
        * [get property selections](#get-property-selections)
        * [get property selections names](#get-property-selections-names)
    + [Tax related data](#get-taxes-section)
        * [get vat id mappings](#get-vat-mappings)
    + [Stock related data](#get-stock-section)
        * [get stock](#get-stock)
        * [get storage locations](#get-storage-locations)
        * [get stock batches for a variation](#get-stock-batches)
        * [get warehouses for a variation](#get-warehouses)
    + [Contact data (CRM)](#get-contact-section)
        * [get contact data](#get-contacts)
    + [Plenty BI related data](#get-bi-section)
		* [get BI rawfile-list](#get-bi)
- [POST-Requests](#post-requests)
    + [Item related data](#post-items-section)
        * [post image avaialability](#post-image-availability)
        * [post items](#post-items)
        * [post variations](#post-variations)
        * [post attributes](#post-attributes)
        * [post attribute names](#post-attribute-names)
        * [post attribute values](#post-attribute-values)
        * [post attribute value names](#post-attribute-value-names)
        * [post property selection](#create-property-selection)
        * [post property selection name](#create-property-selection-name)
    + [Order related data](#post-order-section)
        * [post redistribution (move stock from one warehouse to another)](#post-redistribution)
        * [post reorder (refill stock within a warehouse)](#post-reorder)
        * [create transaction](#post-transaction)
        * [create booking](#post-booking)
- [PUT-Requests](#put-requests)
    + [Order related data](#put-order-section)
        * [update attributes of a redistribution](#update-redistribution)
    + [Stock related data](#put-stock-section)
        * [book incoming quanity](#book-incoming)
        * [book outgoing quanity](#book-outgoing)
    + [Item related data](#put-item-section)
        * [update property selection name](#update-property-selection)
- [Extra features](#extras)

### LOGIN <a name='login'></a>

The login request is sent automatically, as soon as the object is instantiated. There are five methods of providing credentials.

1. **direct**: Providing them over STDIN *[Usually only useful for testing on someone else's machine]* <br>
    `login_method = 'direct'`, `login_data = None` (empty by default)
2. **keyring**: Enter the credentials once per STDIN and save them into a keyring *[Very convenient for commands that are started manually doesn't work for cronjobs]* <br>
    `login_method = 'keyring'`, `login_data = None` (empty by default)
3. **plain_text**: Provide the username and the password as arguments *[Highly discouraged in combination with storing the passwords in plain text files or even worse in the code]* <br>
    `login_method = 'plain_text'`, `login_data = {'user': 'example_user', 'password': '1234abcd'}`
4. **gpg_encrypted**: Provide the username as an argument and a path to a GPG encrypted file for the password *[Works for cronjobs and manual running]* <br>
    `login_method = 'gpg_encrypted'`, `login_data = {'user': 'example_user', 'file_path': '/path/to/encrypted_file.gpg'}`
5. **azure_credential**: Provide the identifier for a azure credential manager instance and fetch the username and password from it directly. <br>
    `login_method = 'azure_credential'`, `login_data = {'credential_identifier': 'cred123'}`

**WARNING**: The logging module activated by the **debug option** of the `PlentySync` object, **will print your username and password** into the log as part of the response body.

#### Example for a GPG encrypted file workflow (on Linux) <a name='gpg_workflow'></a>

The idea behind the GnuPG encrypted file is to simply write the password
of the Plentymarkets REST API user into a `.txt` file and to encrypt that file.
`plenty_api` is then going to decrypt it during authentication and
read the password.
With the username and password, `plenty_api` can then receive an Oauth2
bearer token to be used for authentication.

Here is an example (on Linux):
```
# With a preceding space to skip entering the line into the bash history
  echo "password" > pw.txt
gpg --encrpyt --sign --recipient gpg-key@email.com pw.txt
```

Within python:
```
api = plenty_api.PlentyApi(
        base_url='https://company.plentymarkets-cloud01.com',
        login_method='gpg_encrypted',
        login_data={'user': 'api_user', 'file_path': '/home/user/pw.txt.gpg'}
    )
```

This will try to access your gpg key through your gpg agent, which manages
access to the key.

In some cases, you might want to increase the time until the passphrase
times out (in which case you would have to enter the password again).
This is how you can modify the time:
```
echo -e "default-cache-ttl 18000\nmax-cache-ttl 86400\nignore-cache-for-signing" >> ~/.gnupg/gpg-agent.conf
chmod 600 ~/.gnupg/gpg-agent.conf
```
This will set the default timeout time for a passphrase to 18000s (5h)
and the maximum timeout time to 86400s (24h) (meaning even if you use
the key multiple times during the 24h, after 24h you will have to enter
the password again).

### GET requests: <a name='get-requests'></a>

#### Orders <a name='get-order-section'></a>

##### plenty_api_get_pending_reorders: <a name='get-pending-reorders'></a>

Pull all reorders that have not been closed.

[*Optional parameter*]:

The **sender** parameter takes the ID of a contact in Plentymarkets, which in the case of a reorder should be a producer/supplier.
The **receiver** parameter takes the ID of a warehouse in Plentymarkets.

[*Output format*]:

There are currently two supported output formats: 'json' and 'dataframe'.  
The 'json' format simply returns the raw response, without page information and with multiple pages combined into a single data structure.  
The 'dataframe' format transforms that data structure into a pandas DataFrame, which contains subparts in json, that can be split further by the user application.

---

##### plenty_api_get_pending_redistributions: <a name='get-pending-redistributions'></a>

Pull all redistributions that have not been closed.

[*Optional parameter*]:

The **sender** parameter takes the ID of a contact in Plentymarkets, which in the case of a reorder should be a producer/supplier.
The **receiver** parameter takes the ID of a warehouse in Plentymarkets.
The **shipping_packages** parameter determines if shipping packages shall be added to the response and the extend of information about them. Valid values are ['', 'minimal', 'full'], no shipping packages are added by default. Pulling shipping packages requires additional requests (1 per pallet and 1 per package on each pallet).

[*Output format*]:

There are currently two supported output formats: 'json' and 'dataframe'.  
The 'json' format simply returns the raw response, without page information and with multiple pages combined into a single data structure.  
The 'dataframe' format transforms that data structure into a pandas DataFrame, which contains subparts in json, that can be split further by the user application.

---

##### plenty_api_get_orders_by_date: <a name='get-orders-by-date'></a>

By default, the *start* date is set to **yesterday** and the *end* date is set to **today**. You can adjust the date range by providing a string representation in one of the following formats for either both or one of these parameters.

- YEAR-MONTH-DAY                                    (2020-09-16)        [ISO 8601 date format]
- YEAR-MONTH-DAYTHOUR:MINUTE                        (2020-09-16T08:00)
- YEAR-MONTH-DAYTHOUR:MINUTE:SECOND+UTC-OFFSET      (2020-09-16T08:00)  [W3C date format]

The default `date_type` is **creation**, but you can set it to any of the following 4 types:
- **creation** [date and time when the order was created on PlentyMarkets]
- **change**   [date and time of the last change, within the order]
- **payment**  [date and time when the payment was either automatically received by the order or assigned to the order]
- **delivery** [date and time of the removal of products from the stock of the shipping warehouse]

[*Optional parameter*]:

The **additional** field expects a list of strings, valid values are:  
'addresses', 'relations', 'comments', 'location', 'payments', 'documents', 'contactSender'
'contactReceiver', 'warehouseSender', 'warehouseReceiver', 'orderItems.variation', 'orderItems.giftCardCodes'
'orderItems.transactions', 'orderItems.serialNumbers', 'orderItems.variationBarcodes', 'orderItems.comments',
'originOrderReferences' 'shippingPackages'

The **refine** field can be used to filter the request results by some aspect of the orders.
The field expects a dictionary, where the key has to match one of the following fields:  
orderType, contactId, referrerId, shippingProfileId, shippingServiceProviderId, ownerUserId, warehouseId, isEbayPlus, includedVariation, includedItem, orderIds, countryId, orderItemName, variationNumber, sender.contact, sender.warehouse, receiver.contact, receiver.warehouse, externalOrderId, clientId, paymentStatus, statusFrom, statusTo, hasDocument, hasDocumentNumber, parentOrderId  
For more information about the valid values: [Plenty Developer Documentation](https://developers.plentymarakets.com/rest-doc#/Order/get_rest_orders)

[*Output format*]:

There are currently two supported output formats: 'json' and 'dataframe'.  
The 'json' format simply returns the raw response, without page information and with multiple pages combined into a single data structure.  
The 'dataframe' format transforms that data structure into a pandas DataFrame, which contains subparts in json, that can be split further by the user application.

---

##### plenty_api_get_shipping_pallets: <a name='get-pallets'></a>

Each order can have one or more shipping pallets filled with shipping packages, this route pulls either all shipping pallets or those that are connected to a specific order. A shipping pallet response **DOES NOT CONTAIN** the package items, in order to fetch these you have to either use the `plenty_api_get_shipping_package_items` route for each pallet or use the wrapper method `plenty_api_get_shipping_packages_for_order` to pull all pallets and packages for a specific order.

[*Optional parameter*]:

The **order_id** parameter restricts the request to all pallets connect to the given order ID.

[*Output format*]:

There are currently two supported output formats: 'json' and 'dataframe'.  
The 'json' format simply returns the raw response, without page information and with multiple pages combined into a single data structure.  
The 'dataframe' format transforms that data structure into a pandas DataFrame, which contains subparts in json, that can be split further by the user application.

---

##### plenty_api_get_shipping_package_items: <a name='get-package-items'></a>

Pull the content of a specific package, the response will not include metadata about the package, as these information are only included in the pallet response.

[*Required parameter*]:

The **package_id** parameter contains a Plentymarkets ID for a specific package on a shipping pallet.

[*Output format*]:

There are currently two supported output formats: 'json' and 'dataframe'.  
The 'json' format simply returns the raw response, without page information and with multiple pages combined into a single data structure.  
The 'dataframe' format transforms that data structure into a pandas DataFrame, which contains subparts in json, that can be split further by the user application.

---

##### plenty_api_get_shipping_packages_for_order: <a name='get-packages-for-order'></a>

Wrapper method around both `plenty_api_get_shipping_pallets` and `plenty_api_get_shipping_package_items`, which combines both responses into an easily usable datastructure, which is oriented around the variations. There are two types of report formats: *minimal* and *full*, the structure of both is similar but minimal reduces the output to an absolute minimum (variation ID, pallet ID, package ID, package NO on pallet, quantity, total quantity per variation and a mapping of package IDs to pallet IDs).

[*Required parameter*]:

The **order_id** parameter contains a valid Plentymarkets Order ID.

[*Optional parameter*]:

The **mode** parameter chooses the report format, the default format is *full*. And valid values are: ['full', 'minimal'].

[*Output format*]:

There are currently two supported output formats: 'json' and 'dataframe'.  
The 'json' format simply returns the raw response, without page information and with multiple pages combined into a single data structure.  
The 'dataframe' format transforms that data structure into a pandas DataFrame, which contains subparts in json, that can be split further by the user application.

---

##### plenty_api_get_referrers: <a name='get-referrers'></a>

Fetch all referrers from PlentyMarkets, they contain the following attributes:
'backendName', 'id', 'isEditable', 'isFilterable', 'name', 'orderOwnderId', 'origin'

[*Optional parameter*]:

The **column** parameter limits the response body to the values of a single column. This is actually only useful for 'name', 'id' & 'backendName', but for the sake of completeness the rest is included as well.

[*Output format*]:

There are currently two supported output formats: 'json' and 'dataframe'.  
The 'json' format simply returns the raw response, without page information and with multiple pages combined into a single data structure.  
The 'dataframe' format transforms that data structure into a pandas DataFrame, which contains subparts in json, that can be split further by the user application.

---
---

#### Item data <a name='get-items-section'></a>

##### plenty_api_get_items: <a name='get-items'></a>

[*Optional parameter*]:

The **refine** field can be used to filter the request results by one or more of the attributes of the item:  
id, name, manufacturer, flagOne, flagTwo

Use the **additional** field to add more values to the response, valid values are:  
properties, variations, itemCrossSelling, itemProperties, itemImages, itemShippingProfiles, ebayTitles

With the **last_update** parameter, you can filter the results down to items that were changed at or after the specified date  
The dates are accepted in the following formats:
- YEAR-MONTH-DAY                                    (2020-09-16)        [ISO 8601 date format]
- YEAR-MONTH-DAYTHOUR:MINUTE                        (2020-09-16T08:00)
- YEAR-MONTH-DAYTHOUR:MINUTE:SECOND+UTC-OFFSET      (2020-09-16T08:00)  [W3C date format]

The **lang** field specifies the language of the texts used in the response. Valid values are country abbreviations in ISO-3166-1:  
[List of countries](https://developers.plentymarkets.com/rest-doc/gettingstarted#countries)

[*Output format*]:

There are currently two supported output formats: 'json' and 'dataframe'.  
The 'json' format simply returns the raw response, without page information and with multiple pages combined into a single data structure.  
The 'dataframe' format transforms that data structure into a pandas DataFrame, which contains subparts in json, that can be split further by the user application.

---

##### plenty_api_get_variations: <a name='get-variations'></a>

[*Optional parameter*]:

The **refine** field can be used to filter the request results by one or more of the attributes of the variation:  
id, itemId, flagOne, flagTwo, categoryId, isMain, isActive, barcode, referrerId, sku, date

Use the **additional** field to add more values to the response, valid values are:  
properties, variationProperties, variationBarcodes, variationBundleComponents, variationComponentBundles, variationSalesPrices, marketItemNumbers, variationCategories,
variationClients, variationMarkets, variationDefaultCategory, variationSuppliers, variationWarehouses, images, itemImages, variationAttributeValues, variationSkus,
variationAdditionalSkus, unit, parent, item, stock, tags

The **lang** field specifies the language of the texts used in the response. Valid values are country abbreviations in ISO-3166-1:  
[List of countries](https://developers.plentymarkets.com/rest-doc/gettingstarted#countries)

[*Output format*]:

There are currently two supported output formats: 'json' and 'dataframe'.  
The 'json' format simply returns the raw response, without page information and with multiple pages combined into a single data structure.  
The 'dataframe' format transforms that data structure into a pandas DataFrame, which contains subparts in json, that can be split further by the user application.

---

##### plenty_api_get_attributes: <a name='get-attributes'></a>

List all the attributes from PlentyMarkets (size, color etc.), additionally there is an option to link variations from the PlentyMarkets system to the attribute values.

[*Optional parameter*]:

Use the **additional** field to add more values to the response, valid values are:  
names, values, maps

With the **last_update** parameter, you can filter the results down to items that were changed at or after the specified date  
The dates are accepted in the following formats:
- YEAR-MONTH-DAY                                    (2020-09-16)        [ISO 8601 date format]
- YEAR-MONTH-DAYTHOUR:MINUTE                        (2020-09-16T08:00)
- YEAR-MONTH-DAYTHOUR:MINUTE:SECOND+UTC-OFFSET      (2020-09-16T08:00)  [W3C date format]

Finally, the **variation_map** parameter, performs an additional request to pull all variations in order to link them to the attribute values. Depending on the size of your
PlentyMarkets system, this can take a few seconds and consume some API calls.

[*Output format*]:

There are currently two supported output formats: 'json' and 'dataframe'.  
The 'json' format simply returns the raw response, without page information and with multiple pages combined into a single data structure.  
The 'dataframe' format transforms that data structure into a pandas DataFrame, which contains subparts in json, that can be split further by the user application.

---

##### plenty_api_get_price_configuration: <a name='get-prices'></a>

Fetch price configuration from PlentyMarkets, this can be used among other things to get the ID of a price used by a specific referrer in order to get the price date from variations.

[*Optional parameter*]:

You can reduce the response data to just IDs and names by using the **minimal** parameter (*True/False*).
And you can filter out price configurations, where the last change timestamp is further in the past than the specified date from the **last_change** parameter.
The dates are accepted in the following formats:
- YEAR-MONTH-DAY                                    (2020-09-16)        [ISO 8601 date format]
- YEAR-MONTH-DAYTHOUR:MINUTE                        (2020-09-16T08:00)
- YEAR-MONTH-DAYTHOUR:MINUTE:SECOND+UTC-OFFSET      (2020-09-16T08:00)  [W3C date format]

[*Output format*]:

There are currently two supported output formats: 'json' and 'dataframe'.  
The 'json' format simply returns the raw response, without page information and with multiple pages combined into a single data structure.  
The 'dataframe' format transforms that data structure into a pandas DataFrame, which contains subparts in json, that can be split further by the user application.

---

##### plenty_api_get_manufacturers: <a name='get-manufacturers'></a>

Fetch a list of manufacturers, that were setup on PlentyMarkets.

[*Optional parameter*]:

The **refine** field can be used to reduce the request to only manufacturers with the given name.
example: refine={'name': 'abc_company'}

Use the **additional** field to add more values to the response, valid values are:  
commisions, externals

With the **last_update** parameter, you can filter the results down to items that were changed at or after the specified date  
The dates are accepted in the following formats:
- YEAR-MONTH-DAY                                    (2020-09-16)        [ISO 8601 date format]
- YEAR-MONTH-DAYTHOUR:MINUTE                        (2020-09-16T08:00)
- YEAR-MONTH-DAYTHOUR:MINUTE:SECOND+UTC-OFFSET      (2020-09-16T08:00)  [W3C date format]

[*Output format*]:

There are currently two supported output formats: 'json' and 'dataframe'.  
The 'json' format simply returns the raw response, without page information and with multiple pages combined into a single data structure.  
The 'dataframe' format transforms that data structure into a pandas DataFrame, which contains subparts in json, that can be split further by the user application.

---

##### plenty_api_get_property_names: <a name='get-property-names'></a>

Create a mapping of property IDs to names in one or more languages.

[*Optional parameter*]:

The **property_id** field can be used to reduce the request to a single property ID or to filter the response to a list of property IDs (in the second case, we actually pull all properties from the REST API, but reduce it afterward).

With the **lang** parameter the result set can be further reduced to a single language or a sub-set of available languages.

The default value for both **property_id** and **lang** is `None`, which indicates to pull all properties with all languages.

[*Output format*]:

There are currently two supported output formats: 'json' and 'dataframe'.  
The 'json' format returns a dictionary of property IDs to language-name pairs.  
Example:  
```{1: {'de': 'name de', 'en': 'name en'}}```  
The 'dataframe' format transforms that data structure into a pandas DataFrame.  
Example:
```
property_id | lang | name
1           | de   | name de
1           | en   | name en
```

---

##### plenty_api_get_property_selections_names: <a name='get-property-selections-names'></a>

Get all names of a specific selection_id, with additional data such as the nameId, which is needed for updating selection names.

[*Output format*]:

There are currently two supported output formats: 'json' and 'dataframe'.  
The 'json' format simply returns the raw response, without page information and with multiple pages combined into a single data structure.  
The 'dataframe' format transforms that data structure into a pandas DataFrame, which contains subparts in json, that can be split further by the user application.


---

##### plenty_api_get_property_selections: <a name='get-property-selections'></a>

Create a mapping of property IDs to the selection-values of the property with the ID of the selection and text values for all available languages.

[*Optional parameter*]:

The **refine** field can be used to reduce the request to a single property ID.
example: refine={'propertyID': 123}

[*Output format*]:

There are currently two supported output formats: 'json' and 'dataframe'.  
The 'json' format returns a dictionary of property IDs to its available selection values
example: ```{1: {11: {'de': 'value_1', 'en': 'value_2'}}, 2: {12: {'de': 'value_3', 'en': 'value_4'}}}```
The 'dataframe' format transforms that data structure into a pandas DataFrame.

##### plenty_api_get_property_selections_names: <a name='get-property-selections-names'></a>

Get all names of a specific selection_id, with additional data such as the nameId, which is needed for updating selection names.

[*Output format*]:

There are currently two supported output formats: 'json' and 'dataframe'.  
The 'json' format simply returns the raw response, without page information and with multiple pages combined into a single data structure.  
The 'dataframe' format transforms that data structure into a pandas DataFrame, which contains subparts in json, that can be split further by the user application.

---
---

#### Tax data <a name='get-taxes-section'></a>

##### plenty_api_get_vat_id_mappings: <a name='get-vat-mappings'></a>

Create a mapping of all the different VAT configurations, which map to a country ID together with the Tax ID.

[*Optional parameter*]:

**subset**: supply a list of integer country IDs to limit the data to a specific set of countries

[*Output format*]:

Return a dictionary with the country IDs as keys and the corresponding VAT configuration IDs + the TaxID as value.

#### Stock data <a name='get-stock-section'></a>

##### plenty_api_get_stock <a name='get-stock'></a>

List stock of all warehouses.

[Plentymarkets Developer documentation reference](https://developers.plentymarkets.com/en-gb/plentymarkets-rest-api/index.html#/StockManagement/get_rest_stockmanagement_stock)

[*Optional parameter*]:

The **refine** field can be used to reduce the request by applying certain filters, valid values are:  
variationId

[*Output format*]:

There are currently two supported output formats: 'json' and 'dataframe'.  
The 'json' format simply returns the raw response, without page information and with multiple pages combined into a single data structure.  
The 'dataframe' format transforms that data structure into a pandas DataFrame, which contains subparts in json, that can be split further by the user application.

##### plenty_api_get_storagelocations <a name='get-storage-locations'></a>

Get storage locations from the plentymarkets system.

[Plentymarkets Developer documentation reference](https://developers.plentymarkets.com/en-gb/plentymarkets-rest-api/index.html#/StockManagement/get_rest_stockmanagement_warehouses__warehouseId__stock_storageLocations)

[*Required parameter*]:

This method requires the **warehouse_id** parameter, which contains the target warehouse ID assigned by Plentymarkets. It pulls all storage locations from that warehouse.

[*Optional parameter*]:

The **refine** field can be used to reduce the request by applying certain filters, valid values are:  
variationId, storageLocationId

Use the **additional** field to add more values to the response, valid values are:  
warehouseLocation

[*Output format*]:

There are currently two supported output formats: 'json' and 'dataframe'.  
The 'json' format simply returns the raw response, without page information and with multiple pages combined into a single data structure.  
The 'dataframe' format transforms that data structure into a pandas DataFrame, which contains subparts in json, that can be split further by the user application.

##### plenty_api_get_variation_stock_batches <a name='get-stock-batches'></a>

Get all storage locations that have stock of the given variation.

The method makes multiple API calls, it call `plenty_api_get_stock` once and `plenty_api_get_storagelocations` for every warehouse, that contains stock of the given variation.

[*Required parameter*]:

The only required parameter is the **variation_id**, which refers to ID assigned by Plentymarkets for the target variation.

[*Output format*]:

Returns a list of storage locations (dictionaries).

##### plenty_api_get_variation_warehouses <a name='get-warehouses'></a>

Get basic information about all warehouses, where the target variation is stored.

[Plentymarkets Developer documentation reference](https://developers.plentymarkets.com/en-gb/plentymarkets-rest-api/index.html#/Item/get_rest_items__id__variations__variationId__variation_warehouses)

[*Required parameter*]:

The request needs the **item_id** parameter as well as the **variation_id** variable, to find the correct warehouses for the variation. The **item_id** parameter refers to the ID assigned by Plentymarkets to the container of the variation, while **variation_id** contains the Plentymarkets assigned ID of the specific variation.

[*Output format*]:

There are currently two supported output formats: 'json' and 'dataframe'.  
The 'json' format simply returns the raw response, without page information and with multiple pages combined into a single data structure.  
The 'dataframe' format transforms that data structure into a pandas DataFrame, which contains subparts in json, that can be split further by the user application.

#### Contact data (CRM) <a name='get-contact-section'></a>

##### plenty_api_get_contacts <a name='get-contacts'></a>

Pull contact data from Plentymarkets.

[Plentymarkets Developer documentation reference](https://developers.plentymarkets.com/en-gb/plentymarkets-rest-api/index.html#/Account/get_rest_accounts_contacts)

[*Optional parameter*]:

The **refine** field can be used to reduce the request by applying certain filters, valid values are:  
fullText, contactEmail, email, postalCode, plentyId, externalId, number, typeId, rating, newsletterAllowanceAfter, newsletterAllowanceBefore, newsletterAllowance, contactId, contactAddress, countryId, userId, referrerId, name, nameOrId, town, privatePhone, billingAddressId, deliveryAddressId, tagIds

Use the **additional** field to add more values to the response, valid values are:  
addresses, accounts, options, orderSummary, primaryBillingAddress, contactOrders

[*Output format*]:

There are currently two supported output formats: 'json' and 'dataframe'.  
The 'json' format simply returns the raw response, without page information and with multiple pages combined into a single data structure.  
The 'dataframe' format transforms that data structure into a pandas DataFrame, which contains subparts in json, that can be split further by the user application.

#### Plenty BI related data <a name='get-bi-section'></a>

##### plenty_api_get_bi_raw_files <a name='get-bi'></a>

Get a list of BI raw data files.
More information in the [PlentyMarkets documentation](https://knowledge.plentymarkets.com/en/slp/business-entscheidungen/plenty-bi/reports/reports-verwalten).

[*Optional parameter*]:

The **refine** field can be used to reduce the request by applying certain filters, valid values are:

 - *dataName* (Filter that restricts the search result to raw data files ([Available options](https://knowledge.plentymarkets.com/en/slp/business-entscheidungen/plenty-bi/reports/datenformate)))
 - *createdAtTimestamp* (UNIX-Timestamp from when daily generated raw data
   are to be filtered.)
 - *processStatus*  (Current process status, the status is only changed
   by internal processing.  itemsPerPage (The number of raw data
   files to be returned. This library uses a default value of 100
   instead of 20, which is the default for the REST API.)
 - *sortOrder* (Defines the sort    order, possible values are: asc, desc)
   page (Page)

For custom slicing, the `pages` refine parameter can be used:
[*Examples*]:
```python
refine={'pages':{'start_page':1, 'end_page':5}}  # [1:5]
refine={'pages':{'end_page':3}}  # [:3]
refine={'pages':{'start_page':3}}  # [3:]
```

[*Output format*]:

[*Example*]:
```python
{
  'cloudId': 10,
  'createdAt': '2022-02-28 23:48:17+01',
  'dataCreatedAt': '2022-02-28 00:00:00',
  'dataName': 'orders',
  'id': '12345678-9123-4567-8912-345678912345',
  'path': 'report/rawData/orders/1234/2022/2/orders--2022-02-28--p1--v7.csv.gz',
  'plentyIdHash': 'abcdefghijkl',
  'processStatus': 'processed',
  'shouldProcess': 1
}
```

There are currently two supported output formats: 'json' and 'dataframe'.  
The 'json' format simply returns the raw response, without page information and with multiple pages combined into a single data structure.  
The 'dataframe' format transforms that data structure into a pandas DataFrame, which contains subparts in json, that can be split further by the user application.

### POST requests: <a name='post-requests'></a>

#### Items <a name='post-items-section'></a>

##### plenty_api_set_image_availability: <a name='post-image-availability'></a>

Update a single availability for an image, an image can be available for a marketplace (ebay, webshop etc.), mandant or for a specific listing.

[*Required parameter:*]:

The **item_id** field contains the Item ID used in PlentyMarkets.  
With the **image_id** field, the exact image is specified. It is rather hard to obtain, that ID directly from PlentyMarkets. Your best bet is probably to make a `plenty_api_get_items(additional=['itemImages'])` call and use the ID from there.  
In the **target** field you have to specify:  
    * What kind of target to connect
    * The ID of the target

[*Example*]:
```python
{'marketplace': 1}, {'mandant': 41444}, {'listing': 2}
```

[*Output format*]:

Return a POST request JSON response, if the request fails return the error message.
If the **item_id** field, the **image_id** or the **target** field is not filled the method will return: `{'error': 'missing_parameter'}`.
In case the language within the **target** parameter is invalid the method will return `{'error': 'invalid_target'}`.

##### plenty_api_create_items: <a name='post-items'></a>

Create one or more items on Plentymarkets, but do not create the variations for it. This call requires at least a valid category ID and a valid unit type. Additionally, you are able to specify more details for the main variation (virtual doesn't represent a physical product).

[*Required parameter*]:

The **json** field contains either a list of json objects (dictionaries) or a single json object. Please refer to [Plentymarkets Dev documentation: REST API POST items](https://developers.plentymarkets.com/en-gb/plentymarkets-rest-api/index.html#/Item/post_rest_items), for a list of valid attributes.

[*Example*]:
```json
{
    "position": 2,
    "manufacturerId": 1,
    "variations": [
        {
            "name": "test_main_variation",
            "variationCategories": [
                {
                    "categoryId": 400
                }
            ],
            "unit": {
                "unitId": 1,
                "content": 1
            }
        }
    ]
}
```

[*Output format*]:

Return a list of POST request JSON responses, if one of the requests fails return the error message.
When the JSON object doesn't contain the required attributes the method will return: `{'error': 'invalid_json'}`.

#### plenty_api_create_variations <a name='post-variations'></a>

Create a variation for a specific item on Plentymarkets.

[*Required parameter*]:

The **item_id** field contains the ID given to the item by Plentymarkets, the **json** field contains a single JSON object or a list of JSON objects describing a variation.
Please refer to [Plentymarkets Dev documentation: REST API POST items](https://developers.plentymarkets.com/en-gb/plentymarkets-rest-api/index.html#/Item/post_rest_items__itemId__variations), for a list of valid attributes.

[*Example*]:
```json
{
    'isMain': False,
    'isActive': True,
    'availability': 1,
    'number': 'test1234',
    'unit': {'unitId': 1, 'content': 1},
    'variationAttributeValues': [
        {'valueId': 13}, {'valueId': 17}
    ],
    'variationCategories': [{'categoryId': 21}],
    'variationBarcodes': [{'code': '1234567891011', 'barcodeId': 1}],
    "variationClients": [{"plentyId": 54017}]
},
```

[*Output format*]:

Return a list of POST request JSON responses, if one of the requests fails return the error message.
When the JSON object doesn't contain the required attributes the method will return: `{'error': 'invalid_json'}`.
If the **item_id** field is not filled the method will return: `{'error': 'missing_parameter'}`.

#### plenty_api_create_attribute <a name='post-attributes'></a>

Create a new attribute on Plentymarkets.

[*Required parameter*]:

The **json** parameter contains a single JSON object describing an attribute
Please refer to [Plentymarkets Dev documentation: REST API POST attributes](https://developers.plentymarkets.com/en-gb/plentymarkets-rest-api/index.html#/Item/post_rest_items_attributes), for a list of valid attributes.

[*Example*]:
```json
{
    'backendName': 'Material',
    'position': 3,
    'isLinkableToImage': False,
    'amazonAttribute': 'outer_material_type',
    'isGroupable': False
}
```

[*Output format*]:

Return a POST request JSON response, if one of the requests fails return the error message.
When the JSON object doesn't contain the required attributes the method will return: `{'error': 'invalid_json'}`.

#### plenty_api_create_attribute_name

Create an attribute name for a specific attribute on Plentymarkets.

[*Required parameter*]:

The **attribute_id** parameter contains the ID given to the attribute by Plentymarkets, the **lang** parameter contains a two letter abbreviation of the target language (for a list of valid values look here: [Language codes](https://developers.plentymarkets.com/en-gb/developers/main/rest-api-guides/getting-started.html#_language_codes)), and the **name** parameter contains the visible name for the attribute in the given language.
Please refer to [Plentymarkets Dev documentation: REST API POST attribute names](https://developers.plentymarkets.com/en-gb/plentymarkets-rest-api/index.html#/Item/post_rest_items_attributes__attributeId__names), for a list of valid attributes.

[*Output format*]:

Return a POST request JSON response, if one of the requests fails return the error message.
If the **attribute_id** field is not filled the method will return: `{'error': 'missing_parameter'}`.
In case the language within the **lang** parameter is invalid the method will return `{'error': 'invalid_language'}`.

#### plenty_api_create_attribute_values <a name='post-attribute-values'></a>

Create one or more attribute values for a specific attribute on Plentymarkets.

[*Required parameter*]:

The **attribute_id** parameter contains the ID given to the attribute by Plentymarkets, the **json** parameter contains a single JSON object or a list of JSON objects describing an attribute value.
Please refer to [Plentymarkets Dev documentation: REST API POST attribute values](https://developers.plentymarkets.com/en-gb/plentymarkets-rest-api/index.html#/Item/post_rest_items_attributes__attributeId__values), for a list of valid attributes.

[*Example*]:
```json
{
    'backendName': 'Cotton',
    'amazonValue': 'Cotton',
    'position': 2
},
```
Only `backendName` is a required field.

[*Output format*]:

Return a POST request JSON response, if one of the requests fails return the error message.
When the JSON object doesn't contain the required attributes the method will return: `{'error': 'invalid_json'}`.
If the **attribute_id** field is not filled the method will return: `{'error': 'missing_parameter'}`.

#### plenty_api_create_attribute_value_name

Create an attribute value name for a specific attribute value on Plentymarkets.

[*Required parameter*]:

The **value_id** parameter contains the ID given to the attribute value by Plentymarkets, the **lang** parameter contains a two letter abbreviation of the target language (for a list of valid values look here: [Language codes](https://developers.plentymarkets.com/en-gb/developers/main/rest-api-guides/getting-started.html#_language_codes)), and the **name** parameter contains the visible name for the attribute value in the given language.
Please refer to [Plentymarkets Dev documentation: REST API POST attribute value names](https://developers.plentymarkets.com/en-gb/plentymarkets-rest-api/index.html#/Item/post_rest_items_attribute_values__valueId__names), for a list of valid attributes.

[*Output format*]:

Return a POST request JSON response, if one of the requests fails return the error message.
If the **value_id** field is not filled the method will return: `{'error': 'missing_parameter'}`.
In case the language within the `lang` field of the JSON is invalid the method will return `{'error': 'invalid_language'}`.

#### plenty_api_create_property_selection <a name=create-property-selection></a>

Create a new selection value for an existing property with a variable amount of names.

[*Required parameter*]:

**property_id** parameter, the Plentymarkets ID of a property for which a new selection value is being added.  
**position** parameter, declares the position of the selection value in relation to other selection values (doesn't need to be unique).  
**names** parameter, list of dictionaries containing a combination of a 2 letter language identifier, a matching name and an optional description.  
*Example*:  
```json
[
    {
        'lang': 'de',
        'name': 'Hase',
        'description': 'Karottenfresser'
    },
    {
        'lang': 'en',
        'name': 'Rabbit',
        'description': 'Carrot eater'
    },
]
```

[*Output format*]:

Return a POST request JSON response, if one of the requests fails return the error message.
If the **property_id**, **lang** or **name** field is not filled the method will return: `{'error': 'missing_parameter'}`.
In case the language within the `lang` field of the JSON is invalid the method will return `{'error': 'invalid_language'}`.

#### plenty_api_create_property_selection_name <a name=create-property-selection-name></a>

Create a new name for an existing property selection value for the given language.

[*Required parameter*]:

**property_id** parameter, the Plentymarkets ID of a property for which a new selection name value is being added.  
**selection_id** parameter, the ID of the specific selection.  
**lang** parameter, a two letter abbreviation of the target language (for a list of valid values look here: [Language codes](https://developers.plentymarkets.com/en-gb/developers/main/rest-api-guides/getting-started.html#_language_codes))  
**name** parameter, the visible name for the selection name in the given language.

[*Output format*]:

Return a POST request JSON response, if one of the requests fails return the error message.
If the **property_id**, **lang** or **name** field is not filled the method will return: `{'error': 'missing_parameter'}`.
In case the language within the `lang` field of the JSON is invalid the method will return `{'error': 'invalid_language'}`.

#### Orders <a name='post-oders-section'></a>

#### plenty_api_create_redistribution <a name='post-redistribution'></a>

[*Required parameter*]:

The **template** parameter contains a simplified version of the JSON required for the creation of a redistribution, it is used for multiple purposes, at a minimum it has to contain essential IDs of the sender and receiver storage warehouse, the ID of the Plentymarkets system, and basic data about variations (ID, quantity). This information is combined with some boilerplate elements to create a valid JSON for the POST `/rest/redistribution` route. But it can also include outgoing and incoming storage locations in order to automate some pesky manual labor (More on that below in the example). The **book_out** boolean is used to indicate if any actual booking shall be performed by this function or if this should be done by the storage workers, by default this feature is off.  
Please refer to the [Plentymarkets Dev documentation: REST API POST redistribution](https://developers.plentymarkets.com/en-gb/plentymarkets-rest-api/index.html#/Order/post_rest_redistributions).

[*Example*]:

Here is an example of a template for a redistribution:
Required elements are: `plenty_id`, `sender`, `receiver`, and at least one variation in `variations`.
For `variations`, the required elements are `variation_id` and `total_quantity`.
For `locations` (and for `targets`) the required elements are `location_id` and `quantity`.

Without `locations`, the redistribution order will only include the listing of items all outgoing transactions have to be added manually.
When you include `locations` without `targets` only outgoing transactions are created automatically.
And if you include `targets` for the `locations`, incoming transactions are booked automatically as well.
The latter makes sense for example if you want to book all items on a transit location first.

```json
{
    'plenty_id': 12345,
    'sender': 104,
    'receiver': 114,
    'variations': [
        {
            'variation_id': 12345,
            'total_quantity': 10,
            'name': 'Awesome_product',
            'amounts': 10.50,
            'locations': [
                {
                    'location_id': 10, 'quantity': 5,
                    'targets': [
                        {'location_id': 3, 'quantity': 3},
                        {'location_id': 2, 'quantity': 2}
                    ]
                },
                {
                    'location_id': 12, 'quantity': 5,
                    'targets': [
                        {'location_id': 4, 'quantity': 2},
                        {'location_id': 5, 'quantity': 3}
                    ]
                }
            ]
        }
    ]
}
```

You can also add the following fields to each variation: 'batch', 'bestBeforeDate', 'identification'.

This will be transformed into the following valid JSON object for the REST API:
```json
{
    'typeId': 15,
    'plentyId': 12345,
    'orderItems': [
        {
            'typeId': 1,
            'itemVariationId': 12345,
            'quantity': 10,
            'orderItemName': 'Awesome_product'
        }
    ],
    'relations': [
        {
            'referenceType': 'warehouse',
            'referenceId': 104,
            'relation': 'sender'
        },
        {
            'referenceType': 'warehouse',
            'referenceId': 114,
            'relation': 'receiver'
        }
    ]
}
```

And two outgoing transactions will be created:
```json
{
    'quantity': 5,
    'direction': 'out',
    'status': 'regular',
    'warehouseLocationId': 10
}

{
    'quantity': 5,
    'direction': 'out',
    'status': 'regular',
    'warehouseLocationId': 12
}
```

As well as 4 incoming transactions:
```json
{
    'quantity': 3,
    'direction': 'in',
    'status': 'regular',
    'warehouseLocationId': 3
}

{
    'quantity': 2,
    'direction': 'in',
    'status': 'regular',
    'warehouseLocationId': 2
}

{
    'quantity': 2,
    'direction': 'in',
    'status': 'regular',
    'warehouseLocationId': 4
}

{
    'quantity': 3,
    'direction': 'in',
    'status': 'regular',
    'warehouseLocationId': 5
}
```

If you choose to activate **book_out**, the method will also set the initiation date with the current date:  
(*WARNING* after the initiation of an order it *cannot be changed/deleted*)
```json
    'dates': [
        {
            'typeId': 16,
            'date': '2021-01-01T09:00:00+01:00'
        }
    ]
```

Book out any outgoing transactions and if they exist also the incoming transactions and finally set the finish date with the current date:
```json
    'dates': [
        {
            'typeId': 17,
            'date': '2021-01-01T09:00:01+01:00'
        }
    ]
```

[*Output format*]:

Return a POST request JSON response, if one of the requests fails return the error message.
When the **template** object cannot be validated, the method will return: `{'error': 'invalid_template'}`.

#### plenty_api_create_reorder <a name='post-reorder'></a>

[*Required parameter*]:

The **template** parameter contains a simplified version of the JSON required for the creation of a reorder, it contains information about the sender, receiver, the target plenty system and the variations. Optionally, the user can add location IDs to create incoming transactions automatically.
Please refer to the [Plentymarkets Dev Documnetation: REST API POST reorder](https://developers.plentymarkets.com/en-gb/plentymarkets-rest-api/index.html#/Order/post_rest_reorders)

[*Example*]:

Here is an example of a template for a reorder:
Required elements are: `plenty_id`, `sender`, `receiver`, and at least one variation in `variations`.
For `variations`, the required elements are `variation_id` and `total_quantity`.
For `locations` the required elements are `location_id` and `quantity`.

Without `locations` the reorder will only contain a listing of items, each transaction has to be created manually.

```json
{
    'plenty_id': 12345,
    'sender': 1234,
    'receiver': 111,
    'variations': [
        {
            'variation_id': 1234,
            'total_quantity': 2,
            'name': 'Awesome_test with incoming',
            'amounts': 10,
            'locations': [
                {'location_id': 1234, 'quantity': 2}
            ]
        },
        {
            'variation_id': 2345,
            'total_quantity': 1,
            'name': 'Awesome_test without incoming',
            'amounts': 10
        }
    ]
}
```

[*Output format*]:

Return a POST request JSON response, if one of the requests fails return the error message.

#### plenty_api_create_transaction <a name=post-transaction></a>

This route is used to create a new transaction for an order. A transaction is an exchange of stock between two sides (usually something like warehouse -> customer, warehouse -> warehouse, etc.). Each order contains a part called `relations`, which describes the sender and the receiver of an order.  
The transaction is then created with an `in` or `out` direction, `out` means that the stock is moved out of the sender warehouse and, `in` means that the stock is moved into the receiver warehouse. The warehouse location ID is used to describe the specific location from which the stock is taken or where the stock shall be moved.  
On their own transactions don't actually change the stock, they have to be booked to actually change the stock of a warehouse.

[*Required parameter*]:

The **order_item_id** parameter relates to the specific item (variation) of an order, for which the transaction shall occur. The **json** parameter contains a single JSON object, describing the quantity, direction and target warehouse location.
Please refer to the [Plentymarkets Dev documentation: REST API POST transaction](https://developers.plentymarkets.com/en-gb/plentymarkets-rest-api/index.html#/Order/post_rest_orders_items__orderItemId__transactions).

[*Example*]:
```json
{
    'orderItemId': 12,
    'quantity': 2,
    'direction': 'out',
    'status': 'regular',
    'warehouseLocationId': 5
}
```

[*Output format*]:

Return a POST request JSON response, if one of the requests fails return the error message.
If the **order_item_id** parameter is not filled the method will return: `{'error': 'missing_parameter'}`.
If the **json** parameter contains an invalid JSON object the method will return: `{'error': 'invalid_json'}`.

#### plenty_api_create_booking <a name=post-booking></a>

This route is used to book in/out all pending transactions of an order.

[*Required parameter*]:

The booking is performed for the order specified by the **order_id** parameter, which contains the integer ID of the order assigned by Plentymarkets. The optional **delivery_note** parameter can contain a delivery note document's identifier, that should be connected to the booking.

[*Output format*]:

Return a POST request JSON response, if one of the requests fails return the error message.

[*Output format*]:

Return a POST request JSON response, if one of the requests fails return the error message.

### PUT requests: <a name='put-requests'></a>

#### Orders <a name='put-oders-section'></a>

#### plenty_api_update_redistribution <a name=update-redistribution></a>

A common scenario that requires updating a redistribution, is the setting of certain events like *order initiation*, *setting the estimated delivery date*, and the *finishing an order* event. In these cases, a JSON is provided that contains the target date and the type specifier.

[*Required parameter*]:

The update is performed for the order specified by the **order_id** parameter, which contains the integer ID of the order assigned by Plentymarkets. The **json** parameter contains a single JSON object, filled with the target field/s and the new value/s.
Please refer to the [Plentymarkets Dev documentation: REST API PUT redistribution](https://developers.plentymarkets.com/en-gb/plentymarkets-rest-api/index.html#/Order/put_rest_redistributions__orderId_).

[*Example*]:
```json
{
    'dates': [
        {
            'typeId': 16,
            'date': '2021-01-01T09:00:01+01:00'
        }
    ]
}
```
[*Output format*]:

Return a POST request JSON response, if one of the requests fails return the error message.
If the **order_id** parameter is not filled the method will return: `{'error': 'missing_parameter'}`.

#### plenty_api_book_incoming_items <a name=book-incoming></a>

Book a certain amount of stock of a specific variation into a location.

[Plentymarkets Developer documentation reference](https://developers.plentymarkets.com/en-gb/plentymarkets-rest-api/index.html#/Item/put_rest_items__id__variations__variationId__stock_bookIncomingItems)

[*Required parameter*]:

The **item_id**, **variation_id**, and **warehouse_id** parameters are required to book the stock for the correct variation and the correct warehouse. The **item_id** parameter contains the Plentymarkets assigned ID of the container of the variation. **variation_id** describes the assigned ID for the specific variation to book stock for and **warehouse_id** contains the assigned ID for the warehouse, that contains the target location, which in case of no given location ID points to the standard location (ID 0) of the warehouse.
The **quantity** field contains the amount of stock to book into the target location for the given variation, it's data type is float and it has to contain a positive value.

[*Optional parameter*]:

Optionally, it is possible to only book in stock for a given **batch** and **bestBeforeDate**.
The dates are accepted in the following formats:
- YEAR-MONTH-DAY                                    (2020-09-16)        [ISO 8601 date format]
- YEAR-MONTH-DAYTHOUR:MINUTE                        (2020-09-16T08:00)
- YEAR-MONTH-DAYTHOUR:MINUTE:SECOND+UTC-OFFSET      (2020-09-16T08:00)  [W3C date format]

By specifying a storage location ID within **location_id**, you can target a specific location instead of the standard location (ID 0).

[*Output format*]:

Return a POST request JSON response, if one of the requests fails return the error message.

#### plenty_api_book_outgoing_items <a name=book-outgoing></a>

Book a certain amount of stock of a specific variation from a location.

[Plentymarkets Developer documentation reference](https://developers.plentymarkets.com/en-gb/plentymarkets-rest-api/index.html#/Item/put_rest_items__id__variations__variationId__stock_bookOutgoingItems)

[*Required parameter*]:

The **item_id**, **variation_id**, and **warehouse_id** parameters are required to book the stock from the correct variation and the correct warehouse. The **item_id** parameter contains the Plentymarkets assigned ID of the container of the variation. **variation_id** describes the assigned ID for the specific variation to book stock for and **warehouse_id** contains the assigned ID for the warehouse, that contains the target location, which in case of no given location ID points to the standard location (ID 0) of the warehouse.
The **quantity** field contains the amount of stock to book from the target location for the given variation, it's data type is float and it has to contain a negative value.

[*Optional parameter*]:

Optionally, it is possible to only book stock from a given **batch** and **bestBeforeDate**.
The dates are accepted in the following formats:
- YEAR-MONTH-DAY                                    (2020-09-16)        [ISO 8601 date format]
- YEAR-MONTH-DAYTHOUR:MINUTE                        (2020-09-16T08:00)
- YEAR-MONTH-DAYTHOUR:MINUTE:SECOND+UTC-OFFSET      (2020-09-16T08:00)  [W3C date format]

By specifying a storage location ID within **location_id**, you can target a specific location instead of the standard location (ID 0).

[*Output format*]:

Return a POST request JSON response, if one of the requests fails return the error message.

#### Items <a name='put-item-section'></a>

#### plenty_api_update_property_selection_name <a name=update-property-selection></a>

Update a property selection name via its name ID.

[*Required parameter*]:

The **name_id** from Plentymarkets needs to be given in order to identify the property selection name that will be updated. The **name** parameter describes the new name value.
Please refer to the [Plentymarkets Dev documentation: REST API PUT transaction](https://developers.plentymarkets.com/en-gb/plentymarkets-rest-api/index.html#/).

**NOTE:** To get the name ID from PlentyMarkets use the function ```plenty_api_get_property_selection_names``` where the ```id``` of each entry represents the name ID of the selection feature in that language.

[*Output format*]:

Return a PUT request JSON response, if one of the requests fails return the error message.
If the **name_id** or **name** field is not filled the method will return: `{'error': 'missing_parameter'}`.

### Extra features <a name=extras></a>

**Activating a progress bar for a CLI application**, you can activate a progress bar for requests with multiple pages, by setting the `cli_progress_bar` class attribute to `True` at any point before making the request. You can deactivate it at any point as well, by setting it to `False` again.  

Example
```python
import plenty_api

plenty = plenty_api.PlentyApi(base_url='...')
plenty.cli_progress_bar = True
variations = plenty.plenty_api_get_variations()
plenty.cli_progress_bar = False
```
