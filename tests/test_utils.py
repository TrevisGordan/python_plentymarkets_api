import copy
import pytest
import requests

from plenty_api.utils import (
    get_route, build_endpoint, check_date_range, parse_date, build_date_range,
    get_utc_offset, build_query_date, create_vat_mapping, date_to_timestamp,
    get_language, shrink_price_configuration, sanity_check_parameter,
    attribute_variation_mapping, list_contains, json_field_filled,
    build_redistribution_transactions, validate_redistribution_template,
    summarize_shipment_packages
)


# ======== SAMPLE INPUT DATA ==========


@pytest.fixture
def sample_date_ranges() -> list:
    samples = [
        {'start': '2020-09-14T08:00:00+02:00',  # Normal date => CORRECT
         'end': '2020-09-15T08:00:00+02:00'},
        {'start': '2020-09-16T08:00:00+02:00',  # End before start => FAIL
         'end': '2020-09-13T08:00:00+02:00'},
        {'start': '2019-09-16T08:00:00+02:00',  # Past date => CORRECT
         'end': '2019-10-13T08:00:00+02:00'},
        {'start': '2021-09-16T08:00:00+02:00',  # Future date => FAIL
         'end': '8021-10-13T08:00:00+02:00'}
    ]
    return samples


@pytest.fixture
def sample_input_date() -> list:
    samples = [
        '2020-09-14',
        '14-09-2020',
        '2020-09-14T08:00Z',
        '2020-09-14T08:00',
        '2020-09-14T08:00:00+02:00',
        'abc',
        ''
    ]
    return samples


@pytest.fixture
def expected_date() -> list:
    expected = [
        str(f'2020-09-14T00:00:00+{get_utc_offset()}'),
        str(f'2020-09-14T00:00:00+{get_utc_offset()}'),
        '2020-09-14T08:00:00+00:00',
        str(f'2020-09-14T08:00:00+{get_utc_offset()}'),
        '2020-09-14T08:00:00+02:00',
        '',
        ''
    ]
    return expected


@pytest.fixture
def sample_date_range_input() -> list:
    samples = [
        {'start': '2020-09-14', 'end': '2020-09-15'},
        {'start': '2020-09-14', 'end': '2020-09-13'},
        {'start': '2020-09-14T08:00Z', 'end': '2020-09-14T09:00Z'},
        {'start': '2020-09-14T08:00:00+02:00',
         'end': '2020-09-14T10:00:30+02:00'},
        {'start': 'abc', 'end': 'def'},
        {'start': '', 'end': ''}
    ]
    return samples


@pytest.fixture
def sample_price_response() -> list:
    samples = [
        {
            'accounts': [],
            'clients': [{'createdAt': '1990-07-09T15:33:46+02:00',
                         'plentyId': 1234, 'salesPriceId': 1,
                         'updatedAt': '1990-07-09T15:33:46+02:00'}],
            'countries': [{'countryId': -1,
                           'createdAt': '1990-07-09T15:33:46+02:00',
                           'salesPriceId': 1,
                           'updatedAt': '1990-07-09T15:33:46+02:00'}],
            'createdAt': '1990-09-05 13:24:53',
            'currencies': [{'createdAt': '1990-07-09T15:33:46+02:00',
                            'currency': 'EUR',
                            'salesPriceId': 1,
                            'updatedAt': '1990-07-09T15:33:46+02:00'},
                           {'createdAt': '1990-07-09T15:33:46+02:00',
                            'currency': 'GBP',
                            'salesPriceId': 1,
                            'updatedAt': '1990-07-09T15:33:46+02:00'}],
            'customerClasses': [{'createdAt': '1990-07-09T15:33:46+02:00',
                                 'customerClassId': -1,
                                 'salesPriceId': 1,
                                 'updatedAt': '1990-07-09T15:33:46+02:00'}],
            'id': 1,
            'interval': 'none',
            'isCustomerPrice': False,
            'isDisplayedByDefault': True,
            'isLiveConversion': False,
            'minimumOrderQuantity': 1,
            'names': [{'createdAt': '1990-09-05T13:24:53+02:00',
                       'lang': 'de',
                       'nameExternal': 'Preis',
                       'nameInternal': 'Preis',
                       'salesPriceId': 1,
                       'updatedAt': '1990-09-05T14:46:34+02:00'},
                      {'createdAt': '1990-09-05T13:24:53+02:00',
                       'lang': 'en',
                       'nameExternal': 'Price',
                       'nameInternal': 'Price',
                       'salesPriceId': 1,
                       'updatedAt': '1990-09-05T14:46:34+02:00'}],
            'position': 0,
            'referrers': [{'createdAt': '1990-07-09T15:33:46+02:00',
                           'referrerId': 0,
                           'salesPriceId': 1,
                           'updatedAt': '1990-07-09T15:33:46+02:00'}],
            'type': 'default',
            'updatedAt': '1990-07-09 15:33:46'
        },
        {}
    ]
    return samples


@pytest.fixture
def expected_date_range() -> list:
    expected = [
        {'start': str(f'2020-09-14T00:00:00+{get_utc_offset()}'),
         'end': str(f'2020-09-15T00:00:00+{get_utc_offset()}')},
        {'start': str(f'2020-09-14T00:00:00+{get_utc_offset()}'),
         'end': str(f'2020-09-13T00:00:00+{get_utc_offset()}')},
        {'start': '2020-09-14T08:00:00+00:00',
         'end': '2020-09-14T09:00:00+00:00'},
        {'start': '2020-09-14T08:00:00+02:00',
         'end': '2020-09-14T10:00:30+02:00'},
        None,
        None
    ]
    return expected


