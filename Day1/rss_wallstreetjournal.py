import os
import re, sys
import json
from requests import get
from bs4 import BeautifulSoup
from feedparser import parse

TIMEOUT = 30


def removePunc(phrase):
    phrase=re.sub('&',' and ',phrase)
    phrase=re.sub(u"\"","\'", phrase)
    phrase=re.sub("\%","percent",phrase)
  #  phrase=re.sub(',','\,',phrase)
    return phrase


newsurl = "https://feeds.a.dj.com/rss/RSSOpinion.xml"
newsurl = "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml"
rss = parse(newsurl)
print(rss)

if os.path.exists("data/wsj.json"): os.remove("data/wsj.json")
ffile = open("data/wsj.json","w")

jsonlist = []
print("n_rss_entries: {}".format(len(rss['entries'])))
for i, rss_entry in enumerate(rss['entries']):  # note format can change time to time
    # i, rss_entry = 0, rss['entries'][0]
    # print(rss_entry)
    try:
        url_link = rss_entry['link']
        print("[{}] - {}".format(i, url_link))
        url_content = get(url_link, timeout=TIMEOUT)
        if url_content.ok:
            page = url_content.content.decode('utf-8','ignore')
            soup = BeautifulSoup(page, 'html.parser')
            data = soup.find("div", {"class": "c-rte--article"}).find_all('p')
            content = ""
            for element in data:
                #print (element.text)
                content += element.text.lstrip().rstrip()
            #print (content)
            url_label = removePunc(rss_entry['title'])
            url_id = rss_entry['id']
            url_summary = rss_entry['summary']

            jdata = {"url_id": url_id, "content": {"url_label": url_label,"text":content }}
            jsonlist.append(jdata)
    except Exception as e:
        print(e)
        print (u"Error site for " + url_link)
jdata = json.dump(jsonlist, ffile)
ffile.close()