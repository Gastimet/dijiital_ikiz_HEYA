# ---- MongoDB'ye kaydetmek için gereken minimal kod ----
# Gerekli: pip install pymongo

from pymongo import MongoClient
from datetime import datetime
from tkinter import messagebox

# 1) Mongo bağlantısı ve koleksiyon
client = MongoClient("mongodb://localhost:27017")  # gerekiyorsa URI'yi değiştir
col = client["people"]["names"]
col.create_index({"ad": 1}, unique=True)  # ad alanı benzersiz olsun (isteğe bağlı)

def save_person_to_mongo(ad: str, site: str, url: str, raw_text: str, aciklama: str = "PDF'ten çıkarılan metin"):
    """Kişiyi yoksa ekler, varsa kaynaklar listesine yeni kaynak ekler."""
    if not ad or not site:
        raise ValueError("ad ve site zorunludur")

    src = {
        "site": site,
        "url": url,
        "aciklama": aciklama,
        "eklenmeTarihi": datetime.utcnow()
    }

    # mevcut kişi var mı?
    doc = col.find_one({"ad": ad})
    if doc is None:
        col.insert_one({
            "ad": ad,
            "kaynaklar": [src],
            "raw_text": raw_text
        })
    else:
        col.update_one(
            {"_id": doc["_id"]},
            {
                "$push": {"kaynaklar": src},
                "$set": {"raw_text": raw_text}  # son metni güncellemek istersen
            }
        )

# 2) Tkinter buton callback'i (Entry/Text değişkenlerini kendine göre bağla)
def on_click_save_to_db():
    try:
        ad   = var_ad.get().strip()     # tk.StringVar
        site = var_site.get().strip()   # tk.StringVar
        url  = var_url.get().strip()    # tk.StringVar
        text = extracted_text           # PDF'ten çıkarılmış metin (str)

        save_person_to_mongo(ad=ad, site=site, url=url, raw_text=text)
        messagebox.showinfo("Kayıt", f"{ad} MongoDB'ye kaydedildi.")
    except Exception as e:
        messagebox.showerror("Hata", str(e))

# 3) Buton tanımı (örnek)
# tk.Button(root, text="Veri tabanına ekle", command=on_click_save_to_db).grid(...)
