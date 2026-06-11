"""
server.py — Flask backend dengan SQLite (Railway-ready)
"""
import os
import json
import base64
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_FILE      = "products.db"
UPLOAD_FOLDER = "."

# ── Init database ─────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            key     TEXT PRIMARY KEY,
            name    TEXT NOT NULL,
            price   INTEGER NOT NULL,
            image   TEXT,
            desc    TEXT,
            story   TEXT,
            source  TEXT
        )
    """)
    # Seed data awal jika tabel masih kosong
    if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        seeds = [
            ("batik",    "Batik",    150000, "batik.jpg",    "Kain motif tradisional Nusantara",                "Batik diakui UNESCO 2009 sebagai Warisan Kemanusiaan.",      "UNESCO 2009"),
            ("wayang",   "Wayang",   250000, "wayang.png",   "Kerajinan kulit tokoh pewayangan",                "Terbuat dari kulit kerbau, media moral epik Nusantara.",     "UNESCO 2003"),
            ("angklung", "Angklung", 75000,  "angklung.png", "Alat musik bambu khas Sunda",                     "Satu angklung = satu nada, harmoni lewat kerja sama.",       "UNESCO 2010"),
            ("ukiran",   "Ukiran",   120000, "ukiran.jpg",   "Hiasan pahatan kayu khas Jepara",                 "Ada sejak abad ke-16, harmoni manusia & alam.",              "Kemendikbud RI"),
            ("songket",  "Kain Songket", 350000, "songket.jpg", "Kain tenun tradisional benang emas khas Sumatera", "Songket ditenun dengan benang emas, dulunya hanya untuk bangsawan Melayu.", "Kemendikbud RI"),
            ("kipas",    "Kipas Kayu Cendana", 150000, "kipas.jpg", "Kerajinan tangan berbahan kayu cendana khas Bali", "Kayu cendana dipilih karena aromanya yang harum dan bernilai spiritual.", "Dinas Kebudayaan Bali"),
        ]
        conn.executemany(
            "INSERT INTO products (key,name,price,image,desc,story,source) VALUES (?,?,?,?,?,?,?)",
            seeds
        )
    conn.commit()
    conn.close()
    print("[DB] Database siap.")

# ── Helper: rows → dict ───────────────────────────────────────
def rows_to_dict(rows):
    result = {}
    for row in rows:
        result[row["key"]] = {
            "name":   row["name"],
            "price":  row["price"],
            "image":  row["image"] or "",
            "desc":   row["desc"]  or "",
            "story":  row["story"] or "",
            "source": row["source"] or ""
        }
    return result

# ── GET semua produk ──────────────────────────────────────────
@app.route("/products", methods=["GET"])
def get_products():
    conn = get_db()
    rows = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return jsonify(rows_to_dict(rows))

# ── POST tambah produk ────────────────────────────────────────
@app.route("/products", methods=["POST"])
def add_product():
    body    = request.get_json()
    name    = body.get("name", "").strip()
    desc    = body.get("desc", "").strip()
    price   = int(body.get("price", 0))
    story   = body.get("story", "Karya warisan kerajinan tangan Nusantara.").strip()
    source  = body.get("source", "Kontribusi Kolektor Lokal").strip()
    img_b64 = body.get("image_base64", "")
    img_ext = body.get("image_ext", "jpg")

    if not name or not desc or not price:
        return jsonify({"ok": False, "error": "Nama, deskripsi, dan harga wajib diisi."}), 400

    key = name.lower().split()[0]

    # Simpan gambar jika ada
    image_filename = ""
    if img_b64 and "," in img_b64:
        try:
            _, encoded    = img_b64.split(",", 1)
            image_filename = f"{key}.{img_ext}"
            with open(os.path.join(UPLOAD_FOLDER, image_filename), "wb") as f:
                f.write(base64.b64decode(encoded))
        except Exception as e:
            print(f"[WARN] Gagal simpan gambar: {e}")

    conn = get_db()
    conn.execute("""
        INSERT INTO products (key,name,price,image,desc,story,source)
        VALUES (?,?,?,?,?,?,?)
        ON CONFLICT(key) DO UPDATE SET
            name=excluded.name, price=excluded.price, image=excluded.image,
            desc=excluded.desc, story=excluded.story, source=excluded.source
    """, (key, name, price, image_filename or f"{key}.jpg", desc, story, source))
    conn.commit()
    conn.close()
    print(f"[OK] Produk disimpan: {name} (key: {key})")
    return jsonify({"ok": True, "key": key, "image": image_filename})

# ── DELETE hapus produk ───────────────────────────────────────
@app.route("/products/<key>", methods=["DELETE"])
def delete_product(key):
    conn = get_db()
    cur  = conn.execute("DELETE FROM products WHERE key = ?", (key,))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        return jsonify({"ok": False, "error": "Produk tidak ditemukan."}), 404
    print(f"[OK] Produk dihapus: {key}")
    return jsonify({"ok": True})

# ── Serve index.html (opsional) ───────────────────────────────
@app.route("/")
def index():
    return app.send_static_file("index.html")

if __name__ == "__main__":
    init_db()
    port  = int(os.environ.get("PORT", 5050))
    debug = os.environ.get("FLASK_ENV") != "production"
    print(f"  Server berjalan di port {port}")
    app.run(debug=debug, host="0.0.0.0", port=port)