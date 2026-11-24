"""Agregasi setingkat liga dan klub untuk halaman Overview.

Semua fungsi menerima `klub=None` yang berarti "seluruh liga". Memberi nama klub
menyempitkan perhitungan ke laga klub itu saja, dan itulah satu-satunya perbedaan
antara tampilan bawaan dan tampilan terfilter.
"""
import pandas as pd

try:
    import streamlit as st
    _cache = st.cache_data
except ImportError:  # modul inti tetap bisa diuji tanpa Streamlit
    def _cache(fungsi):
        return fungsi

MUSIM_PENUH = 300  # musim dengan laga lebih sedikit dianggap belum selesai


def _sisi(df: pd.DataFrame, klub: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Laga klub sebagai tuan rumah dan sebagai tamu."""
    return df[df["tim_kandang"] == klub], df[df["tim_tandang"] == klub]


def _jumlah(df: pd.DataFrame, klub: str | None, dasar: str) -> int:
    """Total kolom `dasar_kandang`/`dasar_tandang`, disaring ke satu klub bila diminta."""
    if klub is None:
        return int(df[f"{dasar}_kandang"].sum() + df[f"{dasar}_tandang"].sum())
    k, t = _sisi(df, klub)
    return int(k[f"{dasar}_kandang"].sum() + t[f"{dasar}_tandang"].sum())


def laga_klub(df: pd.DataFrame, klub: str | None) -> pd.DataFrame:
    if klub is None:
        return df
    return df[(df["tim_kandang"] == klub) | (df["tim_tandang"] == klub)]


@_cache
def ringkas_kpi(df: pd.DataFrame, musim: str | None, klub: str | None = None) -> dict:
    """Enam angka kepala. Untuk liga, hitungannya seluruh laga musim itu.

    `kartu_per_pelanggaran` adalah persentase pelanggaran yang berbuah kartu kuning;
    satu-satunya ukuran disiplin yang berupa rasio, jadi bisa dibandingkan antara
    liga dan klub tanpa terganggu jumlah laga yang berbeda.
    """
    sub = df if musim is None else df[df["musim"] == musim]
    sub = laga_klub(sub, klub)
    pelanggaran = _jumlah(sub, klub, "pelanggaran")
    kartu = _jumlah(sub, klub, "kartu_kuning")
    return {
        "laga": len(sub),
        "gol": _jumlah(sub, klub, "gol"),
        "tembakan": _jumlah(sub, klub, "tembakan"),
        "tembakan_tepat": _jumlah(sub, klub, "tembakan_tepat"),
        "kartu_kuning": kartu,
        "pelanggaran": pelanggaran,
        "kartu_per_pelanggaran": round(100 * kartu / pelanggaran, 1) if pelanggaran else 0.0,
    }


KOLOM_TREN = ["musim", "laga", "gol", "kandang", "tembakan", "kartu", "konversi"]


@_cache
def tren_musim(df: pd.DataFrame, klub: str | None = None) -> pd.DataFrame:
    """Lima ukuran per musim, semuanya per laga supaya musim tak utuh tidak membuat cekungan palsu.

    Tanpa klub: angka liga (gol kedua tim per laga, persen laga dimenangi tuan rumah,
    tembakan dan kartu rata-rata per tim). Dengan klub: angka sisi klub itu saja
    (gol yang ia cetak, persen menang di kandangnya sendiri, tembakan dan kartunya),
    bukan campuran klub dan lawannya.
    """
    baris = []
    for musim, g in df.groupby("musim", sort=True):
        if klub is None:
            n = len(g)
            tembakan = int(g["tembakan_kandang"].sum() + g["tembakan_tandang"].sum())
            gol = int(g["gol_kandang"].sum() + g["gol_tandang"].sum())
            kartu = float(g["kartu_kuning_kandang"].sum() + g["kartu_kuning_tandang"].sum())
            kandang = 100 * float((g["hasil"] == "H").mean())
            pembagi = 2 * n  # tembakan dan kartu dirata-rata per tim
        else:
            k, t = _sisi(g, klub)
            n = len(k) + len(t)
            if n == 0:
                continue
            tembakan = int(k["tembakan_kandang"].sum() + t["tembakan_tandang"].sum())
            gol = int(k["gol_kandang"].sum() + t["gol_tandang"].sum())
            kartu = float(k["kartu_kuning_kandang"].sum() + t["kartu_kuning_tandang"].sum())
            kandang = 100 * float((k["hasil"] == "H").mean()) if len(k) else float("nan")
            pembagi = n
        baris.append({
            "musim": musim,
            "laga": n,
            "gol": round(gol / n, 3),
            "kandang": round(kandang, 2),
            "tembakan": round(tembakan / pembagi, 2),
            "kartu": round(kartu / pembagi, 3),
            "konversi": round(100 * gol / tembakan, 2) if tembakan else 0.0,
        })
    return pd.DataFrame(baris, columns=KOLOM_TREN)


@_cache
def juara(df: pd.DataFrame) -> pd.DataFrame:
    """Jumlah gelar per klub, hanya dari musim yang sudah selesai.

    Musim berjalan dikecualikan: klub di puncak klasemen bulan November belum juara,
    dan memasukkannya akan memberi gelar yang belum tentu terjadi.
    """
    gelar: list[str] = []
    for _, g in df.groupby("musim", sort=True):
        if len(g) < MUSIM_PENUH:
            continue
        papan = klasemen(g)
        gelar.append(papan.iloc[0]["klub"])
    hitung = pd.Series(gelar, dtype=str).value_counts()
    return pd.DataFrame({"klub": hitung.index, "gelar": hitung.to_numpy()})


KOLOM_KLASEMEN = ["klub", "main", "menang", "seri", "kalah",
                  "dicetak", "kebobolan", "selisih", "poin"]


def klasemen(df: pd.DataFrame) -> pd.DataFrame:
    """Klasemen dari potongan laga mana pun, urut poin lalu selisih gol lalu gol.

    Potongan kosong (misalnya klub yang tidak bermain di rentang musim terpilih)
    menghasilkan tabel kosong berkolom lengkap, bukan KeyError saat diurutkan.
    """
    baris = []
    for klub in sorted(set(df["tim_kandang"]) | set(df["tim_tandang"])):
        k, t = _sisi(df, klub)
        menang = int((k["hasil"] == "H").sum() + (t["hasil"] == "A").sum())
        seri = int((k["hasil"] == "D").sum() + (t["hasil"] == "D").sum())
        kalah = int((k["hasil"] == "A").sum() + (t["hasil"] == "H").sum())
        dicetak = int(k["gol_kandang"].sum() + t["gol_tandang"].sum())
        kebobolan = int(k["gol_tandang"].sum() + t["gol_kandang"].sum())
        baris.append({
            "klub": klub, "main": menang + seri + kalah,
            "menang": menang, "seri": seri, "kalah": kalah,
            "dicetak": dicetak, "kebobolan": kebobolan,
            "selisih": dicetak - kebobolan, "poin": menang * 3 + seri,
        })
    papan = pd.DataFrame(baris, columns=KOLOM_KLASEMEN)
    return papan.sort_values(["poin", "selisih", "dicetak"], ascending=False).reset_index(drop=True)


@_cache
def distribusi_gol(df: pd.DataFrame, klub: str | None = None,
                   musim: str | None = None) -> pd.DataFrame:
    """Berapa laga berakhir dengan 0, 1, ... 5, dan 6 gol ke atas."""
    sub = df if musim is None else df[df["musim"] == musim]
    sub = laga_klub(sub, klub)
    total = sub["gol_kandang"] + sub["gol_tandang"]
    baris = []
    for g in range(6):
        n = int((total == g).sum())
        baris.append({"gol": str(g), "laga": n})
    n = int((total >= 6).sum())
    baris.append({"gol": "6+", "laga": n})
    jumlah = len(sub) or 1
    hasil = pd.DataFrame(baris)
    hasil["persen"] = (100 * hasil["laga"] / jumlah).round(1)
    return hasil


@_cache
def proporsi_hasil(df: pd.DataFrame, musim: str | None, klub: str | None = None) -> list[dict]:
    """Tiga irisan donat. Untuk liga: kandang/seri/tandang. Untuk klub: menang/seri/kalah."""
    sub = df if musim is None else df[df["musim"] == musim]
    if klub is None:
        n = len(sub) or 1
        return [
            {"label": "Kandang menang", "nilai": round(100 * float((sub["hasil"] == "H").sum()) / n, 1)},
            {"label": "Seri", "nilai": round(100 * float((sub["hasil"] == "D").sum()) / n, 1)},
            {"label": "Tandang menang", "nilai": round(100 * float((sub["hasil"] == "A").sum()) / n, 1)},
        ]
    papan = klasemen(laga_klub(sub, klub))
    baris = papan[papan["klub"] == klub]
    if baris.empty:
        return [{"label": "Menang", "nilai": 0.0}, {"label": "Seri", "nilai": 0.0},
                {"label": "Kalah", "nilai": 0.0}]
    r = baris.iloc[0]
    n = max(int(r["main"]), 1)
    return [
        {"label": "Menang", "nilai": round(100 * int(r["menang"]) / n, 1)},
        {"label": "Seri", "nilai": round(100 * int(r["seri"]) / n, 1)},
        {"label": "Kalah", "nilai": round(100 * int(r["kalah"]) / n, 1)},
    ]


SUMBU_RADAR = ["Serangan", "Ketajaman", "Pertahanan", "Disiplin", "Bola mati"]


def _profil(df: pd.DataFrame, klub: str) -> dict:
    """Lima ukuran mentah per laga untuk satu klub. Semua dari kolom terisi 100%."""
    k, t = _sisi(df, klub)
    n = max(len(k) + len(t), 1)
    tembakan = int(k["tembakan_kandang"].sum() + t["tembakan_tandang"].sum())
    dicetak = int(k["gol_kandang"].sum() + t["gol_tandang"].sum())
    kebobolan = int(k["gol_tandang"].sum() + t["gol_kandang"].sum())
    kartu = int(k["kartu_kuning_kandang"].sum() + t["kartu_kuning_tandang"].sum())
    pojok = int(k["sepak_pojok_kandang"].sum() + t["sepak_pojok_tandang"].sum())
    return {
        "Serangan": tembakan / n,
        "Ketajaman": (100 * dicetak / tembakan) if tembakan else 0.0,
        # pertahanan dan disiplin dibalik: makin sedikit kebobolan dan kartu, makin tinggi
        "Pertahanan": -kebobolan / n,
        "Disiplin": -kartu / n,
        "Bola mati": pojok / n,
    }


@_cache
def radar(df: pd.DataFrame, musim: str | None, klub: str | None = None) -> list[dict]:
    """Nilai radar 0-1 per sumbu, dinormalkan terhadap sebaran klub di musim itu.

    Tanpa klub, yang dikembalikan adalah rata-rata semua klub di rentang itu.
    Klub yang tidak bermain di rentang itu menghasilkan daftar kosong.
    """
    sub = df if musim is None else df[df["musim"] == musim]
    klub_musim = sorted(set(sub["tim_kandang"]) | set(sub["tim_tandang"]))
    profil = {k: _profil(sub, k) for k in klub_musim}
    if not profil:
        return []

    def skala(sumbu: str, nilai: float) -> float:
        semua = [p[sumbu] for p in profil.values()]
        lo, hi = min(semua), max(semua)
        return round((nilai - lo) / (hi - lo), 3) if hi > lo else 0.5

    rata = {s: sum(p[s] for p in profil.values()) / len(profil) for s in SUMBU_RADAR}
    if klub is not None:
        if klub not in profil:  # klub tidak bermain di rentang ini
            return []
        return [
            {"nama": klub, "sorot": True,
             "nilai": [skala(s, profil[klub][s]) for s in SUMBU_RADAR]},
            {"nama": "Rata-rata liga", "sorot": False,
             "nilai": [skala(s, rata[s]) for s in SUMBU_RADAR]},
        ]
    return [{"nama": "Rata-rata liga", "sorot": True,
             "nilai": [skala(s, rata[s]) for s in SUMBU_RADAR]}]


@_cache
def kpi_tren_per_musim(df: pd.DataFrame, klub: str | None = None) -> dict[str, list[float]]:
    """Nilai KPI per musim untuk sparkline dan delta persen, dinormalisasi per laga."""
    seri: dict[str, list[float]] = {
        "gol_per_laga": [], "efisiensi": [], "akurasi": [], "kartu_per_laga": []
    }
    for _, g in df.groupby("musim", sort=True):
        if klub is not None:
            k, t = _sisi(g, klub)
            n = len(k) + len(t)
            if n == 0:
                continue
            gol = int(k["gol_kandang"].sum() + t["gol_tandang"].sum())
            tmb = int(k["tembakan_kandang"].sum() + t["tembakan_tandang"].sum())
            tpt = int(k["tembakan_tepat_kandang"].sum() + t["tembakan_tepat_tandang"].sum())
            krt = int(k["kartu_kuning_kandang"].sum() + t["kartu_kuning_tandang"].sum())
        else:
            n = len(g)
            gol = int(g["gol_kandang"].sum() + g["gol_tandang"].sum())
            tmb = int(g["tembakan_kandang"].sum() + g["tembakan_tandang"].sum())
            tpt = int(g["tembakan_tepat_kandang"].sum() + g["tembakan_tepat_tandang"].sum())
            krt = int(g["kartu_kuning_kandang"].sum() + g["kartu_kuning_tandang"].sum())
        seri["gol_per_laga"].append(round(gol / n, 3))
        seri["efisiensi"].append(round(100 * gol / tmb, 1) if tmb else 0.0)
        seri["akurasi"].append(round(100 * tpt / tmb, 1) if tmb else 0.0)
        seri["kartu_per_laga"].append(round(krt / n, 3))
    return seri


@_cache
def gol_vs_xg(df: pd.DataFrame) -> pd.DataFrame:
    """Gol aktual terhadap gol harapan per klub, dari kolom xG BBC yang cakupannya terluas.

    Hanya laga yang punya xG di kedua sisi yang dipakai, supaya kedua sumbu diukur
    pada kumpulan laga yang sama persis.
    """
    sub = df[df["xg_bbc_kandang"].notna() & df["xg_bbc_tandang"].notna()]
    baris = []
    for klub in sorted(set(sub["tim_kandang"]) | set(sub["tim_tandang"])):
        k, t = _sisi(sub, klub)
        n = len(k) + len(t)
        if n < 10:  # terlalu sedikit untuk ditempatkan di sebaran
            continue
        gol = float(k["gol_kandang"].sum() + t["gol_tandang"].sum())
        xg = float(k["xg_bbc_kandang"].sum() + t["xg_bbc_tandang"].sum())
        baris.append({"klub": klub, "laga": n,
                      "gol": round(gol / n, 3), "xg": round(xg / n, 3),
                      "selisih": round((gol - xg) / n, 3)})
    if not baris:
        return pd.DataFrame(columns=["klub", "laga", "gol", "xg", "selisih"])
    return pd.DataFrame(baris).sort_values("selisih", ascending=False).reset_index(drop=True)
