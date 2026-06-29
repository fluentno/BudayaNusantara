"""
server.py — Flask backend dengan SQLite (Railway-ready)
"""
import os
import json
import base64
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__, static_url_path='', static_folder='.')
CORS(app)

DB_FILE       = "products.db"
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
            key      TEXT PRIMARY KEY,
            name     TEXT NOT NULL,
            price    INTEGER NOT NULL,
            image    TEXT,
            desc     TEXT,
            story    TEXT,
            source   TEXT,
            category TEXT DEFAULT ''
        )
    """)
    # Tambah kolom category jika tabel lama belum punya kolom ini
    try:
        conn.execute("ALTER TABLE products ADD COLUMN category TEXT DEFAULT ''")
        conn.commit()
        print("[DB] Kolom 'category' berhasil ditambahkan.")
    except Exception:
        pass  # Kolom sudah ada, abaikan

    # Seed data awal jika tabel masih kosong
    if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        seeds = [
            ("batik",    "Batik",               150000, "batik.jpg",    "Kain motif tradisional Nusantara",                 "Batik diakui UNESCO 2009 sebagai Warisan Kemanusiaan.",                          "UNESCO 2009",                  "jawa"),
            ("wayang",   "Wayang",              250000, "wayang.png",   "Kerajinan kulit tokoh pewayangan",                 "Terbuat dari kulit kerbau, media moral epik Nusantara.",                         "UNESCO 2003",                  "jawa"),
            ("angklung", "Angklung",             75000, "angklung.png", "Alat musik bambu khas Sunda",                      "Satu angklung = satu nada, harmoni lewat kerja sama.",                           "UNESCO 2010",                  "sunda"),
            ("ukiran",   "Ukiran",              120000, "ukiran.jpg",   "Hiasan pahatan kayu khas Jepara",                  "Ada sejak abad ke-16, harmoni manusia & alam.",                                  "Kemendikbud RI",               "jawa"),
            ("songket",  "Kain Songket",        350000, "songket.jpg",  "Kain tenun tradisional benang emas khas Sumatera", "Songket ditenun dengan benang emas, dulunya hanya untuk bangsawan Melayu.",      "Kemendikbud RI",               "sumatera"),
            ("kipas",    "Kipas Kayu Cendana",  150000, "kipas.jpg",    "Kerajinan tangan berbahan kayu cendana khas Bali", "Kayu cendana dipilih karena aromanya yang harum dan bernilai spiritual.",        "Dinas Kebudayaan Bali",        "bali"),
        ]
        conn.executemany(
            "INSERT INTO products (key,name,price,image,desc,story,source,category) VALUES (?,?,?,?,?,?,?,?)",
            seeds
        )
    else:
        # Update category untuk data lama yang belum punya category
        updates = [
            ("jawa",     "batik"),
            ("jawa",     "wayang"),
            ("sunda",    "angklung"),
            ("jawa",     "ukiran"),
            ("sumatera", "songket"),
            ("bali",     "kipas"),
        ]
        conn.executemany(
            "UPDATE products SET category=? WHERE key=? AND (category IS NULL OR category='')",
            updates
        )

    conn.commit()
    conn.close()
    print("[DB] Database siap.")

# ── Helper: rows → dict ───────────────────────────────────────
def rows_to_dict(rows):
    result = {}
    for row in rows:
        result[row["key"]] = {
            "name":     row["name"],
            "price":    row["price"],
            "image":    row["image"]    or "",
            "desc":     row["desc"]     or "",
            "story":    row["story"]    or "",
            "source":   row["source"]   or "",
            "category": row["category"] or ""
        }
    return result

# ── GET semua produk (bisa difilter by ?category=jawa) ────────
@app.route("/products", methods=["GET"])
def get_products():
    category = request.args.get("category", "").strip().lower()
    conn = get_db()
    if category:
        rows = conn.execute(
            "SELECT * FROM products WHERE LOWER(category) = ?", (category,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return jsonify(rows_to_dict(rows))

# ── GET daftar semua kategori yang tersedia ───────────────────
@app.route("/categories", methods=["GET"])
def get_categories():
    conn = get_db()
    rows = conn.execute(
        "SELECT DISTINCT category FROM products WHERE category != '' ORDER BY category"
    ).fetchall()
    conn.close()
    categories = [row["category"] for row in rows]
    return jsonify(categories)

# ── POST tambah produk ────────────────────────────────────────
@app.route("/products", methods=["POST"])
def add_product():
    body     = request.get_json()
    name     = body.get("name",     "").strip()
    desc     = body.get("desc",     "").strip()
    price    = int(body.get("price", 0))
    story    = body.get("story",    "Karya warisan kerajinan tangan Nusantara.").strip()
    source   = body.get("source",   "Kontribusi Kolektor Lokal").strip()
    category = body.get("category", "").strip().lower()
    img_b64  = body.get("image_base64", "")
    img_ext  = body.get("image_ext", "jpg")

    if not name or not desc or not price:
        return jsonify({"ok": False, "error": "Nama, deskripsi, dan harga wajib diisi."}), 400

    key = name.lower().split()[0]

    # Simpan gambar jika ada
    image_filename = ""
    if img_b64 and "," in img_b64:
        try:
            _, encoded     = img_b64.split(",", 1)
            image_filename = f"{key}.{img_ext}"
            with open(os.path.join(UPLOAD_FOLDER, image_filename), "wb") as f:
                f.write(base64.b64decode(encoded))
        except Exception as e:
            print(f"[WARN] Gagal simpan gambar: {e}")

    conn = get_db()
    conn.execute("""
        INSERT INTO products (key,name,price,image,desc,story,source,category)
        VALUES (?,?,?,?,?,?,?,?)
        ON CONFLICT(key) DO UPDATE SET
            name=excluded.name, price=excluded.price, image=excluded.image,
            desc=excluded.desc, story=excluded.story, source=excluded.source,
            category=excluded.category
    """, (key, name, price, image_filename or f"{key}.jpg", desc, story, source, category))
    conn.commit()
    conn.close()
    print(f"[OK] Produk disimpan: {name} (key: {key}, category: {category})")
    return jsonify({"ok": True, "key": key, "image": image_filename})

# ── PUT edit produk ───────────────────────────────────────────
@app.route("/products/<key>", methods=["PUT"])
def update_product(key):
    conn = get_db()
    if not conn.execute("SELECT 1 FROM products WHERE key = ?", (key,)).fetchone():
        conn.close()
        return jsonify({"ok": False, "error": "Produk tidak ditemukan."}), 404

    body     = request.get_json()
    name     = body.get("name",     "").strip()
    desc     = body.get("desc",     "").strip()
    price    = int(body.get("price", 0))
    story    = body.get("story",    "").strip()
    source   = body.get("source",   "").strip()
    category = body.get("category", "").strip().lower()
    img_b64  = body.get("image_base64", "")
    img_ext  = body.get("image_ext", "jpg")

    if not name or not desc or not price:
        conn.close()
        return jsonify({"ok": False, "error": "Nama, deskripsi, dan harga wajib diisi."}), 400

    # Update gambar jika ada yang baru
    image_filename = ""
    if img_b64 and "," in img_b64:
        try:
            _, encoded     = img_b64.split(",", 1)
            image_filename = f"{key}.{img_ext}"
            with open(os.path.join(UPLOAD_FOLDER, image_filename), "wb") as f:
                f.write(base64.b64decode(encoded))
        except Exception as e:
            print(f"[WARN] Gagal simpan gambar: {e}")

    # Ambil image lama kalau tidak ada gambar baru
    if not image_filename:
        row            = conn.execute("SELECT image FROM products WHERE key = ?", (key,)).fetchone()
        image_filename = row["image"] if row else f"{key}.jpg"

    conn.execute("""
        UPDATE products SET name=?, price=?, image=?, desc=?, story=?, source=?, category=?
        WHERE key=?
    """, (name, price, image_filename, desc, story, source, category, key))
    conn.commit()
    conn.close()
    print(f"[OK] Produk diperbarui: {name} (key: {key}, category: {category})")
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

# ── Serve index.html ──────────────────────────────────────────
@app.route("/")
def index():
    return app.send_static_file("index.html")

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=False, host="0.0.0.0", port=port)
