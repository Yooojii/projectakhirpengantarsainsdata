import math

import pandas as pd
from inti.data import klub_musim, muat_pertandingan
from inti.jadwal import jadwal_sisa

def test_melengkapi_setengah_kompetisi_ganda():
    df = muat_pertandingan()
    sisa = jadwal_sisa(df)
    dimainkan = df[df.musim == "2026/27"]
    assert len(sisa) == 380 - len(dimainkan)
    gabung = set(zip(dimainkan.tim_kandang, dimainkan.tim_tandang)) | set(zip(sisa.tim_kandang, sisa.tim_tandang))
    assert len(gabung) == 380

def test_tidak_mengulang_laga_yang_sudah_dimainkan():
    df = muat_pertandingan()
    dimainkan = set(zip(df[df.musim == "2026/27"].tim_kandang, df[df.musim == "2026/27"].tim_tandang))
    assert not dimainkan & set(zip(*[jadwal_sisa(df)[c] for c in ("tim_kandang", "tim_tandang")]))

def test_semua_tanggal_hari_sabtu_mulai_tujuh_november():
    sisa = jadwal_sisa(muat_pertandingan())
    assert sisa.tanggal.min() == pd.Timestamp("2026-11-07")
    assert set(sisa.tanggal.dt.dayofweek) == {5}

def test_tidak_ada_klub_bermain_dua_kali_pada_tanggal_yang_sama():
    sisa = jadwal_sisa(muat_pertandingan())
    for _, hari in sisa.groupby("tanggal"):
        klub = list(hari.tim_kandang) + list(hari.tim_tandang)
        assert len(klub) == len(set(klub))

def test_jadwal_padat_tanpa_ekor_panjang():
    df = muat_pertandingan()
    sisa = jadwal_sisa(df)
    n_klub = len(klub_musim(df, "2026/27"))
    minimum = math.ceil(len(sisa) / (n_klub // 2))
    assert minimum <= sisa.tanggal.nunique() <= minimum + 3

def test_deterministik():
    df = muat_pertandingan()
    pd.testing.assert_frame_equal(jadwal_sisa(df), jadwal_sisa(df))

def test_mulai_setelah_laga_terakhir_yang_dimainkan():
    df = muat_pertandingan()
    maju = df.copy()
    maju.loc[maju.index[-1], "tanggal"] = pd.Timestamp("2026-12-01")  # Selasa
    sisa = jadwal_sisa(maju)
    assert sisa.tanggal.min() == pd.Timestamp("2026-12-05")

def test_tanpa_sisa_tetap_bertipe_tanggal():
    sisa = jadwal_sisa(muat_pertandingan(), musim="1900/01")
    assert len(sisa) == 0
    assert pd.api.types.is_datetime64_any_dtype(sisa.tanggal)
    assert list(sisa.columns) == ["tanggal", "tim_kandang", "tim_tandang"]
