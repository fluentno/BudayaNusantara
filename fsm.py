from enum import Enum, auto
from engine import NLPEngine

class State(Enum):
    IDLE         = auto()
    ORDERING     = auto()
    CONFIRMATION = auto()
    PAYMENT      = auto()


class BudayaFSM:
    def __init__(self):
        self.state    = State.IDLE
        self.nlp      = NLPEngine()
        self.cart     = []
        self.response = ""

    def get_response(self):
        return self.response

    def calculate_total(self):
        return sum(item['price'] * item['qty'] for item in self.cart)

    # ── Teks menu lengkap ──────────────────────────────────────
    def get_menu_text(self):
        cats = self.nlp.get_all_categories()
        teks = "**Galeri Karya Budaya Nusantara:**\n\n"
        for key, data in self.nlp.menu_data.items():
            display  = data.get("name", key.capitalize())
            cat_info = f" *(Daerah: {data['category'].capitalize()})*" if data.get("category") else ""
            teks += f"- **{display}** (Rp {data['price']:,}): *{data['desc']}*{cat_info}\n"

        if cats:
            cat_list = ", ".join(c.capitalize() for c in cats)
            teks += f"\n💡 Filter per daerah: ketik **'kategori [nama daerah]'** — tersedia: {cat_list}"
        teks += "\n\nKetik pesananmu (contoh: 'Pesan 2 batik') atau ketik 'cerita [nama karya]' untuk tahu filosofinya."
        return teks

    # ── Teks menu per kategori ─────────────────────────────────
    def get_menu_by_category(self, category):
        filtered = self.nlp.get_products_by_category(category)
        if not filtered:
            all_cats = self.nlp.get_all_categories()
            cat_list = ", ".join(c.capitalize() for c in all_cats) if all_cats else "belum ada"
            return (
                f"Belum ada karya dari kategori **{category.capitalize()}** saat ini.\n\n"
                f"Kategori yang tersedia: {cat_list}.\n"
                f"Atau ketik **'galeri'** untuk melihat semua karya."
            )

        teks = f"**Karya Budaya Daerah {category.capitalize()}** ({len(filtered)} karya):\n\n"
        for key, data in filtered.items():
            display = data.get("name", key.capitalize())
            teks   += f"- **{display}** (Rp {data['price']:,}): *{data['desc']}*\n"
        teks += "\nKetik 'pesan [jumlah] [nama karya]' untuk memesan, atau 'cerita [nama karya]' untuk tahu filosofinya."
        return teks

    # ── Format hasil pencarian ────────────────────────────────
    def format_search_results(self, results, query):
        if not results:
            return (
                f"🔍 Tidak ada karya yang cocok dengan pencarian **\"{query}\"**.\n\n"
                "Coba kata kunci lain, atau ketik **'galeri'** untuk melihat semua karya."
            )
        teks = f"🔍 **Hasil pencarian untuk \"{query}\"** — {len(results)} karya ditemukan:\n\n"
        for data in results:
            display  = data.get("name", data["key"].capitalize())
            cat_info = f" *(Daerah: {data['category'].capitalize()})*" if data.get("category") else ""
            teks    += f"- **{display}** (Rp {data['price']:,}): *{data['desc']}*{cat_info}\n"
        teks += "\nKetik 'pesan [jumlah] [nama karya]' untuk memesan, atau 'cerita [nama karya]' untuk tahu filosofinya."
        return teks

    # ── Kurangi item di keranjang ─────────────────────────────
    def reduce_cart(self, item_key, qty_to_remove):
        for item in self.cart:
            if item['item'] == item_key:
                display    = self.nlp.get_display_name(item_key)
                item['qty'] -= qty_to_remove
                if item['qty'] <= 0:
                    self.cart.remove(item)
                    return f"Karya **{display}** telah dihapus dari keranjang."
                else:
                    return f"Jumlah **{display}** dikurangi {qty_to_remove}. Sisa: {item['qty']}."
        display = self.nlp.get_display_name(item_key)
        return f"Gagal: **{display}** tidak ditemukan di keranjang Anda."

    # ── Mesin utama FSM ───────────────────────────────────────
    def step(self, user_input=""):
        import re
        user_input = user_input.strip()
        intent     = self.nlp.detect_intent(user_input)

        # ── RESET (bisa dari state mana saja) ─────────────────
        if intent == "RESET":
            self.__init__()
            self.response = "Sistem di-reset. Halo! Mari dukung pengrajin lokal. Ketik 'galeri' untuk memulai."
            return

        # ── STATE: IDLE ───────────────────────────────────────
        if self.state == State.IDLE:
            self.state    = State.ORDERING
            cats          = self.nlp.get_all_categories()
            cat_hint      = ""
            if cats:
                cat_list = ", ".join(c.capitalize() for c in cats)
                cat_hint = f" Atau ketik **'kategori [daerah]'** untuk melihat karya per daerah ({cat_list})."
            self.response = (
                "Halo, pejuang budaya! Mau lihat karya kerajinan apa hari ini? "
                "Ketik **'galeri'** untuk melihat semua pilihan, **'cari [kata kunci]'** untuk mencari karya tertentu, "
                f"atau **'cerita [karya]'** untuk tahu sejarahnya.{cat_hint}"
            )

        # ── STATE: ORDERING ───────────────────────────────────
        elif self.state == State.ORDERING:

            if intent == "ASK_MENU":
                self.nlp.reload()
                self.response = self.get_menu_text()

            elif intent == "FILTER_CATEGORY":
                # Ekstrak nama kategori dari input
                from engine import KNOWN_CATEGORIES
                t         = user_input.lower()
                found_cat = next((cat for cat in KNOWN_CATEGORIES if cat in t), None)
                if found_cat:
                    self.response = self.get_menu_by_category(found_cat)
                else:
                    cats      = self.nlp.get_all_categories()
                    cat_list  = ", ".join(c.capitalize() for c in cats) if cats else "belum ada data"
                    self.response = (
                        f"Daerah mana yang ingin kamu jelajahi?\n"
                        f"Kategori tersedia: **{cat_list}**\n\n"
                        "Contoh: 'kategori jawa', 'tampilkan karya sunda', 'karya dari bali'"
                    )

            elif intent == "SEARCH":
                query_match = re.sub(
                    r"^\s*(cari|search|temukan|tampilkan)\s*", "", user_input, flags=re.IGNORECASE
                ).strip()
                query         = query_match if query_match else user_input
                results       = self.nlp.search_products(query)
                self.response = self.format_search_results(results, query)

            elif intent == "ASK_STORY":
                found_key = None
                for key in self.nlp.menu_data.keys():
                    if key in user_input.lower():
                        found_key = key
                        break
                if found_key:
                    data    = self.nlp.menu_data[found_key]
                    display = data.get("name", found_key.capitalize())
                    cat_info = f"\n🗺️ *Daerah asal: {data['category'].capitalize()}*" if data.get("category") else ""
                    self.response = (
                        f"**Filosofi {display}**\n{data['story']}\n\n"
                        f"*(Sumber: {data['source']})*{cat_info}\n\n"
                        f"Tertarik melestarikannya? Ketik 'pesan 1 {found_key}'."
                    )
                else:
                    self.response = "Karya apa yang ingin kamu ketahui? Contoh: 'ceritakan sejarah wayang'."

            elif intent == "CANCEL_ALL":
                self.cart     = []
                self.response = "Keranjang telah dikosongkan. Mau pesan karya yang lain?"

            elif intent == "REDUCE_ITEM":
                items = self.nlp.parse_orders(user_input)
                if items:
                    results       = [self.reduce_cart(i['item'], i['qty']) for i in items]
                    self.response = "\n".join(results)
                else:
                    self.response = "Karya apa yang ingin dibatalkan? Contoh: 'batalkan 1 batik'."

            elif intent == "CHECKOUT":
                if not self.cart:
                    self.response = "Keranjang apresiasimu masih kosong."
                else:
                    self.state    = State.CONFIRMATION
                    self.response = f"Total belanja: **Rp {self.calculate_total():,}**. Lanjut bayar? (Ya/Tidak)"

            else:
                new_orders = self.nlp.parse_orders(user_input)
                if new_orders:
                    added = []
                    for order in new_orders:
                        existing = next((i for i in self.cart if i['item'] == order['item']), None)
                        if existing:
                            existing['qty'] += order['qty']
                        else:
                            info = self.nlp.menu_data[order['item']]
                            order.update({"price": info['price'], "image": info.get("image", "")})
                            self.cart.append(order)
                        display = self.nlp.get_display_name(order['item'])
                        added.append(f"{display} x{order['qty']}")
                    self.response = f"Ditambahkan: {', '.join(added)}. Ada lagi? (Ketik 'bayar' untuk selesai)"
                else:
                    cats      = self.nlp.get_all_categories()
                    cat_list  = ", ".join(c.capitalize() for c in cats) if cats else ""
                    cat_hint  = f"\n- **'kategori [daerah]'** — filter per daerah ({cat_list})" if cat_list else ""
                    self.response = (
                        "Maaf, saya tidak mengerti. Coba:\n"
                        "- **'galeri'** — lihat semua produk\n"
                        "- **'cari [kata kunci]'** — cari produk spesifik\n"
                        "- **'cari harga di bawah 150000'** — filter harga\n"
                        f"- **'pesan 2 batik'** — pesan langsung{cat_hint}"
                    )

        # ── STATE: CONFIRMATION ───────────────────────────────
        elif self.state == State.CONFIRMATION:
            if intent == "YES":
                self.state = State.PAYMENT
                self.step()
            elif intent == "NO":
                self.state    = State.ORDERING
                self.response = "Baik, silakan tambah atau ubah pesananmu."
            else:
                self.response = "Tolong jawab dengan 'Ya' atau 'Tidak'."

        # ── STATE: PAYMENT ────────────────────────────────────
        elif self.state == State.PAYMENT:
            total         = self.calculate_total()
            self.response = f"Terima kasih! Pembayaran sebesar **Rp {total:,}** diterima. Kamu telah membantu melestarikan warisan budaya Nusantara! 🎉"
            self.cart     = []
            self.state    = State.IDLE
