import requests
import datetime
import re
import json

BASE_URL = "https://www.youtube.com/watch?v="
REQUEST_HEADERS = {'user-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36'}
BASE_CHAT_REPLAY_LINK = "https://www.youtube.com/live_chat_replay/get_live_chat_replay?continuation="
BASE_CHAT_START_LINK = "https://www.youtube.com/live_chat_replay?continuation="


def money_data_from_text(sc_str):
    sc_str = sc_str.replace(',', '')  # 1,000 => 1000
    currency = re.findall(r'(.*?)\d+', sc_str)[0]
    amount = float(re.findall(r'\d+', sc_str)[0])
    return currency.strip(), amount


class CommentGetter:
    def __init__(self, settings):
        self.session = requests.Session()
        self.next_link = ""
        self.lengthSeconds = 0
        self.last_timestamp = 0
        self.comment_data = []
        self.video_link = ""
        self.received_duplicate = False
        self.data_to_research = []
        self.membership_actions = []
        self.debug = settings['debug']

    def get_html_text(self, url):
        return self.session.get(url, headers=REQUEST_HEADERS).text

    def get_comment_link(self, url):
        html = self.get_html_text(url)
        continuation = re.findall('"continuation":"(.*?)"', html)[2]
        self.lengthSeconds = int(re.findall(r'"lengthSeconds":"(\d+)"', html)[0])
        next_link = BASE_CHAT_START_LINK + continuation + '&hidden=false&pbj=1'
        html = self.get_html_text(next_link)
        self._resolve_data(json.loads(html)[1]["response"])
        continuation = json.loads(html)[1]['response']["continuationContents"]["liveChatContinuation"]["continuations"][0]["liveChatReplayContinuationData"]["continuation"]
        next_link = BASE_CHAT_REPLAY_LINK + continuation + '&hidden=false&pbj=1'
        return next_link

    def add_data_to_research(self, data):
        if self.debug:
            print("### Found Data to research ###")
            print(data)
        self.data_to_research.append(data)

    def _pick_data(self, chat_item):
        ms = int(chat_item["replayChatItemAction"]["videoOffsetTimeMsec"])
        self.last_timestamp = ms
        action = chat_item["replayChatItemAction"]["actions"][0]
        add_data = {"text": None, "ms": ms, "author_ch": None, "super_chat": None}
        if "addChatItemAction" in action:
            add_item_action = action["addChatItemAction"]['item']
            if "liveChatTextMessageRenderer" in add_item_action:
                # 通常チャット
                if "simpleText" in add_item_action["liveChatTextMessageRenderer"]["message"]:
                    add_data["text"] = add_item_action["liveChatTextMessageRenderer"]["message"]["simpleText"]
                else:
                    add_data["text"] = ""
                    for elm in add_item_action["liveChatTextMessageRenderer"]["message"]["runs"]:
                        if "text" in elm:
                            add_data["text"] += elm["text"]
                        else:
                            add_data["text"] += elm["emoji"]["shortcuts"][0]
                add_data['author_ch'] = add_item_action["liveChatTextMessageRenderer"]["authorExternalChannelId"]
                return add_data
            if 'liveChatPaidMessageRenderer' in add_item_action:
                # スパチャ
                raw_info = add_item_action['liveChatPaidMessageRenderer']
                if 'message' in raw_info:
                    if "simpleText" in raw_info["message"]:
                        add_data["text"] = raw_info["message"]["simpleText"]
                    else:
                        add_data["text"] = ""
                        for elm in raw_info["message"]["runs"]:
                            if "text" in elm:
                                add_data["text"] += elm["text"]
                            else:
                                add_data["text"] += elm["emoji"]["shortcuts"][0]
                add_data['author_ch'] = raw_info['authorExternalChannelId']
                currency, amount = money_data_from_text(raw_info['purchaseAmountText']['simpleText'])
                add_data['super_chat'] = {'currency': currency, 'amount': amount, 'sticker': False}
                return add_data
            if "liveChatPaidStickerRenderer" in add_item_action:
                # ステッカースパチャ
                raw_info = add_item_action['liveChatPaidStickerRenderer']
                add_data['author_ch'] = raw_info['authorExternalChannelId']
                add_data['text'] = f"StickerLabel:({raw_info['sticker']['accessibility']['accessibilityData']['label']})"
                currency, amount = money_data_from_text(raw_info['purchaseAmountText']['simpleText'])
                add_data['super_chat'] = {'currency': currency, 'amount': amount, 'sticker': True}
                return add_data
            if "liveChatPlaceholderItemRenderer" in add_item_action:
                # わからんけど，たぶん削除されたメッセージとか
                # self.add_data_to_research(action)
                return None
            if 'liveChatMembershipItemRenderer' in add_item_action:
                # 新規メンバー(他のメンバーシップに関するイベントもこれかも)
                action_data = {'ms': ms, 'author_ch': None, 'action': None, 'tooltip': None}
                raw_info = add_item_action['liveChatMembershipItemRenderer']
                action_data['author_ch'] = raw_info['authorExternalChannelId']
                action_data['action'] = raw_info['headerSubtext']['runs'][0]['text']
                action_data['tooltip'] = raw_info['authorBadges'][0]['liveChatAuthorBadgeRenderer']['tooltip']
                self.membership_actions.append(action_data)
                return None
        if 'addLiveChatTickerItemAction' in action:
            # スパチャの表示を継続させるためのデータ？　無視しておk
            return None
        self.add_data_to_research(action)
        return None

    def _resolve_data(self, data: dict):
        for chat_item in data["continuationContents"]["liveChatContinuation"]["actions"][1:]:
            add_data = self._pick_data(chat_item)
            if add_data is None:
                continue
            action = chat_item["replayChatItemAction"]["actions"][0]
            if add_data["text"] is None and add_data['super_chat'] is None and add_data['author_ch'] is None:
                if self.debug:
                    print("### Found Empty Data ###")
                    print(action)
                self.add_data_to_research(action)
                continue
            if add_data['super_chat'] is None:
                del add_data["super_chat"]
            if add_data in self.comment_data and add_data['ms'] > 0:
                if self.debug:
                    print("### Found Duplicate Action ###")
                    print(action)
                self.received_duplicate = True
                break
            self.comment_data.append(add_data)

    def _finished(self, jump_secs):
        if self.received_duplicate:
            return True
        jump_to = (self.last_timestamp // 1000) + jump_secs
        if jump_to >= self.lengthSeconds:
            return True
        jump_link = self.video_link + "&t=%ss" % str(jump_to)
        if self.debug:
            print("### JUMP TO ###", jump_link)
        self.next_link = self.get_comment_link(jump_link)
        return False

    def get_comment_data(self, video_id: str):
        jump_secs = 0
        self.video_link = BASE_URL+video_id
        self.next_link = self.get_comment_link(self.video_link)
        while True:
            json_response = json.loads(self.get_html_text(self.next_link))['response']
            if "continuationContents" not in json_response:
                jump_secs += 1
                if self._finished(jump_secs):
                    break
                continue
            live_chat_continuation = json_response["continuationContents"]["liveChatContinuation"]
            if "liveChatReplayContinuationData" in live_chat_continuation["continuations"][0]:
                continuation = live_chat_continuation["continuations"][0]["liveChatReplayContinuationData"]["continuation"]
                self.next_link = BASE_CHAT_REPLAY_LINK + continuation + '&hidden=false&pbj=1'
                self._resolve_data(json_response)
            else:
                jump_secs += 1
                if self._finished(jump_secs):
                    break

        result = {
            "video_id": video_id,
            "created_time": datetime.datetime.now().timestamp(),
            "data": self.comment_data,
            "membership_actions": self.membership_actions,
            "data_to_research": self.data_to_research
        }
        return result
