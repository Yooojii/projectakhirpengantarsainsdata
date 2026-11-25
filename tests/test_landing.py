import pandas as pd

from halaman.landing import _dataset, _insight, _modelling, _model, _overview, _praproses, fakta
from inti.data import muat_pertandingan


def _df():
    return muat_pertandingan()


def test_fakta_dihitung_dari_data():
    df = _df()
    f = fakta(df)
    assert f["laga"] == len(df)
    assert f["musim"] == df["musim"].nunique()
    assert f["klub"] == len(set(df["tim_kandang"]) | set(df["tim_tandang"]))
    assert abs(f["menang_kandang"] - 100 * (df["hasil"] == "H").mean()) < 1e-9
    assert 0 < f["konversi"] < 100 and 50 < f["unggul_jeda_menang"] < 100
    assert f["musim_penuh_awal"] < f["musim_penuh_akhir"]


def test_bagian_landing_memuat_isi_yang_diminta():
    df = _df()
    f = fakta(df)
    perbandingan, metrik = _model()
    html = _overview() + _dataset(f) + _praproses(f) + _modelling(perbandingan, metrik) + _insight(f)
    for teks in ["football-data.co.uk", "Pengecekan struktur data", "Kualitas data",
                 "Konversi tipe data", "Feature engineering", "Regresi Poisson", "Dixon-Coles"]:
        assert teks in html, teks
    # tombol tab mengarah ke tautan yang dibaca app.py
    for tujuan in ["?buka=overview", "?buka=analisis", "?buka=history"]:
        assert tujuan in html


def test_judul_bagian_dan_satu_tombol_masuk():
    from halaman.landing import _hero, _nav
    df = _df()
    f = fakta(df)
    perbandingan, metrik = _model()
    html = _overview() + _dataset(f) + _praproses(f) + _modelling(perbandingan, metrik) + _insight(f)
    for judul in ["Explore Football Through Data.", "Behind the Numbers", "Data Pipeline", "Key Insight"]:
        assert judul in html, judul
    assert "Sumber pelengkap" not in html and "E0.csv" not in html
    # tombol "Buka Dashboard" hanya di navigasi kanan atas
    halaman = _nav("") + _hero(f, "") + html
    assert halaman.count("Buka Dashboard") == 1
    # tiap kartu tab punya foto
    assert html.count('<span class="lp-foto"><img src="data:image/webp;base64,') == 4
    assert "?buka=gaya" in html and "Team Styles" in html


def test_tautan_landing_cocok_dengan_pintu_app():
    import app
    assert set(app.PINTU) == {"overview", "analisis", "history", "gaya"}
    assert set(app.PINTU.values()) == set(app.HALAMAN)


def test_kaki_landing_memuat_kelompok_dan_tidak_tersembunyi():
    from gaya.komponen import ANGGOTA
    from halaman.landing import _kaki
    h = _kaki()
    # <footer> disembunyikan tema (kaki bawaan Streamlit), jadi kaki landing harus div
    assert "<footer" not in h and 'class="lp-kaki"' in h
    assert "&copy; " in h and "Kelompok 8" in h
    for nama, nim in ANGGOTA:
        assert nim in h