@pytest.fixture
def sample_query_data() -> list:
    samples = [
        {'date_range': {'start': '2020-09-14T08:00:00+02:00',
                        'end': '2020-09-14T10:00:30+02:00'},
         'date_type': 'Creation'},
        {'date_range': {'start': '2020-09-14T08:00:00+02:00',
                        'end': '2020-09-14T10:00:30+02:00'},
         'date_type': 'Payment'},
        {'date_range': {'start': '2020-09-14T08:00:00+02:00',
                        'end': '2020-09-14T10:00:30+02:00'},
         'date_type': 'Change'},
        {'date_range': {'start': '2020-09-14T08:00:00+02:00',
                        'end': '2020-09-14T10:00:30+02:00'},
         'date_type': 'Delivery'},
        {'date_range': {},
         'date_type': 'Creation'},
        {'date_range': {'start': '2020-09-14T08:00:00+02:00',
                        'end': '2020-09-14T10:00:30+02:00'},
         'date_type': ''},
        {'date_range': {'start': '2020-09-14T08:00:00+02:00',
                        'end': '2020-09-14T10:00:30+02:00'},
         'date_type': 'Creation'}
    ]
    return samples


@pytest.fixture
def sample_vat_data() -> list:
    samples = [
        [
            {
                'id': 1,
                'countryId': 1,
                'taxIdNumber': 'DE12345678910',
                'locationId': 1
            },
            {
                'id': 2,
                'countryId': 2,
                'taxIdNumber': 'GB12345678910',
                'locationId': 2
            },
            {
                'id': 3,
                'countryId': 2,
                'taxIdNumber': 'GB12345678910',
                'locationId': 2
            },
            {
                'id': 4,
                'countryId': 3,
                'taxIdNumber': 'FR12345678910',
                'locationId': 3
            },
            {
                'id': 5,
                'countryId': 1,
                'taxIdNumber': 'DE12345678910',
                'locationId': 1
            }
        ],
        [
            ''
        ]
    ]

    return samples


@pytest.fixture
def sample_sanity_check_parameter() -> list:
    samples = [
        {
            'domain': 'manufacturer',
            'query': {},
            'refine': {},
            'additional': [],
            'lang': ''
        },
        {
            'domain': 'variation',
            'query': {},
            'refine': {'id': 1234, 'itemId': 10234},
            'additional': ['properties', 'stock'],
            'lang': 'de'
        },
        {
            'domain': 'item',
            'query': {},
            'refine': {'id': 10234, 'wrong': 'wrong'},
            'additional': ['variations', 'itemImages'],
            'lang': ''
        },
        {
            'domain': 'order',
            'query': {'orderType': 1},
            'refine': {'wrong': 'wrong'},
            'additional': ['wrong', 'addresses', 'documents'],
            'lang': ''
        },
        {
            'domain': 'wrong',
            'query': {'shall': 'not_appear'},
            'refine': {'should': 'be_insignificant'},
            'additional': ['nono'],
            'lang': 'de'
        }
    ]
    return samples


@pytest.fixture
def sample_attributes() -> list:
    samples = [
        [
            {
                'id': 1,
                'position': 1,
                'values': [
                    {
                        'id': 1,
                        'attributeId': 1,
                        'position': 1,
                        'valueNames': [
                            {
                                'lang': 'de',
                                'valueId': '1',
                                'name': 'rot'
                            },
                            {
                                'lang': 'en',
                                'valueId': '1',
                                'name': 'red'
                            }
                        ],
                    },
                    {
                        'id': 2,
                        'attributeId': 1,
                        'position': 2,
                        'valueNames': [
                            {
                                'lang': 'de',
                                'valueId': '2',
                                'name': 'grau'
                            },
                            {
                                'lang': 'en',
                                'valueId': '2',
                                'name': 'grey'
                            }
                        ],
                    },
                    {
                        'id': 3,
                        'attributeId': 1,
                        'position': 3,
                        'valueNames': [
                            {
                                'lang': 'de',
                                'valueId': '2',
                                'name': 'gelb'
                            },
                            {
                                'lang': 'en',
                                'valueId': '2',
                                'name': 'yellow'
                            }
                        ],
                    }
                ]
            }
        ]
    ]

    return samples


@pytest.fixture
def sample_variation_data() -> list:
    samples = [
        {
            'id': 1234,
            'number': 'test-variation_1',
            'variationAttributeValues': [{'attributeId': 1, 'valueId': 1}],
        },
        {
            'id': 2345,
            'number': 'test-variation_2',
            'variationAttributeValues': [{'attributeId': 1, 'valueId': 1}],
        },
        {
            'id': 3456,
            'number': 'test-variation_3',
            'variationAttributeValues': [{'attributeId': 1, 'valueId': 1}],
        },
        {
            'id': 4567,
            'number': 'test-variation_4',
            'variationAttributeValues': [{'attributeId': 1, 'valueId': 2}],
        },
        {
            'id': 5678,
            'number': 'test-variation_5',
            'variationAttributeValues': [{'attributeId': 1, 'valueId': 2}],
        },
        {
            'id': 6789,
            'number': 'test-variation_6',
            'variationAttributeValues': [{'attributeId': 1, 'valueId': 4}],
        },
        {
            'id': 7891,
            'number': 'test-variation_7',
            'variationAttributeValues': [{'attributeId': 1, 'valueId': 4}],
        }
    ]
    return samples


