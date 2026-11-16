from inti.data import muat_pertandingan, klub_musim
from inti.klub import WARNA, warna_klub, singkatan


def test_semua_klub_musim_berjalan_punya_warna():
    for nama in klub_musim(muat_pertandingan(), "2026/27"):
        assert nama in WARNA
        warna = warna_klub(nama)
        assert warna.startswith("#") and len(warna) == 7
        assert warna != "#6B7A72"


def test_warna_mencakup_klub_semua_musim_persis():
    df = muat_pertandingan()
    klub = set(df.tim_kandang) | set(df.tim_tandang)
    assert klub == set(WARNA)


def test_klub_tak_dikenal_dapat_warna_netral():
    assert warna_klub("Klub Antah Berantah") == "#6B7A72"


def test_singkatan_tiga_huruf():
    assert singkatan("Man United") == "MUN"
    assert singkatan("Nott'm Forest") == "NFO"


def test_singkatan_unik_untuk_semua_klub():
    kode = [singkatan(nama) for nama in WARNA]
    assert len(kode) == len(set(kode))
    assert all(len(k) == 3 for k in kode)
