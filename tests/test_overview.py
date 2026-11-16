from inti.data import muat_pertandingan
from halaman.overview import tabel_kelengkapan


def test_lima_kelompok_dengan_alasan_tertulis():
    t = tabel_kelengkapan(muat_pertandingan())
    assert len(t) == 5
    assert set(t.kelompok) >= {"statistik_dasar", "odds", "statistik_lanjutan"}
    assert t.alasan.str.len().min() > 10


def test_statistik_lanjutan_dinyatakan_tidak_dipakai_model():
    t = tabel_kelengkapan(muat_pertandingan()).set_index("kelompok")
    assert t.loc["statistik_lanjutan", "dipakai_model"] is False
    assert t.loc["odds", "dipakai_model"] is False
    assert t.loc["statistik_dasar", "dipakai_model"] is True


def test_cakupan_statistik_dasar_seratus_persen():
    t = tabel_kelengkapan(muat_pertandingan()).set_index("kelompok")
    assert t.loc["statistik_dasar", "cakupan"] == 100.0
