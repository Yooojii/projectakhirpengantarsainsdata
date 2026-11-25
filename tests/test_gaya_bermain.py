import re

from gaya.komponen import _kontras
from halaman.gaya_bermain import BATAS, PERINGKAT, WARNA, _peringkat, _posisi, kategori, muat, peta


def test_warna_kategori_cukup_kontras_untuk_teks():
    for nama, warna in WARNA.items():
        assert _kontras(warna, "#FFFFFF") >= 4.5, nama


def test_posisi_peta_dijepit_di_dalam_bidang():
    assert _posisi(0) == 50
    assert _posisi(BATAS * 3) == 96 and _posisi(-BATAS * 3) == 4


def test_semua_musim_bisa_ditampilkan():
    df = muat()
    for musim, sub in df.groupby("musim"):
        h = peta(sub, musim)
        assert h.count('class="peta-titik') == len(sub), musim
        for kiri, bawah in re.findall(r"left:([\d.]+)%;bottom:([\d.]+)%", h):
            assert 4 <= float(kiri) <= 96 and 4 <= float(bawah) <= 96
        k = kategori(sub, musim)
        # setiap klub muncul tepat satu kali di daftar kategori
        assert k.count('class="kat-logo"') == len(sub), musim
        for kartu in PERINGKAT.values():
            for judul, kolom, naik, fmt, satuan in kartu:
                html = _peringkat(sub, judul, kolom, naik, fmt, satuan, 0)
                if sub[kolom].notna().any():
                    assert html.count("<li ") == min(5, sub[kolom].notna().sum())
                else:
                    assert html == ""  # mis. penguasaan bola sebelum datanya tersedia


def test_peringkat_kecil_lebih_baik_tetap_menaruh_terbaik_di_atas():
    df = muat()
    sub = df[df.musim == df.musim.max()]
    html = _peringkat(sub, "Paling jarang kebobolan", "gol_kebobolan", True, "{:.2f}", "gol per laga", 0)
    terbaik = sub.sort_values("gol_kebobolan").iloc[0].klub
    assert html.index(terbaik) < html.index('<li style="--i:1"')
    lebar = [float(x) for x in re.findall(r"width:([\d.]+)%", html)]
    assert lebar[0] == max(lebar)  # batang terpanjang milik peringkat pertama
