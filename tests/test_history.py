import pytest
from inti.data import muat_pertandingan
from halaman.history import rekor_pertemuan, keadaan_riwayat, klasemen, bentuk_permainan


@pytest.fixture(scope="module")
def df():
    return muat_pertandingan()


def test_keadaan_kosong_untuk_pasangan_yang_belum_pernah_bertemu(df):
    """Review focus 2: enam pasangan punya nol pertemuan."""
    r = rekor_pertemuan(df, "Hull", "Leeds")
    assert r["total"] == 0
    assert keadaan_riwayat(r["total"]) == "kosong"


def test_keadaan_tipis_di_bawah_empat_pertemuan():
    assert keadaan_riwayat(0) == "kosong"
    assert keadaan_riwayat(3) == "tipis"
    assert keadaan_riwayat(4) == "penuh"


def test_rekor_simetris(df):
    a = rekor_pertemuan(df, "Arsenal", "Tottenham")
    b = rekor_pertemuan(df, "Tottenham", "Arsenal")
    assert a["menang"] == b["kalah"] and a["seri"] == b["seri"] and a["total"] == b["total"]


def test_klasemen_dua_puluh_klub_terurut_poin(df):
    k = klasemen(df, "2026/27")
    assert len(k) == 20
    assert k.poin.is_monotonic_decreasing
    assert k.main.unique().tolist() == [11]


def test_bentuk_permainan_sepuluh_hasil(df):
    b = bentuk_permainan(df, "Arsenal")
    assert len(b) == 10
    assert set(b) <= {"M", "S", "K"}
