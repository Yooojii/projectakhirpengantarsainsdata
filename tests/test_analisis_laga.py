import pandas as pd
import pytest

from gaya.komponen import angka_hitung
from halaman.analisis_laga import (
    STAT,
    bentuk_sebelum,
    catatan_laga,
    panel_laga,
    perkiraan_statistik,
)
from inti.data import muat_pertandingan


@pytest.fixture(scope="module")
def df():
    return muat_pertandingan()


def test_angka_hitung_memecah_bulat_dan_pecahan_dengan_nilai_terbaca():
    h = angka_hitung(2.72, 2)
    assert '<span class="sr">2,72</span>' in h
    assert "--akhir:2" in h and "--akhir:72" in h
    assert 'class="hitung dua"' in h  # pecahan dua digit memakai nol di depan


def test_angka_hitung_bulat_tanpa_koma_dan_tunda_opsional():
    h = angka_hitung(3, tunda_ms=200)
    assert '<span class="sr">3</span>' in h and "--tunda:200ms" in h and "," not in h


def test_bentuk_sebelum_tidak_memakai_laga_pada_atau_setelah_tanggal(df):
    laga = df[df["tim_kandang"] == "Arsenal"].iloc[-1]
    hasil = bentuk_sebelum(df, "Arsenal", laga["tanggal"])
    assert len(hasil) == 5 and set(hasil) <= {"M", "S", "K"}
    sebelum = df[((df.tim_kandang == "Arsenal") | (df.tim_tandang == "Arsenal"))
                 & (df.tanggal < laga["tanggal"])]
    assert len(sebelum) >= 5


def test_perkiraan_statistik_lengkap_dan_tidak_negatif(df):
    tanggal = df["tanggal"].max() + pd.Timedelta(days=1)
    baris = perkiraan_statistik(df, "Arsenal", "Chelsea", tanggal)
    assert [b[0] for b in baris] == [s[0] for s in STAT]
    assert all(k >= 0 and t >= 0 for _, k, t, _ in baris)


def test_skor_besar_menaikkan_tembakan_tuan_rumah(df):
    tanggal = df["tanggal"].max() + pd.Timedelta(days=1)
    menang_besar = perkiraan_statistik(df, "Arsenal", "Chelsea", tanggal, (3, 0))
    kalah_besar = perkiraan_statistik(df, "Arsenal", "Chelsea", tanggal, (0, 3))
    assert menang_besar[0][1] > kalah_besar[0][1]  # tembakan tuan rumah
    assert menang_besar[0][2] < kalah_besar[0][2]  # tembakan tamu


def test_skor_di_atas_batas_digabung_dan_faktor_netral_tanpa_data(df):
    from halaman.analisis_laga import faktor_skor
    assert faktor_skor(df, (7, 1)) == faktor_skor(df, (4, 1))
    assert all(0.2 < f < 5 for pasang in faktor_skor(df, (2, 2)).values() for f in pasang)


def test_catatan_laga_paling_banyak_tiga_dan_menyebut_klub(df):
    r = df.iloc[-1]
    catatan = catatan_laga(r)
    assert 1 <= len(catatan) <= 3
    assert any(r["tim_kandang"] in c or r["tim_tandang"] in c for c in catatan)


def test_panel_laga_memuat_skor_dan_statistik(df):
    indeks = df.index[-1]
    html = panel_laga(df, indeks)
    r = df.loc[indeks]
    assert f'<span class="sr">{int(r["gol_kandang"])}</span>' in html
    assert "Total tembakan" in html and "Statistik pertandingan" in html
