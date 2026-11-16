import pandas as pd
from inti.data import muat_pertandingan
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
    # 290 laga, maksimal 10 per tanggal -> minimal 29 tanggal; jangan jauh lebih panjang
    sisa = jadwal_sisa(muat_pertandingan())
    assert sisa.tanggal.nunique() <= 32
    assert sisa.groupby("tanggal").size().min() >= 5
