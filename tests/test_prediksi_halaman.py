import copy
import pandas as pd
import pytest

from inti.data import muat_pertandingan
from halaman.prediksi_simulasi import hitung_prediksi, selisih, siapkan_sesi

TGL = pd.Timestamp("2026-11-07")


@pytest.fixture(scope="module")
def sesi():
    return siapkan_sesi(muat_pertandingan(), "Arsenal", "Tottenham", TGL)


def test_tanpa_perubahan_tidak_ada_selisih(sesi):
    h = hitung_prediksi(sesi)
    assert selisih(h, hitung_prediksi(sesi)) == {}


def test_menaikkan_penyelesaian_menaikkan_peluang_menang(sesi):
    awal = hitung_prediksi(sesi)
    s = copy.deepcopy(sesi)
    for p in s["skuad_kandang"]:
        if p.inti and p.posisi == "DEP":
            p.atribut["penyelesaian"] = min(99, p.atribut["penyelesaian"] + 15)
    akhir = hitung_prediksi(s)
    assert akhir["p_menang_kandang"] > awal["p_menang_kandang"]
    assert akhir["gol_harapan_kandang"] > awal["gol_harapan_kandang"]


def test_skor_besar_konsisten_dengan_peluang_di_bawahnya(sesi):
    h = hitung_prediksi(sesi)
    k, t = h["skor"]
    peluang = {"H": h["p_menang_kandang"], "D": h["p_seri"], "A": h["p_menang_tandang"]}
    terkuat = max(peluang, key=peluang.get)
    assert (k > t) == (terkuat == "H")
    assert (k == t) == (terkuat == "D")
    assert (k < t) == (terkuat == "A")
