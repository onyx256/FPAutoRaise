import sys
import time
import json
import requests
import configparser

from bs4 import BeautifulSoup
from datetime import datetime
from requests.structures import CaseInsensitiveDict


class FunPay(object):
    def __init__(self, cookies: str, useragent: str):
        self.s = requests.Session()
        self.useragent = useragent
        self.headers = None
        self.headers_xml = None
        self.uid = None
        self.token = None
        self.cookies = self._parse_cookies(cookies)

    def _get_headers(self, xml: bool) -> CaseInsensitiveDict:
        headers = CaseInsensitiveDict()
        headers["content-type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        headers["cookie"] = self.cookies
        headers["user-agent"] = self.useragent

        if xml:
            headers["x-requested-with"] = "XMLHttpRequest"

        return headers

    def _parse_cookies(self, cookies: str) -> str:
        cookies = json.loads(cookies)

        parsed_cookies = ''

        for i in range(len(cookies)):
            if cookies[i]['name'] == '_ym_d':
                parsed_cookies += f'_ym_d={cookies[i]["value"]}; '
            elif cookies[i]['name'] == '_ym_uid':
                parsed_cookies += f'_ym_uid={cookies[i]["value"]}; '
            elif cookies[i]['name'] == '_ga':
                parsed_cookies += f'_ga={cookies[i]["value"]}; '
            elif cookies[i]['name'] == 'golden_key':
                parsed_cookies += f'golden_key={cookies[i]["value"]}; '
            elif cookies[i]['name'] == 'PHPSESSID':
                parsed_cookies += f'PHPSESSID={cookies[i]["value"]}; '
            elif cookies[i]['name'] == 'ym_isad':
                parsed_cookies += f'ym_isad={cookies[i]["value"]}; '
            elif cookies[i]['name'] == '_gid':
                parsed_cookies += f'_gid={cookies[i]["value"]}; '
            elif cookies[i]['name'] == '_ym_visorc':
                parsed_cookies += f'_ym_visorc={cookies[i]["value"]}; '

        self.cookies = parsed_cookies
        self.headers = self._get_headers(False)
        self.headers_xml = self._get_headers(True)

        self._parse_uid_and_token()

        return parsed_cookies

    def _check_cookies(self) -> bool:
        resp = self.s.get('https://funpay.com/', headers=self.headers)

        if ('log in' in resp.text.lower()) or ('войти' in resp.text.lower()):
            input('Невалидные куки')
            sys.exit()

        return True

    def _parse_uid_and_token(self) -> tuple:
        resp = requests.get('https://funpay.com/', headers=self.headers)

        soup = BeautifulSoup(resp.text, 'lxml')

        data = json.loads(soup.body['data-app-data'])

        uid = data['userId']
        token = data['csrf-token']

        self.uid = uid
        self.token = token

        return uid, token

    def _parse_categories(self) -> list:
        resp = self.s.get(f'https://funpay.com/users/{self.uid}/', headers=self.headers)

        soup = BeautifulSoup(resp.text, 'lxml')

        category_elements = soup.find_all('a', class_='btn btn-default btn-plus')

        categories = []
        categories_count = 0

        for i in range(len(category_elements)):
            url = category_elements[i]['href']

            if 'chips' not in url:
                categories.append(url)

            categories_count = i + 1

        return categories

    def _raise_category(self, category_data: dict) -> bool:
        resp = self.s.post('https://funpay.com/lots/raise', data=category_data, headers=self.headers_xml)

        if 'div' in resp.text:
            time.sleep(1)

            html = json.loads(resp.text)['modal']

            soup = BeautifulSoup(html, 'lxml')

            box = soup.find('div', class_='raise-box')

            node_ids = []

            if box is not None:
                checkboxes = box.find_all('div', class_='checkbox')

                for checkbox in checkboxes:
                    node_ids.append(str(checkbox.find('label').find('input')['value']))

            if len(node_ids) == 0:
                return False

            data = {
                'game_id': category_data['game_id'],
                'node_id': category_data['node_id'],
                'node_ids[]': node_ids
            }

            resp = self.s.post('https://funpay.com/lots/raise', data=data, headers=self.headers_xml)

        if ('подняты' in resp.text) or ('raised' in resp.text):
            now = datetime.now()
            current_time = now.strftime('%H:%M:%S')
            print(f'[{current_time}] - Поднял категорию ({category_data["game_id"]})')

            return True

    def refresh_all(self):
        categories = self._parse_categories()

        for category in categories:
            resp = self.s.get(category, headers=self.headers)

            soup = BeautifulSoup(resp.text, 'lxml')

            btn = soup.find('button', class_='btn btn-default btn-block js-lot-raise')

            data = {
                'game_id': btn['data-game'],
                'node_id': btn['data-node']
            }

            self._raise_category(data)

            time.sleep(3)


def main():
    cfg = configparser.ConfigParser()
    cfg.read('config.ini')

    cooldown = float(cfg['SETTINGS']['Cooldown'])
    useragent = cfg['SETTINGS']['UserAgent']

    with open('cookies.txt', 'r', encoding='utf-8') as f:
        cookies = f.read()

    if cookies == '':
        input('Добавьте куки в файл cookies.txt')
        sys.exit()

    fp = FunPay(cookies, useragent)

    while True:
        try:
            fp.refresh_all()

        except Exception as e:
            print(e)

            time.sleep(60)

        time.sleep(cooldown)


if __name__ == '__main__':
    main()
