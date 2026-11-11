import json, os, sqlite3, secrets, hashlib, hmac
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

DB = os.path.join(os.path.dirname(__file__), "parkirkita.db")
AREAS = [
    ("Motor Gerbang Utara", "Gerbang Utara", "motor", 300),
    ("Motor Gedung Fakultas", "Gedung Fakultas", "motor", 200),
    ("Motor Perpustakaan", "Perpustakaan", "motor", 120),
    ("Mobil Gerbang Utara", "Gerbang Utara", "mobil", 80),
    ("Mobil Gedung Rektorat", "Gedung Rektorat", "mobil", 60),
    ("Mobil Auditorium", "Auditorium", "mobil", 100),
]

def db():
    c = sqlite3.connect(DB, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

def make_hash(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    value = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return salt.hex() + "$" + value.hex()

def check_hash(password, saved):
    try:
        salt, expected = saved.split("$")
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt),
                                n=2**14, r=8, p=1).hex()
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False

def setup():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY, nama TEXT, username TEXT UNIQUE,
          password_hash TEXT, role TEXT, aktif INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS sessions(
          token TEXT PRIMARY KEY, user_id INTEGER REFERENCES users(id));
        CREATE TABLE IF NOT EXISTS parking_areas(
          id INTEGER PRIMARY KEY, nama TEXT, lokasi TEXT, jenis TEXT,
          kapasitas INTEGER CHECK(kapasitas>0),
          terisi INTEGER DEFAULT 0 CHECK(terisi>=0 AND terisi<=kapasitas),
          aktif INTEGER DEFAULT 1, diperbarui TEXT);
        CREATE TABLE IF NOT EXISTS parking_events(
          id INTEGER PRIMARY KEY, area_id INTEGER REFERENCES parking_areas(id),
          user_id INTEGER REFERENCES users(id), jenis TEXT, jumlah INTEGER,
          sebelum INTEGER, sesudah INTEGER, waktu TEXT);
        ''')
        if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            c.execute("INSERT INTO users(nama,username,password_hash,role) VALUES(?,?,?,?)",
                      ("Petugas Demo","petugas1",make_hash("parkir123"),"petugas"))
            c.execute("INSERT INTO users(nama,username,password_hash,role) VALUES(?,?,?,?)",
                      ("Admin Demo","admin",make_hash("admin123"),"admin"))
        if c.execute("SELECT COUNT(*) FROM parking_areas").fetchone()[0] == 0:
            now = datetime.now().isoformat(timespec="seconds")
            c.executemany("INSERT INTO parking_areas(nama,lokasi,jenis,kapasitas,terisi,diperbarui) VALUES(?,?,?,?,0,?)",
                          [(a,b,k,n,now) for a,b,k,n in AREAS])

def status(sisa, kapasitas):
    if sisa == 0: return "Penuh"
    if sisa / kapasitas <= .20: return "Hampir penuh"
    return "Tersedia"

PAGE = os.path.join(os.path.dirname(__file__), "index.html")

class App(BaseHTTPRequestHandler):
    def send_json(self, data, code=200, extra=None):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(body)))
        for k,v in (extra or {}).items(): self.send_header(k,v)
        self.end_headers()
        self.wfile.write(body)

    def body(self):
        try:
            n = int(self.headers.get("Content-Length",0))
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception: return {}

    def token(self):
        for item in self.headers.get("Cookie","").split(";"):
            if item.strip().startswith("parkirkita="):
                return item.strip().split("=",1)[1]
        return None

    def user(self, c):
        t = self.token()
        if not t: return None
        r = c.execute("SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND u.aktif=1",(t,)).fetchone()
        return r

    def do_GET(self):
        path = urlparse(self.path)

        if urlparse(self.path).path in ("/", "/index.html"):
            file_html = Path(__file__).parent / "index.html"

            if file_html.exists():
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(file_html.read_bytes())
                return

        if path.path == "/api/me":
            with db() as c:
                u = self.user(c)

                if not u:
                    self.send_json({
                        "logged_in": False
                    })
                    return
                
                self.send_json({
                    "logged_in": True,
                    "id": u["id"],
                    "nama": u["nama"],
                    "username": u["username"],
                    "role": u["role"]
                })
                return
            self.send_json({"error":"Halaman tidak ditemukan."}, 404)

            # with open(PAGE,"rb") as f: body=f.read()
            # self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8")
            # self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body); return
        
        if path.path == "/api/admin/stats":
            with db() as c:
                u = self.user(c)

                if not u or u["role"] != "admin":
                    self.send_json({
                        "error": "Akses hanya untuk admin."
                    }, 403)
                    return
                
                areas = c.execute("""
                    SELECT jenis,
                    SUM(kapasitas) AS kapasitas,
                    SUM(terisi) AS terisi
                    FROM parking_areas
                    WHERE aktif = 1
                    GROUP BY jenis
                """).fetchall()

                statistik = []

                for a in areas:
                    statistik.append({
                        "jenis": a["jenis"],
                        "kapasitas": a["kapasitas"],
                        "terisi": a["terisi"],
                        "sisa": a["kapasitas"] - a["terisi"]
                    })

                events = c.execute("""
                    SELECT
                        jenis, 
                        COUNT(*) AS jumlah_transaksi,
                        SUM(jumlah) AS total_kendaraan
                    FROM parking_events
                    GROUP BY jenis
                """).fetchall()

                aktivitas = [
                    {
                        "jenis": e["jenis"],
                        "transaksi": e["jumlah_transaksi"],
                        "kendaraan": e["total_kendaraan"]
                    }
                    for e in events
                ]

                self.send_json({
                    "statistik": statistik,
                    "aktivitas": aktivitas
                })
                return

        if path.path == "/api/areas":
            kind = parse_qs(path.query).get("jenis",["semua"])[0]
            with db() as c:
                rows = c.execute("SELECT * FROM parking_areas WHERE aktif=1").fetchall()
                all_areas=[]
                for r in rows:
                    left=r["kapasitas"]-r["terisi"]
                    all_areas.append(dict(id=r["id"],nama=r["nama"],lokasi=r["lokasi"],jenis=r["jenis"],
                        kapasitas=r["kapasitas"],terisi=r["terisi"],sisa=left,status=status(left,r["kapasitas"])))
                totals={k:sum(x["sisa"] for x in all_areas if x["jenis"]==k) for k in ("motor","mobil")}
                shown=all_areas if kind not in ("motor","mobil") else [x for x in all_areas if x["jenis"]==kind]
                self.send_json({"areas":shown,"ringkasan":totals}); return
        if path.path == "/api/events":
            with db() as c:
                u=self.user(c)
                if not u: self.send_json({"error":"Silakan login dahulu."},401); return
                rows=c.execute("SELECT e.*,a.nama area FROM parking_events e JOIN parking_areas a ON a.id=e.area_id ORDER BY e.id DESC LIMIT 20").fetchall()
                events=[dict(waktu=r["waktu"].replace("T"," "),area=r["area"],jenis=r["jenis"],
                    jumlah=r["jumlah"],sebelum=r["sebelum"],sesudah=r["sesudah"]) for r in rows]
                self.send_json({"nama":u["nama"],"role":u["role"],"events":events}); return
        self.send_json({"error":"Halaman tidak ditemukan."},404)

    def do_POST(self):
        path=urlparse(self.path).path
        data=self.body()

        # Tambah Area Parkir
        if path == "/api/admin/areas":
            with db() as c:
                u = self.user(c)

                if not u or u["role"] != "admin":
                    self.send_json({
                        "error": "Hanya admin yang dapat mengelola area."
                    }, 403)
                    return
                
                nama = str(data.get("nama", "")).strip()
                lokasi = str(data.get("lokasi", "")).strip()
                jenis = data.get("jenis")
                kapasitas = data.get("kapasitas")

                if not nama or not lokasi:
                    self.send_json({
                        "error": "Nama dan lokasi wajib diisi."
                    }, 400)
                    return
                
                if jenis not in ("motor", "mobil"):
                    self.send_json({
                        "error": "Jenis kendaraan tidak valid."
                    }, 400)
                    return
                
                if type(kapasitas) is not int or kapasitas <= 0:
                    self.send_json({
                        "error": "Kapasitas harus berupa angka positif."
                    }, 400)
                    return
                
                now = datetime.now().isoformat(timespec="seconds")

                c.execute("""
                    INSERT INTO parking_areas
                    (nama, lokasi, jenis, kapasitas,
                    terisi, aktif, diperbarui)
                    VALUES (?, ?, ?, ?, 0, 1, ?)
                """, (nama, lokasi, jenis, kapasitas, now))

                self.send_json({
                    "message": "Area parkir berhasil ditambahkan."
                })
                return 
        
        # EDIT AREA PARKIR 
        if path.startswith("/api/admin/areas/") and path.endswith("/update"): 
            with db() as c: 
                u = self.user(c) 
 
                if not u or u["role"] != "admin": 
                    self.send_json({ 
                        "error": "Akses ditolak." 
                    }, 403) 
                    return 
 
                try: 
                    area_id = int(path.split("/")[-2]) 
                    kapasitas = data.get("kapasitas") 
                    nama = str(data.get("nama", "")).strip() 
                    lokasi = str(data.get("lokasi", "")).strip() 
 
                    if not nama or not lokasi: 
                        raise ValueError("Nama dan lokasi wajib diisi.") 
 
                    if type(kapasitas) is not int or kapasitas <= 0: 
                        raise ValueError("Kapasitas harus angka positif.") 
 
                    area = c.execute(""" 
                        SELECT * FROM parking_areas 
                        WHERE id = ? AND aktif = 1 
                    """, (area_id,)).fetchone() 
 
                    if not area: 
                        raise ValueError("Area tidak ditemukan.") 
 
                    if kapasitas < area["terisi"]: 
                        raise ValueError( 
                            "Kapasitas tidak boleh kurang dari jumlah kendaraan terisi." 
                        ) 
 
                    now = datetime.now().isoformat(timespec="seconds") 
 
                    c.execute(""" 
                        UPDATE parking_areas 
                        SET nama=?, lokasi=?, kapasitas=?, diperbarui=? 
                        WHERE id=? 
                    """, (nama, lokasi, kapasitas, now, area_id)) 
 
                    self.send_json({ 
                        "message": "Area berhasil diperbarui." 
                    }) 
 
                except (ValueError, TypeError) as e: 
                    self.send_json({"error": str(e)}, 400) 
 
                return 
 
        # AKTIF / NONAKTIF AREA 
        if path.startswith("/api/admin/areas/") and path.endswith("/toggle"): 
            with db() as c: 
                u = self.user(c) 
 
                if not u or u["role"] != "admin": 
                    self.send_json({ 
                        "error": "Akses ditolak." 
                    }, 403) 
                    return 
 
                try: 
                    area_id = int(path.split("/")[-2]) 
 
                    area = c.execute(""" 
                        SELECT * FROM parking_areas 
                        WHERE id = ? 
                    """, (area_id,)).fetchone() 
 
                    if not area: 
                        raise ValueError("Area tidak ditemukan.") 
 
                    if area["aktif"] == 1 and area["terisi"] > 0: 
                        raise ValueError( 
                            "Area masih memiliki kendaraan. Kosongkan dahulu." 
                        ) 
 
                    c.execute(""" 
                        UPDATE parking_areas 
                        SET aktif = CASE WHEN aktif=1 THEN 0 ELSE 1 END 
                        WHERE id=? 
                    """, (area_id,)) 
 
                    self.send_json({ 
                        "message": "Status area berhasil diubah." 
                    }) 
 
                except (ValueError, TypeError) as e: 
                    self.send_json({"error": str(e)}, 400) 
 
                return

        if path == "/api/login":
            with db() as c:
                u=c.execute("SELECT * FROM users WHERE username=? AND aktif=1",(data.get("username",""),)).fetchone()
                if not u or not check_hash(data.get("password",""),u["password_hash"]):
                    self.send_json({"error":"Username atau password salah."},401); return
                t=secrets.token_urlsafe(32)
                c.execute("INSERT INTO sessions(token,user_id) VALUES(?,?)",(t,u["id"]))
                self.send_json({"message":"Login berhasil."},200,{"Set-Cookie":f"parkirkita={t}; HttpOnly; SameSite=Strict; Path=/"})
                return
        if path == "/api/logout":
            t=self.token()
            with db() as c:
                if t: c.execute("DELETE FROM sessions WHERE token=?",(t,))
            self.send_json({"message":"Logout berhasil."},200,{"Set-Cookie":"parkirkita=; HttpOnly; Path=/; Max-Age=0"}); return
        parts=path.strip("/").split("/")
        if len(parts)==4 and parts[:2]==["api","areas"] and parts[3] in ("masuk","keluar"):
            try: area_id=int(parts[2])
            except ValueError: self.send_json({"error":"ID area salah."},400); return
            amount=data.get("jumlah",1)
            if type(amount) is not int or not 1<=amount<=10:
                self.send_json({"error":"Jumlah harus 1 sampai 10."},400); return
            with db() as c:
                u=self.user(c)
                # if not u: self.send_json({"error":"Silakan login sebagai petugas."},401); return
                if not u:
                    self.send.json({
                        "error": "Silakan login dahulu."
                    }, 401)
                    return
                
                if u["role"] not in ("petugas", "admin"):
                    self.send_json({
                        "error": "Anda tidak memiliki hak akses."
                    }, 403)
                    return

                try:
                    c.execute("BEGIN IMMEDIATE")
                    a=c.execute("SELECT * FROM parking_areas WHERE id=? AND aktif=1",(area_id,)).fetchone()
                    if not a: raise ValueError("Area tidak ditemukan.")
                    before=a["terisi"]
                    after=before+amount if parts[3]=="masuk" else before-amount
                    if after>a["kapasitas"]: raise ValueError("Area penuh atau slot tidak mencukupi.")
                    if after<0: raise ValueError("Tidak ada kendaraan sebanyak itu untuk dikeluarkan.")
                    now=datetime.now().isoformat(timespec="seconds")
                    c.execute("UPDATE parking_areas SET terisi=?,diperbarui=? WHERE id=?",(after,now,area_id))
                    c.execute("INSERT INTO parking_events(area_id,user_id,jenis,jumlah,sebelum,sesudah,waktu) VALUES(?,?,?,?,?,?,?)",
                              (area_id,u["id"],parts[3],amount,before,after,now))
                    c.commit()
                    self.send_json({"message":f"Berhasil mencatat. Sisa slot: {a['kapasitas']-after}."})
                except ValueError as e:
                    c.rollback(); self.send_json({"error":str(e)},400)
                return
        self.send_json({"error":"Endpoint tidak ditemukan."},404)

    def log_message(self, fmt, *args):
        print(fmt % args)

if __name__ == "__main__":
    setup()
    print("ParkirKita aktif di http://localhost:3000")
    print("Petugas: petugas1 / parkir123 | Admin: admin / admin123")
    ThreadingHTTPServer(("127.0.0.1",3000),App).serve_forever()
