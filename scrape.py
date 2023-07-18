import os
import re
import time
import traceback
from pprint import pprint
from turtle import update

import requests
from apscheduler.schedulers.background import BlockingScheduler
from thefuzz import fuzz

from main import Source
from scrapers.asura import Asura
from scrapers.flame import Flame
from scrapers.leviatan import Leviatan
from scrapers.reaper import Reaper
from scrapers.reddit import Reddit_scraper
from scrapers.tcbscans import TcbScraper
from datetime import datetime
from db import db


class Scraper(Source):
    def __init__(self, leviatan, testing):
        self.base_leviatan_url = leviatan
        self.total_manga = []
        self.testing = testing

    def scrape(self, total_manga):
        self.total_manga = total_manga

        curr_urls = db['scans'].find_one({})
        urls = set()

        print(len(total_manga))
        # pprint(total_manga)
        length = len(total_manga)
        scans = self.update_total_manga()
        self.update_users()

        if curr_urls:
            [urls.add(url) for url in curr_urls['urls']]
        scans = urls.union(scans)
        # pprint(manga_list)
        if not self.testing:
            db['scans'].find_one_and_update(
                {}, {'$set': {'urls': list(urls)}}, upsert=True)

    def update_users(self):
        # self.test_search()
        # return
        print('update users')
        for user in db['manga-list'].find({}):
            user_list = user['manga-list']
            user_id = user['user']
            # print('u_id', user_id)
            if user_list:
                self.update_user_list(user_id, user_list)

    def test_search(self):
        for item in self.total_manga:
            for item2 in self.total_manga[::-1]:
                self.fuzzy_search(item['title'], item2['title'])

    def update_user_list(self, user_id, user_list):
        if not self.total_manga:
            import json
            with open('new_list.json', 'r') as f:
                self.total_manga = json.load(f)
        for total_manga_dict in self.total_manga[::-1]:
            for user_manga in user_list:
                search_res = self.fuzzy_search(
                    user_manga['title'], total_manga_dict['title'])
                if search_res > 82:
                    # if 'berserk' in item['title']:
                    #     print('debvug')
                    # sys.stdout.write('\x1b[2K')
                    # if 'novel' in item['title']:
                    #     print('debvug')
                    # print(
                    #     f" \r{length - i}/{length} {item['title']} {item['latest']} {item['scansite']}", end='')
                    user_manga['latest'] = total_manga_dict['sources']['any']['latest']
                    # if 'world-after' in item['title']:
                    #     print('debug')
                    user_manga['sources'] = self.update_user_sources(
                        user_manga['sources'], total_manga_dict['sources'])
                    current_source = user_manga['current_source']
                    curr_source = 'any' if current_source not in user_manga[
                        'sources'] else current_source
                    # print(manga['title'], user_id, manga)
                    user_manga['read'] = float(
                        user_manga['sources'][curr_source]['latest']) <= float(user_manga['chapter'])
                    if not user_manga['read']:
                        print(
                            f"in {user_id} {total_manga_dict['title']} {user_manga['title']} {user_manga['chapter']}/{total_manga_dict['latest']} {total_manga_dict['scansite']} {search_res} 'read: '{user_manga['read']}")
                        pass
                    break
        if not self.testing:
            db['manga-list'].find_one_and_update(
                {'user': user_id}, {"$set": {f'manga-list': user_list}})
            pass

    def format_title(self, title):
        t1 = re.sub(r'remake', '', title)
        t1 = re.sub(r'\W+', '', t1)
        return t1

    def update_total_manga(self):
        scans = set()
        all_manga = db['all_manga'].find()
        if not self.total_manga:
            import json
            with open('new_list.json', 'r') as f:
                self.total_manga = json.load(f)
        for i, item in enumerate(self.total_manga[::-1]):
            scans.add(item['domain'])
            item['latest_sort'] = float(item['latest'])
            req = db['all_manga'].find_one({'title': item['title']})
            updated = False
            print(
                f"\r {len(self.total_manga) - i}/{len(self.total_manga)}", end='\x1b[1K')
            if req and not self.testing:
                db['all_manga'].find_one_and_update(
                    {'title': item['title']}, {"$set": item})
                updated = True
            elif not updated and req is None:
                for m in all_manga:
                    ratio = fuzz.ratio(item['title'], m['title'])
                    if ratio > 80 and not self.testing:
                        db['all_manga'].find_one_and_update(
                            {'title': m['title']}, {"$set": item}, upsert=True)
                        updated = True
                        break
            if not updated and not self.testing:
                db['all_manga'].find_one_and_update({'title': item['title']}, {
                                                    "$set": item}, upsert=True)
        return scans

    def test_totle_manga(self):
        import json
        with open('new_list.json', 'r') as f:
            total_manga = json.load(f)
        for item in total_manga[::-1]:
            item['latest_sort'] = float(item['latest'])
            req = db['all_manga'].find_one({'title': item['title']})
            updated = False
            if req:
                db['all_manga'].find_one_and_update(
                    {'title': item['title']}, {"$set": item})
                updated = True
            elif not updated and req is None:
                for m in db['all_manga'].find():
                    ratio = fuzz.ratio(item['title'], m['title'])
                    if ratio > 80:
                        db['all_manga'].find_one_and_update(
                            {'title': m['title']}, {"$set": item}, upsert=True)
                        updated = True
            if not updated:
                db['all_manga'].find_one_and_update({'title': item['title']}, {
                                                    "$set": item}, upsert=True)

    def fuzzy_search(self, title, title2):
        fu = fuzz.ratio(self.format_title(title), self.format_title(title2))
        return fu

    def text_similarity(self, title, title2):
        title_split = title.split('-')
        title_split2 = title2.split('-')
        if title_split == title_split2:
            return True
        ite = title_split
        sub = title_split2
        if len(title_split) < len(title_split2):
            ite = title_split2
            sub = title_split
        ret = len([word for word in ite if word not in sub])
        ret = ret/len(ite)
        return ret <= 0.25

    def update_user_sources(self, user_manga: dict, total_manga: dict) -> dict:
        d = {}
        combined_sources = [total_manga, user_manga]
        for source in total_manga:
            try:
                if source in user_manga:
                    if 'url' in user_manga[source]:
                        total_manga[source]['url'] = user_manga[source]['url']
                    if float(total_manga[source]['latest']) < float(user_manga[source]['latest']):
                        print(
                            f"{total_manga[source]['latest']} < {user_manga[source]['latest']}", user_manga[source]['latest_link'])
                        # source_list[source]['latest'] = curr[source]['latest']
            except Exception as e:
                print(traceback.format_exc(),
                      total_manga[source]['latest_link'], user_manga[source])
        return total_manga

    def combine_series_by_title(self, lst):
        ret = []
        seen = set()
        # lst = sorted(lst, key=lambda k: k['time_updated'], reverse=True)
        for item in lst:
            title = item['title']
            if title not in seen:
                potential_series = [x for x in lst if self.text_similarity(
                    x['title'], title)]
                series = potential_series
                if len(potential_series) > 1:
                    series = [x for x in series if x['type'] != 'reddit']
                    if not series:
                        series = potential_series
                ret.append(series)
            seen.add(title)
        return ret

    def combine_manga_sources(self, source_list):
        sorted_data = sorted(
            source_list, key=lambda k: k['latest'])
        combined_sources = sorted_data[0]['sources'] | sorted_data[1]['sources']
        return combined_sources

    def update_manga_sources(self, lst):
        # print('l', lst)
        # takes a list of dupes and makes a list of sources
        db_entries = self.atlas_search(
            lst[0]['title'])
        if len(db_entries) > 1:
            combined_sources = self.combine_manga_sources(db_entries)
            for doc in db_entries:
                doc['sources'] = combined_sources
        # db_entry = db['all_manga'].find_one(
        #     {'title': lst[0]['title']})
        for db_entry in db_entries:
            if 'sources' in db_entry and db_entry['sources']:
                for source_key in db_entry['sources']:
                    if source_key == 'any':
                        continue
                    db_entry['sources'][source_key]['scansite'] = source_key
                    try:
                        updated_source = [source
                                          for source in lst if source['scansite'] == source_key]
                        if updated_source:
                            db_entry['sources'][source_key]['latest'] = updated_source[0]['latest']
                            db_entry['sources'][source_key]['latest_link'] = updated_source[0]['latest_link']
                            db_entry['sources'][source_key]['time_updated'] = updated_source[0]['time_updated']
                        lst.append(db_entry['sources'][source_key])
                    except Exception as e:
                        print(lst, traceback.format_exc())
            try:
                latest_sort = sorted(lst, key=lambda k: (
                    float(k['latest']), -k['time_updated']), reverse=True)
                # print(latest_sort)
                updated_sources = {}
                # pprint(latest_sort)
                # print('latest', latest_sort[0])

                source_string = {'latest': latest_sort[0]['latest'],
                                 'latest_link': latest_sort[0]['latest_link'], 'time_updated': latest_sort[0]['time_updated']}
                updated_sources['any'] = source_string

                for item in latest_sort[::-1]:
                    source_string = {'latest': item['latest'],
                                     'latest_link':  item['latest_link'], 'time_updated': item['time_updated']}
                    try:
                        # pprint(item)
                        updated_sources[item['scansite']] = source_string
                    except KeyError:
                        print('e', item)
                return updated_sources
            except Exception as e:
                print(traceback.format_exc())

    def atlas_search(self, title):
        search_query = {'$search': {
            'index': 'default',
            'text': {
                'query': title,
                'path': 'title',
                # 'fuzzy': {
                #     'maxEdits': 2,
                #     'maxExpansions': 100
                # }
            },
        }}
        query = [
            search_query,
            {'$limit': 3},
            {"$project": {
                'score': {'$meta': "searchScore"},
                "_id": 0,
                'title': 1,
                'latest': 1,
                'sources': 1,
                'latest_sort': 1,
                'scansite': 1
            }}
        ]
        res = db['all_manga'].aggregate(query)
        fuzzysearch = list(res)
        fuzzysearch = [doc for doc in fuzzysearch if doc['score']
                       >= fuzzysearch[0]['score'] * 0.7 and abs(float(doc['latest'])-float(fuzzysearch[0]['latest'])) < 5]
        return fuzzysearch
    def combine_data(self, first_run=False):
        total_manga = Reddit_scraper(self.base_leviatan_url).main(first_run)
        all_manga = total_manga
        print('leviatan')
        asura = Asura('asurascans').main()
        alpha = Asura('alphascans').main()
        cosmic = Asura('cosmicscans').main()
        luminous = Asura('luminousscans').main()
        leviatan = Leviatan().scrape()
        reaper = Reaper().scrape()
        tcb = TcbScraper().scrape()
        flame = Flame().scrape()
        all_manga += asura + alpha + luminous + leviatan + reaper+tcb+flame+cosmic

        # all_manga += leviatan
        # all_manga = tcb

        # pprint(all_manga)
        all_manga = sorted(
            all_manga, key=lambda k: k['time_updated'], reverse=True)
        return all_manga

    def main(self, first_run=False):
        import json
        os.system('cls')
        if self.testing:
            with open('pre_processed.json', 'r', ) as f:
                data = json.load(f)
        else:
            total_manga = self.combine_data(first_run)
            total_manga = self.combine_series_by_title(total_manga)
            data = total_manga
            with open('pre_processed.json', 'w') as f:
                json.dump(data, f)
            print(len(total_manga))
        srt = time.perf_counter()
        new_list = []
        for manga in data:
            try:
                d = {}
                d = manga[0]
                # print(d['title'])
                d['sources'] = self.update_manga_sources(manga)
                new_list.append(d)
            except Exception as e:
                print(traceback.format_exc())
                with open('err.txt', 'w') as f:
                    f.write(str(datetime.now()))
                    f.write(traceback.format_exc())
        with open('new_list.json', 'w') as f:
            json.dump(new_list, f)
        self.scrape(new_list)
        print('\ntime taken', time.perf_counter() - srt)
        return new_list