@pytest.fixture
def sample_orders() -> list:
    orders = [
        # Valid order
        {
            "typeId": 1, "ownerId": 3, "plentyId": 1000, "locationId": 1,
            "statusId": 3, "orderItems": [
                {
                    "typeId": 1, "referrerId": 1, "itemVariationId": 1001,
                    "quantity": 1, "countryVatId": 1, "vatField": 0,
                    "vatRate": 19, "orderItemName": "Awesome shoes",
                    "shippingProfileId": 1, "amounts": [
                        {
                            "isSystemCurrency": True, "currency": "EUR",
                            "exchangeRate": 1, "priceOriginalGross": 300,
                            "surcharge": 20, "discount": 10,
                            "isPercentage": True
                        }
                    ],
                    "properties": [{"typeId": 1, "value": "1"}],
                    "orderProperties": [
                        {
                            "propertyId": 4, "value": "image.jpg",
                            "fileUrl": "http://www.example.com/image.jpg"
                        }
                    ]
                }
            ],
            "properties": [{"typeId": 13, "value": "14"}],
            "addressRelations": [{ "typeId": 1, "addressId": 18 }],
            "relations": [
                {
                    "referenceType": "contact", "referenceId": 118,
                    "relation": "receiver"
                }
            ]
        },
        # Invalid order - invalid type ID
        {
            "typeId": 100, "ownerId": 3, "plentyId": 1000, "locationId": 1,
            "statusId": 3, "orderItems": [
                {
                    "typeId": 1, "referrerId": 1, "itemVariationId": 1001,
                    "countryVatId": 1, "vatField": 0, "vatRate": 19,
                    "orderItemName": "Awesome shoes", "shippingProfileId": 1,
                    "amounts": [
                        {
                            "isSystemCurrency": True, "currency": "EUR",
                            "exchangeRate": 1, "priceOriginalGross": 300,
                            "surcharge": 20, "discount": 10,
                            "isPercentage": True
                        }
                    ],
                    "properties": [{"typeId": 1, "value": "1"}],
                    "orderProperties": [
                        {
                            "propertyId": 4, "value": "image.jpg",
                            "fileUrl": "http://www.example.com/image.jpg"
                        }
                    ]
                }
            ],
            "properties": [{"typeId": 13, "value": "14"}],
            "addressRelations": [{ "typeId": 1, "addressId": 18 }],
            "relations": [
                {
                    "referenceType": "contact", "referenceId": 118,
                    "relation": "receiver"
                }
            ]
        },
        # Invalid order - empty order Items
        {
            "typeId": 15, "ownerId": 3, "plentyId": 1000, "locationId": 1,
            "statusId": 3, "orderItems": [{}],
            "properties": [{"typeId": 13, "value": "14"}],
            "addressRelations": [{ "typeId": 1, "addressId": 18 }],
            "relations": [
                {
                    "referenceType": "contact", "referenceId": 118,
                    "relation": "receiver"
                }
            ]
        },
        # Invalid order - missing attribute (plenty Id)
        {
            "typeId": 3, "ownerId": 3, "locationId": 1,
            "statusId": 3, "orderItems": [
                {
                    "typeId": 1, "referrerId": 1, "itemVariationId": 1001,
                    "countryVatId": 1, "vatField": 0, "vatRate": 19,
                    "orderItemName": "Awesome shoes", "shippingProfileId": 1,
                    "amounts": [
                        {
                            "isSystemCurrency": True, "currency": "EUR",
                            "exchangeRate": 1, "priceOriginalGross": 300,
                            "surcharge": 20, "discount": 10,
                            "isPercentage": True
                        }
                    ],
                    "properties": [{"typeId": 1, "value": "1"}],
                    "orderProperties": [
                        {
                            "propertyId": 4, "value": "image.jpg",
                            "fileUrl": "http://www.example.com/image.jpg"
                        }
                    ]
                }
            ],
            "properties": [{"typeId": 13, "value": "14"}],
            "addressRelations": [{ "typeId": 1, "addressId": 18 }],
            "relations": [
                {
                    "referenceType": "contact", "referenceId": 118,
                    "relation": "receiver"
                }
            ]
        },
        # Empty order
        {}
    ]
    return orders


@pytest.fixture
def sample_redistribution():
    order = {
        "id": 1,
        "plentyId": 12345,
        "typeId": 15,
        "relations": [
            {
                "orderId": 1,
                "referenceType": "warehouse",
                "referenceId": 105,
                "relation": "sender"
            },
            {
                "orderId": 1,
                "referenceType": "warehouse",
                "referenceId": 107,
                "relation": "receiver"
            }
        ],
        "orderItems": [
            {
                "id": 2,
                "orderId": 1,
                "typeId": 1,
                "itemVariationId": 1234,
                "quantity": 10,
                "orderItemName": "test_1"
            },
            {
                "id": 3,
                "orderId": 1,
                "typeId": 1,
                "itemVariationId": 2345,
                "quantity": 12,
                "orderItemName": "test_2",
            }
        ]
    }
    return order


