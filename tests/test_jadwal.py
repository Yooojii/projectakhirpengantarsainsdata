import math
import os
import subprocess
import sys

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
    assert sisa.tanggal.min() == pd.Timestamp("2026-11-28")
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

_SKRIP = """
import hashlib
from inti.data import muat_pertandingan
from inti.jadwal import jadwal_sisa
s = jadwal_sisa(muat_pertandingan())
b = [f"{t.date()}|{h}|{a}" for t, h, a in zip(s.tanggal, s.tim_kandang, s.tim_tandang)]
print(b[:3], b[-3:])
print(hashlib.sha256(chr(10).join(b).encode()).hexdigest())
"""


def test_deterministik_lintas_proses():
    # Hash string Python diacak per proses; dalam satu proses dua panggilan
    # selalu sama, jadi hanya proses terpisah yang bisa menangkap urutan set.
    def jalankan(seed):
        env = {**os.environ, "PYTHONHASHSEED": seed}
        hasil = subprocess.run(
            [sys.executable, "-c", _SKRIP], env=env, capture_output=True,
            text=True, check=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        return hasil.stdout
    assert jalankan("0") == jalankan("1")


def _dengan_laga_terakhir_pada(tanggal):
    df = muat_pertandingan()
    maju = df.copy()
    idx = maju.index[maju.musim == "2026/27"][-1]
    maju.loc[idx, "tanggal"] = pd.Timestamp(tanggal)
    return jadwal_sisa(maju)


def test_mulai_setelah_laga_terakhir_yang_dimainkan():
    assert _dengan_laga_terakhir_pada("2026-12-01").tanggal.min() == pd.Timestamp("2026-12-05")  # Selasa


def test_laga_terakhir_hari_sabtu_maju_tujuh_hari():
    assert _dengan_laga_terakhir_pada("2026-12-05").tanggal.min() == pd.Timestamp("2026-12-12")

def test_tanpa_sisa_tetap_bertipe_tanggal():
    sisa = jadwal_sisa(muat_pertandingan(), musim="1900/01")
    assert len(sisa) == 0
    assert pd.api.types.is_datetime64_any_dtype(sisa.tanggal)
    assert list(sisa.columns) == ["tanggal", "tim_kandang", "tim_tandang"]
