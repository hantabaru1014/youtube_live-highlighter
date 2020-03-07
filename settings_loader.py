import os
import json

INIT_SETTINGS = {
    'config_version': 0.1,
    'comment_data_directory': "comment_data",
    'debug': True,
    'force_download': False,
    'link_before_secs': 60,
    'analyzer': {
        'interval': 30*1000,
        'word_based_machines': [
            {
                'id': "kusa",
                'detect_words': ["w", "草", "ｗ", "kusa"],
            },
            {
                'id': "exclamation",
                'detect_words': ["おお", "ああ", "えええ", "!!", "！！", "おめでとう"]
            },
            {
                'id': "sensitive",
                'detect_words': ["センシティブ", "エッ", "ｴﾁﾁ"]
            },
            {
                'id': "kawaii",
                'detect_words': ["かわいい", "kawaii"]
            }
        ],
        'score_combined_ratio': {
            'comment': 0.7,
            'kusa': 1,
            'exclamation': 1,
            'sensitive': 1,
            'kawaii': 1
        }
    }
}


def deep_merge(base_dict: dict, other: dict, list_add=True):
    cop_dict = base_dict.copy()
    for k, v in other.items():
        if isinstance(v, dict) and k in cop_dict:
            cop_dict[k] = deep_merge(cop_dict[k], v)
        elif list_add and isinstance(v, list) and k in cop_dict and isinstance(cop_dict[k], list):
            temp: list = cop_dict[k]
            for elm in v:
                if elm not in temp:
                    temp.append(elm)
            cop_dict[k] = temp
        else:
            cop_dict[k] = v
    return cop_dict


class SettingsLoader:
    def __init__(self):
        self.settings = self.get_init_settings()

    def get_init_settings(self):
        return INIT_SETTINGS

    def loads(self, dict_list: list):
        for setting_dict in dict_list:
            self.settings = deep_merge(self.settings, setting_dict)
        return self.settings

    def load(self, file_list: list):
        to_loads = []
        for file_path in file_list:
            if os.path.exists(file_path):
                with open(file_path, mode='r', encoding='utf-8') as fh:
                    to_loads.append(json.load(fh))
        return self.loads(to_loads)
