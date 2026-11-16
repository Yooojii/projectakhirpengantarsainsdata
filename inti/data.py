"""Pemuatan dan deskripsi dataset pertandingan Liga Inggris."""
import pandas as pd

try:
    import streamlit as st
    _cache = st.cache_data
except ImportError:  # modul inti tetap bisa diuji tanpa Streamlit
    def _cache(fungsi):
        return fungsi

KELOMPOK_KOLOM: dict[str, list[str]] = {
    "identitas": [
        "tanggal", "musim", "pekan", "waktu", "tim_kandang", "tim_tandang",
        "wasit", "stadion", "id_apifootball", "statistik_lengkap",
    ],
    "hasil": [
        "gol_kandang", "gol_tandang", "hasil",
        "gol_kandang_babak1", "gol_tandang_babak1",
    ],
    "statistik_dasar": [
        "tembakan_kandang", "tembakan_tandang",
        "tembakan_tepat_kandang", "tembakan_tepat_tandang",
        "pelanggaran_kandang", "pelanggaran_tandang",
        "sepak_pojok_kandang", "sepak_pojok_tandang",
        "kartu_kuning_kandang", "kartu_kuning_tandang",
        "kartu_merah_kandang", "kartu_merah_tandang",
    ],
    "odds": ["odds_kandang", "odds_seri", "odds_tandang"],
    "statistik_lanjutan": [
        # xG musim berjalan (2026/27) dan xG dari API (2024/25) adalah dua
        # keluarga terpisah; cakupannya dilaporkan sendiri-sendiri.
        "xg_kandang", "xg_tandang",
        "xg_api_kandang", "xg_api_tandang",
        "tembakan_melenceng_kandang", "tembakan_melenceng_tandang",
        "tembakan_terblok_kandang", "tembakan_terblok_tandang",
        "tembakan_dalam_kotak_kandang", "tembakan_dalam_kotak_tandang",
        "tembakan_luar_kotak_kandang", "tembakan_luar_kotak_tandang",
        "offside_kandang", "offside_tandang",
        "penguasaan_bola_kandang", "penguasaan_bola_tandang",
        "penyelamatan_kiper_kandang", "penyelamatan_kiper_tandang",
        "umpan_kandang", "umpan_tandang",
        "umpan_akurat_kandang", "umpan_akurat_tandang",
        "akurasi_umpan_kandang", "akurasi_umpan_tandang",
        "gol_dicegah_kandang", "gol_dicegah_tandang",
    ],
}


@_cache
def muat_pertandingan(path: str = "data/liga_inggris_gabungan.csv") -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["tanggal"])
    df = df.sort_values("tanggal", kind="stable").reset_index(drop=True)
    # Pra-pemrosesan: tiga baris sumber mencatat tembakan tepat sasaran lebih
    # banyak daripada total tembakan (Coventry 2000-10-14, Bradford 2001-04-13,
    # West Ham tandang 2021-08-15). Itu mustahil, jadi tembakan tepat dibatasi
    # paling banyak sama dengan total tembakan agar rasio akurasi tidak > 1.
    for sisi in ("kandang", "tandang"):
        df[f"tembakan_tepat_{sisi}"] = df[f"tembakan_tepat_{sisi}"].clip(
            upper=df[f"tembakan_{sisi}"]
        )
    return df


def cakupan_kolom(df: pd.DataFrame) -> pd.DataFrame:
    """Jumlah dan persen baris terisi untuk tiap kolom, per kelompok."""
    baris = []
    for kelompok, kolom_kelompok in KELOMPOK_KOLOM.items():
        for kolom in kolom_kelompok:
            terisi = int(df[kolom].notna().sum())
            baris.append({
                "kelompok": kelompok,
                "kolom": kolom,
                "terisi": terisi,
                "persen": round(100 * terisi / len(df), 1),
            })
    return pd.DataFrame(baris)


def klub_musim(df: pd.DataFrame, musim: str) -> list[str]:
    """Klub yang bermain pada musim tertentu, urut abjad."""
    sub = df[df["musim"] == musim]
    return sorted(set(sub["tim_kandang"]) | set(sub["tim_tandang"]))
