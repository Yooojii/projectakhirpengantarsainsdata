"""Penopang keadaan sesi: jalur absolut ke berkas proyek dan skuad sekali-bangkit.

Jalur diturunkan dari lokasi berkas ini, bukan dari direktori kerja, supaya
`streamlit run` dari folder mana pun tetap menemukan model dan data. Tanpa itu,
`muat_model` (yang bawaannya berjalur relatif) diam-diam tidak menemukan
`model/model.joblib` dan dashboard jatuh ke Poisson tanpa tanda apa pun.
"""
from pathlib import Path

import pandas as pd

from inti.pemain import bangkitkan_skuad

AKAR = Path(__file__).resolve().parent.parent
JALUR_DATA = AKAR / "data" / "liga_inggris_gabungan.csv"
JALUR_MODEL = AKAR / "model" / "model.joblib"
JALUR_METRIK = AKAR / "model" / "metrik.json"

BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]


def skuad_klub(keadaan, df: pd.DataFrame, klub: str) -> list:
    """Skuad klub dari `keadaan` (st.session_state); dibangkitkan sekali saja.

    Pemanggilan berikutnya mengembalikan objek yang sama, sehingga suntingan
    penggeser pada pemain tidak terhapus oleh rerun.
    """
    skuad = keadaan.setdefault("skuad", {})
    if klub not in skuad:
        skuad[klub] = bangkitkan_skuad(df, klub, df["tanggal"].max() + pd.Timedelta(days=1))
    return skuad[klub]


def keterangan_cakupan(df: pd.DataFrame) -> str:
    """Satu baris: rentang musim dan tanggal laga terakhir."""
    akhir = df["tanggal"].max()
    tanggal = f"{akhir.day} {BULAN[akhir.month - 1]} {akhir.year}"
    return f"{df['musim'].min()} sampai {df['musim'].max()}, laga terakhir {tanggal}"
