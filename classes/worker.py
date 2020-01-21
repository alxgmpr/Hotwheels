import threading
import random
import string
import re
from datetime import datetime

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
    def __init__(self, settings, task, account_lock):
        super().__init__()
        self.lock = account_lock
        if not settings:
            raise Exception('Missing settings')
        if not task and not settings['generate_accounts']:
            raise Exception('Missing task')
        self.settings = settings
        self.task = task

        # task defined data
        self.cc_num = int()
        self.cc_exp_m = int()
        self.cc_exp_y = int()
        self.cc_cvv = int()
        self.cc_brand = str()
        self.first_name = str()
        self.last_name = str()
        self.email = str()
        self.password = str()
        self.address = str()
        self.apt = str()
        self.city = str()
        self.zip = str()
        self.state = str()

        # if using catchall + generation or task defined
        # TODO: finish setting this
        if not self.settings['use_catchall'] and not self.settings['generate_accounts']:
            self.log('using task defined data')
            try:
                self.cc_num = self.task['cc_num']
                self.cc_exp_m = self.task['cc_exp_m']
                self.cc_exp_y = self.task['cc_exp_y']
                self.cc_cvv = self.task['cc_cvv']
                self.cc_brand = self.task['cc_brand']

                self.first_name = self.task['first_name']
                self.last_name = self.task['last_name']
                self.email = self.task['email']
                self.password = self.task['password']

                # TODO: finish the rest of the address data assigned to self
            except IndexError:
                raise Exception('Missing data from task')
        else:
            self.log('using catchall (task defined CC + address + task defined name/account)')
            try:
                self.cc_num = self.task['cc_num']
                self.cc_exp_m = self.task['cc_exp_m']
                self.cc_exp_y = self.task['cc_exp_y']
                self.cc_cvv = self.task['cc_cvv']
                self.cc_brand = self.task['cc_brand']
            except (TypeError, KeyError):
                self.log('key error - using globally defined cc')
                self.cc_num = self.settings['catchall_credit_card_num']
                self.cc_exp_m = self.settings['catchall_credit_card_exp_m']
                self.cc_exp_y = self.settings['catchall_credit_card_exp_y']
                self.cc_cvv = self.settings['catchall_credit_card_cvv']
                self.cc_brand = self.settings['catchall_credit_card_brand']

        # request configuration
        self.s = requests.Session()
        self.s.headers = BASE_HEADERS
        self.s.verify = False

        # session ids
        self.order_id = int()
        self.order_total = '0.00'
        self.dummy_order_item_id = int()
        self.user_id = int()
        self.shipping_address_id = int()
        self.billing_address_id = int()
        self.cc_id = int()
        self.cc_token = int()
        self.cc_hash = str()
        self.payment_instruction_id = int()

    @staticmethod
    def log(text):
        print('[{}] : {}'.format(datetime.now(), text))

    def create_account(self):
        """
        Generates a random HWC account based on the catchall defined in settings.json. Once this method is called,
        there is no need to login again, as it automatically starts a session.

        NOTE: this method may fail during load/release time, it is best to generate accounts prior to release date
        :return: bool
        """
        name = names.get_full_name()
        r_first_name = name.split(' ')[0]
        r_last_name = name.split(' ')[1]
        r_email = r_first_name[0] + r_last_name + str(random.randrange(99)) + self.settings['catchall_email_suffix']
        r_email = r_email.lower()
        r_password = self.settings['password_prefix'] + str(random.randrange(99))
        # set default names
        self.first_name = r_first_name
        self.last_name = r_last_name
        self.email = r_email
        self.password = r_password
        # create the account
        self.log('pass: {}'.format(r_password))
        self.log('creating account - F: {} L: {}'.format(r_first_name, r_last_name))
        self.log('getting auth token from login page')
        try:
            r = self.s.get(
                url='https://hotwheelscollectors.mattel.com/webapp/wcs/stores/servlet/AjaxLogonView',
                params={
                    'catalogId': self.settings['catalog_id'],
                    'storeId': self.settings['store_id']
                }
            )
        except requests.exceptions.ConnectionError:
            self.log('unable to reach server while getting auth token from login page')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log('bad status {} while getting auth token from login page'.format(r.status_code))
            return False
        try:
            auth_token = re.findall('<input type="hidden" name="authToken" value="(.*)"', r.text)[0]
        except IndexError:
            self.log('unable to find auth token in page source')
            return False
        try:
            r = self.s.post(
                url='https://hotwheelscollectors.mattel.com/shop/UserRegistrationAdd',
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
                    'firstName': r_first_name,
                    'lastName': r_last_name,
                    'email1': r_email,
                    'logonIdDisplay': r_email,
                    'logonId': '{}|{}'.format(self.settings['store_id'], r_email),
                    'logonIdVerifyDisplay': r_email,
                    'logonIdVerify': '{}|{}'.format(self.settings['store_id'], r_email),
                    'logonPassword': r_password,
                    'logonPasswordVerify': r_password,
                    'user_name': r_email.split('@')[0].lower(),
                    'userName': '',  # left blank
                }
            )
        except requests.exceptions.ConnectionError:
            self.log('unable to reach server')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log('bad status code {} while creating account'.format(r.status_code))
            return False
        self.log('generated account: {}:{}'.format(r_email, r_password))
        self.write_account_to_file(r_email, r_password)
        return True

    def write_account_to_file(self, username, password):
        self.lock.acquire()
        with open('accounts.txt', 'a') as account_file:
            account_file.write('{}:{}:{}:{}\n'.format(username, password, self.first_name, self.last_name))
        self.lock.release()

    def login(self):
        """
        Logs into a HWC account based on the email/password parameters. Useful if the accounts have already been
        generated.
        :return:
        """
        self.log('logging in to account {}'.format(self.email))
        try:
            r = self.s.post(
                url='https://hotwheelscollectors.mattel.com/shop/AjaxLogon',
                data={
                    "storeId": self.settings['store_id'],
                    "catalogId": self.settings['catalog_id'],
                    "reLogonURL": "LogonForm",
                    "myAcctMain": "1",
                    "fromOrderId": "*",
                    "toOrderId": ".",
                    "deleteIfEmpty": "*",
                    "continue": "1",
                    "createIfEmpty": "1",
                    "calculationUsageId": "-1",
                    "updatePrices": "0",
                    "previousPage": "logon",
                    "returnPage": "",
                    "mergeCart": "true",
                    "rememberMe": "true",
                    "URL": "RESTOrderCalculate?URL=AjaxLogonForm&calculationUsageId=-1&calculationUsageId=-2"
                           "&deleteCartCookie=true&page=",
                    "logonIdDisplay": self.email,
                    "logonId": "10151|{}".format(self.email),
                    "logonPassword": self.password,
                    "requesttype": "ajax"
                }
            )
        except requests.exceptions.ConnectionError:
            self.log('connection error while logging in')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log('bad status code {} while logging in'.format(r.status_code))
            return False
        self.log('logged in successfully')
        return True

    def set_account_tier(self, tier=2, tier_code='Chrome'):
        self.log('setting account to tier {}'.format(tier))
        try:
            r = self.s.post(
                url='https://hotwheelscollectors.mattel.com/shop/AjaxUpdateMembershipInfo',
                data={
                    "storeId": self.settings['store_id'],
                    "catalogId": self.settings['catalog_id'],
                    "langId": "-1",
                    "membershipTierCode": tier_code,
                    "membershipID": tier,
                    "clubName": "Hot Wheels Collector- {}".format(tier_code),
                    "requesttype": "ajax"
                }
            )
        except requests.exceptions.ConnectionError:
            self.log('connection error while setting account tier')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log('error bad status code {} while setting account tier'.format(r.status_code))
            return False
        self.log('finished setting account tier')
        return True

    def go_to_shop(self):
        """
        Purpose here is really to just populate cookies, it might be an optional step. Further down the line I'd like
        it to retrieve products that are in stock so that we can automatically parse out a dummy item to ATC
        :return:
        """
        self.log('going to shop main page')
        try:
            r = self.s.get(
                url='https://hotwheelscollectors.mattel.com/shop/en-us/hwc/shop'
            )
        except requests.exceptions.ConnectionError:
            self.log('unable to reach server while going to shop')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log('bad status code {} while going to shop'.format(r.status_code))
            return False
        return True

    def add_dummy_item(self):
        """
        Adds a dummy item to cart based on its catalog ID (NOT part number)
        :return:
        """
        self.log('adding dummy item to cart')
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
            self.log('unable to reach server while adding dummy item to cart')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log('bad status {} while adding dummy item to cart'.format(r.status_code))
            return False
        self.log('parsing order item id and order id')
        try:
            self.order_id = re.findall('"orderId": "(.*)",', r.text)[0]
        except IndexError:
            self.log('error unable to find order ID from response data')
            self.log(r.text)

            if 'out of stock' in r.text:
                self.log('dummy item is out of stock')
            return False
        try:
            self.dummy_order_item_id = re.findall('"orderItemId": "(.*)"', r.text)[0]
        except IndexError:
            self.log('error unable to find dummy item ID from response data')
            return False
        self.log('order id: {}, dummy order item id: {}'.format(self.order_id, self.dummy_order_item_id))

        # TODO: this request might be unnecessary, as it only returns some HTML and doesn't seem to modify the order
        #
        # self.log('calling mini cart display')
        # try:
        #     r = self.s.post(
        #         url='https://hotwheelscollectors.mattel.com/shop/MiniShopCartDisplayView',
        #         params={
        #             'storeId': self.settings['store_id'],
        #             'catalogId': self.settings['catalog_id'],
        #             'langId': '-1'
        #         },
        #         data={
        #             'addedOrderItemId': self.dummy_order_item_id,
        #             'deleteCartCookie': 'true',
        #             'objectId': '',
        #             'requesttype': 'ajax'
        #         }
        #     )
        # except requests.exceptions.ConnectionError:
        #     self.log('unable to reach server on mini cart display in dummy add to cart')
        #     return False
        # try:
        #     r.raise_for_status()
        # except requests.exceptions.HTTPError:
        #     self.log('bad status {} on mini cart display in dummy add to cart'.format(r.status_code))
        #     return False
        return True

    def calculate_and_go_to_cart(self):
        """
        This method isn't exactly necessary, as it returns a veiw that doesn't contain anything that we need
        :return:
        """
        self.log('calculating order and going to cart')
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
            self.log('unable to reach server while calculating order')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log('bad status code {} while calculating order'.format(r.status_code))
            return False
        return True

    def save_for_later(self):
        """
        In order to bypass the queue, it appears that this step needs to be taken for the account at least once.
        Once the account has gone through the SFL process, it doesn't seem to need to do it again. This method takes the
        dummy item, saves it for later and then subsequently removes it from the cart (2 separate requests).
        :return:
        """
        self.log('saving dummy item for later')
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
                    'description': '',
                    'actionType': 'addToSFL',
                    'penOrderItemId': self.dummy_order_item_id,
                    'penOrderId': self.order_id,
                    'requesttype': 'ajax'
                }
            )
        except requests.exceptions.ConnectionError:
            self.log('unable to reach server while saving dummy item for later')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log('bad status code {} while saving dummy item for later'.format(r.status_code))
            return False
        self.log('removing dummy item from cart')
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
            self.log('unable to reach server while deleting dummy item after sfl')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log('bad status {} while deleting dummy item after sfl'.format(r.status_code))
            return False
        self.log('successfully removed dummy item to cart after sfl')
        return True

    def re_add_dummy_item(self):
        """
        Adds the dummy item back into the cart from the SFL list.
        :return:
        """
        self.log('re-adding dummy item to cart from sfl list')
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
            self.log('error reaching server while adding dummy item to cart back from sfl')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log('bad status code {} while adding dummy item to cart back from sfl'.format(r.status_code))
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
            self.log('unable to reach server while removing dummy item from sfl list')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log('bad status {} while removing dummy item from sfl list'.format(r.status_code))
            return False

        return False

    def add_target_item(self):
        """
        This is the special request needed to add the target item to cart (the one that Jim has been posting).
        While it takes a target catalog ID and a target part number, it truthfully only needs the part number to work.
        Furthermore, you can test the ATC in browser and it will return the catalog ID based on the part number.
        :return:
        """
        self.log('adding target item {} to cart'.format(self.settings['target_item_part_num']))
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
                    'catEntryId_1': self.settings['target_item_cat_id'],
                    'partNumber': self.settings['target_item_part_num'],
                    'inventoryValidation': 'true',
                    'orderId': '.',
                    'actionType': 'addToCurrent',
                    'quantity': '1',
                    'requesttype': 'ajax'
                }
            )
        except requests.exceptions.ConnectionError:
            self.log('unable to reach server while adding target item to cart')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log('bad status {} while adding target item to cart'.format(r.status_code))
            return False

        # TODO: look for more error potential error codes. Unclear if the site will return this for OOS target
        #   product when site is under load

        if '_ERR_PROD_NOT_ORDERABLE' in r.text:
            self.log('error product out of stock')
            return False
        return True

    def add_and_set_shipping_address(self):
        """

        :return:
        """
        self.log('adding and setting shipping address')
        try:
            self.log('getting auth token')
            r = self.s.get(
                url='https://hotwheelscollectors.mattel.com/webapp/wcs/stores/servlet/OrderShippingView',
                params={
                    'catalogId': self.settings['catalog_id'],
                    'langId': '-1',
                    'storeId': self.settings['store_id']
                }
            )
        except requests.exceptions.ConnectionError:
            self.log('connection error while getting auth token')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log('bad status {} while getting auth token')
            return False
        try:
            auth_token = re.findall('<input type="hidden" name="authToken" value="(.*)"', r.text)[0]
        except IndexError:
            self.log('error unable to find an auth token')
            return False
        self.log('got auth token {}'.format(auth_token))
        try:
            r = self.s.post(
                url='https://hotwheelscollectors.mattel.com/webapp/wcs/stores/servlet/AjaxPersonChangeServiceAddressAdd',
                data={
                    "addressType": "SB",
                    "commonShippingGeoCode": ["", ""],
                    "childAddress": "",
                    "storeId": self.settings['store_id'],
                    "catalogId": self.settings['catalog_id'],
                    "langId": "-1",
                    "status": "Billing",
                    "authToken": auth_token,
                    "jsonObject": "",
                    "addressField2": "",
                    "nickName": "",
                    "isAddressEdited": "false",
                    "isAddressValidated": "0",
                    "firstName": self.first_name,
                    "lastName": self.last_name,
                    "country": "US",
                    "address1": self.settings['catchall_address1'],
                    "address2": self.settings['catchall_address2'],
                    "city": self.settings['catchall_city'],
                    "state": self.settings['catchall_state'],
                    "zipCode": self.settings['catchall_zip'],
                    "phone1": "",
                    "email1": self.email,
                    "email1Display": "",
                    "billingCodeType": "|N|Ncheckout",
                    "requesttype": "ajax"
                }
            )
        except requests.exceptions.ConnectionError:
            self.log('connection error while creating new address')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log('error bad status {} while submitting new address'.format(r.status_code))
            return False
        try:
            self.shipping_address_id = r.text.split('["')[1].split('"]')[0]
        except IndexError:
            self.log('unable to find shipping address id in response')
            return False
        self.log('got new address id {}'.format(self.shipping_address_id))
        self.log('setting address')
        try:
            r = self.s.post(
                url='https://hotwheelscollectors.mattel.com/webapp/wcs/stores/servlet/AjaxRESTOrderShipInfoUpdate',
                data={
                    "storeId": self.settings['store_id'],
                    "catalogId": self.settings['catalog_id'],
                    "langId": "-1",
                    "orderId": ".",
                    "calculationUsage": "-1,-2,-3,-4,-5,-6,-7",
                    "allocate": "***",
                    "backorder": "***",
                    "remerge": "***",
                    "check": "*n",
                    "calculateOrder": "1",
                    "addressId": self.shipping_address_id,
                    "shipModeId": self.settings['shipping_method_id'],
                    "requesttype": "ajax"
                }
            )
        except requests.exceptions.ConnectionError:
            self.log('connection error while setting address')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log('error bad status {} while setting address'.format(r.status_code))
            return False
        return True

    def add_and_set_cc(self):
        self.log('adding billing address and CC')
        try:
            self.log('getting auth token')
            r = self.s.post(
                url='https://hotwheelscollectors.mattel.com/shop/BillingAddressDisplayView_1',
                params={
                    'catalogId': self.settings['catalog_id'],
                    'orderId': self.order_id,
                    'langId': '-1',
                    'storeId': self.settings['store_id']
                },
                data={
                    "paymentAreaNumber": "1",
                    "selectedAddressId": "",
                    "paymentMethodSelected": "",
                    "requestFrom": "",
                    "objectId": "1",
                    "requesttype": "ajax"
                }
            )
        except requests.exceptions.ConnectionError:
            self.log('connection error while getting auth token')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log('error bad status {} while getting auth token'.format(r.status_code))
            return False
        try:
            auth_token = re.findall('<input type="hidden" name="authToken" value="(.*)"', r.text)[0]
        except IndexError:
            self.log('unable to find auth token')
            return False
        self.log('got new auth token {}'.format(auth_token))
        try:
            r = self.s.post(
                url='https://hotwheelscollectors.mattel.com/shop/AjaxPersonChangeServiceAddressAdd',
                data={
                    "addressType": "Billing",
                    "primary": "false",
                    "commonShippingGeoCode": "",
                    "commonTaxGeoCode": "",
                    "storeId": self.settings['store_id'],
                    "catalogId": self.settings['catalog_id'],
                    "langId": "-1",
                    "status": "paymentUpdate",
                    "paramPrefix": "payBill",
                    "authToken": auth_token,
                    "jsonObject": "",
                    "addressField2": "",
                    "nickName": "",
                    "isAddressEdited": "false",
                    "isAddressValidated": "0",
                    "accountFirstName": self.first_name,
                    "firstName": self.first_name,
                    "accountLastName": self.last_name,
                    "lastName": self.last_name,
                    "country": "US",
                    "address1": self.settings['catchall_address1'],
                    "address2": self.settings['catchall_address2'],
                    "city": self.settings['catchall_city'],
                    "state": self.settings['catchall_state'],
                    "zipCode": self.settings['catchall_zip'],
                    "phone1": "",
                    "email1": self.email,
                    "email1Display": "",
                    "billingCodeType": "|N|Ncheckout",
                    "isToggled": "0",
                    "requesttype": "ajax"
                }
            )
        except requests.exceptions.ConnectionError:
            self.log('connection error while adding new billing address')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log('error bad status {} while adding new billing address'.format(r.status_code))
            return False
        try:
            self.billing_address_id = r.text.split('["')[1].split('"]')[0]
        except IndexError:
            self.log('unable to find billing address ID in response')
            return False
        try:
            r = self.s.post(
                url='https://hotwheelscollectors.mattel.com/shop/AjaxAddPaymentInfo',
                data={
                    "storeId": self.settings['store_id'],
                    "catalogId": self.settings['catalog_id'],
                    "langId": "-1",
                    "nameOnCard": "{} {}".format(self.first_name, self.last_name),
                    "cardNum": self.settings['catchall_credit_card_num'],
                    "saveDefCard": "0",
                    "cardType": self.settings['catchall_credit_card_brand'],
                    "month": self.settings['catchall_credit_card_exp_m'],
                    "year": self.settings['catchall_credit_card_exp_y'],
                    "billing_address_id": self.billing_address_id,
                    "requesttype": "ajax"
                }
            )
        except requests.exceptions.ConnectionError:
            self.log('connection error while adding new cc')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log('error bad status {} while adding new cc'.format(r.status_code))
            return False
        try:
            self.cc_id = re.findall('"creditCardId": "(.*)"', r.text)[0]
            self.cc_token = re.findall('"token": "(.*)"', r.text)[0]
        except IndexError:
            self.log('unable to find CC ID in response')
            return False
        self.log('getting cc hash')
        try:
            # now we submit to get the hash
            r = self.s.post(
                url='https://hotwheelscollectors.mattel.com/shop/MattelCreditCardView',
                params={
                    'catalogId': self.settings['catalog_id'],
                    'langId': '-1',
                    'storeId': self.settings['store_id']
                },
                data={
                    "payment1": "",
                    "payment2": "",
                    "payment3": "",
                    "currentPaymentArea": "1",
                    "billingMode1": "none",
                    "billingMode2": "none",
                    "billingMode3": "none",
                    "currentTotal": "",  # this doesnt affect the cc hash, it can be null but TODO: use the actual total
                    "creditCardId": self.cc_id,
                    "objectId": "",
                    "requesttype": "ajax"
                }
            )
        except requests.exceptions.ConnectionError:
            self.log('connection error while getting cc hash')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log('error while getting cc hash')
            return False
        try:
            self.cc_hash = re.findall('id="hashCode_1" value="(.*)"', r.text)[0]
        except IndexError:
            self.log('error unable to find cc hash token in response')
            return False

        # now we get a new auth token by submitting to billing view
        # todo: i have a hunch we could re use a token from earlier...
        # todo: this is replicated above. move to fx

        try:
            self.log('getting auth token')
            r = self.s.post(
                url='https://hotwheelscollectors.mattel.com/shop/BillingAddressDisplayView_1',
                params={
                    'catalogId': self.settings['catalog_id'],
                    'orderId': self.order_id,
                    'langId': '-1',
                    'storeId': self.settings['store_id']
                },
                data={
                    "paymentAreaNumber": "1",
                    "selectedAddressId": self.billing_address_id, # this time we send the billing addy
                    "paymentMethodSelected": "",
                    "requestFrom": "",
                    "objectId": "1",
                    "requesttype": "ajax"
                }
            )
        except requests.exceptions.ConnectionError:
            self.log('connection error while getting auth token')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log('error bad status {} while getting auth token'.format(r.status_code))
            return False
        try:
            auth_token = re.findall('<input type="hidden" name="authToken" value="(.*)"', r.text)[0]
        except IndexError:
            self.log('unable to find auth token')
            return False
        # gather order total
        self.log('getting order total $')
        try:
            r = self.s.post(
                url='https://hotwheelscollectors.mattel.com/webapp/wcs/stores/servlet/orderTotalAsJSON',
                data={
                    "operation": "OrderPrepare",
                    "piFormName": "PaymentForm",
                    "skipOrderPrepare": "false",
                    "storeId": self.settings['store_id'],
                    "catalogId": self.settings['catalog_id'],
                    "langId": "-1"
                }
            )
        except requests.exceptions.ConnectionError:
            self.log('connection error while getting order total')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log('error bad status {} while getting order total'.format(r.status_code))
            return False
        try:
            self.order_total = r.text.split('orderTotal: "')[1].split('"')[0]
            self.log('got order total ${}'.format(self.order_total))
        except IndexError:
            self.log('unable to find order total in response')

        # now we set PI
        self.log('setting payment instruction')
        try:
            r = self.s.post(
                url='https://hotwheelscollectors.mattel.com/webapp/wcs/stores/servlet/AjaxRESTOrderPIAdd',
                data={
                    "storeId": self.settings['store_id'],
                    "catalogId": self.settings['catalog_id'],
                    "langId": "-1",
                    "valueFromProfileOrder": " ",
                    "valueFromPaymentTC": " ",
                    "paymentTCId": "",
                    "payMethodId": self.settings['catchall_credit_card_brand'],
                    "piAmount": self.order_total,
                    "billing_address_id": self.billing_address_id,
                    "requesttype": "ajax",
                    "authToken": auth_token,
                    "cc_brand": self.settings['catchall_credit_card_brand'],
                    "cc_cvc": self.settings['catchall_credit_card_cvv'],
                    "cc_nameoncard": "{} {}".format(self.first_name, self.last_name),
                    "token": self.cc_token,
                    "hashCode": self.cc_hash,
                    "creditCardId": self.cc_id,
                    "account": "XXXXXXXXXXXX{}".format(self.settings['catchall_credit_card_num'][-4:]),  # note: no amex
                    "expire_month": self.settings['catchall_credit_card_exp_m'],
                    "expire_year": self.settings['catchall_credit_card_exp_y'],
                    "check_routing_number": " ",
                    "checkingAccountNumber": " ",
                    "checkRoutingNumber": " "
                }
            )
        except requests.exceptions.ConnectionError:
            self.log('connection error while setting payment instruction')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log('bad status {} while setting payment instruction'.format(r.status_code))
            return False
        try:
            self.payment_instruction_id = re.findall('"piId": "(.*)"', r.text)[0]
            self.log('got payment instruction id {}'.format(self.payment_instruction_id))
        except IndexError:
            self.log('error unable to find payment instruction id in response')
            return False

    def submit_order(self):
        self.log('submitting order')
        try:
            r = self.s.post(
                url='https://hotwheelscollectors.mattel.com/shop/AjaxRESTOrderSubmit',
                data={
                    "orderId": self.order_id,
                    "notifyMerchant": "1",
                    "notifyShopper": "1",
                    "notifyOrderSubmitted": "1",
                    "storeId": self.settings['store_id'],
                    "catalogId": self.settings['catalog_id'],
                    "langId": "-1",
                    "userAgent": BASE_HEADERS['User-Agent'],
                    "paymentInstructionId": self.payment_instruction_id,
                    "pay_data_cc_cvc": self.cc_cvv,
                    "requesttype": "ajax"
                }
            )
        except requests.exceptions.ConnectionError:
            self.log('connection error while submitting order')
            return False
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log('bad status {} while submitting order'.format(r.status_code))
            return False

    def run(self):
        self.log('worker is running')
        if self.settings['generate_accounts']:
            self.create_account()
            self.set_account_tier()
            self.add_dummy_item()
            self.save_for_later()
            return True
        if self.settings['use_catchall']:
            self.login()
            self.add_target_item()
            self.add_and_set_shipping_address()
            self.add_and_set_cc()
            self.submit_order()
            return True
        else:
            # use task based info
            self.login()
            self.add_target_item()
            self.add_and_set_shipping_address()
            self.add_and_set_cc()
            self.submit_order()
            return True


