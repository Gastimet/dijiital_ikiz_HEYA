# -*- coding: utf-8 -*-
import io
import os
import re
import json
import unicodedata
from typing import List, Dict, Optional, Tuple, Union
from concurrent.futures import ProcessPoolExecutor, as_completed
from pymongo import MongoClient

# PDF/text/ocr
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from tqdm.auto import tqdm


class PDFTextExtractor:
    def __init__(self, tesseract_cmd: str = "/usr/bin/tesseract"):
        """PDF'ten metin çıkarma sınıfı"""
        self.set_tesseract_cmd(tesseract_cmd)
        self.check_tesseract("tur")

    def set_tesseract_cmd(self, tesseract_cmd: str):
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def check_tesseract(self, lang_hint: str = "tur"):
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
        if not text:
            return text
        t = unicodedata.normalize("NFKC", text)
        t = t.replace("\u00AD", "")
        t = re.sub(r"(\w)-\r?\n(\w)", r"\1\2", t, flags=re.UNICODE)
        t = re.sub(r"[ \t]{2,}", " ", t)
        return t.strip()

    def _ocr_png_bytes(self, png_bytes: bytes, lang: str = "tur+eng", psm: int = 6) -> str:
        try:
            img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
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
            config = f"--oem 3 --psm {psm}"
            txt = pytesseract.image_to_string(img, lang=lang, config=config)
            return self._normalize_tr_text(txt)
        except Exception as e:
            print(f"OCR error: {e}")
            return f"[OCR_FAILED] {e}"

    def extract_pdf_text(
            self,
            pdf_path: str,
            preserve_layout: bool = False,
            use_ocr: bool = True,
            ocr_lang: str = "tur+eng",
            ocr_threshold_chars: int = 40,
            ocr_dpi: int = 300,
            max_ocr_workers: Optional[int] = None,
            return_pages: bool = False,
            show_progress: bool = True,
    ) -> Union[str, List[Dict[str, Union[int, str]]]]:

        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        doc = fitz.open(pdf_path)
        try:
            n_pages = doc.page_count
            native_texts: List[Optional[str]] = [None] * n_pages
            ocr_jobs: List[Tuple[int, bytes]] = []

            itr = range(n_pages)
            if show_progress:
                itr = tqdm(itr, desc="Sayfalar taranıyor", unit="sayfa")

            for i in itr:
                page = doc.load_page(i)
                try:
                    if preserve_layout:
                        blocks = page.get_text("blocks")
                        blocks.sort(key=lambda b: (round(b[1], 1), round(b[0], 1)))
                        parts = [b[4].strip() for b in blocks if b[4].strip()]
                        native = "\n".join(parts)
                    else:
                        native = page.get_text("text").strip()
                except Exception as e:
                    print(f"Page {i + 1} text extraction error: {e}")
                    native = ""

                native = self._normalize_tr_text(native)

                if use_ocr and len(native) < ocr_threshold_chars:
                    zoom = ocr_dpi / 72.0
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat, alpha=False)
                    png_bytes = pix.tobytes("png")
                    ocr_jobs.append((i, png_bytes))
                    native_texts[i] = None
                else:
                    native_texts[i] = native

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

            if return_pages:
                return [{"page": i + 1, "text": native_texts[i] or ""} for i in range(n_pages)]
            else:
                sep = "\n\n===== SAYFA SONU =====\n\n"
                return sep.join(native_texts)  # type: ignore

        finally:
            doc.close()

    def save_output(self, text_or_pages: Union[str, List[Dict[str, Union[int, str]]]], output_path: str) -> None:
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


if __name__ == "__main__":
    # 👇 PDF dosya yolunu buraya yaz


    doc = MongoClient()["web_crawler"]["persons"].find_one(sort=[('_id', -1)])
    input_pdf = doc["sources"]["PDF Derleyen"]

    # Fazla tırnakları temizle
    input_pdf = input_pdf.strip(' "\'')


    # 👇 Çıktı dosya yolunu otomatik veya elle belirle
    output_path = os.path.splitext(input_pdf)[0] + ".txt"

    extractor = PDFTextExtractor(tesseract_cmd=r"C:\Program Files\Tesseract-OCR\tesseract.exe")

    result = extractor.extract_pdf_text(
        pdf_path=input_pdf,
        preserve_layout=False,
        use_ocr=True,
        ocr_lang="tur+eng",
        ocr_threshold_chars=40,
        ocr_dpi=300,
        max_ocr_workers=None,
        return_pages=False,
        show_progress=True,
    )

    extractor.save_output(result, output_path)
