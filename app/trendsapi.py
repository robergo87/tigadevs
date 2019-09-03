import requests
import time
import sys
import json
import csv
import datetime
import urllib.parse
from os.path import exists

def parse_csv_output(output):
    rows = list(csv.reader(output.strip().split("\n")))
    parsed = {}
    for rownum,row in enumerate(rows):
        if rownum == 0 or rownum == 1: 
            continue
        if rownum == 2:
            cols = list(row)
            for colnum,col in enumerate(cols):
                if colnum == 0: continue
                parsed[col] = []
            continue
        date = False
        for num,colval in enumerate(row):
            if num == 0: 
                date = colval
                continue
            parsed[cols[num]].append((date,colval))
    return parsed     
    
def prepare_csv_link(token,keywords,country):
    today = datetime.datetime.today()
    yearago = today - datetime.timedelta(days=365)
    conf = {
        "time": yearago.strftime("%Y-%m-%d")+"%20"+today.strftime("%Y-%m-%d"),
        "resolution":"WEEK",
        "locale":"en-US",
        "comparisonItem":[],
        "requestOptions": {
            "property":"",
            "backend":"IZG",
            "category":0
        }
    }
    for keyword in keywords:
        conf["comparisonItem"].append(
            {"geo":{"country":country},"complexKeywordsRestriction":{"keyword":[{"type":"BROAD","value":keyword}]}}
        )
    return ("https://trends.google.com/trends/api/widgetdata/multiline/csv?"+
        urllib.parse.urlencode({"req":json.dumps(conf)}).replace("+","").replace("%2520","%20")+
        "&token="+token+"&tz=-120"
    )    
    
def save_to_file(keyword,country,data):
    file = open( 
        "cache/"+keyword+'-'+country+'-'+
        datetime.datetime.today().strftime("%Y-%m-%d")+'.json'
    ,'w')
    file.write(json.dumps(data))
    file.close()

def load_from_file(keyword,country):
    path = ("cache/"+keyword+'-'+country+'-'+
        datetime.datetime.today().strftime("%Y-%m-%d")+'.json')
    if not exists(path): return False
    file = open(path,'r')
    content = file.read()
    file.close()
    return json.loads(content)
    
def obtain_keyword_trends(keyword,country):
    content = load_from_file(keyword,country)
    if content: return True,content
    #cache empty - download result
    session = requests.Session() 
    # initial page - obtaining cookies
    START_URL = "https://trends.google.com/trends/"
    start_page = session.get(START_URL)
    if start_page.status_code != 200:
        return (False,START_URL,start_page.status_code,start_page.text)
    time.sleep(5)
    # explore URL - obtaining token
    EXPLORE_URL = "https://trends.google.com/trends/api/explore?hl=en-US&tz=-120&req=%7B%22comparisonItem%22:%5B%7B%22keyword%22:%22"+keyword+"%22,%22geo%22:%22"+country+"%22,%22time%22:%22today+12-m%22%7D%5D,%22category%22:0,%22property%22:%22%22%7D&tz=-120"
    explore_page = session.get(EXPLORE_URL)
    if explore_page.status_code != 200:
        return (False,EXPLORE_URL,explore_page.status_code,explore_page.text)
    # decode malformed JSON    
    json_prefix = '{"widgets'
    json_raw_content = explore_page.text
    json_raw_content = json_raw_content[json_raw_content.find(json_prefix):]
    explore_obj = json.loads(json_raw_content)
    token = explore_obj["widgets"][0]["token"]
    # download CSV
    CSV_URL = prepare_csv_link(token,[keyword],country)
    csv_page = session.get(CSV_URL)
    content = parse_csv_output(csv_page.text)
    save_to_file(keyword,country,content)
    return (True,content)


