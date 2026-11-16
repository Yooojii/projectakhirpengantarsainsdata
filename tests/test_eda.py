import pytest
from inti.data import muat_pertandingan
from halaman.eda_liga import cukup_lengkap, tren_per_musim, BAGIAN


def test_bagian_statistik_lanjutan_tidur_sekarang():
    """Spec 7.7: tidur sampai cakupan lewat 60%."""
    df = muat_pertandingan()
    assert cukup_lengkap(df, "penguasaan_bola_kandang") is False
    assert cukup_lengkap(df, "tembakan_kandang") is True


def test_bagian_bangun_sendiri_saat_cakupan_cukup():
    """Review focus 4: CSV ditukar dengan hasil scraping lebih lengkap."""
    df = muat_pertandingan()
    df.loc[: int(len(df) * 0.7), "penguasaan_bola_kandang"] = 50.0
    assert cukup_lengkap(df, "penguasaan_bola_kandang") is True


def test_delapan_bagian_dua_di_antaranya_bersyarat():
    assert len(BAGIAN) == 8
    assert sum(1 for b in BAGIAN if b["kolom_syarat"]) == 2


def test_tren_memakai_ukuran_per_laga_bukan_total():
    """Spec 6.4: 2003/04 dan 2004/05 hanya 335 laga."""
    t = tren_per_musim(muat_pertandingan(), "poin").set_index("musim")
    assert t.loc["2003/04", "jumlah_laga"] == 335
    assert 0.5 < t.loc["2003/04", "nilai"] < 3.0
    assert abs(t.loc["2003/04", "nilai"] - t.loc["2002/03", "nilai"]) < 0.5


def test_musim_tidak_utuh_ditandai():
    t = tren_per_musim(muat_pertandingan(), "poin")
    tidak_utuh = set(t[t.jumlah_laga < 380].musim)
    assert tidak_utuh == {"2003/04", "2004/05", "2026/27"}
