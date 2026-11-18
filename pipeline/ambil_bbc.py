"""Mengambil statistik lengkap laga Liga Primer dari halaman BBC Sport.

robots.txt BBC mengizinkan halaman jadwal dan halaman laga, dan halaman aturan pakai BBC
tidak memuat larangan pengambilan otomatis. Pengambilan tetap dibuat sopan: satu
permintaan tiap beberapa detik, hanya halaman yang dibutuhkan, dan setiap laga yang sudah
tersimpan tidak diambil ulang.

Pemakaian:
    python ambil_bbc.py              musim berjalan
    python ambil_bbc.py 2025/26      musim tertentu
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

from ambil_data import _peta_nama

AKAR = Path(__file__).parent
SIMPAN = AKAR / "data" / "bbc"
INDUK = "https://www.bbc.co.uk"
JEDA_DETIK = 3.0
MUSIM_KARTU_BBC = ["2026/27"]  # kartu kuning football-data musim ini banyak berbeda dengan BBC,
                               # Sofascore, dan ESPN, jadi versi BBC yang dipakai
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/157.0 Safari/537.36"}
PETA_MANUAL = {"Manchester City": "Man City", "Manchester United": "Man United",
               "Nottingham Forest": "Nott'm Forest", "Wolverhampton Wanderers": "Wolves",
               "Tottenham Hotspur": "Tottenham", "Brighton & Hove Albion": "Brighton",
               "Sheffield United": "Sheffield United"}

LABEL = {
    "Overall possession": "penguasaan_bola",
    "Total touches inside the opposition box": "sentuhan_kotak_lawan",
    "Goalkeeper saves": "penyelamatan_kiper",
    "Aerial duels won": "duel_udara_menang",
    "Shots off target": "tembakan_melenceng",
    "Attempts out of box": "tembakan_luar_kotak",
    "Hit woodwork": "kena_tiang",
    "Total offsides": "offside",
    "Total passes": "umpan",
    "Pass accuracy %": "akurasi_umpan",
    "Backward passes": "umpan_ke_belakang",
    "Forward passes": "umpan_ke_depan",
    "Total long balls": "bola_panjang",
    "Successful final third passes": "umpan_sepertiga_akhir",
    "Total crosses": "umpan_silang",
    "Total tackles": "tekel",
    "Won tackle %": "persen_tekel_sukses",
    "Total clearances": "sapuan",
    "Clearances off the line": "sapuan_garis_gawang",
    # dipakai untuk cek silang dengan football-data
    "Shots": "cek_tembakan",
    "Shots on target": "cek_tembakan_tepat",
    "Corners taken": "cek_sepak_pojok",
    "Fouls committed": "cek_pelanggaran",
    "Total yellow cards": "cek_kartu_kuning",
}

sesi = requests.Session()
sesi.headers.update(UA)
_terakhir = [0.0]


def ambil(path: str) -> str:
    tunggu = JEDA_DETIK - (time.time() - _terakhir[0])
    if tunggu > 0:
        time.sleep(tunggu)
    r = sesi.get(INDUK + path, timeout=30)
    _terakhir[0] = time.time()
    r.raise_for_status()
    return r.text


def _bersih(html: str) -> str:
    teks = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", html))
    return re.sub(r"(\|\s*)+", "| ", teks)


def laga_di_tanggal(tanggal: str) -> list[dict]:
    html = ambil(f"/sport/football/scores-fixtures/{tanggal}")
    keluar = []
    for url, isi in re.findall(r'<a[^>]+href="(/sport/football/live/[a-z0-9]+)"[^>]*>(.*?)</a>', html, re.S):
        teks = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", isi)).strip()
        m = re.match(r"(.+?) (\d+) , (.+?) (\d+) at Full time", teks)
        if m:
            keluar.append({"url": url, "kandang_bbc": m.group(1), "tandang_bbc": m.group(3),
                           "gol_kandang": int(m.group(2)), "gol_tandang": int(m.group(4))})
    return keluar


def baca_statistik(html: str, kandang: str, tandang: str) -> dict:
    teks = _bersih(html)
    batas = teks.find("| Goals scored |")  # bagian sesudahnya statistik satu musim, bukan laga
    if batas > 0:
        teks = teks[:batas]
    hasil = {}
    m = re.search(r"Overall possession \| \w+ \| ([\d.]+)% \| \w+ \| ([\d.]+)%", teks)
    if m:
        hasil["penguasaan_bola_kandang"], hasil["penguasaan_bola_tandang"] = float(m.group(1)), float(m.group(2))
    m = re.search(rf"xG \| {re.escape(kandang)} ([\d.]+) \| {re.escape(tandang)} ([\d.]+)", teks)
    if m:
        hasil["xg_bbc_kandang"], hasil["xg_bbc_tandang"] = round(float(m.group(1)), 2), round(float(m.group(2)), 2)
    pola = re.compile(rf"\| ([A-Z][A-Za-z %'()-]{{2,60}}?) \| {re.escape(kandang)} ([\d.]+)%? \| "
                      rf"{re.escape(tandang)} ([\d.]+)%?")
    for label, a, b in pola.findall(teks):
        nama = LABEL.get(label.strip())
        if nama and f"{nama}_kandang" not in hasil:
            hasil[f"{nama}_kandang"], hasil[f"{nama}_tandang"] = float(a), float(b)
    return hasil


def ambil_musim(musim: str) -> None:
    folder = SIMPAN / musim.replace("/", "-")
    folder.mkdir(parents=True, exist_ok=True)
    dasar = pd.read_csv(AKAR / "data" / "liga_inggris_lengkap.csv", parse_dates=["tanggal"])
    laga_musim = dasar[dasar.musim == musim]
    tim_fd = sorted(set(laga_musim.tim_kandang) | set(laga_musim.tim_tandang))
    sudah = {p.stem for p in folder.glob("*.json")}
    tersimpan = sum(1 for _ in folder.glob("*.json"))
    print(f"Musim {musim}: {len(laga_musim)} laga di football-data, {tersimpan} sudah tersimpan dari BBC")

    for tanggal, bagian in laga_musim.groupby(laga_musim.tanggal.dt.strftime("%Y-%m-%d")):
        pasangan = set(zip(bagian.tim_kandang, bagian.tim_tandang))
        if all(f"{k}__{t}".replace("'", "") in sudah for k, t in pasangan):
            continue
        try:
            daftar = laga_di_tanggal(tanggal)
        except Exception as e:
            print(f"  {tanggal}: halaman jadwal gagal ({type(e).__name__})")
            continue
        nama_bbc = sorted({d["kandang_bbc"] for d in daftar} | {d["tandang_bbc"] for d in daftar})
        peta = {**_peta_nama(nama_bbc, tim_fd), **PETA_MANUAL}
        for d in daftar:
            k, t = peta.get(d["kandang_bbc"]), peta.get(d["tandang_bbc"])
            if (k, t) not in pasangan:
                continue
            kunci = f"{k}__{t}".replace("'", "")
            if kunci in sudah:
                continue
            try:
                stat = baca_statistik(ambil(d["url"]), d["kandang_bbc"], d["tandang_bbc"])
            except Exception as e:
                print(f"  {tanggal} {k} vs {t}: gagal ({type(e).__name__})")
                continue
            catatan = {"musim": musim, "tanggal": tanggal, "tim_kandang": k, "tim_tandang": t,
                       "url_bbc": INDUK + d["url"], "gol_kandang_bbc": d["gol_kandang"],
                       "gol_tandang_bbc": d["gol_tandang"], **stat}
            (folder / f"{kunci}.json").write_text(json.dumps(catatan, ensure_ascii=False), encoding="utf-8")
            sudah.add(kunci)
        print(f"  {tanggal}: {sum(f'{k}__{t}'.replace(chr(39), '') in sudah for k, t in pasangan)}"
              f" dari {len(pasangan)} laga tersimpan")

    print(f"Selesai: {sum(1 for _ in folder.glob('*.json'))} dari {len(laga_musim)} laga musim {musim}")


def tabel_bbc() -> pd.DataFrame:
    baris = [json.loads(p.read_text(encoding="utf-8")) for p in SIMPAN.glob("*/*.json")]
    return pd.DataFrame(baris)


def lengkapi(gabungan: pd.DataFrame) -> pd.DataFrame:
    """Isi kolom statistik lengkap dari BBC untuk laga yang belum punya, lalu cek silang."""
    bbc = tabel_bbc()
    if bbc.empty:
        return gabungan
    bbc = bbc.drop(columns=["tanggal"])
    gabungan = gabungan.merge(bbc, on=["musim", "tim_kandang", "tim_tandang"], how="left",
                              suffixes=("", "_dari_bbc"), validate="one_to_one")
    for kolom in [c for c in gabungan.columns if c.endswith("_dari_bbc")]:
        asal = kolom.removesuffix("_dari_bbc")
        gabungan[asal] = gabungan[asal].combine_first(gabungan[kolom])
        gabungan = gabungan.drop(columns=kolom)

    ada_bbc = gabungan.url_bbc.notna()
    sumber = gabungan.get("sumber_statistik_lengkap", pd.Series(index=gabungan.index, dtype=object))
    sumber = sumber.where(sumber.notna(), None)
    sumber = sumber.mask(gabungan.get("statistik_lengkap", False).astype(bool) & sumber.isna(), "API-Football")
    sumber = sumber.mask(ada_bbc & sumber.isna(), "BBC Sport")
    gabungan["sumber_statistik_lengkap"] = sumber
    gabungan["statistik_lengkap"] = sumber.notna()

    cek = gabungan[ada_bbc]
    print(f"\nBBC Sport: {int(ada_bbc.sum())} laga tergabung")
    beda_skor = ((cek.gol_kandang != cek.gol_kandang_bbc) | (cek.gol_tandang != cek.gol_tandang_bbc)).sum()
    print(f"  skor berbeda dengan football-data: {int(beda_skor)} laga")
    for asal in ("tembakan", "tembakan_tepat", "sepak_pojok", "pelanggaran", "kartu_kuning"):
        if f"cek_{asal}_kandang" not in cek:
            continue
        beda = pd.concat([(cek[f"{asal}_kandang"] - cek[f"cek_{asal}_kandang"]).abs(),
                          (cek[f"{asal}_tandang"] - cek[f"cek_{asal}_tandang"]).abs()])
        print(f"  {asal:15s} sama persis {(beda == 0).mean():6.1%} | rata-rata selisih {beda.mean():.2f}")

    koreksi = (gabungan.musim.isin(MUSIM_KARTU_BBC) & gabungan.cek_kartu_kuning_kandang.notna()
               & ((gabungan.kartu_kuning_kandang != gabungan.cek_kartu_kuning_kandang)
                  | (gabungan.kartu_kuning_tandang != gabungan.cek_kartu_kuning_tandang)))
    gabungan["kartu_kuning_dikoreksi"] = koreksi
    for sisi in ("kandang", "tandang"):
        gabungan.loc[koreksi, f"kartu_kuning_{sisi}"] = gabungan.loc[koreksi, f"cek_kartu_kuning_{sisi}"]
    print(f"  kartu kuning dikoreksi memakai BBC: {int(koreksi.sum())} laga musim {', '.join(MUSIM_KARTU_BBC)}")
    return gabungan


if __name__ == "__main__":
    ambil_musim(sys.argv[1] if len(sys.argv) > 1 else "2026/27")
