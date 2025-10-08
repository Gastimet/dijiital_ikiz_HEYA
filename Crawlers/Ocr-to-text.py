# -*- coding: utf-8 -*-
import io
import os
import re
import json
import argparse
import unicodedata
from typing import List, Dict, Optional, Tuple, Union
from concurrent.futures import ProcessPoolExecutor, as_completed

# PDF/text/ocr
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from tqdm.auto import tqdm

# >>> NEW: MongoDB & time
from pymongo import MongoClient
from datetime import datetime


class PDFTextExtractor:
    def __init__(self, tesseract_cmd: str = "/usr/bin/tesseract"):
        """PDF'ten metin çıkarma sınıfı"""
        self.set_tesseract_cmd(tesseract_cmd)
        self.check_tesseract("tur")

    def set_tesseract_cmd(self, tesseract_cmd: str):
        """Tesseract komut yolunu ayarla"""
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def check_tesseract(self, lang_hint: str = "tur"):
        """
        Tesseract kontrolü: binary ve dil paketi mevcut mu?
        """
        cmd = pytesseract.pytesseract.tesseract_cmd
        if not os.path.exists(cmd):
            print(f"Tesseract binary not found at {cmd}")
            return False

        try:
            langs = pytesseract.get_languages(config="")
            if lang_hint not in langs:
                print(f"'{lang_hint}' language not available. Installed langs: {langs}")
                return False
            else:
                print(f"Tesseract OK. '{lang_hint}' language available.")
                return True
        except Exception as e:
            print(f"Could not list Tesseract languages: {e}")
            return False

    def _normalize_tr_text(self, text: str) -> str:
        """
        Türkçe odaklı metin normalleştirme:
        - Unicode NFKC (ligatürler vb.)
        - Yumuşak tire temizleme (U+00AD)
        - Satır sonlarındaki tireleri kaldırma: 'Osmanlı-\nlık' -> 'Osmanlılık'
        - Fazla boşlukları temizleme
        """
        if not text:
            return text

        t = unicodedata.normalize("NFKC", text)
        t = t.replace("\u00AD", "")  # soft hyphen

        # Tire ile bölünmüş kelimeleri birleştir
        t = re.sub(r"(\w)-\r?\n(\w)", r"\1\2", t, flags=re.UNICODE)

        # Çoklu boşluk/tab'ları temizle
        t = re.sub(r"[ \t]{2,}", " ", t)

        return t.strip()

    def _ocr_png_bytes(self, png_bytes: bytes, lang: str = "tur+eng", psm: int = 6) -> str:
        """
        PNG görüntüsünü OCR ile metne çevir
        - Görüntü yönlendirmesi otomatik düzeltilir
        - Türkçe normalleştirme uygulanır
        """
        try:
            img = Image.open(io.BytesIO(png_bytes)).convert("RGB")

            # Otomatik yönlendirme tespiti
            try:
                osd = pytesseract.image_to_osd(img)
                for line in osd.splitlines():
                    if "Rotate:" in line:
                        angle = int(line.split(":")[1].strip())
                        if angle and angle % 360 != 0:
                            img = img.rotate(360 - angle, expand=True)
                        break
            except Exception:
                pass

            # OCR konfigürasyonu
            config = f"--oem 3 --psm {psm}"
            txt = pytesseract.image_to_string(img, lang=lang, config=config)

            return self._normalize_tr_text(txt)

        except Exception as e:
            print(f"OCR error: {e}")
            return f"[OCR_FAILED] {e}"

    def extract_pdf_text(
            self,
            pdf_path: str,
            password: Optional[str] = None,
            preserve_layout: bool = False,
            use_ocr: bool = True,
            ocr_lang: str = "tur+eng",
            ocr_threshold_chars: int = 40,
            ocr_dpi: int = 300,
            max_ocr_workers: Optional[int] = None,
            return_pages: bool = False,
            show_progress: bool = True,
    ) -> Union[str, List[Dict[str, Union[int, str]]]]:
        """
        Yüksek performanslı PDF → metin dönüşümü (OCR destekli, Türkçe uyumlu)
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        doc = fitz.open(pdf_path)
        try:
            if doc.needs_pass:
                if not password:
                    raise RuntimeError("PDF is encrypted. Provide a password.")
                if not doc.authenticate(password):
                    raise RuntimeError("Wrong password or cannot authenticate PDF.")

            n_pages = doc.page_count
            native_texts: List[Optional[str]] = [None] * n_pages
            ocr_jobs: List[Tuple[int, bytes]] = []

            # 1. Aşama: Hızlı doğal metin çıkarma; OCR gereken sayfaları belirle
            itr = range(n_pages)
            if show_progress:
                itr = tqdm(itr, desc="Sayfalar taranıyor", unit="sayfa")

            for i in itr:
                page = doc.load_page(i)
                try:
                    if preserve_layout:
                        # Blok tabanlı okuma (sütunlar için daha iyi)
                        blocks = page.get_text("blocks")
                        blocks.sort(key=lambda b: (round(b[1], 1), round(b[0], 1)))
                        parts = []
                        for b in blocks:
                            content = (b[4] or "").strip()
                            if content:
                                parts.append(content)
                        native = "\n".join(parts).strip()
                    else:
                        native = page.get_text("text").strip()
                except Exception as e:
                    print(f"Page {i + 1} text extraction error: {e}")
                    native = ""

                native = self._normalize_tr_text(native)

                if use_ocr and len(native) < ocr_threshold_chars:
                    # OCR için görüntü hazırla
                    zoom = ocr_dpi / 72.0
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat, alpha=False)
                    png_bytes = pix.tobytes("png")
                    ocr_jobs.append((i, png_bytes))
                    native_texts[i] = None
                else:
                    native_texts[i] = native

            # 2. Aşama: OCR gereken sayfaları işle (paralel)
            if ocr_jobs and use_ocr:
                if show_progress:
                    pbar = tqdm(total=len(ocr_jobs), desc="OCR işleniyor", unit="sayfa")
                else:
                    pbar = None

                try:
                    with ProcessPoolExecutor(max_workers=max_ocr_workers) as ex:
                        futures = {ex.submit(self._ocr_png_bytes, png, ocr_lang): idx
                                   for idx, png in ocr_jobs}
                        for fut in as_completed(futures):
                            page_idx = futures[fut]
                            try:
                                ocr_text = fut.result().strip()
                            except Exception as e:
                                ocr_text = f"[OCR_FAILED] {e}"
                            native_texts[page_idx] = ocr_text
                            if pbar:
                                pbar.update(1)
                finally:
                    if pbar:
                        pbar.close()

            # Çıktıyı birleştir
            assert all(t is not None for t in native_texts), "Internal error: missing page text"

            if return_pages:
                return [{"page": i + 1, "text": native_texts[i] or ""} for i in range(n_pages)]
            else:
                sep = "\n\n===== SAYFA SONU =====\n\n"
                return sep.join(native_texts)  # type: ignore

        finally:
            doc.close()

    def save_output(self, text_or_pages: Union[str, List[Dict[str, Union[int, str]]]], output_path: str) -> None:
        """
        Metni veya sayfa listesini dosyaya kaydet
        """
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        if isinstance(text_or_pages, str):
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text_or_pages)
            print(f"✅ Metin dosyası kaydedildi: {output_path}")
        else:
            with open(output_path, "w", encoding="utf-8") as f:
                for rec in text_or_pages:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"✅ JSONL dosyası kaydedildi: {output_path}")


# >>> NEW: Mongo helper
def save_person_to_mongo(
    mongo_uri: str,
    db_name: str,
    coll_name: str,
    ad: str,
    site: str,
    url: str,
    raw_text: str,
    aciklama: str = "PDF’ten çıkarılan metin"
):
    """
    Kişiyi yoksa ekler, varsa kaynaklar listesine yeni kaynak ekler ve raw_text'i günceller.
    """
    if not ad or not site:
        raise ValueError("ad ve site zorunludur")

    client = MongoClient(mongo_uri)
    col = client[db_name][coll_name]
    # ad alanını benzersiz yapmak istersen ilk çalıştırmada şu satırı aç:
    # col.create_index({"ad": 1}, unique=True)

    src = {
        "site": site,
        "url": url,
        "aciklama": aciklama,
        "eklenmeTarihi": datetime.utcnow()
    }

    doc = col.find_one({"ad": ad})
    if doc is None:
        col.insert_one({
            "ad": ad,
            "kaynaklar": [src],
            "raw_text": raw_text
        })
        print(f"✅ MongoDB: yeni kişi eklendi → {ad}")
    else:
        col.update_one(
            {"_id": doc["_id"]},
            {
                "$push": {"kaynaklar": src},
                "$set": {"raw_text": raw_text}
            }
        )
        print(f"✅ MongoDB: mevcut kişiye kaynak eklendi → {ad}")


def main():
    """Komut satırı arayüzü"""
    parser = argparse.ArgumentParser(description="PDF'ten metin çıkarıcı (Türkçe OCR destekli)")
    parser.add_argument('input_pdf', help='Giriş PDF dosyası')
    parser.add_argument('-o', '--output', help='Çıktı dosyası (otomatik belirlenmezse)')
    parser.add_argument('--password', help='PDF şifresi (gerekliyse)')
    parser.add_argument('--tesseract-cmd', default='/usr/bin/tesseract',
                        help='Tesseract komut yolu (varsayılan: /usr/bin/tesseract)')
    parser.add_argument('--jsonl', action='store_true',
                        help='JSONL formatında çıktı (sayfa bazlı)')
    parser.add_argument('--preserve-layout', action='store_true',
                        help='Düzeni koru (çok sütunlu belgeler için)')
    parser.add_argument('--no-ocr', action='store_true',
                        help='OCR kullanma')
    parser.add_argument('--ocr-lang', default='tur+eng',
                        help='OCR dilleri (varsayılan: tur+eng)')
    parser.add_argument('--ocr-threshold', type=int, default=40,
                        help='OCR eşik karakter sayısı (varsayılan: 40)')
    parser.add_argument('--ocr-dpi', type=int, default=300,
                        help='OCR DPI (varsayılan: 300)')
    parser.add_argument('--workers', type=int,
                        help='Paralel işçi sayısı (varsayılan: CPU sayısı)')

    # >>> NEW: Mongo seçenekleri
    parser.add_argument('--mongo', action='store_true',
                        help='İşlenen metni MongoDB’ye kaydet')
    parser.add_argument('--person', help='Kişi adı (MongoDB için zorunlu)')
    parser.add_argument('--site', help='Kaynağın site alanı (MongoDB için)')
    parser.add_argument('--url', default='', help='Kaynağın URL alanı (opsiyonel)')
    parser.add_argument('--mongo-uri', default='mongodb://localhost:27017',
                        help='Mongo bağlantı URI (varsayılan: mongodb://localhost:27017)')
    parser.add_argument('--db', default='people', help='MongoDB database adı (varsayılan: people)')
    parser.add_argument('--coll', default='names', help='MongoDB koleksiyon adı (varsayılan: names)')

    args = parser.parse_args()

    # Çıktı dosyasını belirle
    if args.output:
        output_path = args.output
    else:
        base_name = os.path.splitext(args.input_pdf)[0]
        output_path = base_name + ('.jsonl' if args.jsonl else '.txt')

    # PDF işleyiciyi başlat
    extractor = PDFTextExtractor(tesseract_cmd=args.tesseract_cmd)

    # Metni çıkar
    result = extractor.extract_pdf_text(
        pdf_path=args.input_pdf,
        password=args.password,
        preserve_layout=args.preserve_layout,
        use_ocr=not args.no_ocr,
        ocr_lang=args.ocr_lang,
        ocr_threshold_chars=args.ocr_threshold,
        ocr_dpi=args.ocr_dpi,
        max_ocr_workers=args.workers,
        return_pages=args.jsonl,
        show_progress=True,
    )

    # JSONL istendi ise dosyaya yaz
    if args.jsonl:
        extractor.save_output(result, output_path)
        # Mongo'ya ham sayfa sayfa eklemek yerine birleştirilmiş metni de eklemek isteyebilirsin:
        merged_text = "\n\n".join(rec["text"] for rec in result)  # type: ignore
        if args.mongo:
            if not args.person or not args.site:
                raise SystemExit("MongoDB için --person ve --site zorunlu.")
            save_person_to_mongo(
                mongo_uri=args.mongo_uri,
                db_name=args.db,
                coll_name=args.coll,
                ad=args.person,
                site=args.site,
                url=args.url or "",
                raw_text=merged_text
            )
    else:
        # result str ise tek dosya yaz
        extractor.save_output(result, output_path)
        if args.mongo:
            if not args.person or not args.site:
                raise SystemExit("MongoDB için --person ve --site zorunlu.")
            # result burada str
            save_person_to_mongo(
                mongo_uri=args.mongo_uri,
                db_name=args.db,
                coll_name=args.coll,
                ad=args.person,
                site=args.site,
                url=args.url or "",
                raw_text=result  # type: ignore
            )


if __name__ == "__main__":
    main()
