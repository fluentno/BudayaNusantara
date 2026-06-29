import json
import re
import os

PRODUCTS_FILE = "products.json"

# Kata kunci angka dalam bahasa Indonesia
ANGKA_MAP = {
    "satu": 1, "dua": 2, "tiga": 3, "empat": 4, "lima": 5,
    "enam": 6, "tujuh": 7, "delapan": 8, "sembilan": 9, "sepuluh": 10
}

# Semua kategori yang dikenali
KNOWN_CATEGORIES = ["jawa", "sunda", "bali", "sumatera", "melayu", "kalimantan", "sulawesi", "papua", "lombok", "madura"]


class NLPEngine:
    def __init__(self):
        self.menu_data = {}
        self.reload()

    def reload(self):
        """Muat ulang data produk dari products.json."""
        if os.path.exists(PRODUCTS_FILE):
            with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
                self.menu_data = json.load(f)
        else:
            self.menu_data = {}

    def get_display_name(self, key):
        """Ambil nama tampilan dari key produk."""
        data = self.menu_data.get(key, {})
        return data.get("name", key.capitalize())

    def detect_intent(self, text):
        """Deteksi maksud dari input pengguna."""
        t = text.lower().strip()

        if not t:
            return "EMPTY"

        # Reset / restart
        if any(k in t for k in ["reset", "mulai ulang", "restart"]):
            return "RESET"

        # Lihat menu / galeri
        if any(k in t for k in ["galeri", "menu", "daftar", "katalog", "semua produk", "apa saja", "lihat semua"]):
            return "ASK_MENU"

        # Pencarian keyword
        if any(k in t for k in ["cari", "search", "temukan", "tampilkan"]):
            return "SEARCH"

        # Filter kategori daerah — CEK SEBELUM STORY agar tidak bentrok
        for cat in KNOWN_CATEGORIES:
            if cat in t:
                # Hanya trigger FILTER_CATEGORY kalau bukan pesan/order/cerita
                if not any(k in t for k in ["pesan", "beli", "order", "cerita", "filosofi", "sejarah", "kisah"]):
                    return "FILTER_CATEGORY"

        # Cerita / filosofi produk
        if any(k in t for k in ["cerita", "filosofi", "sejarah", "kisah", "asal", "makna"]):
            return "ASK_STORY"

        # Batalkan semua
        if any(k in t for k in ["batalkan semua", "kosongkan", "hapus semua", "clear"]):
            return "CANCEL_ALL"

        # Kurangi / batalkan item tertentu
        if any(k in t for k in ["batalkan", "kurangi", "hapus", "cancel"]):
            return "REDUCE_ITEM"

        # Checkout / bayar
        if any(k in t for k in ["bayar", "checkout", "selesai", "pesan sekarang", "konfirmasi"]):
            return "CHECKOUT"

        # Konfirmasi ya/tidak
        if t in ["ya", "yes", "iya", "ok", "oke", "lanjut", "setuju", "betul"]:
            return "YES"
        if t in ["tidak", "no", "nggak", "batal", "ga", "gak"]:
            return "NO"

        return "OTHER"

    def parse_orders(self, text):
        """
        Ekstrak pesanan dari teks pengguna.
        Contoh: 'pesan 2 batik dan 1 wayang' → [{'item':'batik','qty':2}, {'item':'wayang','qty':1}]
        """
        orders = []
        t      = text.lower()

        # Ganti kata angka dengan angka
        for kata, angka in ANGKA_MAP.items():
            t = re.sub(rf"\b{kata}\b", str(angka), t)

        # Cari pola: [angka] [nama_produk]
        for key in self.menu_data.keys():
            # Pattern: angka diikuti nama produk (atau sebaliknya)
            patterns = [
                rf"(\d+)\s+{re.escape(key)}",     # "2 batik"
                rf"{re.escape(key)}\s+(\d+)",     # "batik 2"
            ]
            for pattern in patterns:
                match = re.search(pattern, t)
                if match:
                    qty = int(match.group(1))
                    if qty > 0:
                        # Hindari duplikat
                        if not any(o["item"] == key for o in orders):
                            orders.append({"item": key, "qty": qty})
                    break

        return orders

    def search_products(self, query):
        """
        Cari produk berdasarkan keyword.
        Mendukung filter harga: 'harga di bawah 150000', 'harga di atas 100000'
        """
        q      = query.lower().strip()
        result = []

        # Deteksi filter harga
        price_max = None
        price_min = None

        match_max = re.search(r"(di bawah|kurang dari|max|maksimal)\s*(\d+)", q)
        match_min = re.search(r"(di atas|lebih dari|min|minimal)\s*(\d+)", q)

        if match_max:
            price_max = int(match_max.group(2))
        if match_min:
            price_min = int(match_min.group(2))

        # Deteksi filter kategori dalam query pencarian
        cat_filter = None
        for cat in KNOWN_CATEGORIES:
            if cat in q:
                cat_filter = cat
                break

        for key, data in self.menu_data.items():
            # Filter harga
            if price_max and data["price"] > price_max:
                continue
            if price_min and data["price"] < price_min:
                continue

            # Filter kategori
            if cat_filter and data.get("category", "").lower() != cat_filter:
                continue

            # Filter keyword (kalau bukan hanya filter harga/kategori)
            keyword_only = re.sub(
                r"(di bawah|di atas|kurang dari|lebih dari|max|min|maksimal|minimal)\s*\d+", "", q
            ).strip()
            keyword_only = re.sub(
                r"\b(" + "|".join(KNOWN_CATEGORIES) + r")\b", "", keyword_only
            ).strip()

            if keyword_only:
                haystack = f"{key} {data.get('name','')} {data.get('desc','')} {data.get('category','')}".lower()
                if keyword_only not in haystack:
                    continue

            result.append({"key": key, **data})

        return result

    def get_products_by_category(self, category):
        """Ambil semua produk dalam kategori tertentu."""
        return {
            key: data
            for key, data in self.menu_data.items()
            if data.get("category", "").lower() == category.lower()
        }

    def get_all_categories(self):
        """Ambil daftar kategori yang tersedia."""
        cats = set()
        for data in self.menu_data.values():
            cat = data.get("category", "").strip()
            if cat:
                cats.add(cat)
        return sorted(cats)
