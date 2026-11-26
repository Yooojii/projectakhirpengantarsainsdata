"""Klasemen musim berjalan untuk Overview: zona kompetisi, form lima laga dengan detail, dan lawan berikutnya."""
from html import escape

import pandas as pd

from gaya.komponen import logo_kecil
from halaman.history import klasemen
from inti.sesi import AKAR

MUSIM = "2026/27"
JALUR_JADWAL = AKAR / "pipeline" / "data" / "jadwal_musim.csv"
ZONA = [  # (peringkat, kelas, keterangan)
    (range(1, 5), "zona-ucl", "Liga Champions"),
    (range(5, 6), "zona-uel", "Liga Europa"),
    (range(6, 7), "zona-uecl", "Liga Konferensi"),
    (range(18, 21), "zona-degradasi", "Degradasi ke Championship"),
]
KODE = {"M": "W", "S": "D", "K": "L"}
BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def _logo(klub: str) -> str:
    return logo_kecil(klub).replace("<img ", '<img style="width:18px;min-width:18px;height:18px" ')


def _form(sub: pd.DataFrame, klub: str) -> str:
    laga = sub[(sub.tim_kandang == klub) | (sub.tim_tandang == klub)].sort_values("tanggal").tail(5)
    kotak = []
    for i, r in enumerate(laga.itertuples()):
        gs, gl = (r.gol_kandang, r.gol_tandang) if r.tim_kandang == klub else (r.gol_tandang, r.gol_kandang)
        h = "M" if gs > gl else "S" if gs == gl else "K"
        tgl = f"{r.tanggal.day} {BULAN[r.tanggal.month - 1]}"
        terbaru = " terbaru" if i == len(laga) - 1 else ""
        kotak.append(
            f'<span class="form-kotak form-{h}{terbaru}">{KODE[h]}<span class="form-info">'
            f'<small>{tgl}</small><span>{escape(r.tim_kandang)} {_logo(r.tim_kandang)} '
            f'<b>{int(r.gol_kandang)} - {int(r.gol_tandang)}</b> {_logo(r.tim_tandang)} '
            f'{escape(r.tim_tandang)}</span></span></span>')
    return "".join(kotak)


def _lawan_berikut() -> dict:
    try:
        j = pd.read_csv(JALUR_JADWAL, parse_dates=["tanggal"])
    except FileNotFoundError:
        return {}
    j = j[(j.musim == MUSIM) & ~j.sudah_main.astype(str).str.lower().eq("true")].sort_values("tanggal")
    berikut = {}
    for r in j.itertuples():
        berikut.setdefault(r.tim_kandang, (r.tim_tandang, r.tanggal, "kandang"))
        berikut.setdefault(r.tim_tandang, (r.tim_kandang, r.tanggal, "tandang"))
    return berikut


def panel_klasemen(df: pd.DataFrame, sorot: str | None = None) -> str:
    sub = df[df.musim == MUSIM]
    tabel = klasemen(df, MUSIM)
    berikut = _lawan_berikut()
    baris = []
    for i, r in enumerate(tabel.itertuples(), 1):
        zona = next((k for rg, k, _ in ZONA if i in rg), "")
        lawan = berikut.get(r.klub)
        sel_lawan = (f'<span class="form-kotak lawan">{_logo(lawan[0])}<span class="form-info">'
                     f'<small>{lawan[1].day} {BULAN[lawan[1].month - 1]}, {lawan[2]}</small>'
                     f'<span>{escape(lawan[0])}</span></span></span>') if lawan else ""
        kelas = f'{zona}{" sorot" if r.klub == sorot else ""}'
        baris.append(
            f'<tr class="{kelas}"><td>{i}</td><td>{_logo(r.klub)}</td>'
            f'<td style="text-align:left">{escape(r.klub)}</td><td>{r.main}</td><td>{r.menang}</td>'
            f'<td>{r.seri}</td><td>{r.kalah}</td><td>{r.gol_memasukkan}-{r.gol_kemasukan}</td>'
            f'<td>{r.selisih:+d}</td><td><b>{r.poin}</b></td>'
            f'<td class="sel-form">{_form(sub, r.klub)}</td><td>{sel_lawan}</td></tr>')
    kepala = "".join(f"<th>{h}</th>" for h in
                     ["#", "", "Klub", "Main", "M", "S", "K", "+/-", "SG", "Poin", "Form", "Berikutnya"])
    legenda = "".join(f'<span class="legenda {k}">{t}</span>' for _, k, t in ZONA)
    return (f'<div class="blok klasemen-liga"><div class="blok-judul"><b>Klasemen {MUSIM}</b></div>'
            f'<table class="tabel" style="width:100%"><thead><tr>{kepala}</tr></thead>'
            f'<tbody>{"".join(baris)}</tbody></table><div class="legenda-zona">{legenda}</div></div>')
