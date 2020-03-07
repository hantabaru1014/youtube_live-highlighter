import json
import os
import argparse
import re

from comment_getter import CommentGetter
from analyzer import Analyzer
from settings_loader import SettingsLoader

DEFAULT_SETTINGS_JSON_PATH = "default_settings.json"
YOUTUBE_VIDEO_ID_PATTERN = r"\?v=([^&]+)"


def get_timed_link(video_id, sec):
    return f"https://www.youtube.com/watch?v={video_id}&t={sec}s"


def get_video_id(text):
    m = re.search(YOUTUBE_VIDEO_ID_PATTERN, text)
    if m is not None:
        return m.group(1)
    else:
        return text


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('video_id', help="Youtubeの動画ID　または　動画URL")
    parser.add_argument('--settings', nargs='*', help="設定ファイル。複数指定で指定した順に読み込み。")
    parser.add_argument('--force_download', action='store_true', help="コメントデータが存在する場合でもDLし直す")
    parser.add_argument('--gen_default_settings', action='store_true', help="設定ファイルを出力")
    parser.add_argument('--debug', action='store_true', help="デバッグメッセージを表示")

    args = parser.parse_args()
    target_video_id = get_video_id(args.video_id)

    settings = SettingsLoader().get_init_settings()
    to_loads = []
    if os.path.exists(DEFAULT_SETTINGS_JSON_PATH):
        to_loads.append(DEFAULT_SETTINGS_JSON_PATH)
    if args.settings is not None and len(args.settings) > 0:
        to_loads.extend(args.settings)
    settings = SettingsLoader().load(to_loads)
    
    if args.force_download:
        settings['force_download'] = args.force_download
    if args.debug:
        settings['debug'] = args.debug
    if args.gen_default_settings:
        settings = SettingsLoader().get_init_settings()
        with open(DEFAULT_SETTINGS_JSON_PATH, mode='w', encoding='utf-8') as fh:
            json.dump(settings, fh, indent=4, ensure_ascii=False)
    if target_video_id == "" or target_video_id is None:
        print("video_idは必須です！")
        exit(0)

    comment_data_path = os.path.join(settings['comment_data_directory'], f"comment_data-{target_video_id}.json")
    comment_data = {}
    if os.path.exists(comment_data_path) and not settings['force_download']:
        with open(comment_data_path, mode='r', encoding='utf-8') as fh:
            comment_data = json.load(fh)
        print(f"Load Comment Data File: {comment_data_path}")
    else:
        print(f"Start download comment data. id={target_video_id}")
        comment_data = CommentGetter(settings).get_comment_data(target_video_id)
        with open(comment_data_path, mode='w', encoding="utf-8") as fh:
            json.dump(comment_data, fh, indent=4, ensure_ascii=False)
        print("Finish download.")

    analyzer = Analyzer(settings)
    before_secs = settings['link_before_secs']
    print("### Total ###")
    i = 1
    for dt, score in analyzer.analyze(comment_data):
        print(f"{i}. {dt} - {score}\n   {get_timed_link(target_video_id, dt.seconds-before_secs)}")
        i += 1
