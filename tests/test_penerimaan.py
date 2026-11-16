import copy
import pandas as pd
import pytest

from inti.data import muat_pertandingan
from halaman.prediksi_simulasi import hitung_prediksi, siapkan_sesi

TGL = pd.Timestamp("2026-11-07")


@pytest.fixture(scope="module")
def sesi():
    return siapkan_sesi(muat_pertandingan(), "Arsenal", "Tottenham", TGL)


def setel(sesi, atribut, nilai):
    s = copy.deepcopy(sesi)
    for p in s["skuad_kandang"]:
        if p.inti and atribut in p.atribut:
            p.atribut[atribut] = nilai
    return s


@pytest.mark.parametrize("atribut,kunci,naik", [
    ("penyelesaian", "gol_harapan_kandang", True),
    ("kreativitas", "gol_harapan_kandang", True),
    ("antisipasi", "gol_harapan_tandang", False),
    ("rebutan", "gol_harapan_tandang", False),
])
def test_uji_arah(sesi, atribut, kunci, naik):
    """Spec 7.4 uji 1: naikkan 10 poin, pastikan bergerak ke arah yang benar."""
    awal = hitung_prediksi(sesi)[kunci]
    s = copy.deepcopy(sesi)
    for p in s["skuad_kandang"]:
        if p.inti and atribut in p.atribut:
            p.atribut[atribut] = min(99, p.atribut[atribut] + 10)
    akhir = hitung_prediksi(s)[kunci]
    assert akhir > awal if naik else akhir < awal


@pytest.mark.parametrize("atribut,kunci", [
    ("penyelesaian", "gol_harapan_kandang"),
    ("kreativitas", "gol_harapan_kandang"),
])
def test_uji_kepekaan_minimal_setengah_gol(sesi, atribut, kunci):
    """Spec 7.4 uji 2: sapuan penuh harus menggeser gol harapan minimal 0,5."""
    rendah = hitung_prediksi(setel(sesi, atribut, 20))[kunci]
    tinggi = hitung_prediksi(setel(sesi, atribut, 95))[kunci]
    assert tinggi - rendah >= 0.5, (
        f"{atribut} hanya menggeser {tinggi - rendah:.3f} gol. "
        "Bobot bentuk permainan dalam model kemungkinan terlalu dominan — "
        "bereskan di sisi model, jangan perbesar pengali di sisi dashboard."
    )
