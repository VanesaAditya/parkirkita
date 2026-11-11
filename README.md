# ParkirKita - Aplikasi Sederhana

## Cara menjalankan
1. Ekstrak ZIP.
2. Pastikan Python 3.9+ sudah terpasang.
3. Buka CMD/Terminal di folder ini.
4. Jalankan `python app.py`.
5. Buka browser: http://localhost:3000

Tidak perlu menginstal library tambahan. Database `parkirkita.db` dibuat otomatis saat pertama kali dijalankan.

## Akun demo
- Petugas: `petugas1` / `parkir123`
- Admin: `admin` / `admin123`

## Fitur
- Melihat daftar area parkir tanpa login.
- Filter kendaraan motor dan mobil.
- Ringkasan slot kosong.
- Status Tersedia, Hampir penuh, dan Penuh.
- Login petugas/admin.
- Mencatat kendaraan masuk dan keluar.
- Validasi kapasitas dan jumlah kendaraan.
- Riwayat 20 pencatatan terakhir.
- Pembaruan tampilan otomatis setiap 5 detik.

## Mengubah area parkir
Edit daftar `AREAS` di bagian atas `app.py`. Jika database sudah pernah dibuat, hentikan aplikasi lalu hapus `parkirkita.db` agar data area awal dibuat ulang. Penghapusan database akan menghapus seluruh data demo yang tersimpan.

## Catatan
Ini versi sederhana untuk demo lokal, belum untuk dipasang langsung ke server publik. Fitur grafik, laporan, pengelolaan area, dan notifikasi belum dibuat.


# ParkirKita 
Sistem Monitoring Ketersediaan Slot Parkir Cerdas Kampus. 
## Teknologi - Python - HTML - CSS - JavaScript - SQLite 
## Fitur Pengunjung - Melihat ketersediaan slot parkir. - Filter motor dan mobil. - Melihat status area parkir. - Melihat jumlah slot kosong. 
## Fitur Petugas - Login petugas. - Mencatat kendaraan masuk. - Mencatat kendaraan keluar. - Melihat riwayat pencatatan. - Mencari riwayat kendaraan. 
## Fitur Admin - Login admin. - Melihat statistik parkir. - Melihat grafik kepadatan. - Menambah area parkir. - Mengedit area parkir. - Mengaktifkan dan menonaktifkan area. 
## Menjalankan Aplikasi 
1. Pastikan Python 3.9 atau lebih baru sudah terpasang. 
2. Buka folder aplikasi. 
3. Jalankan: 
python app.py 
4. Buka browser: 
http://localhost:3000 
## Akun Demo 
Petugas: - Username: petugas1 - Password: parkir123 
Admin: - Username: admin - Password: admin123 
## Pengujian 
Jalankan: 
python -m unittest discover -s tests -v 
## Catatan 
Aplikasi ini merupakan simulasi monitoring parkir berbasis 
pencatatan petugas dan pembaruan data berkala. 
Aplikasi belum menggunakan sensor parkir fisik.