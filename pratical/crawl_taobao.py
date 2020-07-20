import re
import requests
import json
import math
import time


# import pymongo


class TaoBaoComment:
    def __init__(self):
        self.target_url = 'https://item.taobao.com/item.htm?spm=a21wu.241046-cn.4691948847.13.41cab6cbAYOzKx&scm=1007.15423.84311.100200300000001&id=528372171237&pvid=16c7deb2-025d-4cfd-be2e-a8ab29f3eef0'
        self.raw_url = 'https://rate.taobao.com/feedRateList.htm?'
        self.post_url = 'https://login.taobao.com/member/login.jhtml?'
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36',
            'cookie':   't=3ce6092a544f48bebe64e815e76cc7eb; cna=xKBkF6Mof0ACAdtLdp+UwYCo; lgc=mingsqtt; tracknick=mingsqtt; enc=nSCjRnjnFaaGdf3ti2U3dqqo5s7RWNO0FTtBRCYjG5z2wzPD4SOjxpwyuaMExVRZJBvCq0uWewU8zWob4wHouQ%3D%3D; hng=CN%7Czh-CN%7CCNY%7C156; thw=cn; UM_distinctid=1729212aaeb348-0cd2c976923011-143f6257-1fa400-1729212aaec98e; _fbp=fb.1.1591613621069.1440142622; _m_h5_tk=6b4eb4de4914b64a5d116692eb6cdab6_1593422742123; _m_h5_tk_enc=3538634479d2b2f7b9727fe94375c3fb; v=0; cookie2=12821a9f2e29d5d4892fb9a272285e3f; _tb_token_=e3debe9e379f3; _samesite_flag_=true; sgcookie=EQx%2BXhIHgBqh%2B1m4phmhT; unb=113486842; uc3=id2=UoCKFTKvcERO&lg2=Vq8l%2BKCLz3%2F65A%3D%3D&nk2=Dlkyc45XWzo%3D&vt3=F8dBxGJsyCC%2FunsD5mc%3D; csg=21da68be; cookie17=UoCKFTKvcERO; dnk=mingsqtt; skt=98069aa6f7d33d63; existShop=MTU5MzQxNDQ3Mw%3D%3D; uc4=nk4=0%40DDxxo1CInlW0C5U7EQx%2FXxLByg%3D%3D&id4=0%40UOg2sTzvjfcvSmQOA6dtyOpWm4I%3D; _cc_=W5iHLLyFfA%3D%3D; _l_g_=Ug%3D%3D; sg=t2b; _nk_=mingsqtt; cookie1=WvdDm%2BJMWP5NP534Dyk2lFLtMhQvoKimUTSPmIgD1Wo%3D; tfstk=c_bABPGxL7hYjFRRTiEkftMBiJPhZCw9Fj9iW5PZqduQBhuOiM_hJIqQcCMvy7C..; mt=ci=6_1; uc1=cookie14=UoTV75eOjLkc3A%3D%3D&pas=0&cookie16=VT5L2FSpNgq6fDudInPRgavC%2BQ%3D%3D&cookie21=VT5L2FSpczFp&existShop=false&cookie15=U%2BGCWk%2F75gdr5Q%3D%3D; l=eBO7mRGrQVRZ6rSkKOfwourza77OSIRAguPzaNbMiOCP9M5e5vFfWZY_b38wC3GNh6-yR3RuWvqMBeYBcn4wsWRKe5DDwQHmn; isg=BJ6eIceNTDC3-Jhwyl_Dzx_V7zLgX2LZTpzq9UgnCuHcaz5FsO-y6cQJZ3_n01rx',
            "referer": self.target_url
        }
        self.item_id = self.parse_url(self.target_url)

    #        self.session = requests.session()

    def parse_url(self, url):
        pattern = re.compile('.*?id=([0-9]+)&.*?', re.S)
        result = re.findall(pattern, url)
        return result[0]

    #    def login_in(self):
    #        data = {'TPL_username': 'xxx', 'TPL_password': 'xxx'}
    #        post_resp = self.session.post(self.post_url, headers=self.headers, data=data)
    #        print(post_resp.status_code)

    def get_page(self, pagenum):
        params = {
            'auctionNumId': self.item_id,
            'currentPageNum': pagenum
        }
        resp = requests.get(self.raw_url, params=params, headers=self.headers)
        print(resp.status_code)
        #        resp.encoding = resp.apparent_encoding
        content = re.sub(r'[\n\r()]', '', resp.content.decode(resp.encoding))
        print(content)
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
        # self.login_in()
        content = self.get_page(1)
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
    comment = TaoBaoComment()
    comment.run()

