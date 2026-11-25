"""Mengambil statistik lengkap per laga dari API-Football lalu menggabungkannya
dengan data football-data.co.uk menjadi satu CSV.

Paket gratis hanya membuka musim 2022/23 sampai 2024/25 dan 100 permintaan per hari,
jadi pengunduhan dibuat bisa dilanjutkan: setiap jawaban disimpan sebagai berkas, laga
yang sudah tersimpan dilewati, dan proses berhenti sendiri sebelum kuota habis.

Pemakaian:
    python ambil_apifootball.py          unduh sebagian lalu gabungkan
    python ambil_apifootball.py gabung   hanya menggabungkan yang sudah terunduh
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

AKAR = Path(__file__).parent
SIMPAN = AKAR / "data" / "apifootball"
BERKAS_KUNCI = AKAR.parent / "apikeyfootball.txt"
HOST = "https://v3.football.api-sports.io"
LIGA = 39
MUSIM_TERBUKA = [2024, 2022]  # laga yang sudah punya statistik BBC dilewati supaya kuota tidak terbuang
JEDA_DETIK = 6.5                   # paket gratis dibatasi 10 permintaan per menit
SISA_MINIMAL = 3                   # sisakan sedikit kuota untuk pengecekan manual

KOLOM_STATISTIK = {
    "Ball Possession": "penguasaan_bola",
    "Total Shots": "tembakan_api",
    "Shots on Goal": "tembakan_tepat_api",
    "Shots off Goal": "tembakan_melenceng",
    "Blocked Shots": "tembakan_terblok",
    "Shots insidebox": "tembakan_dalam_kotak",
    "Shots outsidebox": "tembakan_luar_kotak",
    "Fouls": "pelanggaran_api",
    "Corner Kicks": "sepak_pojok_api",
    "Offsides": "offside",
    "Yellow Cards": "kartu_kuning_api",
    "Red Cards": "kartu_merah_api",
    "Goalkeeper Saves": "penyelamatan_kiper",
    "Total passes": "umpan",
    "Passes accurate": "umpan_akurat",
    "Passes %": "akurasi_umpan",
    "expected_goals": "xg_api",
    "goals_prevented": "gol_dicegah",
}
PETA_TIM = {
    "Manchester United": "Man United", "Manchester City": "Man City",
    "Nottingham Forest": "Nott'm Forest", "Sheffield Utd": "Sheffield United",
    "Wolves": "Wolves", "Tottenham": "Tottenham", "Newcastle": "Newcastle",
    "Brighton": "Brighton", "West Ham": "West Ham", "Leicester": "Leicester",
    "Ipswich": "Ipswich", "Luton": "Luton", "Leeds": "Leeds",
}


def kunci_api() -> str:
    kunci = os.environ.get("APIFOOTBALL_KEY") or (
        BERKAS_KUNCI.read_text(encoding="utf-8-sig").strip() if BERKAS_KUNCI.exists() else "")
    if not kunci:
        sys.exit(f"Kunci API tidak ditemukan. Simpan di {BERKAS_KUNCI} atau variabel APIFOOTBALL_KEY.")
    return kunci


class Klien:
    def __init__(self, kunci: str):
        self.sesi = requests.Session()
        self.sesi.headers["x-apisports-key"] = kunci
        self.sisa: int | None = None
        self.terpakai = 0

    def ambil(self, path: str, **param) -> dict:
        if self.terpakai:
            time.sleep(JEDA_DETIK)
        r = self.sesi.get(f"{HOST}{path}", params=param, timeout=40)
        self.terpakai += 1
        sisa = r.headers.get("x-ratelimit-requests-remaining")
        self.sisa = int(sisa) if sisa is not None else self.sisa
        data = r.json()
        if data.get("errors"):
            raise RuntimeError(f"API menolak {path} {param}: {data['errors']}")
        return data

    def masih_boleh(self) -> bool:
        return self.sisa is None or self.sisa > SISA_MINIMAL


def daftar_laga(klien: Klien, musim: int) -> list[dict]:
    berkas = SIMPAN / f"laga_{musim}.json"
    if berkas.exists():
        return json.loads(berkas.read_text(encoding="utf-8"))
    data = klien.ambil("/fixtures", league=LIGA, season=musim)["response"]
    berkas.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def _kunci_laga(f: dict, musim: int) -> tuple[str, str, str]:
    nama = lambda sisi: PETA_TIM.get(f["teams"][sisi]["name"], f["teams"][sisi]["name"])
    return f"{musim}/{(musim + 1) % 100:02d}", nama("home"), nama("away")


def unduh() -> None:
    SIMPAN.mkdir(parents=True, exist_ok=True)
    (SIMPAN / "statistik").mkdir(exist_ok=True)
    klien = Klien(kunci_api())
    status = klien.ambil("/status")["response"]["requests"]
    klien.sisa = status["limit_day"] - status["current"]
    print(f"Kuota hari ini: {status['current']} terpakai dari {status['limit_day']}")

    import ambil_bbc

    bbc = ambil_bbc.tabel_bbc()
    ada_bbc = set(zip(bbc.musim, bbc.tim_kandang, bbc.tim_tandang)) if not bbc.empty else set()

    for musim in MUSIM_TERBUKA:
        if not klien.masih_boleh():
            break
        laga = [f for f in daftar_laga(klien, musim) if f["fixture"]["status"]["short"] == "FT"]
        belum = [f for f in laga
                 if not (SIMPAN / "statistik" / f"{f['fixture']['id']}.json").exists()
                 and _kunci_laga(f, musim) not in ada_bbc]  # yang sudah ada di BBC tidak perlu kuota
        print(f"Musim {musim}/{(musim + 1) % 100:02d}: {len(laga) - len(belum)} dari {len(laga)} sudah ada")
        for f in belum:
            if not klien.masih_boleh():
                break
            jawaban = klien.ambil("/fixtures/statistics", fixture=f["fixture"]["id"])["response"]
            (SIMPAN / "statistik" / f"{f['fixture']['id']}.json").write_text(
                json.dumps(jawaban, ensure_ascii=False), encoding="utf-8")
        sudah = sum((SIMPAN / "statistik" / f"{f['fixture']['id']}.json").exists() for f in laga)
        print(f"  sekarang {sudah} dari {len(laga)} laga")

    print(f"Permintaan dipakai sesi ini: {klien.terpakai}, sisa kuota hari ini: {klien.sisa}")


def _angka(nilai):
    if nilai is None:
        return None
    if isinstance(nilai, str):
        nilai = nilai.replace("%", "").strip()
        return float(nilai) if nilai else None
    return float(nilai)


def tabel_api() -> pd.DataFrame:
    baris = []
    for berkas_laga in sorted(SIMPAN.glob("laga_*.json")):
        musim = int(berkas_laga.stem.split("_")[1])
        for f in json.loads(berkas_laga.read_text(encoding="utf-8")):
            stat_berkas = SIMPAN / "statistik" / f"{f['fixture']['id']}.json"
            if not stat_berkas.exists():
                continue
            jawaban = json.loads(stat_berkas.read_text(encoding="utf-8"))
            if len(jawaban) != 2:
                continue
            satu = {
                "musim": f"{musim}/{(musim + 1) % 100:02d}",
                "tim_kandang": PETA_TIM.get(f["teams"]["home"]["name"], f["teams"]["home"]["name"]),
                "tim_tandang": PETA_TIM.get(f["teams"]["away"]["name"], f["teams"]["away"]["name"]),
                "id_apifootball": f["fixture"]["id"],
                "stadion": (f["fixture"].get("venue") or {}).get("name"),
                "pekan": f["league"].get("round", "").replace("Regular Season - ", ""),
            }
            for sisi, tim in zip(("kandang", "tandang"), jawaban):
                for item in tim["statistics"]:
                    nama = KOLOM_STATISTIK.get(item["type"])
                    if nama:
                        satu[f"{nama}_{sisi}"] = _angka(item["value"])
            baris.append(satu)
    return pd.DataFrame(baris)


def gabung() -> pd.DataFrame:
    dasar = pd.read_csv(AKAR / "data" / "liga_inggris_lengkap.csv", parse_dates=["tanggal"])
    api = tabel_api()
    if api.empty:
        api = pd.DataFrame(columns=["musim", "tim_kandang", "tim_tandang", "id_apifootball"])

    tak_cocok = (set(api.tim_kandang) | set(api.tim_tandang)) - (
        set(dasar.tim_kandang) | set(dasar.tim_tandang))
    if tak_cocok:
        print("Peringatan, nama tim belum terpetakan:", sorted(tak_cocok))

    gabungan = dasar.merge(api, on=["musim", "tim_kandang", "tim_tandang"], how="left",
                           validate="one_to_one")
    gabungan["statistik_lengkap"] = gabungan.id_apifootball.notna()
    gabungan["sumber_statistik_lengkap"] = np.where(gabungan.statistik_lengkap, "API-Football", None)

    # pemeriksaan silang statistik yang ada di kedua sumber
    cek = gabungan[gabungan.statistik_lengkap]
    print(f"\nTergabung {len(cek)} laga dari {len(api)} laga API-Football")
    for asal, api_kolom in [("tembakan", "tembakan_api"), ("tembakan_tepat", "tembakan_tepat_api"),
                            ("sepak_pojok", "sepak_pojok_api"), ("pelanggaran", "pelanggaran_api"),
                            ("kartu_kuning", "kartu_kuning_api")]:
        beda = (cek[f"{asal}_kandang"] - cek[f"{api_kolom}_kandang"]).abs()
        print(f"  {asal:15s} sama persis {(beda == 0).mean():6.1%} | rata-rata selisih {beda.mean():.2f}")

    import ambil_bbc

    gabungan = ambil_bbc.lengkapi(gabungan)

    # kolom yang kembar dengan football-data dibuang, football-data tetap jadi acuan
    kembar = [k for k in gabungan.columns if (k.endswith(("_api_kandang", "_api_tandang"))
              and not k.startswith("xg_api")) or k.startswith("cek_")
              or k in ("gol_kandang_bbc", "gol_tandang_bbc")]
    gabungan = gabungan.drop(columns=kembar)
    gabungan.to_csv(AKAR / "data" / "liga_inggris_gabungan.csv", index=False)
    print(f"\nTersimpan: data/liga_inggris_gabungan.csv, {len(gabungan)} laga, "
          f"{gabungan.shape[1]} kolom, {int(gabungan.statistik_lengkap.sum())} laga berstatistik lengkap")
    return gabungan


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "gabung":
        unduh()
    gabung()
