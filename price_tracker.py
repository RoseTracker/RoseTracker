#!/usr/bin/env python3
'''price_tracker.py script parse products pages and compares their prices with
your price. all data is stored in google spreadsheets'''


import requests
import re
import bs4
from torrequest import TorRequest
import random
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import smtplib
import json
import time
from colorama import Fore, Style


class PriceTracker(object):
    def __init__(self, shop_list_file):
        self.shop_list_file = shop_list_file

    # function to get price from the desire url
    def scrap_price(self, shop_link, your_price, email):
        print(f'Checking price of product at {Style.BRIGHT}"{shop_link}"\
                {Style.RESET_ALL}')
        # regex for define domain of the url
        regex_domain = re.compile(
            r'(www)(.*)([\.]+)(com|net|org|info|coop|int|co\.uk'
            r'|org\.uk|ac\.uk|uk)'
        )
        print(regex_domain)
        mo = regex_domain.search(shop_link)
        # the domain of the url for the Host header in the request
        domain = mo.group()
        # the number of tries if request return None
        count_try = 20
        # start loop for repetative tor request till price not equale None,
        # count_try - number of tries
        while True:
            user_agents = ['Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:70.0)'
                           ' Gecko/20100101 Firefox/70.0',
                           'Mozilla/5.0 (X11; Linux x86_64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko)'
                           'Ubuntu Chromium/77.0.3865.90 Chrome/77.0.3865.90'
                           ' Safari/537.36',
                           'Opera/9.80 (X11; Linux i686; Ubuntu/14.10) '
                           'Presto/2.12.388 Version/12.16']
            # random choose user agent to hide your bot for the site
            user_agent = random.choice(user_agents)
            with TorRequest(password='16:EBEF754F385E691E608949F6DA3EF25A82B'
                                     '7807DB625941C9590D378D2') as tr:
                tr.reset_identity()  # change our ip with tor
                try:
                    res = tr.get(shop_link,
                                 headers={'User-Agent': user_agent,
                                          'Host': domain,
                                          'Accept': 'text/html,application/'
                                          'xhtml+xml,'
                                          'application/xml;q=0.9,*/*;q=0.8',
                                          'Accept-Language': 'en-us,en;q=0.5',
                                          'Accept-Encoding': 'gzip,deflate',
                                          'Accept-Charset': 'ISO-8859-1,'
                                          'utf-8;q=0.7,*;q=0.7',
                                          'Keep-Alive': '115',
                                          'Connection': 'keep-alive'},
                                 timeout=20)  # get request with tor
                    response = tr.get('http://ipecho.net/plain')
                    print("New Ip Address: ", response.text)
                # hadling timeout exception
                except requests.exceptions.Timeout:
                    error = 'Timeout error'
                    print(f'{Fore.RED}{error}{Style.RESET_ALL}\n')
                    return error
            if str(res) == '<Response [404]>':  # handling 404 error exception
                error = 'The page was not found'
                print(f'{Fore.RED}{error}{Style.RESET_ALL}\n')
                return error

            # open our json file with dict of domains and lists of tags which
            # we use to find elements on the page
            with open('keys.json', 'r') as my_keys:
                my_dict = json.load(my_keys)
            for x in my_dict:
                # if x (domain from the json file) is in shop_ling string
                if x in shop_link:
                    # copy tags and args for certain domain
                    price_tag_name = my_dict[x]['price_tag_name']
                    price_attr_name = my_dict[x]['price_attr_name']
                    price_attr_value = my_dict[x]['price_attr_value']
                    title_tag_name = my_dict[x]['title_tag_name']
                    title_attr_name = my_dict[x]['title_attr_name']
                    title_attr_value = my_dict[x]['title_attr_value']

            # creating soup object of the source
            soup = bs4.BeautifulSoup(res.text, features="html.parser")
            # finding price on the page
            price = soup.find(price_tag_name, attrs={
                              price_attr_name: price_attr_value})
            # if price isn't None breake the while loop and continues
            # our function
            if price != None:
                break
            if count_try <= 0:
                error = "Can't find a price on the site"
                print(f'{Fore.RED}{error}{Style.RESET_ALL}\n')
                return error
            count_try -= 1
            print(count_try)
            time.sleep(random.randint(2, 30))

        try:
            price = float(re.sub('[^0-9.]', '', str(price)))
            product_title = (soup.find(title_tag_name,
                                      {title_attr_name: title_attr_value})
            .text.lstrip())
            print(f'The price of {Style.BRIGHT}"{product_title}"'
                  f'{Style.RESET_ALL} is {Style.BRIGHT}"{price}"'
                  f'{Style.RESET_ALL} and your prise '
                  f'is {Style.BRIGHT}"{your_price}"{Style.RESET_ALL}')
            if your_price > price:
                self.send_email(email, shop_link, your_price, price)
                print(f'{Fore.GREEN}The price of {Style.BRIGHT}"'
                      f'{product_title}"{Style.RESET_ALL}{Fore.GREEN}'
                      f' is low enough. The email was sent.\n'
                      f'{Style.RESET_ALL}')
                return True
            else:
                print(f'The price of {Style.BRIGHT}"{product_title}"'
                      f'{Style.RESET_ALL} still higher than your. You '
                      f'should to wait.\n')
        except Exception as error:
            print(f'{Fore.RED}{error}{Style.RESET_ALL}\n')
            return str(error)

    def parse_shop_list(self):
        self.smtp_connect()
        regex_url = re.compile(r'^(?:http|ftp)s?://')
        regex_email = '^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$'
        # use creds to create a client to interact with the Google Drive API
        scope = ['https://spreadsheets.google.com/feeds']
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            'rivne-price-tracker-0ea490480fcf.json', scope)
        client = gspread.authorize(creds)
        # work with spreadsheet
        wb = client.open_by_url('https://docs.google.com/spreadsheets/d/1Cv'
                                '-zzL2YXqEizoH-ewQ0athDOtcjDL_T9xfNbc2YzUE/'
                                'edit#gid=0')
        ws = wb.worksheet('list')
        max_rows = len(ws.get_all_values())

        for row in range(2, max_rows + 1):
            error = ''
            values = ws.row_values(row)
            if len(values) >= 5:
                row_number = values[0]
                print(f'Row #{Style.BRIGHT}{row_number}{Style.RESET_ALL}')

                if values[1]:
                    row_url = values[1]
                else:
                    row_url = ""

                if values[2]:
                    try:
                        row_price = float(values[2].replace(',', '.'))
                    except:
                        error = 'The price must be integer or float'
                        ws.update_cell(row, 6, error)
                        print(f'{Fore.RED}{error}{Style.RESET_ALL}\n')
                else:
                    row_price = 0

                if values[3] and (re.search(regex_email, values[3])):
                    row_email = values[3]
                else:
                    row_email = ""
                    error = 'Wrong or empty email'
                    ws.update_cell(row, 6, error)
                    print(f'{Fore.RED}{error}{Style.RESET_ALL}\n')

                if values[4]:
                    try:
                        row_repeat = int(values[4])
                    except:
                        row_repeat = 0
                        error = 'The repeat number must be integer'
                        ws.update_cell(row, 6, error)
                        print(f'{Fore.RED}{error}{Style.RESET_ALL}\n')
                else:
                    row_repeat = 0

                if row_url == "":
                    pass
                elif not (re.search(regex_url, row_url)):
                    error = 'The url should start from http:// or https://'
                    ws.update_cell(row, 6, error)
                    print(f'{Fore.RED}{error}{Style.RESET_ALL}\n')
                elif error == '' and row_repeat > 0:
                    result = self.scrap_price(row_url, row_price, row_email)
                    if result is True:
                        ws.update_cell(row, 5, row_repeat - 1)
                    else:
                        ws.update_cell(row, 6, result)
            else:
                print(f'{Fore.RED}in row number {row - 1} '
                      f'some fields are empty{Style.RESET_ALL}')
        self.disconnect_smtp()

    def smtp_connect(self):
        self.smtpObj = smtplib.SMTP('smtp.gmail.com', 587)
        self.smtpObj.ehlo()
        self.smtpObj.starttls()
        self.smtpObj.login('rivne.price.tracker@gmail.com', 'p0r4i8c3')

    def send_email(self, email, shop_link, your_price, price):
        subject_text = 'Price of your good was reached your limit!!!'
        message_text = (f'The goods price at {shop_link} is {price} that '
                        f'less than your price - {your_price}!!!')
        message = f'Subject:{subject_text}\n\n{message_text}'
        self.smtpObj.sendmail('rivne.price.tracker@gmail.com',
                              email, message)

    def disconnect_smtp(self):
        self.smtpObj.quit()


reebok_price = PriceTracker('list.xlsx')

iteration_number = 0
while True:
    iteration_number += 1
    print(f'\n{Style.BRIGHT}Iteration #{iteration_number}{Style.RESET_ALL}\n')
    reebok_price.parse_shop_list()
    time.sleep(random.randint(3600, 4500))
