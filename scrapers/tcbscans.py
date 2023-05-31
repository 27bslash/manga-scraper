import datetime
import re
import time
import traceback

import requests
from bs4 import BeautifulSoup
from db import db
from main import Source


class TcbScraper(Source):
    def main(self):
        req = requests.get('https://onepiecechapters.com/')
        # print(req.status_code, req.text)
        with open('scrapers/tcb.html', 'w', encoding="utf-8") as f:
            print(req.status_code)
            f.write(req.text)
        pass

    def scrape(self, debug=False):
        link_regex = r"[^\/]+$"
        title_regex = r".*(?=-chapter)"
        chapter_regex = r"(?<=chapter-)\d*\.?\d+"

        strt = time.perf_counter()
        if not debug:
            try:
                req = requests.get('https://onepiecechapters.com/')
                print(req)
                if req.status_code != 200:
                    print('tcbscasn', req.status_code, 'broken')
                text = req.text
            except:
                return []
        else:
            with open('scrapers/test_pages/tcb.html', 'r', encoding="utf-8") as f:
                text = f.read()
        soup = BeautifulSoup(text, 'html.parser')
        cards = soup.select('div[class*="bg-card"]')
        lst = []
        for card in cards:
            link = card.find('a')
            url = link.get('href')
            url = f"https://onepiecechapters.com{url}"
            # print(timeago)
            d = {}
            try:
                timeago = card.find('time-ago').get('datetime')
                path = re.search(link_regex, url).group(0)
                title = re.search(title_regex, path).group(0)
                chapter = re.search(chapter_regex, path).group(0)
                chapter = super().clean_chapter(chapter)
                title = super().clean_title(title)
                time_updated = self.convert_time_string(timeago)
                d['type'] = 'tcb'
                if time_updated:
                    d['time_updated'] = time_updated
                else:
                    d['time_updated'] = time.time()-self.seconds_since_update()
                if not title or not chapter or not link:
                    continue
                d['title'] = title
                d['latest'] = chapter
                d['domain'] = 'https://onepiecechapters.com/'
                d['latest_link'] = url
                d['scansite'] = 'tcbscans'
                lst.append(d)
                # print(d)
                if debug:
                    print('tcb', title, chapter, time_updated)
            except TypeError:
                print('tcb',url, traceback.format_exc())
                continue
        # print(lst)
        if len(lst) == 0:
            print('tcb broken check logs')
        # print(time.perf_counter()-strt)
        return lst

    def convert_time_string(self, timestamp):
        datetime_object = datetime.datetime.strptime(
            timestamp, '%Y-%m-%dT%H:%M:%SZ')
        unix_timestamp = datetime_object.timestamp()
        return unix_timestamp

    def seconds_since_update(self):
        today = datetime.datetime.today().weekday()
        days_since_thursday = 7 - (3 - today) % 7
        if today == 3:
            return 0
        else:
            return 86400 * days_since_thursday

    def __call__(self):
        return self.scrape()


# t = TcbScraper()()
if __name__ == '__main__':
    t = TcbScraper()
    t.scrape(debug=False)
