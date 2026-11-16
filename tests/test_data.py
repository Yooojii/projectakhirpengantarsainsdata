import pandas as pd
from pathlib import Path
from inti.data import muat_pertandingan, cakupan_kolom, KELOMPOK_KOLOM, klub_musim

def test_muat_pertandingan_bentuk_dan_tipe():
    df = muat_pertandingan()
    assert df.shape == (9880, 56)
    assert pd.api.types.is_datetime64_any_dtype(df["tanggal"])
    assert df["tanggal"].is_monotonic_increasing

def test_kelompok_kolom_mencakup_semua_kolom_tanpa_tumpang_tindih():
    df = muat_pertandingan()
    semua = [k for kolom in KELOMPOK_KOLOM.values() for k in kolom]
    assert len(semua) == len(set(semua))
    assert set(semua) == set(df.columns)

def test_cakupan_xg_musim_berjalan_terpisah_dari_statistik_api():
    df = muat_pertandingan()
    cak = cakupan_kolom(df).set_index("kolom")
    assert cak.loc["xg_kandang", "terisi"] == 90
    assert cak.loc["xg_api_kandang", "terisi"] == 102
    assert cak.loc["xg_kandang", "kelompok"] == "statistik_lanjutan"
    assert cak.loc["tembakan_kandang", "persen"] == 100.0

def test_klub_musim_berjalan_ada_dua_puluh():
    klub = klub_musim(muat_pertandingan(), "2026/27")
    assert len(klub) == 20
    assert klub[0] == "Arsenal"
    assert "Coventry" in klub

def test_tembakan_tepat_tidak_melebihi_total_tembakan():
    df = muat_pertandingan()
    assert (df["tembakan_tepat_kandang"] <= df["tembakan_kandang"]).all()
    assert (df["tembakan_tepat_tandang"] <= df["tembakan_tandang"]).all()

def test_klem_tembakan_tepat_hanya_mengubah_lima_sel_yang_diputuskan():
    mentah = pd.read_csv(
        Path(__file__).resolve().parent.parent / "data" / "liga_inggris_gabungan.csv",
        parse_dates=["tanggal"],
    )
    df = muat_pertandingan()
    kunci = ["tanggal", "tim_kandang", "tim_tandang"]
    kolom = ["tembakan_tepat_kandang", "tembakan_tepat_tandang"]
    gabung = mentah[kunci + kolom].merge(
        df[kunci + kolom], on=kunci, suffixes=("_mentah", "_bersih"), validate="one_to_one"
    )
    assert len(gabung) == 9880
    beda = {}
    for k in kolom:
        b = gabung[gabung[f"{k}_mentah"] != gabung[f"{k}_bersih"]]
        for _, r in b.iterrows():
            beda[(r["tanggal"].strftime("%Y-%m-%d"), r["tim_kandang"], k)] = (
                r[f"{k}_mentah"], r[f"{k}_bersih"])
    assert beda == {
        ("2000-10-14", "Coventry", "tembakan_tepat_kandang"): (5.0, 0.0),
        ("2000-10-14", "Coventry", "tembakan_tepat_tandang"): (5.0, 4.0),
        ("2001-04-13", "Bradford", "tembakan_tepat_kandang"): (8.0, 4.0),
        ("2001-04-13", "Bradford", "tembakan_tepat_tandang"): (8.0, 3.0),
        ("2021-08-15", "Newcastle", "tembakan_tepat_tandang"): (9.0, 8.0),
    }