def get_leviatan_url():
    req = requests.get('https://leviatanscans.com/')
    return req.url


def change_leviatan_url(base_url):
    # base_url = 'https://leviatanscans.com/omg'
    lst = db['manga-list'].find({})
    regex = r".*leviatan.*(?=\/manga)"
    for entry in lst:
        user = entry['user']
        manga_list = entry['manga-list']
        for doc in manga_list:
            if 'link' in doc:
                doc['link'] = re.sub(regex, base_url, doc['link'])
            for source in doc['sources']:
                if 'link' in source:
                    source['link'] = re.sub(regex, base_url, source['link'])
                if 'latest_link' in source:
                    source['latest_link'] = re.sub(
                        regex, base_url, source['latest_link'])
                if 'url' in source:
                    source['url'] = re.sub(regex, base_url, source['url'])
        db['manga-list'].find_one_and_update(
            {'user': user}, {"$set": {'manga-list':  manga_list}})


def net_test(retries):
    for i in range(retries):
        try:
            req = requests.get('https://www.google.co.uk/')
            if req.status_code == 200:
                print('connected to the internet')
                return True
            else:
                time.sleep(1)
                continue
        except Exception as e:
            time.sleep(1)
    return False


# scrape(None, False)
if __name__ == '__main__':
    first_run = True
    testing = False
    leviatan_url = 'https://en.leviatanscans.com/home'
    # Scraper(leviatan_url).update_total_manga()
    # Scraper(leviatan_url).main(first_run=first_run)
    if net_test(500):
        if first_run and not testing:
            leviatan_url = get_leviatan_url()
            change_leviatan_url(base_url=leviatan_url)
        scraper = Scraper(leviatan_url, testing)
        scraper.main(first_run=first_run)
        time.sleep(1800)
        scheduler = BlockingScheduler()
        try:
            scheduler.add_job(scraper.main, 'cron', timezone='Europe/London',
                              start_date=datetime.now(), id='scrape',
                              hour='*', minute='*/30', day_of_week='mon-sun')
            scheduler.start()
        except Exception as e:
            print(e, e.__class__)
            scheduler.shutdown()
