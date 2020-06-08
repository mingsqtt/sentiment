import re
import json
from requests import get
from bs4 import BeautifulSoup


def removeIndent(phrase):
    phrase=re.sub("\n",' ',phrase)
    phrase=re.sub("\r",' ',phrase)
    phrase=re.sub("\t",' ',phrase)
    return phrase


yelp_url = "https://www.yelp.com/biz/the-sushi-bar-singapore?osq=Restaurants"
ffile = open("data/yelp_1.json","w")

url_content = get(yelp_url)
page = url_content.content.decode('utf-8','ignore')

soup = BeautifulSoup(page, 'html.parser')
script_tags = soup.findAll("script", type="application/ld+json")
for tag in script_tags:
    if tag.string.find("\"review\"") > 0:
        data = tag.string.lstrip().rstrip()
        data = removeIndent(data)

        jsondata = json.loads(data)
        print(jsondata)
        json.dump(jsondata, ffile)
ffile.close()