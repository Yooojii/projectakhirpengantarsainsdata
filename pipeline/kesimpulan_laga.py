"""Menulis paragraf kesimpulan setiap laga musim berjalan memakai Gemini.

Data laga (skor, statistik asli, prediksi model, performa terbaru) dirangkum lalu
dikirim ke Gemini dengan instruksi hanya memakai angka yang diberikan. Angka di
paragraf dicek ulang terhadap data; bila ada yang tidak cocok, atau API gagal,
dipakai paragraf dari template. Hasil disimpan dan laga yang sudah ada dilewati.

Pemakaian:
    python kesimpulan_laga.py            tulis yang belum ada
    python kesimpulan_laga.py ulang      tulis ulang semua
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

AKAR = Path(__file__).parent
BERKAS_KUNCI = AKAR.parent / "apikeygemini.txt"
KELUAR = AKAR / "data" / "kesimpulan_laga.json"
MODEL = "gemini-3.1-flash-lite"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
MUSIM = "2026/27"
JEDA_DETIK = 7.0  # paket gratis membatasi permintaan per menit

STAT = [("penguasaan_bola", "penguasaan bola (%)"), ("tembakan", "tembakan"),
        ("tembakan_tepat", "tembakan tepat sasaran"), ("sepak_pojok", "sepak pojok"),
        ("pelanggaran", "pelanggaran"), ("kartu_kuning", "kartu kuning"),
        ("umpan", "umpan"), ("akurasi_umpan", "akurasi umpan (%)")]

ATURAN = """Kamu penulis ringkasan sepak bola berbahasa Indonesia.
Tulis SATU paragraf (3 sampai 4 kalimat, paling banyak 90 kata) berdasarkan data di bawah.
Aturan:
- Pakai hanya fakta dan angka yang ada di data. Jangan menyebut nama pemain, cedera, pelatih, atau apa pun yang tidak tertulis.
- Tulis angka persis seperti di data (peluang boleh dibulatkan ke persen bulat).
- Gaya santai tapi rapi, tanpa tanda pisah panjang, tanpa emoji, tanpa judul, tanpa poin-poin.
- {fokus}
Data:
{data}"""
FOKUS_SELESAI = ("Laga sudah selesai: jelaskan hasilnya, statistik yang paling menentukan, "
                 "lalu bandingkan dengan prediksi model (sesuai atau meleset).")
FOKUS_MENDATANG = ("Laga belum dimainkan: jelaskan siapa yang diunggulkan model dan alasannya "
                   "dari performa terbaru, lalu sebut skor dan statistik yang diperkirakan.")


def _bulat(x, n=0):
    return None if pd.isna(x) else (int(round(x)) if n == 0 else round(float(x), n))


def bentuk_terakhir(laga: pd.DataFrame, tim: str, sebelum: pd.Timestamp, n: int = 5) -> str:
    main = laga[laga.sudah_main & (laga.tanggal < sebelum)
                & ((laga.tim_kandang == tim) | (laga.tim_tandang == tim))].tail(n)
    kode = []
    for r in main.itertuples():
        gs, gl = (r.gol_kandang, r.gol_tandang) if r.tim_kandang == tim else (r.gol_tandang, r.gol_kandang)
        kode.append("M" if gs > gl else "S" if gs == gl else "K")
    return "".join(kode) or "belum ada"


def rangkum(r, laga: pd.DataFrame) -> dict:
    d = {"tanggal": r.tanggal.strftime("%d-%m-%Y"), "pekan": _bulat(r.pekan),
         "tuan_rumah": r.tim_kandang, "tamu": r.tim_tandang,
         "lima_laga_terakhir (M=menang, S=seri, K=kalah, terbaru di kanan)": {
             r.tim_kandang: bentuk_terakhir(laga, r.tim_kandang, r.tanggal),
             r.tim_tandang: bentuk_terakhir(laga, r.tim_tandang, r.tanggal)},
         "rating_elo": {r.tim_kandang: _bulat(r.elo_k), r.tim_tandang: _bulat(r.elo_t)},
         "prediksi_model": {
             "peluang_menang_tuan_rumah_%": _bulat(100 * r.peluang_menang_kandang),
             "peluang_seri_%": _bulat(100 * r.peluang_seri),
             "peluang_menang_tamu_%": _bulat(100 * r.peluang_menang_tandang),
             "skor_paling_mungkin": r.skor_dugaan,
             "statistik_diperkirakan": {nama: [_bulat(getattr(r, f"duga_{k}_kandang")),
                                               _bulat(getattr(r, f"duga_{k}_tandang"))]
                                        for k, nama in STAT if pd.notna(getattr(r, f"duga_{k}_kandang", None))}}}
    if r.sudah_main:
        d["hasil_akhir"] = f"{int(r.gol_kandang)}-{int(r.gol_tandang)}"
        d["statistik_asli [tuan rumah, tamu]"] = {
            nama: [_bulat(getattr(r, f"{k}_kandang")), _bulat(getattr(r, f"{k}_tandang"))]
            for k, nama in STAT if pd.notna(getattr(r, f"{k}_kandang", None))}
    return d


def template(d: dict) -> str:
    k, t, p = d["tuan_rumah"], d["tamu"], d["prediksi_model"]
    unggul = (k if p["peluang_menang_tuan_rumah_%"] >= p["peluang_menang_tamu_%"] else t)
    if "hasil_akhir" in d:
        gk, gt = map(int, d["hasil_akhir"].split("-"))
        hasil = f"{k} menang {gk}-{gt} atas {t}" if gk > gt else (
            f"{t} menang {gt}-{gk} di kandang {k}" if gt > gk else f"{k} dan {t} bermain imbang {gk}-{gt}")
        s = d["statistik_asli [tuan rumah, tamu]"]
        teks = f"{hasil}."
        if "tembakan" in s:
            teks += f" {k} melepaskan {s['tembakan'][0]} tembakan, sedangkan {t} {s['tembakan'][1]}."
        teks += (f" Model sebelumnya mengunggulkan {unggul} dan memperkirakan skor "
                 f"{p['skor_paling_mungkin']}.")
        return teks
    return (f"Model mengunggulkan {unggul} pada laga {k} melawan {t}, dengan peluang menang tuan rumah "
            f"{p['peluang_menang_tuan_rumah_%']}%, seri {p['peluang_seri_%']}%, dan tamu "
            f"{p['peluang_menang_tamu_%']}%. Skor yang paling mungkin {p['skor_paling_mungkin']}.")


def angka_di(obj) -> set[str]:
    return set(re.findall(r"\d+(?:[.,]\d+)?", json.dumps(obj, ensure_ascii=False)))


def angka_sah(teks: str, d: dict) -> bool:
    """Semua angka di paragraf harus ada di data (selain angka kecil seperti 'dua' atau 'satu')."""
    sah = angka_di(d)
    for a in re.findall(r"\d+(?:[.,]\d+)?", teks):
        a = a.replace(",", ".")
        if a in sah or (a.isdigit() and int(a) <= 5) or a.rstrip("0").rstrip(".") in sah:
            continue
        return False
    return True


class KuotaHabis(RuntimeError):
    pass


def tanya_gemini(kunci: str, prompt: str) -> str:
    badan = {"contents": [{"parts": [{"text": prompt}]}],
             "generationConfig": {"temperature": 0.6, "maxOutputTokens": 400}}
    for coba in range(4):
        r = requests.post(URL, headers={"x-goog-api-key": kunci}, json=badan, timeout=120)
        if r.status_code == 429 and "PerDay" in r.text:
            raise KuotaHabis("kuota harian Gemini habis, coba lagi besok")
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(30 * (coba + 1))
            continue
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    raise RuntimeError(f"Gemini menolak terus ({r.status_code})")


def main(ulang: bool = False) -> None:
    kunci = BERKAS_KUNCI.read_text(encoding="utf-8-sig").strip()
    laga = pd.read_csv(AKAR / "data" / "prediksi_laga.csv", parse_dates=["tanggal"], low_memory=False)
    laga["sudah_main"] = laga.sudah_main.astype(str).str.lower().eq("true")
    laga = laga.sort_values("tanggal")
    hasil = {} if ulang or not KELUAR.exists() else json.loads(KELUAR.read_text(encoding="utf-8"))
    sasaran = laga[(laga.musim == MUSIM) & laga.peluang_seri.notna()]

    baru = gagal = 0
    for r in sasaran.itertuples():
        kunci_laga = f"{r.musim}|{r.tim_kandang}|{r.tim_tandang}"
        status = "selesai" if r.sudah_main else "mendatang"
        d = rangkum(r, laga)
        sidik = hashlib.sha1(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
        lama = hasil.get(kunci_laga)
        # ditulis ulang bila statusnya berubah, datanya berubah (misalnya model dilatih ulang),
        # atau sebelumnya jatuh ke template
        if lama and lama.get("sidik") == sidik and lama.get("sumber") == "gemini":
            continue
        prompt = ATURAN.format(fokus=FOKUS_SELESAI if r.sudah_main else FOKUS_MENDATANG,
                               data=json.dumps(d, ensure_ascii=False, indent=1))
        try:
            teks = tanya_gemini(kunci, prompt)
            teks = teks.replace("—", ",").replace("–", "-")
            sumber = "gemini" if angka_sah(teks, d) else "template"
        except KuotaHabis as e:
            print(f"Berhenti: {e}")
            break
        except Exception as e:
            print(f"  {kunci_laga}: Gemini gagal ({type(e).__name__}), pakai template")
            sumber = "template"
        if sumber == "template":
            teks, gagal = template(d), gagal + 1
        hasil[kunci_laga] = {"status": status, "sumber": sumber, "teks": teks, "sidik": sidik}
        KELUAR.write_text(json.dumps(hasil, ensure_ascii=False, indent=1), encoding="utf-8")
        baru += 1
        time.sleep(JEDA_DETIK)

    print(f"Selesai: {baru} paragraf baru, {gagal} memakai template, total {len(hasil)} laga")


if __name__ == "__main__":
    main(ulang=len(sys.argv) > 1 and sys.argv[1] == "ulang")
