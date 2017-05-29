
#http://bible.youversionapi.com/3.1/chapter.json?id=100&reference=HOS.2
from pprint import pprint

from bs4 import BeautifulSoup
import requests

r = requests.get('http://bible.youversionapi.com/3.1/chapter.json?id=100&reference=HOS.2')
d = r.json()
ch = d.get("response").get("data").get("content")
# soup = BeautifulSoup(ch, "html.parser")
# print(soup.get_text())
pprint(ch)
