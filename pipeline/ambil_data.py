"""Mengunduh data Liga Primer Inggris dari football-data.co.uk.

Koneksi langsung dicoba lebih dulu. Bila gagal karena pemblokiran DNS oleh ISP,
alamat situs diambil lewat DNS over HTTPS Cloudflare lalu disambungkan langsung
ke alamat IP-nya dengan SNI tetap utuh, sehingga TLS tidak dilanggar.
"""

from __future__ import annotations

import http.client
import io
import socket
import ssl
from pathlib import Path
from urllib.parse import urlparse

import certifi
import pandas as pd
import requests

MUSIM = {
    "2000/01": "0001",
    "2001/02": "0102",
    "2002/03": "0203",
    "2003/04": "0304",
    "2004/05": "0405",
    "2005/06": "0506",
    "2006/07": "0607",
    "2007/08": "0708",
    "2008/09": "0809",
    "2009/10": "0910",
    "2010/11": "1011",
    "2011/12": "1112",
    "2012/13": "1213",
    "2013/14": "1314",
    "2014/15": "1415",
    "2015/16": "1516",
    "2016/17": "1617",
    "2017/18": "1718",
    "2018/19": "1819",
    "2019/20": "1920",
    "2020/21": "2021",
    "2021/22": "2122",
    "2022/23": "2223",
    "2023/24": "2324",
    "2024/25": "2425",
    "2025/26": "2526",
    "2026/27": "2627",
}
INDUK = "https://www.football-data.co.uk"
FOLDER = Path(__file__).parent / "data"
KONTEKS = ssl.create_default_context(cafile=certifi.where())


def _alamat_doh(nama: str) -> str:
    r = requests.get(
        "https://cloudflare-dns.com/dns-query",
        params={"name": nama, "type": "A"},
        headers={"accept": "application/dns-json"},
        timeout=20,
    )
    jawaban = [a["data"] for a in r.json().get("Answer", []) if a["type"] == 1]
    if not jawaban:
        raise RuntimeError(f"DNS over HTTPS tidak mengembalikan alamat untuk {nama}")
    return jawaban[0]


def _unduh_doh(host: str, path: str, lompat: int = 0) -> bytes:
    sambungan = socket.create_connection((_alamat_doh(host), 443), timeout=30)
    koneksi = http.client.HTTPSConnection(host, 443, timeout=30, context=KONTEKS)
    koneksi.sock = KONTEKS.wrap_socket(sambungan, server_hostname=host)
    koneksi.request("GET", path, headers={"User-Agent": "Mozilla/5.0", "Host": host})
    tanggapan = koneksi.getresponse()
    isi = tanggapan.read()
    lokasi = tanggapan.getheader("Location")
    koneksi.close()
    if tanggapan.status in (301, 302, 303, 307, 308) and lokasi and lompat < 3:
        u = urlparse(lokasi if "://" in lokasi else f"https://{host}{lokasi}")
        return _unduh_doh(u.netloc, u.path + (f"?{u.query}" if u.query else ""), lompat + 1)
    if tanggapan.status != 200:
        raise RuntimeError(f"status {tanggapan.status} untuk {host}{path}")
    return isi


def unduh(url: str) -> bytes:
    """Unduh satu berkas, langsung dulu, lalu lewat DNS over HTTPS bila gagal."""
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        r.raise_for_status()
        return r.content
    except Exception:
        u = urlparse(url)
        return _unduh_doh(u.netloc, u.path + (f"?{u.query}" if u.query else ""))


def _baca_csv(isi: bytes) -> pd.DataFrame:
    """Baca CSV football-data dan bersihkan tanda BOM pada nama kolom."""
    try:
        d = pd.read_csv(io.BytesIO(isi), encoding="utf-8-sig", on_bad_lines="skip")
    except UnicodeDecodeError:
        d = pd.read_csv(io.BytesIO(isi), encoding="latin-1", on_bad_lines="skip")
    d.columns = [str(k).replace("﻿", "").replace("ï»¿", "").strip() for k in d.columns]
    return d


