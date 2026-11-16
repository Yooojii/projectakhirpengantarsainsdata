"""Jadwal simulasi sisa musim berjalan (data buatan, bukan hasil scraping)."""
from itertools import permutations

import pandas as pd

from inti.data import klub_musim

SABTU_PERTAMA = pd.Timestamp("2026-11-07")
LAGA_MAKS_PER_TANGGAL = 10


def _putaran(sisa: set[tuple[str, str]], klub: list[str]) -> list[tuple[str, str]]:
    """Satu putaran: pilih laga tanpa klub ganda, utamakan klub dengan sisa laga terbanyak."""
    derajat = {k: 0 for k in klub}
    for h, a in sisa:
        derajat[h] += 1
        derajat[a] += 1
    terpakai: set[str] = set()
    putaran: list[tuple[str, str]] = []
    for k in sorted(klub, key=lambda x: (-derajat[x], x)):
        if k in terpakai:
            continue
        calon = [
            (h, a) for h, a in sisa
            if k in (h, a) and h not in terpakai and a not in terpakai
        ]
        if not calon:
            continue
        lawan = lambda laga: laga[1] if laga[0] == k else laga[0]
        laga = min(calon, key=lambda l: (-derajat[lawan(l)], l))
        putaran.append(laga)
        terpakai.update(laga)
    return putaran


def jadwal_sisa(df: pd.DataFrame, musim: str = "2026/27") -> pd.DataFrame:
    """Laga yang belum dimainkan pada musim ini, dikelompokkan per hari Sabtu berurutan."""
    klub = klub_musim(df, musim)
    ada = df[df.musim == musim]
    dimainkan = set(zip(ada.tim_kandang, ada.tim_tandang))
    sisa = set(permutations(klub, 2)) - dimainkan

    baris = []
    tanggal = SABTU_PERTAMA
    while sisa:
        putaran = _putaran(sisa, klub)[:LAGA_MAKS_PER_TANGGAL]
        for h, a in putaran:
            baris.append({"tanggal": tanggal, "tim_kandang": h, "tim_tandang": a})
        sisa -= set(putaran)
        tanggal += pd.Timedelta(days=7)
    return pd.DataFrame(baris, columns=["tanggal", "tim_kandang", "tim_tandang"])
