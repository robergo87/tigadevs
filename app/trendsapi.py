"""
Google Trends API unofficial implementation
"""
import time
import json
import csv
import datetime
from os.path import exists
import urllib.parse

import requests

START_URL = "https://trends.google.com/trends/"
EXPLORE_URL = ("https://trends.google.com/trends/api/explore"
               + "?hl=en-US&tz=-120&req=%7B%22comparisonItem%22:%5B%7B%22keyword%22:%22"
               + "{{keyword}}%22,%22geo%22:%22{{country}}%22,%22time%22:%22today+12-m%22"
               + "%7D%5D,%22category%22:0,%22property%22:%22%22%7D&tz=-120"
               )
CSV_URL = "https://trends.google.com/trends/api/widgetdata/multiline/csv"

class TrendsAPIError(Exception):
    """
    Exception class for Google Trends API errors
    """
    def __init__(self, message, error):
        super().__init__(message)
        self.error = error

class TrendsAPISession:
    """
    Session object responisble implementing unofficial Google Trends API
    """
    session = None
    explore_response = {}
    token = ""

    def download_trends_url(self, url, sleep_time=5):
        """ download given url, wait after request, throw exception if error occurs """
        page = self.session.get(url)
        if page.status_code != 200:
            exception_content = {
                "url" : url,
                "status": page.status_code,
                "response": page.text
            }
            raise TrendsAPIError("Unable to load "+url, exception_content)
        time.sleep(sleep_time)
        return page.text

    @staticmethod
    def __cache_path(keyword, country):
        return (
            "cache/"+keyword+'-'+country+'-'
            + datetime.datetime.today().strftime("%Y-%m-%d")
            +'.json'
        )

    def save_to_cache(self, keyword, country, data):
        """ save specified data to trends api cache. Keys: keyword, country """
        file = open(self.__cache_path(keyword, country), 'w')
        file.write(json.dumps(data))
        file.close()

    def load_from_cache(self, keyword, country):
        """ load specified data from trends api cache. Keys: keyword, country """
        path = self.__cache_path(keyword, country)
        if not exists(path):
            return False
        file = open(path, 'r')
        content = file.read()
        file.close()
        return json.loads(content)

    def create_session(self):
        """ initial session creation """
        self.session = requests.Session()
        self.download_trends_url(START_URL)

    def one_time_token(self, keyword, country):
        """ method for obtaining token. Token is unique per keyword, country pair """
        url = EXPLORE_URL.replace("{{country}}", country).replace("{{keyword}}", keyword)
        explore_response_raw = self.download_trends_url(url, sleep_time=0)
        json_start_position = explore_response_raw.find('{"widgets')
        if json_start_position == -1:
            raise TrendsAPIError(
                "Unable to parse api /explore response",
                {"status" : 200, "content" : explore_response_raw}
            )
        explore_response_text = explore_response_raw[json_start_position:]
        try:
            json_content = json.loads(explore_response_text)
            self.explore_response = json_content
            self.token = json_content["widgets"][0]["token"]
        except ValueError:
            raise TrendsAPIError(
                "invalid json api /explore response",
                {"status" : 200, "content" : explore_response_raw}
            )
        except KeyError:
            raise TrendsAPIError(
                "invalid json api /explore response - path 'widgets.0.token'",
                {"status" : 200, "content" : explore_response_text}
            )

    def __csv_url(self, keyword, country):
        today = datetime.datetime.today()
        yearago = today - datetime.timedelta(days=365)
        rep_struct = {
            "time": yearago.strftime("%Y-%m-%d")+"%20"+today.strftime("%Y-%m-%d"),
            "resolution": "WEEK",
            "locale": "en-US",
            "comparisonItem": [
                {
                    "geo":{"country": country},
                    "complexKeywordsRestriction":{
                        "keyword": [
                            {"type": "BROAD", "value": keyword}
                        ]
                    }
                }
            ],
            "requestOptions": {
                "property": "",
                "backend": "IZG",
                "category": 0
            }
        }
        rep_struct_encoded = urllib.parse.urlencode({"req":json.dumps(rep_struct)})
        rep_struct_encoded = rep_struct_encoded.replace("+", "").replace("%2520", "%20")
        get_params = '?'+rep_struct_encoded+"&token="+self.token+"&tz=-120"
        return CSV_URL+get_params

    @staticmethod
    def __parse_csv(output):
        rows = list(csv.reader(output.strip().split("\n")))
        parsed = {}
        for rownum, row in enumerate(rows):
            if rownum in  (0, 1):
                continue
            if rownum == 2:
                cols = list(row)
                for colnum, col in enumerate(cols):
                    if colnum == 0:
                        continue
                    parsed[col] = []
                continue
            date = False
            for num, colval in enumerate(row):
                if num == 0:
                    date = colval
                else:
                    parsed[cols[num]].append((date, colval))
        return parsed

    def get_trends(self, keyword, country, force_refresh=False):
        """
        obtain trends result for specific country, keyword pair
        results are returned as list of tuples (date, value)
        """
        if not force_refresh:
            content = self.load_from_cache(keyword, country)
            if content:
                return content
        if not self.session:
            self.create_session()
        if not self.token:
            self.one_time_token(keyword, country)
        url = self.__csv_url(keyword, country)
        content = self.__parse_csv(self.download_trends_url(url))
        self.save_to_cache(keyword, country, content)
        return content
        