@pytest.fixture
def sample_redistribution_without_transactions():
    variations = [
        {
            'variation_id': 1234,
            'total_quantity': 10,
            'name': 'test_1'
        },
        {
            'variation_id': 2345,
            'total_quantity': 12,
            'name': 'test_2'
        }
    ]
    return variations


@pytest.fixture
def sample_redistribution_with_outgoing_transactions(
        sample_redistribution_without_transactions: dict):
    sample = sample_redistribution_without_transactions
    sample[0]['locations'] = [{'location_id': 1, 'quantity': 10}]
    sample[1]['locations'] = [
        {'location_id': 2, 'quantity': 6}, {'location_id': 3, 'quantity': 6}
    ]
    return sample


@pytest.fixture
def sample_redistribution_with_both_transactions(
        sample_redistribution_with_outgoing_transactions: dict):
    sample = sample_redistribution_with_outgoing_transactions
    sample[0]['locations'][0]['targets'] = [
        {'location_id': 110, 'quantity': 10}
    ]
    sample[1]['locations'][0]['targets'] = [
        {'location_id': 111, 'quantity': 6}
    ]
    sample[1]['locations'][1]['targets'] = [
        {'location_id': 112, 'quantity': 3},
        {'location_id': 113, 'quantity': 3}
    ]
    return sample


@pytest.fixture
def sample_redistribution_with_extra_attributes(
        sample_redistribution_with_outgoing_transactions: dict):
    sample = sample_redistribution_with_outgoing_transactions
    sample[0]['batch'] = '1234_batch'
    sample[1]['batch'] = '2345_batch'
    sample[0]['bestBeforeDate'] = '2020-01-03T15:00:00+02:00'
    sample[1]['bestBeforeDate'] = '2020-01-03T15:00:00+02:00'
    sample[0]['identification'] = '1234_identification'
    sample[1]['identification'] = '2345_identification'
    sample[0]['amounts'] = 10
    sample[1]['amounts'] = 20
    return sample


# ======== EXPECTED DATA ==========


@pytest.fixture
def expected_date_query() -> list:
    expected = [
        'createdAtFrom=2020-09-14T08%3A00%3A00%2B02%3A00' +
        '&createdAtTo=2020-09-14T10%3A00%3A30%2B02%3A00',
        'paidAtFrom=2020-09-14T08%3A00%3A00%2B02%3A00' +
        '&paidAtTo=2020-09-14T10%3A00%3A30%2B02%3A00',
        'updatedAtFrom=2020-09-14T08%3A00%3A00%2B02%3A00' +
        '&updatedAtTo=2020-09-14T10%3A00%3A30%2B02%3A00',
        'outgoingItemsBookedAtFrom=2020-09-14T08%3A00%3A00%2B02%3A00' +
        '&outgoingItemsBookedAtTo=2020-09-14T10%3A00%3A30%2B02%3A00',
        '',
        '',
        'createdAtFrom=2020-09-14T08%3A00%3A00%2B02%3A00' +
        '&createdAtTo=2020-09-14T10%3A00%3A30%2B02%3A00'
    ]
    return expected


@pytest.fixture
def expected_query_attributes() -> list:
    expected = [
        '&with%5B%5D=documents',
        '&with%5B%5D=documents&with%5B%5D=comments&orderType=1,4&referrerId=1',
        '&with%5B%5D=shippingPackages&countryId=1',
        '&with%5B%5D=documents'
    ]
    return expected


@pytest.fixture
def expected_prices() -> list:
    expected = [
        {
            'id': 1,
            'type': 'default',
            'position': 0,
            'names': {'de': 'Preis', 'en': 'Price'},
            'referrers': [0],
            'accounts': [],
            'clients': [1234],
            'countries': [-1],
            'currencies': ['EUR', 'GBP'],
            'customerClasses': [-1]
         }, {}
    ]
    return expected


@pytest.fixture
def expected_sanity_check_query() -> list:
    expected = [
        # empty query
        {},
        # domain: variation
        # valid domain, 2 refine, 2 additional, lang all valid arguments
        {'id': 1234, 'itemId': 10234,
         'with': 'properties,stock', 'lang': 'de'},
        # domain: item
        # valid domain 2 refine, 1 additional, 1 invalid refine
        {'id': 10234, 'with': 'variations,itemImages'},
        # domain: order
        # invalid & valid arguments, but preexisting query
        # check if the 'additional' field is handled differently for 'order'
        {'orderType': 1, 'with[]': ['addresses', 'documents']},
        # domain: wrong
        # invalid domain
        {}
    ]
    return expected


