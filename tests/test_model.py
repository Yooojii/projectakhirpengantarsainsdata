import pandas as pd
import pytest

from inti.fitur import NAMA_FITUR
from inti.model import (distribusi_skor, muat_evaluasi, muat_model, pembanding,
                        prediksi, skor_utama)


def test_tanpa_berkas_model_tetap_memprediksi():
    """Review focus 3: berkas model rekan kelompok kemungkinan belum ada."""
    assert muat_model("model/tidak_ada.joblib") is None
    h = prediksi({"rata_gol_dicetak": 1.8, "rata_gol_kebobolan": 1.0, "penanda_kandang": 1.0},
                 {"rata_gol_dicetak": 1.2, "rata_gol_kebobolan": 1.4, "penanda_kandang": 0.0})
    assert h["gol_harapan_kandang"] > h["gol_harapan_tandang"]
    assert h["p_menang_kandang"] > h["p_menang_tandang"]
    assert sum(h[k] for k in ("p_menang_kandang", "p_seri", "p_menang_tandang")) == pytest.approx(1.0)


def test_fallback_rata_rata_liga_mendekati_data_nyata():
    """Masukan rata-rata liga harus memberi ~1.53 / ~1.18 gol dan kandang ~46%."""
    rata = {"rata_gol_dicetak": 1.355, "rata_gol_kebobolan": 1.355}
    h = prediksi({**rata, "penanda_kandang": 1.0}, {**rata, "penanda_kandang": 0.0})
    assert h["gol_harapan_kandang"] == pytest.approx(1.53, abs=0.05)
    assert h["gol_harapan_tandang"] == pytest.approx(1.18, abs=0.05)
    assert 0.40 < h["p_menang_kandang"] < 0.52


def test_distribusi_skor_berjumlah_satu():
    d = distribusi_skor(1.6, 1.1)
    assert sum(d.values()) == pytest.approx(1.0, abs=1e-3)
    assert all(v >= 0 for v in d.values())


def test_gol_harapan_nol_tidak_menghasilkan_nan():
    """Review focus 5: atribut digeser ke nilai terendah bisa menghasilkan nol."""
    d = distribusi_skor(0.0, 0.0)
    assert sum(d.values()) == pytest.approx(1.0, abs=1e-3)
    assert d[(0, 0)] == pytest.approx(1.0, abs=1e-3)
    assert not any(v != v for v in d.values())


def test_skor_utama_tidak_pernah_membantah_hasil_terkuat():
    """Spec 6.6: papan tidak boleh menulis 2-1 di atas 'kalah 46%'."""
    d = distribusi_skor(1.2, 1.9)   # Poisson condong ke tamu
    k, t = skor_utama(d, "H")
    assert k > t
    k, t = skor_utama(d, "D")
    assert k == t
    k, t = skor_utama(d, "A")
    assert k < t


class _ModelPalsu:
    classes_ = ["A", "D", "H"]  # urutan alfabet, seperti sklearn

    def __init__(self):
        self.diterima = None

    def predict_proba(self, x):
        self.diterima = x
        return [[0.2, 0.3, 0.5]]


def _lengkap(nilai):
    return {n: nilai + i for i, n in enumerate(NAMA_FITUR)}


def test_jalur_model_memetakan_kelas_dan_urutan_fitur():
    m = _ModelPalsu()
    h = prediksi(_lengkap(1.0), _lengkap(2.0), model=m)
    assert h["p_menang_kandang"] == pytest.approx(0.5)
    assert h["p_seri"] == pytest.approx(0.3)
    assert h["p_menang_tandang"] == pytest.approx(0.2)
    assert list(m.diterima[0]) == [_lengkap(1.0)[n] for n in NAMA_FITUR]


def test_jalur_model_menolak_fitur_tidak_lengkap():
    with pytest.raises(ValueError, match="rata_tembakan"):
        prediksi({"rata_gol_dicetak": 1.0}, _lengkap(1.0), model=_ModelPalsu())


def test_muat_evaluasi_none_bila_tidak_ada(tmp_path):
    assert muat_evaluasi(str(tmp_path / "tidak_ada.json")) is None


def test_muat_evaluasi_membaca_json(tmp_path):
    p = tmp_path / "metrik.json"
    p.write_text('{"akurasi": 0.5}')
    assert muat_evaluasi(str(p)) == {"akurasi": 0.5}


def test_pembanding_dihitung_pada_baris_yang_sama():
    uji = pd.DataFrame({
        "hasil": ["H", "A", "D", "H"],
        "prediksi": ["H", "H", "D", "H"],
        # Baris 4 dipilih agar tebakan bandar (A, salah) berbeda dari akurasi model.
        "odds_kandang": [1.5, 4.0, 2.0, 3.0],
        "odds_seri": [4.0, 3.5, 3.0, 3.6],
        "odds_tandang": [6.0, 1.9, 3.5, 1.8],
    })
    p = pembanding(uji)
    assert p["model"] == pytest.approx(0.75)
    assert p["selalu_kandang"] == pytest.approx(0.5)
    # odds terendah: H, A, H, A -> benar, benar, salah, salah
    assert p["ikut_odds"] == pytest.approx(0.5)


def test_jalur_model_menolak_label_bukan_hnd():
    class Angka(_ModelPalsu):
        classes_ = [0, 1, 2]
    with pytest.raises(ValueError, match=r"\[0, 1, 2\].*\"H\""):
        prediksi(_lengkap(1.0), _lengkap(2.0), model=Angka())


def test_pembanding_menolak_odds_kosong():
    uji = pd.DataFrame({
        "hasil": ["H", "A"], "prediksi": ["H", "A"],
        "odds_kandang": [1.5, None], "odds_seri": [4.0, 3.0],
        "odds_tandang": [6.0, 2.0],
    })
    with pytest.raises(ValueError, match=r"1 baris.*2019/20"):
        pembanding(uji)
