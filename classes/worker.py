import threading
import random
import string
import re

import requests
import names
import urllib3


BASE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/76.0.3809.100 Safari/537.36',
    'DNT': '1'
}
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Worker(threading.Thread):
    def __init__(self, settings, task):
        super().__init__()
        if not settings:
            raise Exception('Missing settings')
        if not task:
            raise Exception('Missing task')
        self.settings = settings
        self.task = task

        self.s = requests.Session()
        self.s.headers = BASE_HEADERS
        self.s.verify = False

        self.r_first_name = ''
        self.r_last_name = ''
        self.r_email = ''
        self.r_password = ''

        self.order_id = int()
        self.dummy_order_item_id = int()

        self.user_id = int()
        self.address_id = int()

    def create_account(self):
        name = names.get_full_name()
        self.r_first_name = name.split(' ')[0]
        self.r_last_name = name.split(' ')[1]
        self.r_email = self.r_first_name[0] + self.r_last_name + str(random.randrange(99)) + self.settings['catchall']
        self.r_email = self.r_email.lower()
        self.r_password = 'Passw0rd' + str(random.randrange(99))
        print('pass: {}'.format(self.r_password))
        print('creating account - F: {} L: {}'.format(name.split(' ')[0], name.split(' ')[1]))
        print('getting auth token from login page')
        try:
            r = self.s.get(
                url='https://hotwheelscollectors.mattel.com/webapp/wcs/stores/servlet/AjaxLogonView',
                params={
                    'catalogId': self.settings['catalog_id'],
                    'storeId': self.settings['store_id']
                }
            )
        except requests.exceptions.ConnectionError:
            print('unable to reach server while getting auth token from login page')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            print('bad status {} while getting auth token from login page'.format(r.status_code))
            return False
        try:
            auth_token = re.findall('<input type="hidden" name="authToken" value="(.*)" id="WC_UserRegistrationAddForm_FormInput_authToken_In_Register_1"/>', r.text)[0]
        except (KeyError, IndexError):
            print('unable to find auth token in page source')
            return False
        try:
            r = self.s.post(
                url='https://hotwheelscollectors.mattel.com/shop/UserRegistrationAdd',
                headers={
                    **BASE_HEADERS
                },
                data={
                    'authToken': auth_token,
                    'myAcctMain': '1',
                    'new': 'Y',
                    'storeId': self.settings['store_id'],
                    'catalogId': self.settings['catalog_id'],
                    'rememberMe': 'true',
                    'sourceName': 'WebCreateAccount',
                    'URL': 'AjaxLogonForm?logonId*=&firstName*=&lastName*=&address1*=&address2*=&city*=&country'
                           '*=&state*=&zipCode*=&email1*=&phone1*=&register_type=user',
                    'URLOrg': 'AjaxLogonForm?usr_logonId*=&usr_firstName*=&usr_lastName*=&usr_address1*=&usr_address2'
                              '*=&usr_city*=&usr_country*=&usr_state*=&usr_zipCode*=&usr_email1*=&usr_phone1'
                              '*=&org_orgEntityName*=&org_address1*=&org_address2*=&org_city*=&org_country'
                              '*=&org_state*=&org_zipCode*=&org_email1*=&org_phone1*=&register_type=organization',
                    'receiveSMSNotification': 'false',
                    'receiveSMS': 'false',
                    'errorViewName': 'AjaxLogonView',
                    'page': 'account',
                    'registerType': 'G',
                    'primary': 'true',
                    'isBuyerUser': 'true',
                    'demographicField5': 'on',
                    'challengeQuestion': '-',
                    'challengeAnswer': '-',
                    'usr_profileType': 'B',
                    'addressType': 'PARTY',
                    'receiveEmail': 'false',
                    'AddressForm_FieldsOrderByLocale': 'first_name,LAST_NAME,EMAIL1_HIDDEN',
                    'firstName': self.r_first_name,
                    'lastName': self.r_last_name,
                    'email1': self.r_email,
                    'logonIdDisplay': self.r_email,
                    'logonId': '{}|{}'.format(self.settings['store_id'], self.r_email),
                    'logonIdVerifyDisplay': self.r_email,
                    'logonIdVerify': '{}|{}'.format(self.settings['store_id'], self.r_email),
                    'logonPassword': self.r_password,
                    'logonPasswordVerify': self.r_password,
                    'user_name': self.r_email.split('@')[0].lower(),
                    'userName': '',  # left blank,
                }
            )
        except requests.exceptions.ConnectionError:
            print('unable to reach server')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            print('bad status code {} while creating account'.format(r.status_code))
            return False
        print('generated account: {}:{}'.format(self.r_email, self.r_password))
        return True

    def go_to_shop(self):
        """
        Purpose here is really to just populate cookies, it might be an optional step. Further down the line I'd like
        it to retrieve products that are in stock so that we can automatically parse out a dummy item to ATC
        :return:
        """
        print('going to shop main page')
        try:
            r = self.s.get(
                url='https://hotwheelscollectors.mattel.com/shop/en-us/hwc/shop'
            )
        except requests.exceptions.ConnectionError:
            print('unable to reach server while going to shop')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            print('bad status code {} while going to shop'.format(r.status_code))
            return False
        return True

    def add_dummy_item(self):
        print('adding dummy item to cart')
        try:
            r = self.s.post(
                url='https://hotwheelscollectors.mattel.com/shop/AjaxRESTOrderItemAdd',
                data={
                    'storeId': self.settings['store_id'],
                    'catalogId': self.settings['catalog_id'],
                    'langId': '-1',
                    'catEntryId_1': self.settings['dummy_item_cat_id'],
                    'quantity_1': '1',
                    'isFromQV': 'true',
                    'requesttype': 'ajax'
                }
            )
        except requests.exceptions.ConnectionError:
            print('unable to reach server while adding dummy item to cart')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            print('bad status {} while adding dummy item to cart'.format(r.status_code))
            return False
        print('parsing order item id and order id')
        self.order_id = re.findall('"orderId": "(.*)",', r.text)[0]
        self.dummy_order_item_id = re.findall('"orderItemId": "(.*)"', r.text)[0]
        print('order id: {}, dummy order item id: {}'.format(self.order_id, self.dummy_order_item_id))
        print('mini cart display')
        try:
            r = self.s.post(
                url='https://hotwheelscollectors.mattel.com/shop/MiniShopCartDisplayView',
                params={
                    'storeId': self.settings['store_id'],
                    'catalogId': self.settings['catalog_id'],
                    'langId': '-1'
                },
                data={
                    'addedOrderItemId': self.dummy_order_item_id,
                    'deleteCartCookie': 'true',
                    'objectId': '',
                    'requesttype': 'ajax'
                }
            )
        except requests.exceptions.ConnectionError:
            print('unable to reach server on mini cart display in dummy add to cart')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            print('bad status {} on mini cart display in dummy add to cart'.format(r.status_code))
            return False
        return True

    def calculate_and_go_to_cart(self):
        print('calculating order and going to cart')
        try:
            r = self.s.get(
                url='https://hotwheelscollectors.mattel.com/shop/RESTOrderCalculate',
                params={
                    'calculationUsageId': '-1',
                    'catalogId': self.settings['catalog_id'],
                    'doConfigurationValidation': 'Y',
                    'updatePrices': '1',
                    'orderId': '.',
                    'langId': '-1',
                    'storeId': self.settings['store_id'],
                    'errorViewName': 'AjaxOrderItemDisplayView',
                    'URL': '/shop/AjaxOrderItemDisplayView'
                }
            )
        except requests.exceptions.ConnectionError:
            print('unable to reach server while calculating order')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            print('bad status code {} while calculating order'.format(r.status_code))
            return False
        return True

    def save_for_later(self):
        print('saving dummy item for later')
        try:
            r = self.s.post(
                url='https://hotwheelscollectors.mattel.com/shop/MattelAjaxSFLOrderProcess',
                data={
                    'storeId': self.settings['store_id'],
                    'catalogId': self.settings['catalog_id'],
                    'langId': '-1',
                    'calculateOrder': '0',
                    'URL': 'SuccessfulAJAXRequest',
                    'partNumber': '',
                    'catEntryId': self.settings['dummy_item_cat_id'],
                    'quantity': '1',
                    'description': '',  # todo
                    'actionType': 'addToSFL',
                    'penOrderItemId': self.dummy_order_item_id,
                    'penOrderId': self.order_id,
                    'requesttype': 'ajax'
                }
            )
        except requests.exceptions.ConnectionError:
            print('unable to reach server while saving dummy item for later')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            print('bad status code {} while saving dummy item for later'.format(r.status_code))
            return False
        print('removing dummy item from cart')
        try:
            r = self.s.post(
                url='https://hotwheelscollectors.mattel.com/shop/AjaxRESTOrderItemDelete',
                data={
                    'storeId': self.settings['store_id'],
                    'catalogId': self.settings['catalog_id'],
                    'langId': '-1',
                    'orderId': '.',
                    'orderItemId': self.dummy_order_item_id,
                    'calculationUsage': '-1,-2,-5,-6,-7',
                    'doInventory': 'N',
                    'calculateOrder': '1',
                    'mattelOrderType': 'Standard Orders',
                    'requesttype': 'ajax'
                }
            )
        except requests.exceptions.ConnectionError:
            print('unable to reach server while deleting dummy item after sfl')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            print('bad status {} while deleting dummy item after sfl'.format(r.status_code))
            return False
        print('successfully removed dummy item to cart after sfl')
        return True

    def re_add_dummy_item(self):
        """
        Adds the dummy item back into the cart from the SFL list
        :return:
        """
        print('re-adding dummy item to cart from sfl list')
        try:
            r = self.s.post(
                url='https://hotwheelscollectors.mattel.com/shop/MattelAjaxSFLOrderProcess',
                data={
                    'storeId': self.settings['store_id'],
                    'catalogId': self.settings['catalog_id'],
                    'langId': '-1',
                    'calculationUsage': '-1,-2,-3,-4,-5,-6,-7',
                    'calculateOrder': '1',
                    'mergeToCurrentPendingOrder': 'Y',
                    'URL': '',
                    'sflOrderItemId': self.dummy_order_item_id,
                    'partNumber': self.settings['dummy_item_part_num'],
                    'inventoryValidation': 'true',
                    'orderId': '.',
                    'actionType': 'addToCurrent',
                    'quantity': '1',
                    'requesttype': 'ajax'
                }
            )
        except requests.exceptions.ConnectionError:
            print('error reaching server while adding dummy item to cart back from sfl')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            print('bad status code {} while adding dummy item to cart back from sfl'.format(r.status_code))
            return False
        try:
            r = self.s.post(
                url='https://hotwheelscollectors.mattel.com/shop/MattelAjaxSFLOrderProcess',
                data={
                    'orderItemId': self.dummy_order_item_id,
                    'storeId': self.settings['store_id'],
                    'catalogId': self.settings['catalog_id'],
                    'langId': '-1',
                    'actionType': 'deleteSavedItem',
                    'orderId': self.order_id,
                    'calculationUsage': '-1,-2,-3,-4,-5,-6,-7',
                    'check': '*n',
                    'requesttype': 'ajax'
                }
            )
        except requests.exceptions.ConnectionError:
            print('unable to reach server while removing dummy item from sfl list')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            print('bad status {} while removing dummy item from sfl list'.format(r.status_code))
            return False

        return False

    def add_target_item(self):
        print('adding target item to cart')
        try:
            r = self.s.get(
                url='https://hotwheelscollectors.mattel.com/shop/MattelAjaxSFLOrderProcess',
                params={
                    'storeId': self.settings['store_id'],
                    'catalogId': self.settings['catalog_id'],
                    'langId': '-1',
                    'calculationUsage': '-1,-2,-3,-4,-5,-6,-7',
                    'calculateOrder': '1',
                    'mergeToCurrentPendingOrder': 'Y',
                    'URL': '',
                    'catEntryId_1': '',  # todo, this is the target
                    'partNumber': '',  # todo, this is the target
                    'inventoryValidation': 'true',
                    'orderId': '.',
                    'actionType': 'addToCurrent',
                    'quantity': '1',
                    'requesttype': 'ajax'
                }
            )
        except requests.exceptions.ConnectionError:
            print('unable to reach server while adding target item to cart')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            print('bad status {} while adding target item to cart'.format(r.status_code))
            return False
        return True

    def run(self):
        print('worker is running')
        if self.settings['use_catchall']:
            self.create_account()
            self.go_to_shop()
            self.add_dummy_item()
            self.calculate_and_go_to_cart()
        else:
            return False


