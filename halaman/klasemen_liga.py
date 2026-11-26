"""Klasemen liga dipakai Overview dan History: zona kompetisi per musim, form lima laga
(sorot untuk detail, klik untuk membuka laga di Match Analysis), dan lawan berikutnya."""
from html import escape

import pandas as pd
import streamlit as st

from gaya.komponen import logo_kecil
from halaman.history import klasemen
from inti.sesi import AKAR

MUSIM_BERJALAN = "2026/27"
JALUR_JADWAL = AKAR / "pipeline" / "data" / "jadwal_musim.csv"
KODE = {"M": "W", "S": "D", "K": "L"}
BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
# pengurangan poin resmi supaya klasemen sama dengan versi Premier League
POTONGAN = {("2009/10", "Portsmouth"): 9, ("2023/24", "Everton"): 8, ("2023/24", "Nott'm Forest"): 4}
LEGENDA = {"zona-ucl": "Liga Champions", "zona-uel": "Liga Europa",
           "zona-uecl": "Liga Konferensi", "zona-degradasi": "Degradasi ke Championship"}


def zona_musim(musim: str, jumlah_klub: int) -> dict[int, str]:
    """Zona per peringkat, disederhanakan: jatah Liga Champions 4 (5 pada 2024/25),
    lalu satu Liga Europa, satu Liga Konferensi sejak 2021/22, dan tiga terbawah degradasi.
    Jatah sebenarnya bisa bergeser karena juara piala domestik."""
    ucl = 5 if musim == "2024/25" else 4
    zona = {i: "zona-ucl" for i in range(1, ucl + 1)}
    zona[ucl + 1] = "zona-uel"
    if musim >= "2021/22":
        zona[ucl + 2] = "zona-uecl"
    zona.update({i: "zona-degradasi" for i in range(jumlah_klub - 2, jumlah_klub + 1)})
    return zona


def _logo(klub: str) -> str:
    return logo_kecil(klub, "logo-klasemen").replace("<img ", '<img width="20" height="20" ')


def _tgl(t: pd.Timestamp) -> str:
    return f"{t.day} {BULAN[t.month - 1]} {t.year}"


def _form(sub: pd.DataFrame, klub: str) -> str:
    laga = sub[(sub.tim_kandang == klub) | (sub.tim_tandang == klub)].sort_values("tanggal").tail(5)
    kotak = []
    for r in laga.itertuples():
        gs, gl = (r.gol_kandang, r.gol_tandang) if r.tim_kandang == klub else (r.gol_tandang, r.gol_kandang)
        h = "M" if gs > gl else "S" if gs == gl else "K"
        kotak.append(
            f'<a class="form-kotak form-{h}" href="?buka=analisis&laga={r.Index}" target="_self">'
            f'{KODE[h]}<span class="form-info"><small>{_tgl(r.tanggal)}</small>'
            f'<span>{escape(r.tim_kandang)} {_logo(r.tim_kandang)} <b>{int(r.gol_kandang)} - '
            f'{int(r.gol_tandang)}</b> {_logo(r.tim_tandang)} {escape(r.tim_tandang)}</span>'
            f'<small>klik untuk analisis laga</small></span></a>')
    return "".join(kotak)


@st.cache_data
def _lawan_berikut(jalur: str) -> dict:
    try:
        j = pd.read_csv(jalur, parse_dates=["tanggal"])
    except FileNotFoundError:
        return {}
    j = j[(j.musim == MUSIM_BERJALAN) & ~j.sudah_main.astype(str).str.lower().eq("true")]
    berikut = {}
    for r in j.sort_values("tanggal").itertuples():
        berikut.setdefault(r.tim_kandang, (r.tim_tandang, r.tanggal, "kandang"))
        berikut.setdefault(r.tim_tandang, (r.tim_kandang, r.tanggal, "tandang"))
    return berikut


def pilih_musim(df: pd.DataFrame, kunci: str) -> str:
    """Dropdown musim klasemen; bawaannya musim berjalan."""
    daftar = sorted(df.musim.unique(), reverse=True)
    return st.selectbox("Musim klasemen", daftar, key=kunci)


def panel_klasemen(df: pd.DataFrame, musim: str = MUSIM_BERJALAN, sorot: str | None = None,
                   lawan: str | None = None) -> str:
    sub = df[df.musim == musim]
    tabel = klasemen(df, musim)
    for (m, klub), kurang in POTONGAN.items():
        if m == musim:
            tabel.loc[tabel.klub == klub, "poin"] -= kurang
    tabel = tabel.sort_values(["poin", "selisih", "gol_memasukkan", "klub"],
                              ascending=[False, False, False, True], kind="stable").reset_index(drop=True)
    zona = zona_musim(musim, len(tabel))
    berjalan = musim == MUSIM_BERJALAN
    berikut = _lawan_berikut(str(JALUR_JADWAL)) if berjalan else {}

    baris = []
    for i, r in enumerate(tabel.itertuples(), 1):
        sel_lawan = ""
        if berjalan and r.klub in berikut:
            nama, tgl, tempat = berikut[r.klub]
            sel_lawan = (f'<td><span class="form-kotak lawan">{_logo(nama)}<span class="form-info">'
                         f'<small>{_tgl(tgl)}, {tempat}</small><span>{escape(nama)}</span></span></span></td>')
        elif berjalan:
            sel_lawan = "<td></td>"
        kelas = zona.get(i, "") + (" sorot" if r.klub == sorot else "")
        tanda = ' <small class="tanda-lawan">lawan</small>' if r.klub == lawan else ""
        catat = "*" if (musim, r.klub) in POTONGAN else ""
        baris.append(
            f'<tr class="{kelas}"><td>{i}</td><td>{_logo(r.klub)}</td>'
            f'<td>{escape(r.klub)}{tanda}</td><td>{r.main}</td><td>{r.menang}</td>'
            f'<td>{r.seri}</td><td>{r.kalah}</td><td>{r.gol_memasukkan}-{r.gol_kemasukan}</td>'
            f'<td>{r.selisih:+d}</td><td><b>{r.poin}{catat}</b></td>'
            f'<td class="sel-form">{_form(sub, r.klub)}</td>{sel_lawan}</tr>')
    judul = ["#", "", "Klub", "Main", "M", "S", "K", "+/-", "SG", "Poin", "Form"] + (["Berikutnya"] if berjalan else [])
    kepala = "".join(f"<th>{h}</th>" for h in judul)
    dipakai = dict.fromkeys(zona.values())
    legenda = "".join(f'<span class="legenda-kl {k}">{LEGENDA[k]}</span>' for k in LEGENDA if k in dipakai)
    potong = [f"{k} dikurangi {v} poin" for (m, k), v in POTONGAN.items() if m == musim]
    if potong:
        legenda += f'<span class="legenda-catatan">* {", ".join(potong)}</span>'
    status = "sampai " + _tgl(sub.tanggal.max()) if berjalan and len(sub) else "klasemen akhir"
    return (f'<div class="blok klasemen-liga"><div class="blok-judul"><b>Klasemen {musim}</b>'
            f'<span>{status}</span></div>'
            f'<table class="tabel" style="width:100%"><thead><tr>{kepala}</tr></thead>'
            f'<tbody>{"".join(baris)}</tbody></table><div class="legenda-zona">{legenda}</div></div>')
