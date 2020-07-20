import re
import requests
import json
import math
import time
from bs4 import BeautifulSoup
from feedparser import parse
from datetime import datetime
import pandas as pd
import numpy as np
import spacy
from spacy import displacy

comment_bodies = list()
sequences = list()
user_locations = list()
user_ids = list()
thumbups = list()


headers = {
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36"
}
params = {}
article_url = 'https://forums.hardwarezone.com.sg/apple-clinic-5/macbook-pro-13-2020-a-6277665-8.html'


def crawl_thread(url_template, from_page=1, to_page=500, print_prod_name=None):
    post_list = list()
    if from_page == 1:
        crawl_page(url_template.format(""), post_list)
    for page in range(max(from_page, 2), to_page + 1):
        if print_prod_name is not None:
            print(print_prod_name, "Page", page)
        input_url = url_template.format("-" + str(page))
        output_url = crawl_page(input_url, post_list)
        if input_url != output_url:
            break
    return post_list


def crawl_page(url, post_list):
    resp = requests.get(url, params=params, headers=headers)
    if resp.status_code == 200:
        content = re.sub(r'[\n\r()]', '', resp.content.decode(resp.encoding))
        soup = BeautifulSoup(content, 'html.parser')
        post_div_tags = soup.find_all("div", {"class": "post_message"})
        for post_tag in post_div_tags:
            post_lines = list()
            for child_tag in post_tag.children:
                line = None
                if child_tag.name is not None:
                    if child_tag.name == "div":
                        if (child_tag.attrs is not None) and (child_tag.attrs.__contains__("class")) and (child_tag.attrs["class"][0] == "quote"):
                            pass
                        elif child_tag.find("iframe") is not None:
                            pass
                        else:
                            line = child_tag.getText()
                    elif child_tag.name == "a":
                        if child_tag.find("img") is None:
                            pass
                        else:
                            line = child_tag.getText()
                    elif (child_tag.name == "br") or (child_tag.name == "img"):
                        pass
                    else:
                        line = child_tag.getText()
                else:
                    line = child_tag.strip()

                if line is not None:
                    try:
                        line = line.replace("\ud83d", "").replace("\ud83e", "").replace("\udd14", "").replace("\n", " ").strip().strip('\n')
                        line.encode("utf-8")
                        post_lines.append(line)
                    except UnicodeEncodeError:
                        print(line, url)

            post_text = "\n".join(post_lines).strip()
            if post_text != "":
                post_list.append(post_text)
        return resp.url
    else:
        return None


def remove_lf(text):
    if text.find("\n") > 0:
        return text.replace("\n\n\n\n", "\n").replace("\n\n\n", "\n").replace("\n\n", "\n").replace(",\n", ", ").replace(":\n", ": ").replace(".\n", ". ").replace("!\n", "! ").replace("?\n", "? ").replace("\n", ". ")
    else:
        return text


thread_urls = [
    ("Huawei Matebook 13", "https://forums.hardwarezone.com.sg/notebook-clinic-77/huawei-matebook-13-14-worth-buying-6171793{}.html"),
    ("XPS 15 and XPS 17 2020", "https://forums.hardwarezone.com.sg/notebook-clinic-77/dells-new-xps-15-xps-17-2020-laptops-have-razor-thin-bezels-tons-power-6284506{}.html"),
    ("Chromebook", "https://forums.hardwarezone.com.sg/notebook-clinic-77/%5Bofficial%5D-chromebook-sg-5564364{}.html"),
    ("Huawei Matebook X Pro", "https://forums.hardwarezone.com.sg/notebook-clinic-77/huawei-matebook-x-pro-5835208{}.html"),
    ("Lenovo Ideapad L340", "https://forums.hardwarezone.com.sg/notebook-clinic-77/lenovo-ideapad-l340-15irh-work-light-gaming-6049393{}.html"),
    ("Lenovo Thinkpad", "https://forums.hardwarezone.com.sg/notebook-clinic-77/amd-ryzen-nb-discussion%7C-lenovo-thinkpad-e495-e595-t495-x395-well-rounder-performance-cpu-gpu-5859884{}.html"),
    ("mbp 16", "https://forums.hardwarezone.com.sg/apple-clinic-5/macbook-pro-16-inch-officially-released-6148001{}.html"),
    ("mba 2020", "https://forums.hardwarezone.com.sg/apple-clinic-5/macbook-air-2020-a-6234067{}.html"),
    ("mbp 2020", "https://forums.hardwarezone.com.sg/apple-clinic-5/macbook-pro-13-2020-a-6277665{}.html"),
    ("MBP Battery Swelling", "https://forums.hardwarezone.com.sg/apple-clinic-5/mbp-battery-swelling-6325373{}.html"),
    ("Xiaomi Redmi Ryzen 4000", "https://forums.hardwarezone.com.sg/notebook-clinic-77/xiaomi-redmi-ryzen-4000-laptops-6297066{}.html"),
    ("LG brand 14", "https://forums.hardwarezone.com.sg/notebook-clinic-77/lg-brand-14-laptop-6220521{}.html"),
    ("Lenovo Ideapad 5 14", "https://forums.hardwarezone.com.sg/notebook-clinic-77/lenovo-ideapad-5-14-lazada-atrix-king-budget-laptops-6305043{}.html"),
    ("MAIBENBEN Laptops", "https://forums.hardwarezone.com.sg/notebook-clinic-77/maibenben-laptops-lazada-6259637{}.html"),
]

data = None
for prod, url in thread_urls:
    prod_posts = crawl_thread(url, print_prod_name=prod)
    if data is None:
        data = pd.DataFrame({
            "prod": prod,
            "post": prod_posts
        })
    else:
        data = pd.concat([data, pd.DataFrame({
            "prod": prod,
            "post": prod_posts
        })])

data.to_csv("hardwarezone-posts.csv", index=False, encoding="utf-8")


nlp = spacy.load('en_core_web_lg')

data = pd.read_csv("hardwarezone-posts.csv")

prod_names = list()
post_ids = list()
sents = list()
for i, row in data.iterrows():
    doc = nlp(remove_lf(row["post"]))
    for s, sent in enumerate(doc.sents):
        prod_names.append(row["prod"])
        post_ids.append(i)
        sents.append(sent.text.strip())

pd.DataFrame({
    "prod": prod_names,
    "post": post_ids,
    "sent": sents
}).to_csv("hardwarezone-cents.csv", index=False, encoding="utf-8")
