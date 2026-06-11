import streamlit as st
from fsm import BudayaFSM

# --- 1. SETUP HALAMAN ---
# Menggunakan layout centered karena akan di-embed di iFrame berukuran kecil (380px)
st.set_page_config(page_title="Asisten Budaya", page_icon="🎭", layout="centered")

# --- 2. CUSTOM CSS UNTUK TAMPILAN IFRAME YANG BERSIH ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
        background-color: #FAFAF8;
    }
    
    /* Sembunyikan elemen bawaan Streamlit agar terlihat seperti widget chat asli */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Modifikasi kotak expander keranjang */
    div[data-testid="stExpander"] {
        background-color: #FFF8DC;
        border: 1px solid #EDE0CC;
        border-radius: 10px;
    }

    /* Modifikasi tampilan bubble chat */
    [data-testid="stChatMessage"] {
        background-color: white;
        border: 1px solid #EDE0CC;
        border-radius: 12px;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. INISIALISASI FSM & STATE ---
if 'bot' not in st.session_state:
    st.session_state.bot = BudayaFSM()
    st.session_state.bot.step() # Memicu state awal (IDLE -> ORDERING)
    st.session_state.history = [{"role": "assistant", "content": st.session_state.bot.get_response()}]

# --- 4. WIDGET KERANJANG (DI BAGIAN ATAS CHAT) ---
# Dibuat menggunakan expander agar bisa dilipat dan menghemat ruang di layar kecil
cart_count = sum(item['qty'] for item in st.session_state.bot.cart)
with st.expander(f"🛒 Keranjang Belanja ({cart_count} Item)", expanded=False):
    if st.session_state.bot.cart:
        total = 0
        for item in st.session_state.bot.cart:
            subtotal = item['price'] * item['qty']
            total += subtotal
            st.markdown(f"**{item['item'].capitalize()}** (x{item['qty']}) — Rp {subtotal:,}")
            
        st.divider()
        st.markdown(f"**Total Pembayaran: Rp {total:,}**")
        
        if st.button("🗑️ Kosongkan Keranjang", use_container_width=True):
            st.session_state.bot.cart = []
            st.rerun()
    else:
        st.info("Keranjangmu masih kosong. Yuk pesan sesuatu!")

# --- 5. AREA CHAT HISTORY ---
# Menggunakan height fix agar chat bisa di-scroll dengan rapi di dalam iFrame
chat_container = st.container(height=350, border=False)
with chat_container:
    for msg in st.session_state.history:
        avatar = "🎭" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

# --- 6. LOGIKA INPUT USER ---
if prompt := st.chat_input("Ketik pesan... (cth: pesan 1 batik)"):
    # Simpan input user
    st.session_state.history.append({"role": "user", "content": prompt})
    
    # Jalankan FSM Engine
    with st.spinner("Sari sedang mengetik..."):
        st.session_state.bot.step(prompt)
        bot_reply = st.session_state.bot.get_response()
        
    # Simpan balasan bot
    st.session_state.history.append({"role": "assistant", "content": bot_reply})
    
    # Trigger efek balon jika checkout sukses
    if "Terima kasih! Pembayaran" in bot_reply:
        st.balloons()
        
    st.rerun()