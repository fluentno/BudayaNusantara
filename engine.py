import re
import json
import requests

class NLPEngine:
    def __init__(self):
        self.menu_data = self._load_products()
        self._build_patterns()

    def _load_products(self):
        API_URL = "https://web-budaya.up.railway.app/products" 
        
        try:
            # Chatbot mencoba mengambil data langsung dari API
            response = requests.get(API_URL)
            if response.status_code == 200:
                data = response.json()
                print(f"[engine] Sukses sinkronisasi dari API: {list(data.keys())}")
                return data
        except Exception as e:
            print(f"[engine] Gagal sinkronisasi API: {e}")

        # Prioritas Terakhir: Hardcode default (muncul kalau API lagi error/mati)
        print("[engine] Pakai data default karena API gagal.")
        return {
            "batik":    {"name":"Batik",    "price":150000, "image":"batik.jpg",    "desc":"Kain motif tradisional Nusantara",   "story":"Diakui UNESCO 2009.", "source":"UNESCO 2009"},
            "wayang":   {"name":"Wayang",   "price":250000, "image":"wayang.png",   "desc":"Kerajinan kulit tokoh pewayangan",   "story":"Media moral epik Nusantara.", "source":"UNESCO 2003"},
            "angklung": {"name":"Angklung", "price":75000,  "image":"angklung.png", "desc":"Alat musik bambu khas Sunda",        "story":"Satu nada, harmoni bersama.", "source":"UNESCO 2010"},
            "ukiran":   {"name":"Ukiran",   "price":120000, "image":"ukiran.jpg",   "desc":"Hiasan pahatan kayu khas Jepara",    "story":"Ada sejak abad ke-16.", "source":"Kemendikbud RI"},
        }

    def _build_patterns(self):
        self.re_number     = r"\b(\d+)\b"
        menu_keys          = "|".join(re.escape(k) for k in self.menu_data.keys())
        self.re_menu       = rf"\b({menu_keys})\b"
        self.re_split      = r"[,.]|\bdan\b|\b&\b"
        self.re_cancel_all = r"\b(batalkan semua|hapus semua|reset keranjang|kosongkan)\b"
        self.re_reduce     = r"\b(batalkan|kurangi|tidak jadi|hapus|cancel)\b"

    def reload(self):
        self.menu_data = self._load_products()
        self._build_patterns()

    def get_display_name(self, key):
        return self.menu_data.get(key, {}).get("name", key.capitalize())

    def _parse_single_segment(self, text):
        text = text.lower().strip()
        item_match = re.search(self.re_menu, text)
        if not item_match:
            return None
        item_key  = item_match.group(1)
        qty_match = re.search(self.re_number, text)
        qty = int(qty_match.group(1)) if qty_match else 1
        return {
            "item":  item_key,
            "qty":   qty,
            "price": self.menu_data[item_key]["price"],
            "image": self.menu_data[item_key].get("image", "")
        }

    def parse_orders(self, full_text):
        segments = re.split(self.re_split, full_text)
        return [o for seg in segments if seg.strip() for o in [self._parse_single_segment(seg)] if o]

    def detect_intent(self, text):
        t = text.lower()
        if re.search(r"\b(reset|ulang|batal semua)\b", t):                      return "RESET"
        if re.search(self.re_cancel_all, t):                                     return "CANCEL_ALL"
        if re.search(self.re_reduce, t):                                         return "REDUCE_ITEM"
        if re.search(r"(galeri|menu|daftar|apa saja|jual apa|list|karya)", t):  return "ASK_MENU"
        if re.search(r"\b(cerita|filosofi|sejarah|info|tentang)\b", t):         return "ASK_STORY"
        if re.search(r"\b(selesai|bayar|checkout|cukup)\b", t):                 return "CHECKOUT"
        if re.search(r"\b(ya|yes|oke|betul|siap|baik)\b", t):                  return "YES"
        if re.search(r"\b(tidak|enggak|batal|no|salah)\b", t):                 return "NO"
        return "UNKNOWN"
