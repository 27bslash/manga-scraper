from pprint import pprint
import re
import requests
from bs4 import BeautifulSoup
from main import Source


class Flame(Source):

    def scrape(self, debug=False):
        lst = []

        url = 'https://flamescans.org'
        try:
            rq = requests.get(url)
        except:
            print('req broke', 'flame')
            pass
        if rq.status_code == 200:
            soup = BeautifulSoup(rq.text, 'html.parser')
        else:
            print('selenium', url)
            try:
                soup = BeautifulSoup(super().sel(url), 'html.parser')
            except Exception as e:
                print('flame sel error', e)
        updates = soup.find_all('div', 'bigor')
        for update in updates:
            d = {}
            try:
                title = update.find('div', 'tt').text.strip()
                chapter = update.find('div', 'epxs')
                if chapter is None:
                    continue
                chapter = chapter.text.strip()
                if not re.search(r'\d+', chapter):
                    continue
                chapter = super().clean_chapter(chapter)
                title = super().clean_title(title)
                link = update.find('div', 'chapter-list').find('a').get('href')
                # print('c', chapter)
                # chapter = up
                date = update.find('div', 'epxdate').text.strip()
                time_updated = super().convert_time(date)
                if not title or not chapter or not link:
                    continue
                d['type'] = 'flamescans'
                d['title'] = title
                d['latest'] = chapter
                d['latest_link'] = link
                d['time_updated'] = time_updated
                d['scansite'] = 'flamescans'
                d['domain'] = 'https://flamescans.org'
                lst.append(d)
                if debug:
                    print('flamescans', title, chapter, time_updated)
            except Exception as e:
                print('flame', title,  e)
                pass
        if len(lst) == 0:
            print('flame broken check logs')
        return lst


if __name__ == "__main__":
    s = Flame().scrape(True)