@pytest.fixture
def expected_attribute_variation_map() -> list:
    expected = [
        [
            {
                'id': 1,
                'position': 1,
                'values': [
                    {
                        'id': 1,
                        'attributeId': 1,
                        'position': 1,
                        'valueNames': [
                            {'lang': 'de', 'valueId': '1', 'name': 'rot'},
                            {'lang': 'en', 'valueId': '1', 'name': 'red'}
                        ],
                        'linked_variations': [
                            1234, 2345, 3456
                        ]
                    },
                    {
                        'id': 2,
                        'attributeId': 1,
                        'position': 2,
                        'valueNames': [
                            {'lang': 'de', 'valueId': '2', 'name': 'grau'},
                            {'lang': 'en', 'valueId': '2', 'name': 'grey'}
                        ],
                        'linked_variations': [
                            4567, 5678
                        ]
                    },
                    {
                        'id': 3,
                        'attributeId': 1,
                        'position': 3,
                        'valueNames': [
                            {'lang': 'de', 'valueId': '2', 'name': 'gelb'},
                            {'lang': 'en', 'valueId': '2', 'name': 'yellow'}
                        ]
                    }
                ]
            }
        ],
        # Missing variation data
        [
            {
                'id': 1,
                'position': 1,
                'values': [
                    {
                        'id': 1,
                        'attributeId': 1,
                        'position': 1,
                        'valueNames': [
                            {'lang': 'de', 'valueId': '1', 'name': 'rot'},
                            {'lang': 'en', 'valueId': '1', 'name': 'red'}
                        ],
                    },
                    {
                        'id': 2,
                        'attributeId': 1,
                        'position': 2,
                        'valueNames': [
                            {'lang': 'de', 'valueId': '2', 'name': 'grau'},
                            {'lang': 'en', 'valueId': '2', 'name': 'grey'}
                        ],
                    },
                    {
                        'id': 3,
                        'attributeId': 1,
                        'position': 3,
                        'valueNames': [
                            {'lang': 'de', 'valueId': '2', 'name': 'gelb'},
                            {'lang': 'en', 'valueId': '2', 'name': 'yellow'}
                        ],
                    }
                ]
            }
        ],
        # Missing attribute dat
        {}
    ]
    return expected


# ======== UNIT TESTS ==========


def test_get_route() -> None:
    sample_data = ['order', 'item', 'ITEMS', 'oRdErS', 'wrong', '',
                   'manufacturer', 'manfacturer', 'attribute']
    result = []
    expected = ['/rest/orders', '/rest/items', '/rest/items', '/rest/orders',
                '', '', '/rest/items/manufacturers', '',
                '/rest/items/attributes']

    for domain in sample_data:
        result.append(get_route(domain=domain))

    assert expected == result


def test_build_endpoint() -> None:
    sample_data = [
        {'url': 'https://test.plentymarkets-cloud01.com',
         'route': '/rest/orders'},
        {'url': 'https://test.plentymarkets-cloud01.com',
         'route': '/rest/orders'},
        {'url': 'invalid.com',
         'route': '/rest/orders'},
        {'url': 'https://test.plentymarkets-cloud01.com',
         'route': '/rest/invalid'},
        {'url': '',
         'route': '/rest/orders'},
        {'url': 'https://test.plentymarkets-cloud01.com',
         'route': ''}
    ]

    expected = ['https://test.plentymarkets-cloud01.com/rest/orders',
                'https://test.plentymarkets-cloud01.com/rest/orders', '', '',
                '', '']
    result = []

    for sample in sample_data:
        result.append(build_endpoint(url=sample['url'],
                                     route=sample['route']))

    assert expected == result


def test_check_date_range(sample_date_ranges: list) -> None:
    expected = [True, False, True, False]
    result = []

    for sample in sample_date_ranges:
        result.append(check_date_range(date_range=sample))

    assert expected == result


def test_parse_date(sample_input_date: list,
                    expected_date: list) -> None:
    result = []

    for sample in sample_input_date:
        result.append(parse_date(date=sample))

    assert expected_date == result


def test_build_date_range(sample_date_range_input: list,
                          expected_date_range: list) -> None:
    result = []
    for sample in sample_date_range_input:
        result.append(build_date_range(start=sample['start'],
                                       end=sample['end']))

    assert expected_date_range == result


def test_F_date(sample_query_data: list,
                expected_date_query: list) -> None:
    result = []

    for sample in sample_query_data:
        query = build_query_date(date_range=sample['date_range'],
                                 date_type=sample['date_type'])
        req = requests.Request('POST', 'https://httpbin.org/get', params=query)
        prepped = req.prepare()
        result += (prepped.url.split('?')[1:])
        if not prepped.url.split('?')[1:]:
            result.append('')
    assert expected_date_query == result


def test_create_vat_mapping(sample_vat_data: list) -> None:
    subset = [[], [1, 2]]
    expected = [
        {
            '1': {'config': ['1', '5'], 'TaxId': 'DE12345678910'},
            '2': {'config': ['2', '3'], 'TaxId': 'GB12345678910'},
            '3': {'config': ['4'], 'TaxId': 'FR12345678910'}
        },
        {
            '1': {'config': ['1', '5'], 'TaxId': 'DE12345678910'},
            '2': {'config': ['2', '3'], 'TaxId': 'GB12345678910'}
        },
        {},
        {}
    ]
    result = []

    for sample in sample_vat_data:
        for sub in subset:
            result.append(create_vat_mapping(data=sample, subset=sub))

    assert expected == result


def test_date_to_timestamp() -> None:
    samples = ['2020-08-01', '2020-08-01T15:00', '2020-08-01T15:00:00+02:00',
               '01-08-2020', '2020.08.01', 'abc', '']
    expected = [1596232800, 1596286800, 1596290400,
                -1, 1596232800, -1, -1]
    result = []

    for sample in samples:
        result.append(date_to_timestamp(date=sample))

    assert expected == result


def test_get_language() -> None:
    samples = ['de', 'EN', 'fR', 'Greece', '12', '']
    expected = ['de', 'en', 'fr', 'INVALID_LANGUAGE',
                'INVALID_LANGUAGE', 'INVALID_LANGUAGE']
    result = []

    for sample in samples:
        result.append(get_language(lang=sample))

    assert expected == result


