import heapq
import datetime


def min_max(source_list):
    """
    リストを正規化する
    :param source_list: 
    :return: 
    """
    l_min = min(source_list)
    l_max = max(source_list)
    return [(i - l_min) / (l_max - l_min) for i in source_list]


def has_word(text, word_list):
    if not isinstance(text, str):
        return False
    for word in word_list:
        if word in text:
            return True
    return False


def get_top_pos_n(index, value, count):
    hq = []
    result = []
    for i, v in enumerate(value):
        heapq.heappush(hq, (v, index[i]))
    for tup in heapq.nlargest(count, hq):
        v2, i2 = tup
        dt = datetime.timedelta(seconds=i2)
        result.append((dt, v2))
    return result


class Analyzer:
    def __init__(self, settings):
        self.settings = settings

        self.pos_s = []
        self.com_count = []
        self.word_based_score_count = {}
        self.total_score_count = []

    def get_top_n_word_score(self, machine_id, n):
        return get_top_pos_n(self.pos_s, self.word_based_score_count[machine_id], n)

    def analyze(self, comment_data, get_count=10):
        word_based_machines = self.settings['analyzer']['word_based_machines']
        interval = self.settings['analyzer']['interval']
        score_combined_ratio: dict = self.settings['analyzer']['score_combined_ratio']

        for machine in word_based_machines:
            self.word_based_score_count[machine['id']] = []

        end_time = 0
        for data in comment_data["data"]:
            if end_time < data["ms"]:
                end_time = data["ms"]

        current_time = 0
        here_com_count = 0
        here_word_count = {}
        for machine in word_based_machines:
            here_word_count[machine['id']] = 0
        self.pos_s.append(current_time)
        for i, data in enumerate(comment_data["data"]):
            if current_time + interval <= data["ms"]:
                self.com_count.append(here_com_count)
                for machine in word_based_machines:
                    self.word_based_score_count[machine['id']].append(here_word_count[machine['id']]/here_com_count)
                    here_word_count[machine['id']] = 0
                here_com_count = 0
                current_time = current_time + interval
                if current_time < end_time:
                    self.pos_s.append(current_time / 1000)
            here_com_count += 1
            for machine in word_based_machines:
                if has_word(data['text'], machine['detect_words']):
                    here_word_count[machine['id']] += 1
                    break
            if i + 1 >= len(comment_data["data"]):
                self.com_count.append(here_com_count)
                for machine in word_based_machines:
                    self.word_based_score_count[machine['id']].append(here_word_count[machine['id']]/here_com_count)

        self.total_score_count = [0]*len(self.pos_s)
        for machine_id, ratio in score_combined_ratio.items():
            if machine_id == 'comment':
                for i, count in enumerate(min_max(self.com_count)):
                    self.total_score_count[i] += count * ratio
                continue
            for i, count in enumerate(self.word_based_score_count[machine_id]):
                self.total_score_count[i] += count * ratio

        return get_top_pos_n(self.pos_s, self.total_score_count, get_count)
