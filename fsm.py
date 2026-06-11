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

    def get_menu_text(self):
        teks = "**Galeri Karya Budaya Nusantara:**\n\n"
        for key, data in self.nlp.menu_data.items():
            display = data.get("name", key.capitalize())
            teks += f"- **{display}** (Rp {data['price']:,}): *{data['desc']}*\n"
        teks += "\nMari lestarikan budaya! Ketik pesananmu (contoh: 'Pesan 2 batik') atau ketik 'cerita [nama karya]' untuk tahu filosofinya."
        return teks

    def reduce_cart(self, item_key, qty_to_remove):
        for item in self.cart:
            if item['item'] == item_key:
                display = self.nlp.get_display_name(item_key)
                item['qty'] -= qty_to_remove
                if item['qty'] <= 0:
                    self.cart.remove(item)
                    return f"Karya **{display}** telah dihapus dari keranjang."
                else:
                    return f"Jumlah **{display}** dikurangi {qty_to_remove}. Sisa: {item['qty']}."
        display = self.nlp.get_display_name(item_key)
        return f"Gagal: **{display}** tidak ditemukan di keranjang Anda."

    def step(self, user_input=""):
        user_input = user_input.strip()
        intent     = self.nlp.detect_intent(user_input)

        if intent == "RESET":
            self.__init__()
            self.response = "Sistem di-reset. Halo! Mari dukung pengrajin lokal. Ketik 'galeri' untuk memulai."
            return

        if self.state == State.IDLE:
            self.state    = State.ORDERING
            self.response = "Halo, pejuang budaya! Mau lihat karya kerajinan apa hari ini? Ketik 'galeri' untuk melihat pilihan, atau 'cerita [karya]' untuk tahu sejarahnya."

        elif self.state == State.ORDERING:
            if intent == "ASK_MENU":
                # BARIS INI YANG DITAMBAHKAN AGAR OTOMATIS SINKRON KE API
                self.nlp.reload() 
                self.response = self.get_menu_text()

            elif intent == "ASK_STORY":
                found_key = None
                for key in self.nlp.menu_data.keys():
                    if key in user_input.lower():
                        found_key = key
                        break
                if found_key:
                    data    = self.nlp.menu_data[found_key]
                    display = data.get("name", found_key.capitalize())
                    self.response = (
                        f"**Filosofi {display}**\n{data['story']}\n\n"
                        f"*(Sumber: {data['source']})*\n\n"
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
                    results = [self.reduce_cart(i['item'], i['qty']) for i in items]
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
                            order.update({"price": info['price'], "image": info.get("image","")})
                            self.cart.append(order)
                        display = self.nlp.get_display_name(order['item'])
                        added.append(f"{display} x{order['qty']}")
                    self.response = f"Ditambahkan: {', '.join(added)}. Ada lagi? (Ketik 'bayar' untuk selesai)"
                else:
                    self.response = "Maaf, saya tidak mengerti. Coba: 'pesan 2 batik' atau 'ceritakan tentang angklung'."

        elif self.state == State.CONFIRMATION:
            if intent == "YES":
                self.state = State.PAYMENT
                self.step()
            elif intent == "NO":
                self.state    = State.ORDERING
                self.response = "Baik, silakan tambah atau ubah pesananmu."
            else:
                self.response = "Tolong jawab dengan 'Ya' atau 'Tidak'."

        elif self.state == State.PAYMENT:
            total         = self.calculate_total()
            self.response = f"Terima kasih! Pembayaran sebesar **Rp {total:,}** diterima. Kamu telah membantu melestarikan warisan budaya Nusantara! 🎉"
            self.cart     = []
            self.state    = State.IDLE