def test_shrink_price_configuration(sample_price_response: list,
                                    expected_prices: list) -> None:
    result = []

    for sample in sample_price_response:
        result.append(shrink_price_configuration(data=sample))

    assert expected_prices == result


def test_sanity_check_parameter(sample_sanity_check_parameter: list,
                                expected_sanity_check_query: list) -> None:
    result = []

    for sample in sample_sanity_check_parameter:
        result.append(sanity_check_parameter(domain=sample['domain'],
                                             query=sample['query'],
                                             refine=sample['refine'],
                                             additional=sample['additional'],
                                             lang=sample['lang']))

    assert expected_sanity_check_query == result


def test_attribute_variation_mapping(sample_attributes: list,
                                     sample_variation_data: list,
                                     expected_attribute_variation_map: list):
    result = []

    for sample in sample_attributes:
        first = sample
        second = copy.deepcopy(sample)
        # Test with variations and attribute
        result.append(attribute_variation_mapping(
            variation=sample_variation_data, attribute=first))
        # Test with attributes and without variations
        result.append(attribute_variation_mapping(
            variation=None, attribute=second))

    # Test without attributes and without variations
    result.append(attribute_variation_mapping(variation=None, attribute=None))

    assert expected_attribute_variation_map == result


def test_list_contains():
    l1 = [
        [1, 2, 3],
        ['a', 'b', 'c'],
        ['aba', 'bcb', 'cdc'],
        ['a', 'b', 'c'],
        ['aba', 'bcb'],
        []
    ]
    l2 = [
        [1, 4, 5, 6, 2, 3],
        ['c', 'b', 'a'],
        ['aba', 'bcb', 'cdc'],
        ['a', 'c', 'd'],
        [],
        [1, 2, 3]
    ]
    result = []
    expected = [True, True, True, False, False, True]

    for lists in zip(l1, l2):
        result.append(list_contains(search_list=lists[0],
                                    target_list=lists[1]))

    assert expected == result


def test_json_field_filled():
    sample = [
        (1, 0), (1.0, 1), ('test', 2), ({'test': 1}, 3),
        ([{'test': 1}], 4), ('test', 0), (1, 2), ({}, 3), ([{}], 4)
    ]
    expected = [True, True, True, True, True, False, False, False, False]
    result = []

    for json_field, field_type in sample:
        result.append(json_field_filled(json_field=json_field,
                                        field_type=field_type))

    assert expected == result


def describe_build_redistribution_transactions():
    def with_no_outgoing_or_incoming_transaction(
            sample_redistribution: dict,
            sample_redistribution_without_transactions: list):
        result = build_redistribution_transactions(
            order=sample_redistribution,
            variations=sample_redistribution_without_transactions)

        assert ([], []) == result

    def with_outgoing_transactions(
            sample_redistribution: dict,
            sample_redistribution_with_outgoing_transactions: list):
        expected = (
            [
                {
                    'quantity': 10, 'direction': 'out', 'status': 'regular',
                    'warehouseLocationId': 1, 'orderItemId': 2
                },
                {
                    'quantity': 6, 'direction': 'out', 'status': 'regular',
                    'warehouseLocationId': 2, 'orderItemId': 3
                },
                {
                    'quantity': 6, 'direction': 'out', 'status': 'regular',
                    'warehouseLocationId': 3, 'orderItemId': 3
                }
            ],
            []
        )

        result = build_redistribution_transactions(
            order=sample_redistribution,
            variations=sample_redistribution_with_outgoing_transactions)

        assert expected == result

    def with_outgoing_and_incoming_transactions(
            sample_redistribution: dict,
            sample_redistribution_with_both_transactions: list):
        expected = (
            [
                {
                    'quantity': 10, 'direction': 'out', 'status': 'regular',
                    'warehouseLocationId': 1, 'orderItemId': 2
                },
                {
                    'quantity': 6, 'direction': 'out', 'status': 'regular',
                    'warehouseLocationId': 2, 'orderItemId': 3
                },
                {
                    'quantity': 6, 'direction': 'out', 'status': 'regular',
                    'warehouseLocationId': 3, 'orderItemId': 3
                }
            ],
            [
                {
                    'quantity': 10, 'direction': 'in', 'status': 'regular',
                    'warehouseLocationId': 110, 'orderItemId': 2
                },
                {
                    'quantity': 6, 'direction': 'in', 'status': 'regular',
                    'warehouseLocationId': 111, 'orderItemId': 3
                },
                {
                    'quantity': 3, 'direction': 'in', 'status': 'regular',
                    'warehouseLocationId': 112, 'orderItemId': 3
                },
                {
                    'quantity': 3, 'direction': 'in', 'status': 'regular',
                    'warehouseLocationId': 113, 'orderItemId': 3
                }
            ]
        )

        result = build_redistribution_transactions(
            order=sample_redistribution,
            variations=sample_redistribution_with_both_transactions)

        assert expected == result

    def with_extra_attributes(
            sample_redistribution: dict,
            sample_redistribution_with_extra_attributes: list):
        expected = (
            [
                {
                    'quantity': 10, 'direction': 'out', 'status': 'regular',
                    'warehouseLocationId': 1, 'batch': '1234_batch',
                    'bestBeforeDate': '2020-01-03T15:00:00+02:00',
                    'identification': '1234_identification', 'orderItemId': 2
                },
                {
                    'quantity': 6, 'direction': 'out', 'status': 'regular',
                    'warehouseLocationId': 2, 'batch': '2345_batch',
                    'bestBeforeDate': '2020-01-03T15:00:00+02:00',
                    'identification': '2345_identification', 'orderItemId': 3
                },
                {
                    'quantity': 6, 'direction': 'out', 'status': 'regular',
                    'warehouseLocationId': 3, 'batch': '2345_batch',
                    'bestBeforeDate': '2020-01-03T15:00:00+02:00',
                    'identification': '2345_identification', 'orderItemId': 3
                }
            ],
            []
        )

        result = build_redistribution_transactions(
            order=sample_redistribution,
            variations=sample_redistribution_with_extra_attributes)

        assert expected == result


