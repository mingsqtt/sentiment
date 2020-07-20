import re
import requests
import json
import math
import time


# import pymongo


class TaoBaoCommentByLogin:
    def __init__(self):
        self.target_url = 'https://item.taobao.com/item.htm?spm=a21wu.241046-cn.4691948847.13.41cab6cbAYOzKx&scm=1007.15423.84311.100200300000001&id=528372171237&pvid=16c7deb2-025d-4cfd-be2e-a8ab29f3eef0'
        # self.target_url = 'https://item.taobao.com/item.htm?spm=a219r.lm874.14.58.7cd87156tmSUG2&id=579824132873&ns=1&abbucket=18#detail'
        self.raw_url = 'https://rate.taobao.com/feedRateList.htm?'
        self.post_url = 'https://login.taobao.com/member/login.jhtml?'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36',
            'Cookie': 'cookie'  # 登陆后获取，也可以使用session登陆
        }
        self.item_id = self.parse_url(self.target_url)

        self.session = requests.session()

    def parse_url(self, url):
        pattern = re.compile('.*?id=([0-9]+)&.*?', re.S)
        result = re.findall(pattern, url)
        return result[0]

    def login_in(self):
        data = {'TPL_username': 'mingsqtt', 'TPL_password': 'p0249852'}
        post_resp = self.session.post(self.post_url, headers=self.headers, data=data)
        print(post_resp.status_code)

    def get_page(self, pagenum):
        params = {
            'auctionNumId': self.item_id,
            'currentPageNum': pagenum
        }
        resp = requests.get(self.raw_url, params=params, headers=self.headers)
        print(resp.status_code)
        #        resp.encoding = resp.apparent_encoding
        content = re.sub(r'[\n\r()]', '', resp.content.decode(resp.encoding))
        return content

    def get_detail(self, content):
        if content:
            page = json.loads(content)
            if page and ('comments' in page.keys()):
                total = page['total']
                comments = self.get_comment(page)
                return comments, total

    def get_comment(self, page):
        if page and ('comments' in page.keys()):
            detail_list = []
            for comment in page['comments']:
                details = {'date': comment['date']}
                details['num'] = comment['buyAmount']

                if comment['bidPriceMoney']:
                    details['amount'] = comment['bidPriceMoney']['amount']

                if comment['auction']['sku']:
                    details['sku'] = comment['auction']['sku'].replace('&nbsp', '')

                details['comment'] = comment['content']
                if comment['photos']:
                    details['photos'] = [i['url'].replace('_400x400.jpg', '') for i in comment['photos']]

                if comment['append']:
                    details['extra_comment'] = comment['append']['content']
                    if comment['append']['photos']:
                        details['extra_photos'] = [i['url'].replace('_400x400.jpg', '') for i in
                                                   comment['append']['photos']]
                    details['dayAfterConfirm'] = comment['append']['dayAfterConfirm']

                detail_list.append(details)
            return detail_list

    def on_save(self, content):
        if content:
            with open('taobao_reviews.txt', 'a', encoding='utf-8') as f:
                f.write(json.dumps(content, ensure_ascii=False))
                f.write('\n')

    def run(self):
        self.login_in()
        content = self.get_page(1)
        print(content)
        comments, total = self.get_detail(content)
        for comment in comments:
            self.on_save(comment)
        pagenum = math.ceil(total / 20)
        n = 2
        while pagenum >= n:
            content = self.get_page(2)
            time.sleep(5)
            comments, _ = self.get_detail(content)
            for comment in comments:
                self.on_save(comment)
            print('page {} saved'.format(n))
            n += 1


if __name__ == '__main__':
    comment = TaoBaoCommentByLogin()
    comment.run()

