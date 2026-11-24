import unicodedata

import pandas as pd

from app import HALAMAN
from inti.sesi import AKAR, JALUR_DATA, keterangan_cakupan, skuad_klub


def test_tiga_halaman_dengan_urutan_tetap():
    # Match Prediction dan Analisis Liga digabung menjadi Match Analysis
    assert list(HALAMAN) == ["Overview", "Match Analysis", "History"]


def test_nama_halaman_tanpa_ikon_dan_tanpa_huruf_kapital_seluruhnya():
    for nama in HALAMAN:
        assert nama != nama.upper()
        for ch in nama:
            assert unicodedata.category(ch) != "So", f"ikon atau emoji di {nama!r}"


def test_setiap_halaman_dapat_dipanggil():
    assert all(callable(f) for f in HALAMAN.values())


def test_jalur_proyek_absolut_dan_data_ada():
    assert AKAR.is_absolute()
    assert JALUR_DATA.is_file()


def test_keterangan_cakupan_memuat_rentang_dan_tanggal_terakhir():
    df = pd.DataFrame({"musim": ["2000/01", "2026/27"],
                       "tanggal": pd.to_datetime(["2000-08-19", "2026-11-02"])})
    assert keterangan_cakupan(df) == "2000/01 sampai 2026/27, laga terakhir 2 November 2026"


def test_skuad_dibangkitkan_sekali_dan_objeknya_sama():
    from inti.data import muat_pertandingan
    df = muat_pertandingan(str(JALUR_DATA))
    keadaan = {}
    pertama = skuad_klub(keadaan, df, "Arsenal")
    pertama[0].nama = "disunting"
    kedua = skuad_klub(keadaan, df, "Arsenal")
    assert kedua is pertama and kedua[0].nama == "disunting"