def describe_validate_redistribution_template():
    def with_valid_template_without_transactions(
            sample_redistribution_without_transactions):
        sample = sample_redistribution_without_transactions
        template = {'variations': sample}
        assert True is validate_redistribution_template(template)

    def with_valid_template_with_outgoing_transactions(
            sample_redistribution_with_outgoing_transactions):
        sample = sample_redistribution_with_outgoing_transactions
        template = {'variations': sample}
        assert True is validate_redistribution_template(template)

    def with_invalid_template_with_outgoing_transactions(
            sample_redistribution_with_outgoing_transactions):
        sample = sample_redistribution_with_outgoing_transactions
        # Change the quantity of one of the locations
        sample[0]['locations'][0]['quantity'] = 8
        template = {'variations': sample}
        assert False is validate_redistribution_template(template)

    def with_valid_transaction_with_both_transactions(
            sample_redistribution_with_both_transactions):
        sample = sample_redistribution_with_both_transactions
        template = {'variations': sample}
        assert True is validate_redistribution_template(template)

    def with_invalid_transaction_with_both_transactions(
            sample_redistribution_with_both_transactions):
        sample = sample_redistribution_with_both_transactions
        # Change the quantity of one of the targets
        sample[1]['locations'][1]['targets'][0]['quantity'] = 8
        template = {'variations': sample}
        assert False is validate_redistribution_template(template)


