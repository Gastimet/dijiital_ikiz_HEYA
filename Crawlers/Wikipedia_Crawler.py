import os
import bs4
from bs4 import BeautifulSoup
import requests
from datetime import datetime
import time
import lxml
import lxml.html

from mongo_saver import save_wiki_article  # <<< EKLENDİ

class WikiCrawler():
    def __init__(self):
        super().__init__()

    def again(self):
        input_again = input("Tekrar denemek ister misiniz (y/n) ?")
        if input_again.lower() == "y":
            time.sleep(.5)
            self.main()
        elif input_again.lower() == "n":
            print("Just wanted to say goodbye, have a good day")
            time.sleep(.5)
        else:
            print(" Lutfen 'y' ya da 'n' giriniz")
            time.sleep(.5)
            self.again()

    def turkce_baslik_formatla(self, text):
        text = text.strip()
        text = ' '.join(text.split())
        def kelime_buyut(kelime):
            if not kelime: return kelime
            kucuk_buyuk = {'a':'A','b':'B','c':'C','ç':'Ç','d':'D','e':'E','f':'F','g':'G','ğ':'Ğ','h':'H','ı':'I','i':'İ','j':'J','k':'K','l':'L','m':'M','n':'N','o':'O','ö':'Ö','p':'P','r':'R','s':'S','ş':'Ş','t':'T','u':'U','ü':'Ü','v':'V','y':'Y','z':'Z'}
            ilk = kelime[0]
            buyuk = kucuk_buyuk.get(ilk.lower(), ilk.upper())
            if ilk in kucuk_buyuk.values() or ilk.lower() not in kucuk_buyuk:
                return kelime
            return buyuk + kelime[1:]
        return '_'.join(kelime_buyut(k) for k in text.split())

    def main(self):
        article = input("Hangi makaleyi çekmek istersin? : ")
        article = self.turkce_baslik_formatla(article)
        url = f"https://tr.wikipedia.org/wiki/{article}"
        print("Bilgiler cekiliyor, lutfen bekleyiniz")

        try:
            session = requests.Session()
            resp = session.get(url, headers={"User-Agent": "Mozilla/5.0"})
        except requests.RequestException as e:
            print(f"İstek hatası: {e}")
            self.again(); return

        if not resp.ok:
            print(f"Sayfa alinamadi (HTTP {resp.status_code}).")
            self.again(); return

        soup = BeautifulSoup(resp.text, "html.parser")
        content = soup.select_one("#mw-content-text .mw-parser-output")
        if not content:
            print("Icerik bolumu bulunamadi.")
            self.again(); return

        paragraphs = [p.get_text(" ", strip=True) for p in content.select("p") if p.get_text(strip=True)]
        if not paragraphs:
            print("Sayfa bos !")
            self.again(); return

        intro = '\n'.join(paragraphs[:3])
        print(intro)

        # <<< MONGO KAYIT
        save_wiki_article(
            title=article.strip(),
            url=url,
            paragraphs=paragraphs,
            # mongo_uri="mongodb://localhost:27017",
            db_name="wikipedia",
            coll_name="articles"
        )

        self.again()
        return paragraphs

if __name__ == "__main__":
    crawler = WikiCrawler()
    paragraphs = crawler.main()
