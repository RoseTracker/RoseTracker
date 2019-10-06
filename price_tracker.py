#!/usr/bin/env python3
'''price_tracker.py script parse products pages and compares their prices with
your price. all data is stored in google spreadsheets'''


import requests
import re
import bs4
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import smtplib
import time
from colorama import Fore, Style


class PriceTracker(object):
    def __init__(self, shop_list_file):
        self.shop_list_file = shop_list_file

    def scrap_price(self, shop_link, your_price, email):
        print(f'Checking price of product at {Style.BRIGHT}"{shop_link}"\
{Style.RESET_ALL}')
        res = requests.get(shop_link, headers={"User-Agent": "price_tracker.py"})
        res.raise_for_status
        if str(res) == '<Response [404]>':
            error = 'The page was not found'
            print(f'{Fore.RED}{error}{Style.RESET_ALL}\n')
            return error

        soup = bs4.BeautifulSoup(res.text, features="html.parser")
        price = soup.find('span', class_='gl-price__value')
        try:
            price = float(re.sub('[^0-9.]', '', str(price)))
            product_title = soup.find('h1', {'data-auto-id': 'product-title\
'}).text
            print(f'The price of {Style.BRIGHT}"{product_title}"\
{Style.RESET_ALL} is {Style.BRIGHT}"{price}"{Style.RESET_ALL} and your prise \
is {Style.BRIGHT}"{your_price}"{Style.RESET_ALL}')
            if your_price > price:
                self.send_email(email, shop_link, your_price, price)
                print(f'{Fore.GREEN}The price of {Style.BRIGHT}"\
{product_title}"{Style.RESET_ALL}{Fore.GREEN} is low enough. The email was \
sent.\n{Style.RESET_ALL}')
                return True
            else:
                print(f'The price of {Style.BRIGHT}"{product_title}"\
{Style.RESET_ALL} still higher than your. You should to wait.\n')
        except Exception as error:
            print(f'{Fore.RED}{error}{Style.RESET_ALL}\n')
            return error

    def parse_shop_list(self):
        self.smtp_connect()
        regex_url = re.compile(r'^(?:http|ftp)s?://')
        regex_email = '^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$'
        # use creds to create a client to interact with the Google Drive API
        scope = ['https://spreadsheets.google.com/feeds']
        creds = ServiceAccountCredentials.from_json_keyfile_name('rivne-price-tracker-0ea490480fcf.json', scope)
        client = gspread.authorize(creds)
        #work with spreadsheet
        wb = client.open_by_url('https://docs.google.com/spreadsheets/d/1Cv-zzL2YXqEizoH-ewQ0athDOtcjDL_T9xfNbc2YzUE/edit#gid=0')
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
                print(f"{Fore.RED}in row number {row - 1} some fields are empty{Style.RESET_ALL}")
        self.disconnect_smtp()

    def smtp_connect(self):
        self.smtpObj = smtplib.SMTP('smtp.gmail.com', 587)
        self.smtpObj.ehlo()
        self.smtpObj.starttls()
        self.smtpObj.login('rivne.price.tracker@gmail.com', 'p0r4i8c3')

    def send_email(self, email, shop_link, your_price, price):
        subject_text = 'Price of your good was reached your limit!!!'
        message_text = f'The goods price at {shop_link} is {price} that less \
than your price - {your_price}!!!'
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
    time.sleep(10)

