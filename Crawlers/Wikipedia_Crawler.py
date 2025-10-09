import os
import bs4
from bs4 import BeautifulSoup
import requests
from datetime import datetime
import time
import lxml
import lxml.html
from mongo_saver import save_wiki_article

class WikiCrawler():
    def __init__(self):
        super().__init__() # we need to fill that guys

    def again(self): # main class'a yazilabilir
        input_again = input("Tekrar denemek ister misiniz (y/n) ?")
        if input_again.lower() == "y":
            #os.system("cls")
            time.sleep(.5)
            self.main()
        elif input_again.lower() == "n":
            print("Just wanted to say goodbye, have a good day")
            #os.system("cls")
            time.sleep(.5)
            pass # belki exit de olaiblir
        else:
            print(" Lutfen 'y' ya da 'n' giriniz")
            #os.system("cls")
            time.sleep(.5)
            self.again()

    def turkce_baslik_formatla(self, text):
        """
        Türkçe karakterleri dikkate alarak makale başlığını formatlar:
        - Baştaki ve sondaki boşlukları temizler
        - Boşlukları alt çizgi (_) ile değiştirir
        - Her kelimenin ilk harfini büyük yapar (Türkçe kurallara uygun)
        - Türkçe karakterleri korur
        """
        # Baştaki ve sondaki boşlukları temizle
        text = text.strip()

        # Birden fazla boşluğu tek boşluğa indirge
        text = ' '.join(text.split())

        # Türkçe karakterleri koruyarak her kelimenin ilk harfini büyük yap
        def kelime_buyut(kelime):
            if not kelime:
                return kelime

            # Türkçe karakter dönüşümleri
            kucuk_buyuk = {
                'a': 'A', 'b': 'B', 'c': 'C', 'ç': 'Ç', 'd': 'D',
                'e': 'E', 'f': 'F', 'g': 'G', 'ğ': 'Ğ', 'h': 'H',
                'ı': 'I', 'i': 'İ', 'j': 'J', 'k': 'K', 'l': 'L',
                'm': 'M', 'n': 'N', 'o': 'O', 'ö': 'Ö', 'p': 'P',
                'r': 'R', 's': 'S', 'ş': 'Ş', 't': 'T', 'u': 'U',
                'ü': 'Ü', 'v': 'V', 'y': 'Y', 'z': 'Z'
            }

            # İlk karakteri büyüt
            ilk_karakter = kelime[0]
            buyuk_ilk_karakter = kucuk_buyuk.get(ilk_karakter.lower(), ilk_karakter.upper())

            # Eğer ilk karakter küçükse büyüt, değilse olduğu gibi bırak
            if ilk_karakter in kucuk_buyuk.values() or ilk_karakter.lower() not in kucuk_buyuk:
                # Zaten büyük veya İngilizce karakter
                return kelime
            else:
                return buyuk_ilk_karakter + kelime[1:]

        # Kelimeleri ayır ve her birini işle
        kelimeler = text.split()
        formatli_kelimeler = [kelime_buyut(kelime) for kelime in kelimeler]

        # Boşlukları alt çizgi ile değiştir
        text = '_'.join(formatli_kelimeler)

        return text




    def main(self):
        article = input("Hangi makaleyi çekmek istersin? : ")
        article = self.turkce_baslik_formatla(article)
        url = f"https://tr.wikipedia.org/wiki/{article}"
        print("Bilgiler cekiliyor, lutfen bekleyiniz")

        try:
            session = requests.Session()
            # Basit bir User-Agent, engellenme riskini azaltır
            resp = session.get(url, headers={"User-Agent": "Mozilla/5.0"})
        except requests.RequestException as e:
            print(f"İstek hatası: {e}")
            self.again()
            return

        if not resp.ok:
            print(f"Sayfa alinamadi (HTTP {resp.status_code}).")
            self.again()
            return

        soup = BeautifulSoup(resp.text, "html.parser")

        # İçeriğin bulunduğu ana bölümdeki ilk birkaç paragraf
        content = soup.select_one("#mw-content-text .mw-parser-output")
        if not content:
            print("Icerik bolumu bulunamadi.")
            self.again()
            return

        paragraphs = [p.get_text(" ", strip=True) for p in content.select("p") if p.get_text(strip=True)]
        if not paragraphs:
            print("Sayfa bos !")
            self.again()
            return
        save_wiki_article(
            title=article.strip(),
            url=url,
            paragraphs=paragraphs,
            # mongo_uri="mongodb://localhost:27017",  # istersen belirt
            db_name="wikipedia",
            coll_name="articles"
        )
        intro = '\n'.join(paragraphs[:3])
        print(intro)
        self.again()

        return paragraphs # mongodbye atmak icin

if __name__ == "__main__":
    crawler = WikiCrawler()
    paragraphs = crawler.main() # buradan itibaren mongo db yapılmalı bu paragraphs ile. Paragraphs -> List["str"] !!!
