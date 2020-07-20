import re
import requests
import json
import math
import time
from bs4 import BeautifulSoup
from feedparser import parse
from datetime import datetime

class WsjCrawler:
    def __init__(self):
        self.target_url = 'https://www.wsj.com/articles/rfk-vs-d-c-statehood-11593709155'
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
    crawler = WsjCrawler()
    crawler.run()

headers = {
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36",
    "cookie": "wsjregion=na%2Cus; gdprApplies=false; ccpaApplies=false; ab_uuid=774534ea-c2f4-4196-aa3c-6b39364d614f; usr_bkt=K8ZnHJ5Uyn; cX_P=kc5kxmpb6yqqmmtj; cX_S=kc5kxmphsmv7605f; AMCVS_CB68E4BA55144CAA0A4C98A5%40AdobeOrg=1; vidoraUserId=iacsc6902kksn43ccj8dvgpsopbs97; cX_G=cx%3A1kinj3lutsavz3nks86v72hm7b%3A1t89ahqf778pj; s_cc=true; __gads=ID=000c394d0f8aac50:T=1593742163:S=ALNI_MbBgQbBiqqG0TqNANaHw0QG1mGinQ; _scid=a064e1dd-f716-4b92-8e35-aa7c684a6be5; bkuuid=snqZnIhn9991t%2BNK; hok_seg=none; _rdt_uuid=1593742164885.5cdaa13a-bfa5-4c90-9a33-0b4c78d35ee8; _fbp=fb.1.1593742164961.1443149506; _sctr=1|1593705600000; OB-USER-TOKEN=db3ffa31-1962-4840-9f85-05be3075804e; djcs_route=765a376b-de75-4574-8491-cd622798b62e; TR=V2-a899baead6153017888d6c96452606d944c0146335c06e3bcd2934be934ac2f4; djcs_auto=M1593723824%2FnuT%2Bc2mJO7UW8sT4WOJeEsjW0lJFrLYroLTvgn%2FX%2BwUAPFT2%2Fxc4lcnYvuWot%2BB4BvXSbdAkTArb%2BlnN8NNsK5vCwB46MJIpu9iLm6y%2FXR4Fc8FrJnu6ogQGbOlVj1ngdbkBnaAgQRxXnm%2B60Fypmau4e0Kifr%2Fe8eGzVyFnyndYeW23Bd6eVjPbU0auKHIoIZQv2aoHkHYWcCp7Bxz0A3PhDpECjAnYdMuGPzjznVB7Mcaza%2Fr8tCEV3T%2B93bayY3CpVOCqhltpcUb0PeAL8o2%2F2vSZLH%2FaNXkrmWJsbjOc5W9z2ucl%2BaVdvCRotxejG1ZFOV5r0hHyqUOu3bfNpNNvpR5Ff%2BGRPD%2B4RoOXPmxtw9PoXCtePwk%2F0brHjayFskE9BA%2F94sL0RQyWYKo4YQ%3D%3DG; djcs_session=M1593737028%2FGUzsA%2BT1nSflevNJ02qftSbBxStiTzkyN5Y1HmuDYXAzs%2F22oUsFWX0CO77gm8axhfYHRs9qwzQgwyiJiIEOiIaJhfTaNHEse2cviFGxBXEyJGXlluFk%2FxEM5WYkr1gmDJtN6mYf4Yy%2FTQ5uTN6tT%2BEd3ofNyw9NOEv66CbbpmvgYusKISVVB%2F04GRYej8mLtOhgl4DLcCyuFZ%2FVWplbVMtI7ODNZb%2F0erVpyR2rI1spjxXfwikPJ2A7dGdEXHnlBO8OMwKVONpa%2BFm8W4lKBm0mFunZhlRdQpLQ%2FE%2F5STHGxbPF2HsGt%2BDAl2VkJu6TeEU3FyDDeIbDdXxj0gACIKbUqHH6iesVAyNTIlc4YsGOgaGK85JgK1pCnWUyX1aSRTssP0GhIn137vnLH0h%2BzFW2gZPPG8gYwqjljsQn65%2FfkyMaosJgXV%2BS%2Fq5QyJWix7J%2FEo5Q%2FwFA3pRumNoEd1arCaym4WYYB5k4Gx6ZTuo%3DG; kuid=vbye9rs23; _ncg_id_=172cf71c38e-099ef3d1-a98a-402e-a136-7b6e85cecd9e; usr_prof_v2=eyJwIjp7InBzIjowLjk2LCJxIjowLjkxfSwiY3AiOnsiZWMiOiJObyBIaXN0b3J5IiwicGMiOjAuMDUwOTMsInBzciI6MC4yNzExNSwidGQiOjE1LCJhZCI6MywicWMiOjc4LCJxbyI6NzksInNjZW4iOnsiY2hlIjowLjA0ODksImNobiI6MC4wNDIwNiwiY2hhIjowLjA0Mzk5LCJjaHAiOjAuMDUzNX19LCJpYyI6N30%3D; _ncg_g_id_=fc62237c-c65c-4a19-be6b-5f5e95967b68; s_sq=%5B%5BB%5D%5D; utag_main=v_id:0173126f7e0a0041d5faf3e23ef403079005307100bd0$_sn:3$_se:1$_ss:1$_st:1593769267346$vapi_domain:wsj.com$ses_id:1593767467346%3Bexp-session$_pn:1%3Bexp-session$_prevpage:WSJ_Article_Opinion_RFK%20vs.%20D.C.%20Statehood%3Bexp-1593771067352; AMCV_CB68E4BA55144CAA0A4C98A5%40AdobeOrg=1585540135%7CMCIDTS%7C18447%7CMCMID%7C05537579202809907891925495016448841815%7CMCAAMLH-1594372267%7C3%7CMCAAMB-1594372267%7CRKhpRz8krg2tLO6pguXWp5olkAcUniQYPHaMWWgdJ3xzPWQmdj0y%7CMCOPTOUT-1593774667s%7CNONE%7CMCAID%7CNONE%7CvVersion%7C4.4.0; _ncg_sp_id.5378=8daa77e7-f0c9-4f6d-b458-37c5b5412ee1.1593742164.1.1593767468.1593742164.9778a1b2-c154-42f2-a61c-1e5f84341aea; _tq_id.TV-63639009-1.1fc3=77e034c449c42859.1593742165.0.1593767469..; _am_sp_djcsses.1fc3=*; _parsely_session={%22sid%22:5%2C%22surl%22:%22https://www.wsj.com/articles/rfk-vs-d-c-statehood-11593709155%22%2C%22sref%22:%22%22%2C%22sts%22:1593785280559%2C%22slts%22:1593767465719}; _parsely_visitor={%22id%22:%22pid=55393675cb41001e2801be949f7aff7c%22%2C%22session_count%22:5%2C%22last_session_ts%22:1593785280559}; s_tp=6417; s_ppv=WSJ_Article_Opinion_RFK%2520vs.%2520D.C.%2520Statehood%2C28%2C17%2C1813; _am_sp_djcsid.1fc3=166e06f9-b8e9-420d-8342-60d1c05a60e5.1593742164.5.1593786877.1593768709.f8f15fb7-1d38-406e-8edf-7d786b4e5d77; GED_PLAYLIST_ACTIVITY=W3sidSI6IlVHNUsiLCJ0c2wiOjE1OTM3ODY4NzksIm52IjowLCJ1cHQiOjE1OTM3Njc0NjYsImx0IjoxNTkzNzg2ODY3fV0."
}
params = {}
article_url = 'https://www.wsj.com/articles/rfk-vs-d-c-statehood-11593709155'
comment_url = "https://commenting.wsj.com/api/v1/graph/ql"
resp = requests.get(article_url, params=params, headers=headers)
if resp.status_code == 200:
    content = re.sub(r'[\n\r()]', '', resp.content.decode(resp.encoding))
    soup = BeautifulSoup(content, 'html.parser')
    header_tag = soup.find("h1", {"class": "wsj-article-headline"})
    subheader_tag = soup.find("h2", {"class": "sub-head"})
    time_tag = soup.find("time", {"class": "timestamp"})
    article_para_tags = soup.find("div", {"class": "article-content"}).find_all("p")
    if header_tag is not None:
        header_text = header_tag.getText().strip()
    if subheader_tag is not None:
        subheader_text = subheader_tag.getText().strip()
    if time_tag is not None:
        time_text = time_tag.getText().strip()
        if time_text.find("ET") > 0:
            article_time = datetime.strptime(time_text, "%B %d, %Y %I:%M %p ET")
        elif time_text.find("PT") > 0:
            article_time = datetime.strptime(time_text, "%B %d, %Y %I:%M %p PT")
        else:
            article_time = datetime.strptime(time_text, "%B %d, %Y %I:%M %p")
    article_content = "\n\n".join([p.getText().strip() for p in article_para_tags])

    token_url = "https://commenting.wsj.com/api/v1/auth/dj/token"
    resp = requests.get(token_url, params={}, headers=headers)
    if resp.status_code == 200:
        token = json.loads(re.sub(r'[\n\r()]', '', resp.content.decode(resp.encoding)))["token"]

    paylod = {
        "operationName": "CoralEmbedStream_Embed",
        "variables": {
            "assetId": "",
            "assetUrl": article_url,
            "commentId": "",
            "hasComment": False,
            "excludeIgnored": True,
            "sortBy": "CREATED_AT",
            "sortOrder": "DESC"
        },
        "query": "query CoralEmbedStream_Embed($assetId: ID, $assetUrl: String, $commentId: ID!, $hasComment: Boolean!, $excludeIgnored: Boolean, $sortBy: SORT_COMMENTS_BY!, $sortOrder: SORT_ORDER!) { me { id state { status { username { status __typename } banned { status __typename } alwaysPremod { status __typename } suspension { until __typename } __typename } __typename } __typename } asset(id: $assetId, url: $assetUrl) { ...CoralEmbedStream_Configure_asset ...CoralEmbedStream_Stream_asset ...CoralEmbedStream_AutomaticAssetClosure_asset __typename } ...CoralEmbedStream_Stream_root ...CoralEmbedStream_Configure_root } fragment CoralEmbedStream_Stream_root on RootQuery { me { state { status { username { status __typename } banned { status __typename } alwaysPremod { status __typename } suspension { until __typename } __typename } __typename } ignoredUsers { id __typename } role __typename } settings { organizationName __typename } ...TalkSlot_StreamTabPanes_root ...TalkSlot_StreamFilter_root ...TalkSlot_Stream_root ...CoralEmbedStream_Comment_root __typename } fragment CoralEmbedStream_Comment_root on RootQuery { me { ignoredUsers { id __typename } __typename } ...TalkSlot_CommentInfoBar_root ...TalkSlot_CommentAuthorName_root ...TalkEmbedStream_DraftArea_root ...TalkEmbedStream_DraftArea_root __typename } fragment TalkEmbedStream_DraftArea_root on RootQuery { __typename } fragment CoralEmbedStream_Stream_asset on Asset { comment(id: $commentId) @include(if: $hasComment) { ...CoralEmbedStream_Stream_comment parent { ...CoralEmbedStream_Stream_singleComment parent { ...CoralEmbedStream_Stream_singleComment parent { ...CoralEmbedStream_Stream_singleComment __typename } __typename } __typename } __typename } id title url isClosed created_at settings { moderation infoBoxEnable infoBoxContent premodLinksEnable questionBoxEnable questionBoxContent questionBoxIcon closedTimeout closedMessage disableCommenting disableCommentingMessage charCountEnable charCount requireEmailConfirmation __typename } totalCommentCount @skip(if: $hasComment) comments(query: {limit: 10, excludeIgnored: $excludeIgnored, sortOrder: $sortOrder, sortBy: $sortBy}) @skip(if: $hasComment) { nodes { ...CoralEmbedStream_Stream_comment __typename } hasNextPage startCursor endCursor __typename } ...TalkSlot_StreamTabsPrepend_asset ...TalkSlot_StreamTabPanes_asset ...TalkSlot_StreamFilter_asset ...CoralEmbedStream_Comment_asset __typename } fragment CoralEmbedStream_Comment_asset on Asset { __typename id ...TalkSlot_CommentInfoBar_asset ...TalkSlot_CommentActions_asset ...TalkSlot_CommentReactions_asset ...TalkSlot_CommentAuthorName_asset } fragment CoralEmbedStream_Stream_comment on Comment { id status user { id __typename } ...CoralEmbedStream_Comment_comment __typename } fragment CoralEmbedStream_Comment_comment on Comment { ...CoralEmbedStream_Comment_SingleComment replies(query: {limit: 3, excludeIgnored: $excludeIgnored}) { nodes { ...CoralEmbedStream_Comment_SingleComment replies(query: {limit: 3, excludeIgnored: $excludeIgnored}) { nodes { ...CoralEmbedStream_Comment_SingleComment replies(query: {limit: 3, excludeIgnored: $excludeIgnored}) { nodes { ...CoralEmbedStream_Comment_SingleComment __typename } hasNextPage startCursor endCursor __typename } __typename } hasNextPage startCursor endCursor __typename } __typename } hasNextPage startCursor endCursor __typename } __typename } fragment CoralEmbedStream_Comment_SingleComment on Comment { id body created_at status replyCount tags { tag { name __typename } __typename } user { id username __typename } status_history { type __typename } action_summaries { __typename count current_user { id __typename } } editing { edited editableUntil __typename } ...TalkSlot_CommentInfoBar_comment ...TalkSlot_CommentActions_comment ...TalkSlot_CommentReactions_comment ...TalkSlot_CommentAuthorName_comment ...TalkSlot_CommentAuthorTags_comment ...TalkSlot_CommentContent_comment ...TalkEmbedStream_DraftArea_comment ...TalkEmbedStream_DraftArea_comment __typename } fragment TalkEmbedStream_DraftArea_comment on Comment { __typename ...TalkSlot_DraftArea_comment } fragment CoralEmbedStream_Stream_singleComment on Comment { id status user { id __typename } ...CoralEmbedStream_Comment_SingleComment __typename } fragment CoralEmbedStream_Configure_root on RootQuery { __typename ...CoralEmbedStream_Settings_root } fragment CoralEmbedStream_Settings_root on RootQuery { __typename } fragment CoralEmbedStream_Configure_asset on Asset { __typename ...CoralEmbedStream_AssetStatusInfo_asset ...CoralEmbedStream_Settings_asset } fragment CoralEmbedStream_AssetStatusInfo_asset on Asset { id closedAt isClosed __typename } fragment CoralEmbedStream_Settings_asset on Asset { id settings { moderation premodLinksEnable questionBoxEnable questionBoxIcon questionBoxContent __typename } __typename } fragment CoralEmbedStream_AutomaticAssetClosure_asset on Asset { id closedAt __typename } fragment TalkSlot_StreamTabPanes_root on RootQuery { ...TalkFeaturedComments_TabPane_root __typename } fragment TalkFeaturedComments_TabPane_root on RootQuery { __typename ...TalkFeaturedComments_Comment_root } fragment TalkFeaturedComments_Comment_root on RootQuery { __typename ...TalkSlot_CommentAuthorName_root } fragment TalkSlot_StreamFilter_root on RootQuery { ...TalkViewingOptions_ViewingOptions_root __typename } fragment TalkViewingOptions_ViewingOptions_root on RootQuery { __typename } fragment TalkSlot_Stream_root on RootQuery { ...Talk_AccountDeletionRequestedSignIn_root __typename } fragment Talk_AccountDeletionRequestedSignIn_root on RootQuery { me { scheduledDeletionDate __typename } __typename } fragment TalkSlot_CommentInfoBar_root on RootQuery { ...TalkModerationActions_root __typename } fragment TalkModerationActions_root on RootQuery { me { id __typename } __typename } fragment TalkSlot_CommentAuthorName_root on RootQuery { ...TalkAuthorMenu_AuthorName_root __typename } fragment TalkAuthorMenu_AuthorName_root on RootQuery { __typename ...TalkSlot_AuthorMenuActions_root } fragment TalkSlot_StreamTabsPrepend_asset on Asset { ...TalkFeaturedComments_Tab_asset __typename } fragment TalkFeaturedComments_Tab_asset on Asset { featuredCommentsCount: totalCommentCount(tags: [\"FEATURED\"]) @skip(if: $hasComment) __typename } fragment TalkSlot_StreamTabPanes_asset on Asset { ...TalkFeaturedComments_TabPane_asset __typename } fragment TalkFeaturedComments_TabPane_asset on Asset { id featuredComments: comments(query: {tags: [\"FEATURED\"], sortOrder: $sortOrder, sortBy: $sortBy, excludeIgnored: $excludeIgnored}, deep: true) @skip(if: $hasComment) { nodes { ...TalkFeaturedComments_Comment_comment __typename } hasNextPage startCursor endCursor __typename } ...TalkFeaturedComments_Comment_asset __typename } fragment TalkFeaturedComments_Comment_comment on Comment { id body created_at replyCount tags { tag { name __typename } __typename } user { id username __typename } ...TalkSlot_CommentReactions_comment ...TalkSlot_CommentAuthorName_comment ...TalkSlot_CommentContent_comment __typename } fragment TalkFeaturedComments_Comment_asset on Asset { __typename ...TalkSlot_CommentReactions_asset ...TalkSlot_CommentAuthorName_asset } fragment TalkSlot_StreamFilter_asset on Asset { ...TalkViewingOptions_ViewingOptions_asset __typename } fragment TalkViewingOptions_ViewingOptions_asset on Asset { __typename } fragment TalkSlot_CommentInfoBar_asset on Asset { ...TalkModerationActions_asset __typename } fragment TalkModerationActions_asset on Asset { id __typename } fragment TalkSlot_CommentActions_asset on Asset { ...TalkPermalink_Button_asset __typename } fragment TalkPermalink_Button_asset on Asset { url __typename } fragment TalkSlot_CommentReactions_asset on Asset { ...LikeButton_asset __typename } fragment LikeButton_asset on Asset { id __typename } fragment TalkSlot_CommentAuthorName_asset on Asset { ...TalkAuthorMenu_AuthorName_asset __typename } fragment TalkAuthorMenu_AuthorName_asset on Asset { __typename } fragment TalkSlot_CommentInfoBar_comment on Comment { ...TalkFeaturedComments_Tag_comment ...TalkModerationActions_comment __typename } fragment TalkFeaturedComments_Tag_comment on Comment { tags { tag { name __typename } __typename } __typename } fragment TalkModerationActions_comment on Comment { id status user { id __typename } tags { tag { name __typename } __typename } __typename } fragment TalkSlot_CommentActions_comment on Comment { ...TalkPermalink_Button_comment __typename } fragment TalkPermalink_Button_comment on Comment { id __typename } fragment TalkSlot_CommentReactions_comment on Comment { ...LikeButton_comment __typename } fragment LikeButton_comment on Comment { id action_summaries { __typename ... on LikeActionSummary { count current_user { id __typename } __typename } } __typename } fragment TalkSlot_CommentAuthorName_comment on Comment { ...UserAvatar_comment ...TalkAuthorMenu_AuthorName_comment __typename } fragment UserAvatar_comment on Comment { user { avatar username vxid __typename } __typename } fragment TalkAuthorMenu_AuthorName_comment on Comment { __typename id user { username __typename } ...TalkSlot_AuthorMenuActions_comment } fragment TalkSlot_CommentAuthorTags_comment on Comment { ...TalkSubscriberBadge_SubscriberBadge_comment __typename } fragment TalkSubscriberBadge_SubscriberBadge_comment on Comment { user { tags { tag { name __typename } __typename } __typename } __typename } fragment TalkSlot_CommentContent_comment on Comment { ...TalkPluginRichText_CommentContent_comment __typename } fragment TalkPluginRichText_CommentContent_comment on Comment { body richTextBody __typename } fragment TalkSlot_DraftArea_comment on Comment { ...TalkPluginRichText_Editor_comment __typename } fragment TalkPluginRichText_Editor_comment on Comment { body richTextBody __typename } fragment TalkSlot_AuthorMenuActions_root on RootQuery { ...TalkIgnoreUser_IgnoreUserAction_root __typename } fragment TalkIgnoreUser_IgnoreUserAction_root on RootQuery { me { id __typename } __typename } fragment TalkSlot_AuthorMenuActions_comment on Comment { ...ProfileLink_comment ...TalkIgnoreUser_IgnoreUserAction_comment __typename } fragment ProfileLink_comment on Comment { user { vxid __typename } __typename } fragment TalkIgnoreUser_IgnoreUserAction_comment on Comment { user { id __typename } ...TalkIgnoreUser_IgnoreUserConfirmation_comment __typename } fragment TalkIgnoreUser_IgnoreUserConfirmation_comment on Comment { user { id username __typename } __typename } "
    }
    headers["cookie"] = "wsjregion=na%2Cus; ab_uuid=774534ea-c2f4-4196-aa3c-6b39364d614f; usr_bkt=K8ZnHJ5Uyn; cX_P=kc5kxmpb6yqqmmtj; cX_G=cx%3A1kinj3lutsavz3nks86v72hm7b%3A1t89ahqf778pj; __gads=ID=000c394d0f8aac50:T=1593742163:S=ALNI_MbBgQbBiqqG0TqNANaHw0QG1mGinQ; _scid=a064e1dd-f716-4b92-8e35-aa7c684a6be5; bkuuid=snqZnIhn9991t%2BNK; hok_seg=none; _fbp=fb.1.1593742164961.1443149506; _sctr=1|1593705600000; OB-USER-TOKEN=db3ffa31-1962-4840-9f85-05be3075804e; djcs_route=765a376b-de75-4574-8491-cd622798b62e; TR=V2-a899baead6153017888d6c96452606d944c0146335c06e3bcd2934be934ac2f4; _ncg_id_=172cf71c38e-099ef3d1-a98a-402e-a136-7b6e85cecd9e; _ncg_g_id_=fc62237c-c65c-4a19-be6b-5f5e95967b68; gdprApplies=false; ccpaApplies=false; djcs_auto=M1593723824%2FOUfHMl%2FLoFwBQq5%2FxT2WepbUC%2FI09DK9o14aKfzalaVTgIjEGH4FZj5g8Snhibs98P6%2Bj%2BES5IoA0bgpRFklQmFxX6ddzXOYlvIEcE2JL2eAXMFAU8bPn2MY5lSgQAZUneppVvAuc3LznrznqIiQarOOvMcT2a%2BH75wwo9t%2Byb7oQxBPbrbkrpDe5QGkgz%2BYUn8j4J5TC3l6NhtVs148DSFn5EZoERJ1mhky89i%2FM6jenl8S17bqUf%2FTLmcQkHkSHpxB5U2sJPqHTW26a5zChucEvcWh8Mww%2BH62liW1U2mBPpmBSQUu2xAHhLcFix7EzmpqfbrhVoh5F5E3AyxojA%2BS15WDWpFgf72WOxdAFI%2BUVQdgJJg8sj%2BHaYJRM%2BtT81QJjqvcaBMbXuamyxfkwQ%3D%3DG; djcs_session=M1593787428%2FWhTjHcviR5ggoL8LFJoNIHc%2B7eHBMXevOVRYwqR0dbnIAyGshpQ5xzoI3CkcmbcEPNQS2s%2FFjIXHd0gFQ9ivZku19CY6E3nGyC5HFOwJGXswVcbS%2FnhZ2Rs8XZBNhnix0DFhzZDwFXNRh3bhD1z%2FPj00PBwYwaRrCGjrT5SZBoXhW6ypL79dvMSMgU%2B5WdhRztBWoVzHjRpW9Zv%2BUyU0zKgWZEH7RCCZ2Mjdqf%2F9AuP%2Fz7Mz7PJ8e%2BxOkjqIXseiQ6QRmeWnEXyZoHOUgj0HNRQEfq4GTDAJT%2BMgCwQcmjp21DULG23So3Py4%2BHbb4Yt7DwTEz56weeu6Si7GyKFP4nlXuRNL115dXTDU61hE7VcL%2F2ZENtvC1mK5BbmAoPK6yIM71TrSfBzOV5lOlze%2B9Lvt3P%2By6lOhFPUi38I5IY8LEnr1NZC1UBdfUqDU%2FZzWnGVTMuOaoERJzAKVavAdjV6H6QpJFNDTYedD6BFQrbXu4L0Zw9MCnvzb1k3%2FInHG; cX_S=kc6dccwqmj7rr4xp; AMCVS_CB68E4BA55144CAA0A4C98A5%40AdobeOrg=1; kuid=vbye9rs23; s_cc=true; usr_prof_v2=eyJwIjp7InBzIjowLjk2LCJxIjowLjkxfSwiY3AiOnsiZWMiOiJObyBIaXN0b3J5IiwicGMiOjAuMDUwOTMsInBzciI6MC4yNzExNSwidGQiOjE1LCJhZCI6MywicWMiOjc4LCJxbyI6NzksInNjZW4iOnsiY2hlIjowLjA0ODksImNobiI6MC4wNDIwNiwiY2hhIjowLjA0Mzk5LCJjaHAiOjAuMDUzNX19LCJpYyI6N30%3D; _parsely_session={%22sid%22:6%2C%22surl%22:%22https://www.wsj.com/articles/rfk-vs-d-c-statehood-11593709155%22%2C%22sref%22:%22%22%2C%22sts%22:1593828124119%2C%22slts%22:1593785280559}; _parsely_visitor={%22id%22:%22pid=55393675cb41001e2801be949f7aff7c%22%2C%22session_count%22:6%2C%22last_session_ts%22:1593828124119}; utag_main=v_id:0173126f7e0a0041d5faf3e23ef403079005307100bd0$_sn:7$_se:1$_ss:1$_st:1593829926241$vapi_domain:wsj.com$ses_id:1593828126241%3Bexp-session$_pn:1%3Bexp-session$_prevpage:WSJ_Article_Opinion_RFK%20vs.%20D.C.%20Statehood%3Bexp-1593831726250; AMCV_CB68E4BA55144CAA0A4C98A5%40AdobeOrg=1585540135%7CMCIDTS%7C18447%7CMCMID%7C05537579202809907891925495016448841815%7CMCAAMLH-1594432926%7C3%7CMCAAMB-1594432926%7CRKhpRz8krg2tLO6pguXWp5olkAcUniQYPHaMWWgdJ3xzPWQmdj0y%7CMCOPTOUT-1593835326s%7CNONE%7CMCAID%7CNONE%7CvVersion%7C4.4.0; _ncg_sp_ses.5378=*; _ncg_sp_id.5378=8daa77e7-f0c9-4f6d-b458-37c5b5412ee1.1593742164.1.1593828127.1593742164.9778a1b2-c154-42f2-a61c-1e5f84341aea; s_sq=djglobal%3D%2526c.%2526a.%2526activitymap.%2526page%253DWSJ_Article_Opinion_RFK%252520vs.%252520D.C.%252520Statehood%2526link%253DSHOW%252520CONVERSATION%252520%252528368%252529%2526region%253Dcoral-container%2526pageIDType%253D1%2526.activitymap%2526.a%2526.c%2526pid%253DWSJ_Article_Opinion_RFK%252520vs.%252520D.C.%252520Statehood%2526pidt%253D1%2526oid%253DSHOW%252520CONVERSATION%25250A%252528368%252529%2526oidt%253D3%2526ot%253DSUBMIT; connect.sid=s%3AcUzMLkbXCWvmpN91mwg8VkNKxNAK_lwt.O9o72TV0p2RDjg5FMI0%2F9ha56w8B2TDerCEKHlA0iqE; s_tp=6304; s_ppv=WSJ_Article_Opinion_RFK%2520vs.%2520D.C.%2520Statehood%2C87%2C87%2C5481; AWSALB=2tUy7NxOFNMqq1OiyoBO45TJcEROb5HLDRsTk5iyY1eDhu2kBTx4ofMHHqqGVUC9nMXM8wxpgxlf/zP455XXmaQwU0QkApzvT1qKQtTfuY9rRiWNhc7JuKhAV84p; AWSALBCORS=2tUy7NxOFNMqq1OiyoBO45TJcEROb5HLDRsTk5iyY1eDhu2kBTx4ofMHHqqGVUC9nMXM8wxpgxlf/zP455XXmaQwU0QkApzvT1qKQtTfuY9rRiWNhc7JuKhAV84p"
    headers["referer"] = "https://commenting.wsj.com/embed/stream?asset_url=https%3A%2F%2Fwww.wsj.com%2Farticles%2Frfk-vs-d-c-statehood-11593709155&initialWidth=0&childId=coral_talk_SB11571365534377524600504586480402702889680&parentTitle=RFK%20vs.%20D.C.%20Statehood%20-%20WSJ&parentUrl=https%3A%2F%2Fwww.wsj.com%2Farticles%2Frfk-vs-d-c-statehood-11593709155"
    headers["authorization"] = "Bearer " + token
    headers["authority"] = "commenting.wsj.com"
    headers["content-type"] = "application/json"
    resp = requests.post(comment_url, data=paylod, headers=headers)
    print(resp)
#     < h1
#
#
#     class ="wsj-article-headline" >
#
#
#     RFK
#     vs.D.C.Statehood
# < / h1 >
else:
    print(resp)