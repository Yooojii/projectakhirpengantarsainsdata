# tests/test_agregasi.py
import copy

import pandas as pd
import pytest

from inti.agregasi import agregasi_fitur, kalibrasi
from inti.data import muat_pertandingan
from inti.fitur import NAMA_FITUR, fitur_tim
from inti.pemain import bangkitkan_skuad

TGL = pd.Timestamp("2026-11-03")


@pytest.fixture(scope="module")
def df():
    return muat_pertandingan()


def siapkan(df, klub, kandang=True):
    asli = fitur_tim(df, klub, TGL, kandang)
    return asli, bangkitkan_skuad(df, klub, TGL), kalibrasi(df, klub, TGL)


@pytest.mark.parametrize("klub", ["Arsenal", "Hull", "Coventry"])
@pytest.mark.parametrize("kandang", [True, False])
def test_titik_nol_mereproduksi_fitur_nyata(df, klub, kandang):
    """Spec 7.1: penggeser di posisi awal harus menghasilkan fitur yang sama persis."""
    asli, s, k = siapkan(df, klub, kandang)
    hasil = agregasi_fitur(s, k, asli["poin_lima_laga"], kandang)
    assert list(hasil) == NAMA_FITUR
    for nama in NAMA_FITUR:
        assert hasil[nama] == pytest.approx(asli[nama], rel=1e-9)


def geser(skuad, atribut, delta):
    s = copy.deepcopy(skuad)
    for p in s:
        if atribut in p.atribut:
            p.atribut[atribut] = max(1, min(99, p.atribut[atribut] + delta))
    return s


@pytest.mark.parametrize("atribut,fitur,naik", [
    ("penyelesaian", "rasio_konversi", True),
    ("kreativitas", "rata_tembakan", True),
    ("kreativitas", "rata_sepak_pojok", True),
    ("rebutan", "rata_pelanggaran", True),
    ("ketenangan", "rata_kartu_kuning", False),
    ("antisipasi", "rata_gol_kebobolan", False),
    ("rebutan", "rata_gol_kebobolan", False),
    ("refleks", "rata_gol_kebobolan", False),
])
def test_arah_pergerakan_tiap_atribut(df, atribut, fitur, naik):
    asli, s, k = siapkan(df, "Arsenal")
    awal = agregasi_fitur(s, k, asli["poin_lima_laga"], True)[fitur]
    akhir = agregasi_fitur(geser(s, atribut, 10), k, asli["poin_lima_laga"], True)[fitur]
    assert akhir > awal if naik else akhir < awal


def test_gol_dicetak_adalah_turunan_bukan_dihitung_langsung(df):
    """Spec 7.4: gol dicetak = konversi x tembakan, supaya tidak dihitung dua kali."""
    asli, s, k = siapkan(df, "Arsenal")
    h = agregasi_fitur(geser(s, "penyelesaian", 15), k, asli["poin_lima_laga"], True)
    assert h["rata_gol_dicetak"] == pytest.approx(h["rasio_konversi"] * h["rata_tembakan"])
    assert h["rata_tembakan_tepat"] <= h["rata_tembakan"]


def test_satu_geseran_tidak_dihitung_dua_kali(df):
    """Menggeser penyelesaian menaikkan gol dicetak hanya lewat konversi."""
    asli, s, k = siapkan(df, "Arsenal")
    awal = agregasi_fitur(s, k, asli["poin_lima_laga"], True)
    akhir = agregasi_fitur(geser(s, "penyelesaian", 10), k, asli["poin_lima_laga"], True)
    assert akhir["rata_tembakan"] == awal["rata_tembakan"]
    assert akhir["rata_gol_dicetak"] / awal["rata_gol_dicetak"] == pytest.approx(
        akhir["rasio_konversi"] / awal["rasio_konversi"])


def test_bentuk_permainan_dibekukan(df):
    asli, s, k = siapkan(df, "Arsenal")
    h = agregasi_fitur(geser(s, "penyelesaian", 20), k, asli["poin_lima_laga"], True)
    assert h["poin_lima_laga"] == asli["poin_lima_laga"]


def test_cadangan_tidak_berpengaruh(df):
    asli, s, k = siapkan(df, "Arsenal")
    awal = agregasi_fitur(s, k, asli["poin_lima_laga"], True)
    diubah = copy.deepcopy(s)
    for p in diubah:
        if not p.inti:
            for a in p.atribut:
                p.atribut[a] = 99
    assert agregasi_fitur(diubah, k, asli["poin_lima_laga"], True) == awal
