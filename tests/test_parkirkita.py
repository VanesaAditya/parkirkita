import unittest 
import sqlite3 
 
def hitung_sisa(kapasitas, terisi): 
    if kapasitas <= 0: 
        raise ValueError("Kapasitas harus positif") 
 
    if terisi < 0 or terisi > kapasitas: 
        raise ValueError("Jumlah kendaraan tidak valid") 
 
    return kapasitas - terisi 
 
 
def kendaraan_masuk(kapasitas, terisi, jumlah=1): 
    if type(jumlah) is not int or not 1 <= jumlah <= 10: 
        raise ValueError("Jumlah tidak valid") 
 
    if terisi + jumlah > kapasitas: 
        raise ValueError("Parkir penuh") 
 
    return terisi + jumlah 
 
 
def kendaraan_keluar(terisi, jumlah=1): 
    if type(jumlah) is not int or not 1 <= jumlah <= 10: 
        raise ValueError("Jumlah tidak valid") 
 
    if terisi - jumlah < 0: 
        raise ValueError("Kendaraan tidak mencukupi") 
 
    return terisi - jumlah 
 
 
class TestParkirKita(unittest.TestCase): 
 
    def test_sisa_slot(self): 
        self.assertEqual(hitung_sisa(100, 40), 60) 
 
    def test_area_penuh(self): 
        self.assertEqual(kendaraan_masuk(10, 9), 10) 
 
    def test_masuk_melebihi_kapasitas(self): 
        with self.assertRaises(ValueError): 
            kendaraan_masuk(10, 10) 
 
    def test_kendaraan_keluar(self): 
        self.assertEqual(kendaraan_keluar(10, 2), 8) 
 
    def test_keluar_melebihi_terisi(self): 
        with self.assertRaises(ValueError): 
            kendaraan_keluar(0) 
 
    def test_jumlah_tidak_valid(self): 
        with self.assertRaises(ValueError): 
            kendaraan_masuk(10, 2, 0) 
 
    def test_kapasitas_tidak_valid(self): 
        with self.assertRaises(ValueError): 
            hitung_sisa(0, 0) 
 
    def test_sqlite_connection(self): 
        conn = sqlite3.connect(":memory:") 
 
        conn.execute(""" 
            CREATE TABLE area ( 
                id INTEGER PRIMARY KEY, 
                nama TEXT 
            ) 
        """) 
 
        conn.execute(""" 
            INSERT INTO area (nama) 
            VALUES ('Motor Utara') 
        """) 
 
        result = conn.execute( 
            "SELECT nama FROM area" 
        ).fetchone() 
 
        self.assertEqual(result[0], "Motor Utara") 
 
        conn.close() 
 
 
if __name__ == "__main__": 
    unittest.main(verbosity=2) 