def describe_summarize_shipment_packages():
    def with_empty_response():
        expect = {}
        assert summarize_shipment_packages(response=[],
                                           mode='minimal') == expect

    def with_one_package_minimal():
        response = [
            {
                'createdAt': '1999-01-01 18:00:00', 'id': 12345,
                'isClosed': False, 'labelPath': '', 'noOfPackage': 1,
                'noOfPackagesInPallet': '1 of 1', 'orderId': 12345,
                'packageId': 3, 'packageNumber': '', 'packageSscc': '',
                'packageType': 0, 'palletId': 12345, 'returnPackageNumber': '',
                'updatedAt': '1999-01-01 18:00:00', 'volume': 0, 'weight': 325,
                'content': [
                    {
                        'attributeValues': 'Orange', 'batch': '',
                        'bestBeforeDate': '', 'id': 12345,
                        'itemId': 1234, 'itemName': 'test_product_1',
                        'itemNetWeight': '0', 'itemQuantity': 1,
                        'itemWeight': '220', 'orderItemId': 23456,
                        'orderItemName': 'test_product', 'packageId': 23826,
                        'serialNumber': None, 'variationId': 1234,
                        'variationNumber': 'test_sku_1'
                    },
                ]
             },
        ]
        expect = {
            'content': {
                1234: {
                    'totalQuantity': 1,
                    'packages': {
                        12345: {23826: {'packageNo': 1, 'quantity': 1}}
                    }
                }
            },
            'pallets': {12345: [23826]}
        }
        assert summarize_shipment_packages(response=response,
                                           mode='minimal') == expect

    def with_one_package_full():
        response = [
            {
                'createdAt': '1999-01-01 18:00:00', 'id': 12345,
                'isClosed': False, 'labelPath': '', 'noOfPackage': 1,
                'noOfPackagesInPallet': '1 of 1', 'orderId': 12345,
                'packageId': 3, 'packageNumber': '', 'packageSscc': '',
                'packageType': 0, 'palletId': 12345, 'returnPackageNumber': '',
                'updatedAt': '1999-01-01 18:00:00', 'volume': 0, 'weight': 325,
                'content': [
                    {
                        'attributeValues': 'Orange', 'batch': '',
                        'bestBeforeDate': '', 'id': 12345,
                        'itemId': 1234, 'itemName': 'test_product_1',
                        'itemNetWeight': '0', 'itemQuantity': 1,
                        'itemWeight': '220', 'orderItemId': 23456,
                        'orderItemName': 'test_product', 'packageId': 23826,
                        'serialNumber': None, 'variationId': 1234,
                        'variationNumber': 'test_sku_1'
                    },
                ]
             },
        ]
        expect = {
            'content': {
                1234: {
                    'totalQuantity': 1,
                    'attributeValues': 'Orange', 'batch': '',
                    'bestBeforeDate': '', 'itemName': 'test_product_1',
                    'itemNetWeight': '0', 'itemWeight': '220',
                    'orderItemId': 23456, 'orderItemName': 'test_product',
                    'serialNumber': None, 'variationId': 1234,
                    'variationNumber': 'test_sku_1',
                    'packages': {
                        12345: {
                            23826: {
                                'packageNo': 1, 'quantity': 1,
                                'createdAt': '1999-01-01 18:00:00',
                                'isClosed': False, 'labelPath': '',
                                'noOfPackagesInPallet': '1 of 1',
                                'packageId': 3, 'packageNumber': '',
                                'packageSscc': '', 'packageType': 0,
                                'returnPackageNumber': '',
                                'updatedAt': '1999-01-01 18:00:00',
                                'volume': 0, 'weight': 325,
                            }
                        }
                    }
                }
            },
            'pallets': {12345: [23826]}
        }
        assert summarize_shipment_packages(response=response,
                                           mode='full') == expect

    def with_multiple_packages_minimal():
        response = [
            {
                'createdAt': '1999-01-01 18:00:00', 'id': 23826,
                'isClosed': False, 'labelPath': '', 'noOfPackage': 1,
                'noOfPackagesInPallet': '1 of 2', 'orderId': 12345,
                'packageId': 3, 'packageNumber': '', 'packageSscc': '',
                'packageType': 0, 'palletId': 12345, 'returnPackageNumber': '',
                'updatedAt': '1999-01-01 18:00:00', 'volume': 0, 'weight': 325,
                'content': [
                    {
                        'attributeValues': 'Orange', 'batch': '',
                        'bestBeforeDate': '', 'id': 12345,
                        'itemId': 1234, 'itemName': 'test_product_1',
                        'itemNetWeight': '0', 'itemQuantity': 1,
                        'itemWeight': '220', 'orderItemId': 23456,
                        'orderItemName': 'test_product', 'packageId': 23826,
                        'serialNumber': None, 'variationId': 1234,
                        'variationNumber': 'test_sku_1'
                    },
                ]
            },
            {
                'createdAt': '1999-01-01 18:05:00', 'id': 23827,
                'isClosed': False, 'labelPath': '', 'noOfPackage': 2,
                'noOfPackagesInPallet': '2 of 2', 'orderId': 12345,
                'packageId': 3, 'packageNumber': '', 'packageSscc': '',
                'packageType': 0, 'palletId': 12345, 'returnPackageNumber': '',
                'updatedAt': '1999-01-01 18:05:00', 'volume': 0, 'weight': 325,
                'content': [
                    {
                        'attributeValues': 'Orange', 'batch': '',
                        'bestBeforeDate': '', 'id': 12345,
                        'itemId': 1234, 'itemName': 'test_product_1',
                        'itemNetWeight': '0', 'itemQuantity': 1,
                        'itemWeight': '220', 'orderItemId': 23456,
                        'orderItemName': 'test_product', 'packageId': 23827,
                        'serialNumber': None, 'variationId': 1234,
                        'variationNumber': 'test_sku_1'
                    },
                    {
                        'attributeValues': 'Blue', 'batch': '',
                        'bestBeforeDate': '', 'id': 12346,
                        'itemId': 1234, 'itemName': 'test_product_2',
                        'itemNetWeight': '0', 'itemQuantity': 2,
                        'itemWeight': '220', 'orderItemId': 23457,
                        'orderItemName': 'test_product', 'packageId': 23827,
                        'serialNumber': None, 'variationId': 1235,
                        'variationNumber': 'test_sku_2'
                    }
                ]
            },
            {
                'createdAt': '1999-01-01 18:10:00', 'id': 23828,
                'isClosed': False, 'labelPath': '', 'noOfPackage': 1,
                'noOfPackagesInPallet': '1 of 1', 'orderId': 12345,
                'packageId': 3, 'packageNumber': '', 'packageSscc': '',
                'packageType': 0, 'palletId': 12346, 'returnPackageNumber': '',
                'updatedAt': '1999-01-01 18:10:00', 'volume': 0, 'weight': 325,
                'content': [
                    {
                        'attributeValues': 'Red', 'batch': '',
                        'bestBeforeDate': '', 'id': 12347,
                        'itemId': 1234, 'itemName': 'test_product_3',
                        'itemNetWeight': '0', 'itemQuantity': 3,
                        'itemWeight': '220', 'orderItemId': 23458,
                        'orderItemName': 'test_product', 'packageId': 23828,
                        'serialNumber': None, 'variationId': 1236,
                        'variationNumber': 'test_sku_3'
                    },
                    {
                        'attributeValues': 'Blue', 'batch': '',
                        'bestBeforeDate': '', 'id': 12348,
                        'itemId': 1234, 'itemName': 'test_product_2',
                        'itemNetWeight': '0', 'itemQuantity': 4,
                        'itemWeight': '220', 'orderItemId': 23457,
                        'orderItemName': 'test_product', 'packageId': 23828,
                        'serialNumber': None, 'variationId': 1235,
                        'variationNumber': 'test_sku_2'
                    }
                ]
            },
        ]
        expect = {
            'content': {
                1234: {
                    'totalQuantity': 2,
                    'packages': {
                        12345: {
                            23826: {'packageNo': 1, 'quantity': 1},
                            23827: {'packageNo': 2, 'quantity': 1}
                        }
                    }
                },
                1235: {
                    'totalQuantity': 6,
                    'packages': {
                        12345: {
                            23827: {'packageNo': 2, 'quantity': 2}
                        },
                        12346: {
                            23828: {'packageNo': 1, 'quantity': 4}
                        }
                    }
                },
                1236: {
                    'totalQuantity': 3,
                    'packages': {
                        12346: {23828: {'packageNo': 1, 'quantity': 3}}
                    }
                }
            },
            'pallets': {12345: [23826, 23827], 12346: [23828]}
        }
        assert summarize_shipment_packages(response=response,
                                           mode='minimal') == expect