def ambil_musim(kode: str) -> pd.DataFrame:
    return _baca_csv(unduh(f"{INDUK}/mmz4281/{kode}/E0.csv"))


def ambil_jadwal() -> pd.DataFrame:
    jadwal = _baca_csv(unduh(f"{INDUK}/fixtures.csv"))
    return jadwal[jadwal["Div"] == "E0"].copy()


KOLOM = {
    "Date": "tanggal", "Time": "waktu", "HomeTeam": "tim_kandang", "AwayTeam": "tim_tandang",
    "FTHG": "gol_kandang", "FTAG": "gol_tandang", "FTR": "hasil",
    "HTHG": "gol_kandang_babak1", "HTAG": "gol_tandang_babak1", "Referee": "wasit",
    "HS": "tembakan_kandang", "AS": "tembakan_tandang",
    "HST": "tembakan_tepat_kandang", "AST": "tembakan_tepat_tandang",
    "HF": "pelanggaran_kandang", "AF": "pelanggaran_tandang",
    "HC": "sepak_pojok_kandang", "AC": "sepak_pojok_tandang",
    "HY": "kartu_kuning_kandang", "AY": "kartu_kuning_tandang",
    "HR": "kartu_merah_kandang", "AR": "kartu_merah_tandang",
    "HxG": "xg_kandang", "AxG": "xg_tandang",
    "AvgH": "odds_kandang", "AvgD": "odds_seri", "AvgA": "odds_tandang",
}


def rapikan(mentah: pd.DataFrame, musim: str) -> pd.DataFrame:
    d = mentah.rename(columns=KOLOM)
    tersedia = [k for k in KOLOM.values() if k in d.columns]
    d = d[tersedia].copy()
    d["tanggal"] = pd.to_datetime(d["tanggal"], dayfirst=True, errors="coerce")
    d["musim"] = musim
    return d.dropna(subset=["tanggal", "tim_kandang"]).reset_index(drop=True)


def perbarui_semua() -> pd.DataFrame:
    FOLDER.mkdir(parents=True, exist_ok=True)
    kumpulan = []
    for musim, kode in MUSIM.items():
        try:
            d = rapikan(ambil_musim(kode), musim)
            kumpulan.append(d)
            print(f"  {musim}: {len(d)} laga, {d.shape[1]} kolom")
        except Exception as e:
            print(f"  {musim}: gagal ({type(e).__name__}: {str(e)[:70]})")
    gabung = pd.concat(kumpulan, ignore_index=True).sort_values("tanggal")
    gabung.to_csv(FOLDER / "liga_inggris_lengkap.csv", index=False)

    try:
        jadwal = ambil_jadwal().rename(columns=KOLOM)
        kolom = [k for k in ["tanggal", "waktu", "tim_kandang", "tim_tandang", "wasit",
                             "odds_kandang", "odds_seri", "odds_tandang"] if k in jadwal.columns]
        jadwal = jadwal[kolom]
        jadwal["tanggal"] = pd.to_datetime(jadwal["tanggal"], format="%d/%m/%Y", errors="coerce")
        jadwal.to_csv(FOLDER / "jadwal_mendatang.csv", index=False)
        print(f"  jadwal mendatang: {len(jadwal)} laga")
    except Exception as e:
        print(f"  jadwal mendatang: gagal ({type(e).__name__}: {str(e)[:70]})")
    return gabung


# --------------------------------------------------------------- jadwal penuh
SUMBER_JADWAL = (
    "https://raw.githubusercontent.com/openfootball/football.json/master/{musim}/en.1.json"
)
PETA_MANUAL = {
    "Manchester City FC": "Man City",
    "Manchester United FC": "Man United",
    "Nottingham Forest FC": "Nott'm Forest",
}


