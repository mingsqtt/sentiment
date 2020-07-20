import re
import requests
import json
import math
import time
from bs4 import BeautifulSoup
from feedparser import parse
from datetime import datetime
import pandas as pd

comment_bodies = list()
sequences = list()
user_locations = list()
user_ids = list()
thumbups = list()

def add_comment(comment):
    comment_bodies.append(comment["commentBody"])
    sequences.append(comment["commentSequence"])
    user_locations.append(comment["userLocation"])
    user_ids.append(comment["userID"])
    thumbups.append(int(comment["recommendations"]))
    print(len(comment_bodies), comment["commentSequence"])

headers = {
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36",
    "cookie": "nyt-gdpr=0; nyt-geo=SG; nyt-a=RO3BWR0AcEJeL73gdi8wyy; nyt-purr=cfhhcfhhhu; _cb_ls=1; purr-cache=<K0<r<C_<G_<S0; b2b_cig_opt=%7B%22isCorpUser%22%3Afalse%7D; edu_cig_opt=%7B%22isEduUser%22%3Afalse%7D; _gcl_au=1.1.782714591.1593870897; __gads=ID=8c6f9c242a0a9d37:T=1593870896:S=ALNI_MZhcuF6JYRzyy3wHSipvJU6no5vYQ; _cb=Du286LDuC3l5C_yquk; walley=GA1.2.1599675869.1593870897; walley_gid=GA1.2.2036054845.1593870897; nyt-us=0; iter_id=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjb21wYW55X2lkIjoiNWMwOThiM2QxNjU0YzEwMDAxMmM2OGY5IiwidXNlcl9pZCI6IjVmMDA4YTM0MTliZjZlMDAwMTBiZGI4NSIsImlhdCI6MTU5Mzg3MDkxN30.aErtMa4WYEd2HJXHrdN2GO17KPDYEVs9_tCR5Ot4Wis; NYT-S=1wd1yohHgFD6yhx5P4DKGmxMzsKrBycxmwt4PoFmK4Ziw2H90o8qFKFvpE/wNg4n3JjOoea6bgYnSmrYRS.71QM7qcxHZKTdfUXfENw/21PcDABtCgvtMS/jxDTQO38FS1; nyt-auth-method=sso; optimizelyEndUserId=oeu1593871302656r0.39252010856446384; FPC=id=1e836e62-1d7d-4156-b04d-93b5816eca4c; WTPERSIST=regi_id=137556607; _fbp=fb.1.1593871308186.1243026391; LPVID=M4Nzk5MGQyYWJkOGYxMzMy; LPSID-17743901=UnWvTHJbRkiINoGDEKxM1g; _pin_unauth=dWlkPU1HSXlPVGczT0RrdFkyVmlZaTAwTVRRM0xXRmlOR1F0TjJObU1qYzNOV0ZpWmpFeQ; datadome=HQo~ovOW2dQA8Yv9pwF0SYTRJkTMLwRLa-Ie7N0s346BzZFS1WeqviS8Va2MYDjdGOQCYWJBWgXpQzBGW3k91qT6WJksx8eYG9b9l77y5z; mnet_session_depth=2%7C1593872013878; nyt-jkidd=uid=137556607&lastRequest=1593872021203&activeDays=%5B0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C1%5D&adv=1&a7dv=1&a14dv=1&a21dv=1&lastKnownType=regi; _chartbeat2=.1593870897213.1593872022933.1.DgYpWuCXmd3r_NMsvD4ZYrSCNLPOR.17; _gat_UA-58630905-2=1; nyt-m=A2AC8CB032EC0FDAD0EB3EFE5FF11B87&iue=i.0&ird=i.0&ira=i.0&s=s.core&ft=i.0&ier=i.0&igf=i.0&l=l.4.2596059587.3473943403.750364181.719790825&n=i.2&fv=i.0&cav=i.0&igd=i.0&e=i.1596240000&prt=i.0&vp=i.0&igu=i.1&ifv=i.0&iir=i.0&rc=i.0&ica=i.0&imv=i.0&pr=l.4.0.0.0.0&g=i.0&er=i.1593876591&vr=l.4.0.0.0.0&iub=i.0&iga=i.0&iru=i.0&uuid=s.4721b302-ac5b-4ea2-a181-f496e64d8d16&v=i.4&imu=i.1&t=i.4"
}
params = {}
article_url = 'https://www.nytimes.com/2020/07/02/opinion/coronavirus-masks.html'
comment_url = "https://commenting.wsj.com/api/v1/graph/ql"
resp = requests.get(article_url, params=params, headers=headers)
if resp.status_code == 200:
    content = re.sub(r'[\n\r()]', '', resp.content.decode(resp.encoding))
    soup = BeautifulSoup(content, 'html.parser')
    article_div_tags = soup.find_all("div", {"class": "StoryBodyCompanionColumn"})
    article_content_paras = list()
    for div in article_div_tags:
        article_content_paras.extend([p.getText().strip() for p in div.find_all("p")])
    with open("coronavirus-masks.txt", "w") as f:
        f.writelines("\n\n".join(article_content_paras))

    encoded_article_url = "https%3A%2F%2Fwww.nytimes.com%2F2020%2F07%2F02%2Fopinion%2Fcoronavirus-masks.html"
    comment_url = "https://www.nytimes.com/svc/community/V3/requestHandler?url=" + encoded_article_url + "&method=get&commentSequence=0&offset=0&includeReplies=true&sort=newest&cmd=GetCommentsAll"
    resp = requests.get(comment_url, params={}, headers=headers)
    if resp.status_code == 200:
        content = re.sub(r'[\n\r()]', '', resp.content.decode("utf-8"))
        comment_result = json.loads(content)
        n_comments = int(comment_result["results"]["totalCommentsFound"])
        if n_comments > 0:
            for comment in comment_result["results"]["comments"]:
                add_comment(comment)

            for page in range(1, math.ceil(n_comments / 25)):
                comment_url = "https://www.nytimes.com/svc/community/V3/requestHandler?url=" + encoded_article_url + "&method=get&commentSequence=0&offset=" + str(page * 25) + "&includeReplies=true&sort=newest&cmd=GetCommentsAll"
                resp = requests.get(comment_url, params={}, headers=headers)
                if resp.status_code == 200:
                    content = re.sub(r'[\n\r()]', '', resp.content.decode("utf-8"))
                    comment_result = json.loads(content)
                    for comment in comment_result["results"]["comments"]:
                        add_comment(comment)

pd.DataFrame({
    "sn": sequences,
    "comment": comment_bodies,
    "user": user_ids,
    "loc": user_locations,
    "thumbups": thumbups
}).to_csv("coronavirus-masks-comments.csv", index=False)

