import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from datetime import datetime, timezone
from pymongo import MongoClient, errors

# ==== MongoDB Ayarları ====
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "web_crawler"   # gerekirse "people"
COLL_NAME = "persons"     # gerekirse "names"

class ModernWebCrawlerUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Web Crawler")
        self.root.geometry("1200x800")
        self.root.configure(bg='#1e1e1e')

        self.mongo_client = None
        self.mongo_db = None
        self.mongo_coll = None

        self.colors = {
            'bg': '#1e1e1e', 'card_bg': '#2d2d2d', 'accent': '#007acc',
            'success': '#00d26a', 'warning': '#ffa500', 'error': '#ff4444',
            'info': '#00bfff', 'text': '#ffffff', 'text_secondary': '#cccccc',
            'button_primary': '#007acc', 'button_secondary': '#6c757d',
            'button_success': '#28a745', 'button_danger': '#dc3545',
            'log_bg': '#1a1a1a', 'log_even': '#1f1f1f', 'log_odd': '#242424',
            'log_number': '#ffd700', 'log_time': '#00ff00',
            'log_success': '#90ee90', 'log_error': '#ff6b6b',
            'log_warning': '#ffd700', 'log_info': '#87ceeb'
        }

        self.setup_ui()
        self._init_mongo()

    # ----------------- MongoDB -----------------
    def _init_mongo(self):
        try:
            self.mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
            self.mongo_client.admin.command("ping")
            self.mongo_db = self.mongo_client[DB_NAME]
            self.mongo_coll = self.mongo_db[COLL_NAME]
            try:
                self.mongo_coll.create_index("person", background=True)
            except Exception:
                pass
            self.add_log(f"MongoDB bağlandı → {DB_NAME}.{COLL_NAME}", "success", "🟢")
        except Exception as e:
            self.mongo_client = None
            self.mongo_db = None
            self.mongo_coll = None
            self.add_log(f"MongoDB bağlantı hatası: {e}", "error", "🔴")
            messagebox.showerror("MongoDB", f"Bağlantı kurulamadı:\n{e}")

    # ----------------- UI -----------------
    def setup_ui(self):
        title_frame = tk.Frame(self.root, bg=self.colors['card_bg'])
        title_frame.pack(fill='x', padx=20, pady=15)
        tk.Label(title_frame, text="Web Crawler", font=('Arial', 24, 'bold'),
                 fg=self.colors['accent'], bg=self.colors['card_bg'], pady=12).pack()

        top_frame = tk.Frame(self.root, bg=self.colors['bg'])
        top_frame.pack(fill='x', padx=20, pady=10)
        left_frame = tk.Frame(top_frame, bg=self.colors['bg']); left_frame.pack(side='left', fill='both', expand=True)
        right_frame = tk.Frame(top_frame, bg=self.colors['bg']); right_frame.pack(side='right', fill='both', expand=True)

        self.setup_person_sources_section(left_frame)
        self.setup_progress_section(right_frame)
        self.setup_buttons()
        self.setup_logs_section()

    def setup_person_sources_section(self, parent):
        main_frame = tk.LabelFrame(parent, text=" Ayarlar", font=('Arial', 12, 'bold'),
                                   fg=self.colors['text'], bg=self.colors['card_bg'],
                                   bd=2, relief='flat', highlightbackground=self.colors['accent'],
                                   highlightthickness=2)
        main_frame.pack(fill='both', expand=True)

        person_frame = tk.Frame(main_frame, bg=self.colors['card_bg'])
        person_frame.pack(fill='x', padx=15, pady=12)
        tk.Label(person_frame, text="Kişi İsmi:", font=('Arial', 11, 'bold'),
                 fg=self.colors['text'], bg=self.colors['card_bg'], anchor='w').pack(fill='x', pady=(0, 5))
        self.person_name = tk.Entry(person_frame, font=('Arial', 11), bg='#3d3d3d',
                                    fg=self.colors['text'], insertbackground=self.colors['text'],
                                    relief='flat', bd=2)
        self.person_name.pack(fill='x', pady=5)
        self.person_name.insert(0, "Sadık")

        tk.Frame(main_frame, bg='#444444', height=1).pack(fill='x', padx=10, pady=8)

        sources_title_frame = tk.Frame(main_frame, bg=self.colors['card_bg'])
        sources_title_frame.pack(fill='x', padx=15, pady=(0, 8))
        tk.Label(sources_title_frame, text="Veri Kaynakları:", font=('Arial', 11, 'bold'),
                 fg=self.colors['text'], bg=self.colors['card_bg'], anchor='w').pack(fill='x')

        sources = [
            ("📄", "PDF Derleyen"),
            ("🌐", "Wikipedia"),
            ("🐦", "Twitter"),
            ("💼", "LinkedIn"),
            ("🔍", "OCR To Text")
        ]

        self.source_entries = {}
        sources_inner_frame = tk.Frame(main_frame, bg=self.colors['card_bg'])
        sources_inner_frame.pack(fill='x', padx=15, pady=8)

        placeholders = {
            "PDF Derleyen": "PDF dosya yolu veya URL",
            "Wikipedia": "Wikipedia sayfa bağlantısı",
            "Twitter": "Twitter kullanıcı adı veya URL",
            "LinkedIn": "LinkedIn profil bağlantısı",
            "OCR To Text": "OCR için görsel dosya yolu"
        }

        for icon, text in sources:
            source_frame = tk.Frame(sources_inner_frame, bg=self.colors['card_bg']); source_frame.pack(fill='x', pady=4)
            tk.Label(source_frame, text=f"{icon} {text}:", font=('Arial', 10, 'bold'),
                     fg=self.colors['text'], bg=self.colors['card_bg'], width=15, anchor='w').pack(side='left', padx=(0, 10))

            entry = tk.Entry(source_frame, font=('Arial', 10), bg='#3d3d3d', fg=self.colors['text'],
                             insertbackground=self.colors['text'], relief='flat', bd=1)
            entry.pack(side='left', fill='x', expand=True, padx=5)

            if text in placeholders:
                entry.insert(0, placeholders[text]); entry.config(fg=self.colors['text_secondary'])

                def on_focus_in(event, e=entry, default_text=placeholders[text]):
                    if e.get() == default_text:
                        e.delete(0, tk.END); e.config(fg=self.colors['text'])
                def on_focus_out(event, e=entry, default_text=placeholders[text]):
                    if not e.get():
                        e.insert(0, default_text); e.config(fg=self.colors['text_secondary'])

                entry.bind('<FocusIn>', on_focus_in); entry.bind('<FocusOut>', on_focus_out)

            self.source_entries[text] = entry

    def setup_progress_section(self, parent):
        progress_frame = tk.LabelFrame(parent, text=" Tarama İlerlemesi", font=('Arial', 12, 'bold'),
                                       fg=self.colors['text'], bg=self.colors['card_bg'], bd=2, relief='flat',
                                       highlightbackground=self.colors['accent'], highlightthickness=2)
        progress_frame.pack(fill='both', expand=True, padx=(10, 0))
        inner = tk.Frame(progress_frame, bg=self.colors['card_bg']); inner.pack(fill='both', expand=True, padx=12, pady=12)
        header = tk.Frame(inner, bg=self.colors['card_bg']); header.pack(fill='x', pady=5)
        tk.Label(header, text="Durum:", font=('Arial', 10, 'bold'),
                 fg=self.colors['text'], bg=self.colors['card_bg']).pack(side='left')
        self.status_text = tk.Label(header, text="0/361 tamamlandı", font=('Arial', 10, 'bold'),
                                    fg=self.colors['warning'], bg=self.colors['card_bg']); self.status_text.pack(side='right')
        style = ttk.Style(); style.theme_use('clam')
        style.configure("Custom.Horizontal.TProgressbar", background=self.colors['success'],
                        troughcolor='#3d3d3d', bordercolor=self.colors['accent'],
                        lightcolor=self.colors['success'], darkcolor=self.colors['success'])
        self.progress = ttk.Progressbar(inner, orient='horizontal', mode='determinate', maximum=361,
                                        style="Custom.Horizontal.TProgressbar")
        self.progress.pack(fill='x', pady=8); self.progress['value'] = 0

    def setup_buttons(self):
        button_frame = tk.Frame(self.root, bg=self.colors['bg']); button_frame.pack(pady=15)
        buttons = [
            ("🚀 Başlat", self.start_crawl, self.colors['button_success'], 14),
            ("🔄 Yeniden Başlat", self.restart_crawl, self.colors['button_primary'], 12),
            ("⏹️ Durdur", self.stop_crawl, self.colors['button_danger'], 12),
            ("📊 Rapor Al", self.generate_report, self.colors['button_secondary'], 12),
            ("💾 Veri Tabanına Ekle", self.add_to_database, self.colors['info'], 12)
        ]
        for text, command, color, font_size in buttons:
            btn = tk.Button(button_frame, text=text, command=command, font=('Arial', font_size, 'bold'),
                            bg=color, fg='white', relief='raised', bd=0, padx=20, pady=10, cursor='hand2')
            btn.pack(side='left', padx=8, pady=5)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=self.lighten_color(b['bg'])))
            btn.bind("<Leave>", lambda e, b=btn, c=color: b.config(bg=c))

    def setup_logs_section(self):
        logs_frame = tk.LabelFrame(self.root, text=" 📋 İşlem Logları", font=('Arial', 14, 'bold'),
                                   fg=self.colors['text'], bg=self.colors['card_bg'], bd=2, relief='flat',
                                   highlightbackground=self.colors['accent'], highlightthickness=2)
        logs_frame.pack(fill='both', expand=True, padx=20, pady=(10, 20))

        log_controls = tk.Frame(logs_frame, bg=self.colors['card_bg']); log_controls.pack(fill='x', padx=15, pady=10)
        for text, cmd in [("🗑️ Temizle", self.clear_logs), ("💾 Kaydet", self.save_logs),
                          ("🔍 Filtrele", self.filter_logs), ("📈 İstatistik", self.show_stats)]:
            btn = tk.Button(log_controls, text=text, command=cmd, font=('Arial', 10, 'bold'),
                            bg=self.colors['button_secondary'], fg='white', relief='raised', bd=0, padx=15, pady=6, cursor='hand2')
            btn.pack(side='left', padx=5)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=self.lighten_color(b['bg'])))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=self.colors['button_secondary']))

        container = tk.Frame(logs_frame, bg=self.colors['card_bg']); container.pack(fill='both', expand=True, padx=15, pady=(0, 15))
        scrollbar = ttk.Scrollbar(container); scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_canvas = tk.Canvas(container, bg=self.colors['log_bg'], yscrollcommand=scrollbar.set,
                                    highlightthickness=0, relief='flat')
        self.log_canvas.pack(side=tk.LEFT, fill='both', expand=True); scrollbar.config(command=self.log_canvas.yview)
        self.logs_inner_frame = tk.Frame(self.log_canvas, bg=self.colors['log_bg'])
        self.log_canvas_window = self.log_canvas.create_window((0, 0), window=self.logs_inner_frame, anchor="nw")
        self.logs_inner_frame.bind("<Configure>", self.on_frame_configure)
        self.log_canvas.bind("<Configure>", self.on_canvas_configure)
        self.add_sample_logs()

    # ----------------- Log yardımcıları -----------------
    def on_frame_configure(self, event): self.log_canvas.configure(scrollregion=self.log_canvas.bbox("all"))
    def on_canvas_configure(self, event): self.log_canvas.itemconfig(self.log_canvas_window, width=event.width)

    def create_log_entry(self, number, time_str, status="normal", icon="", message=""):
        bg_color = self.colors['log_even'] if number % 2 == 0 else self.colors['log_odd']
        log_frame = tk.Frame(self.logs_inner_frame, bg=bg_color, relief='flat', height=25)
        log_frame.pack(fill='x', padx=5, pady=1); log_frame.pack_propagate(False)
        number_frame = tk.Frame(log_frame, bg=self.colors['log_number'], relief='raised', bd=1)
        number_frame.pack(side='left', padx=(8, 12), pady=3)
        tk.Label(number_frame, text=f"{number:03d}", font=('Consolas', 9, 'bold'),
                 fg='#000', bg=self.colors['log_number'], width=4, anchor='center').pack(padx=4, pady=1)
        time_color = self.colors['log_time']
        if status == "success": time_color = self.colors['log_success']
        elif status == "error": time_color = self.colors['log_error']
        elif status == "warning": time_color = self.colors['log_warning']
        elif status == "info": time_color = self.colors['log_info']
        tk.Label(log_frame, text=(f"{icon} {time_str}" if icon else time_str),
                 font=('Consolas', 10, 'bold'), fg=time_color, bg=bg_color, anchor='w').pack(side='left', padx=(0, 20))
        if message:
            tk.Label(log_frame, text=message, font=('Consolas', 9),
                     fg=self.colors['text_secondary'], bg=bg_color, anchor='w').pack(side='left', fill='x', expand=True)
        def on_enter(e):
            log_frame.configure(bg='#2a2a2a')
            for c in log_frame.winfo_children():
                if isinstance(c, tk.Frame): c.configure(bg=c['bg'])
                else: c.configure(bg='#2a2a2a')
        def on_leave(e):
            orig = self.colors['log_even'] if number % 2 == 0 else self.colors['log_odd']
            log_frame.configure(bg=orig)
            for c in log_frame.winfo_children():
                if isinstance(c, tk.Frame): c.configure(bg=c['bg'])
                else: c.configure(bg=orig)
        log_frame.bind("<Enter>", on_enter); log_frame.bind("<Leave>", on_leave)
        return log_frame

    def add_sample_logs(self):
        for w in self.logs_inner_frame.winfo_children(): w.destroy()
        self.create_log_entry(1, datetime.now().strftime("%H:%M:%S"), "info", "🟡", "Uygulama hazır")

    def add_log(self, message, status="normal", icon="⏱️"):
        current_logs = [w for w in self.logs_inner_frame.winfo_children() if isinstance(w, tk.Frame)]
        next_number = len(current_logs) + 1
        self.create_log_entry(next_number, datetime.now().strftime("%H:%M:%S"), status, icon, message)
        self.log_canvas.update_idletasks(); self.log_canvas.yview_moveto(1.0)

    def clear_logs(self):
        for w in self.logs_inner_frame.winfo_children(): w.destroy()
        self.add_log("Loglar temizlendi", "info", "🗑️")

    def save_logs(self):
        self.add_log("Loglar kaydediliyor...", "info", "💾")
        messagebox.showinfo("Başarılı", "Loglar başarıyla kaydedildi!")

    def filter_logs(self):
        self.add_log("Log filtreleme açıldı", "info", "🔍")
        messagebox.showinfo("Filtre", "Log filtreleme özelliği aktif!")

    def show_stats(self):
        total_logs = len([w for w in self.logs_inner_frame.winfo_children() if isinstance(w, tk.Frame)])
        self.add_log(f"Toplam {total_logs} log kaydı bulundu", "info", "📈")
        messagebox.showinfo("İstatistik", f"Toplam Log Sayısı: {total_logs}")

    # ----------------- İşlevler -----------------
    def lighten_color(self, color):
        if color == self.colors['button_primary']: return '#3399ff'
        if color == self.colors['button_success']: return '#34ce57'
        if color == self.colors['button_danger']: return '#e04b59'
        if color == self.colors['info']: return '#33ccff'
        return '#868e96'

    def collect_inputs(self):
        placeholders = {
            "PDF Derleyen": "PDF dosya yolu veya URL",
            "Wikipedia": "Wikipedia sayfa bağlantısı",
            "Twitter": "Twitter kullanıcı adı veya URL",
            "LinkedIn": "LinkedIn profil bağlantısı",
            "OCR To Text": "OCR için görsel dosya yolu",
        }
        data = {"person": self.person_name.get().strip(), "sources": {}}
        for label, entry in self.source_entries.items():
            val = (entry.get() or "").strip()
            if val and val != placeholders.get(label, ""):
                data["sources"][label] = val
        return data

    def start_crawl(self):
        person_name = self.person_name.get().strip()
        if not person_name:
            messagebox.showwarning("Uyarı", "Lütfen kişi ismini girin!"); return
        self.add_log(f"Kullanıcı: {person_name} - Tarama başlatılıyor...", "info", "🚀")
        self.progress['value'] = 0
        self.status_text.config(text="0/361 tamamlandı", fg=self.colors['warning'])
        messagebox.showinfo("Başlatılıyor", f"Kişi: {person_name}\n\nTarama işlemi başlatılıyor...")

    def restart_crawl(self):
        self.progress['value'] = 0
        self.status_text.config(text="0/361 tamamlandı", fg=self.colors['warning'])
        self.add_log("Tarama yeniden başlatılıyor...", "warning", "🔄")
        def simulate():
            total = 361
            for i in range(total):
                time.sleep(0.01)
                self.progress['value'] = i + 1
                self.status_text.config(text=f"{i+1}/{total} tamamlandı")
                if (i + 1) % 50 == 0: self.add_log(f"{i+1}/{total} sayfa tamamlandı", "success", "✅")
            self.status_text.config(text=f"{total}/{total} tamamlandı", fg=self.colors['success'])
            self.add_log("Tarama işlemi başarıyla tamamlandı!", "success", "🎉")
            messagebox.showinfo("Tamamlandı", "Tarama işlemi başarıyla tamamlandı!")
        threading.Thread(target=simulate, daemon=True).start()

    def stop_crawl(self):
        self.progress['value'] = 180
        self.status_text.config(text="180/361 durduruldu", fg=self.colors['warning'])
        self.add_log("Tarama işlemi kullanıcı tarafından durduruldu", "error", "⏹️")
        messagebox.showinfo("Durduruldu", "Tarama işlemi durduruldu!")

    def generate_report(self):
        person_name = self.person_name.get().strip()
        self.add_log(f"'{person_name}' için rapor oluşturuluyor...", "info", "📊")
        messagebox.showinfo("Rapor", f"'{person_name}' için detaylı rapor oluşturuluyor...")

    def add_to_database(self):
        # ---- FIX: PyMongo bool kontrolü yerine None karşılaştırması ----
        if self.mongo_client is None or self.mongo_db is None or self.mongo_coll is None:
            self.add_log("Mongo bağlantısı yok; kayıt yapılamadı.", "error", "🔴")
            messagebox.showerror("MongoDB", "Bağlantı yok. Uygulamayı yeniden başlatmayı deneyin.")
            return

        payload = self.collect_inputs()
        if not payload["person"]:
            messagebox.showwarning("Uyarı", "Lütfen kişi ismini girin!"); return
        if not payload["sources"]:
            messagebox.showwarning("Uyarı", "Lütfen en az bir veri kaynağı için bilgi girin!"); return

        self.add_log(f"'{payload['person']}' veritabanına ekleniyor...", "info", "💾")

        def op():
            try:
                doc = {
                    "person": payload["person"],
                    "sources": payload["sources"],
                    "created_at": datetime.now(timezone.utc),
                    "app": "ModernWebCrawlerUI"
                }
                result = self.mongo_coll.insert_one(doc)
                for k, v in payload["sources"].items():
                    self.add_log(f"{k}: {v}", "info", "📝")
                self.add_log(f"MongoDB insert_ok: {str(result.inserted_id)}", "success", "✅")
                messagebox.showinfo("Başarılı", "Veriler başarıyla MongoDB'ye eklendi.")
            except errors.PyMongoError as e:
                self.add_log(f"Mongo hata: {e}", "error", "❌")
                messagebox.showerror("MongoDB Hatası", str(e))

        threading.Thread(target=op, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = ModernWebCrawlerUI(root)
    root.mainloop()