def _sederhana(nama: str) -> str:
    import re

    nama = re.sub(
        r"\b(FC|AFC|United|City|Hotspur|Wanderers|Albion|Town|Rovers|County|Forest|"
        r"Palace|Villa|Athletic)\b",
        " ",
        nama,
    )
    return re.sub(r"[^a-z]", "", nama.lower())


def _peta_nama(nama_sumber, nama_acuan) -> dict:
    peta = dict(PETA_MANUAL)
    for a in nama_sumber:
        if a in peta:
            continue
        cocok = [b for b in nama_acuan if _sederhana(a) and _sederhana(a) == _sederhana(b)]
        if not cocok:
            cocok = [
                b for b in nama_acuan
                if _sederhana(b) and (_sederhana(b) in _sederhana(a) or _sederhana(a) in _sederhana(b))
            ]
        if len(cocok) == 1:
            peta[a] = cocok[0]
    return peta


def ambil_jadwal_musim(musim: str = "2026/27") -> pd.DataFrame:
    """Jadwal lengkap satu musim dari openfootball, nama tim disamakan ke football-data."""
    import json

    kode = musim.replace("/", "-20") if len(musim.split("/")[-1]) == 4 else musim.replace("/", "-")
    isi = unduh(SUMBER_JADWAL.format(musim=kode))
    data = json.loads(isi.decode("utf-8"))
    jadwal = pd.DataFrame(data["matches"])[["round", "date", "time", "team1", "team2"]]
    jadwal.columns = ["putaran", "tanggal", "waktu", "tim_kandang", "tim_tandang"]

    hasil = pd.read_csv(FOLDER / "liga_inggris_lengkap.csv")
    acuan = sorted(set(hasil[hasil.musim == musim].tim_kandang))
    peta = _peta_nama(
        sorted(set(jadwal.tim_kandang) | set(jadwal.tim_tandang)), acuan
    )
    jadwal["tim_kandang"] = jadwal.tim_kandang.map(peta).fillna(jadwal.tim_kandang)
    jadwal["tim_tandang"] = jadwal.tim_tandang.map(peta).fillna(jadwal.tim_tandang)
    jadwal["tanggal"] = pd.to_datetime(jadwal["tanggal"])
    jadwal["musim"] = musim

    sudah = hasil[hasil.musim == musim][["tim_kandang", "tim_tandang"]].apply(tuple, axis=1)
    jadwal["sudah_main"] = jadwal[["tim_kandang", "tim_tandang"]].apply(tuple, axis=1).isin(set(sudah))
    jadwal.to_csv(FOLDER / "jadwal_musim.csv", index=False)
    return jadwal


def perbarui_musim_berjalan(musim: str = "2026/27") -> pd.DataFrame:
    """Unduh ulang musim berjalan saja, lalu ganti barisnya di data gabungan."""
    berkas = FOLDER / "liga_inggris_lengkap.csv"
    lama = pd.read_csv(berkas, parse_dates=["tanggal"])
    baru = rapikan(ambil_musim(MUSIM[musim]), musim)
    gabung = pd.concat([lama[lama.musim != musim], baru], ignore_index=True).sort_values("tanggal")
    gabung.to_csv(berkas, index=False)
    print(f"  {musim}: {len(baru)} laga (sebelumnya {int((lama.musim == musim).sum())})")
    jadwal = ambil_jadwal_musim(musim)
    print(f"  jadwal: {int(jadwal.sudah_main.sum())} sudah main, {int((~jadwal.sudah_main).sum())} belum")
    try:
        import ambil_apifootball

        ambil_apifootball.gabung()
    except Exception as e:
        print(f"  penggabungan API-Football dilewati: {type(e).__name__}: {str(e)[:80]}")
    return gabung


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "berjalan":
        print("Memperbarui musim berjalan")
        perbarui_musim_berjalan()
        raise SystemExit
    print("Mengunduh data football-data.co.uk")
    hasil = perbarui_semua()
    print(f"\nTotal {len(hasil)} laga tersimpan di {FOLDER / 'liga_inggris_lengkap.csv'}")
