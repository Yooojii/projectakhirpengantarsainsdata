"""Panel Overview untuk musim berjalan: posisi klub di liga, proyeksi simulasi, gol vs xG,
jadwal berikutnya, dan sorotan liga. Angka selalu diberi pembanding (peringkat atau rata-rata liga)."""
from html import escape

import altair as alt
import pandas as pd
import streamlit as st

from gaya.komponen import logo_kecil
from halaman.klasemen_liga import JALUR_JADWAL, MUSIM_BERJALAN, _tgl
from inti.model import prediksi_ensemble
from inti.sesi import AKAR

JALUR_SIMULASI = AKAR / "pipeline" / "data" / "simulasi_juara.csv"
JALUR_PREDIKSI = AKAR / "pipeline" / "data" / "prediksi_laga.csv"
JALUR_KLASTER = AKAR / "data" / "klaster_gaya.csv"


def _koma(v: float, d: int = 2) -> str:
    return f"{v:.{d}f}".replace(".", ",")


def _logo(klub: str) -> str:
    return logo_kecil(klub, "logo-klasemen").replace("<img ", '<img width="20" height="20" ')


def _kartu(judul: str, ket: str, isi: str) -> str:
    return (f'<div class="kartu"><div class="judul">{escape(judul)}</div>'
            f'<div class="ket">{escape(ket)}</div><div class="isi"><div class="ov-isi">{isi}</div></div></div>')


@st.cache_data
def _baca(jalur: str, tanggal: bool = False) -> pd.DataFrame:
    try:
        return pd.read_csv(jalur, low_memory=False, parse_dates=["tanggal"] if tanggal else None)
    except FileNotFoundError:
        return pd.DataFrame()


def _xg(sub: pd.DataFrame, sisi: str) -> pd.Series:
    asli = sub[f"xg_{sisi}"] if f"xg_{sisi}" in sub else pd.Series(index=sub.index, dtype=float)
    api = sub[f"xg_api_{sisi}"] if f"xg_api_{sisi}" in sub else pd.Series(index=sub.index, dtype=float)
    return asli.fillna(api)


def tabel_klub(df: pd.DataFrame) -> pd.DataFrame:
    """Satu baris per klub musim berjalan: angka per laga untuk KPI dan peringkatnya."""
    sub = df[df.musim == MUSIM_BERJALAN]
    potong = []
    for sisi, lawan in (("kandang", "tandang"), ("tandang", "kandang")):
        potong.append(pd.DataFrame({
            "klub": sub[f"tim_{sisi}"], "gol": sub[f"gol_{sisi}"], "kebobolan": sub[f"gol_{lawan}"],
            "xg": _xg(sub, sisi), "penguasaan": sub.get(f"penguasaan_bola_{sisi}")}))
    return pd.concat(potong).groupby("klub").agg(
        main=("gol", "size"), gol=("gol", "mean"), kebobolan=("kebobolan", "mean"),
        xg=("xg", "mean"), penguasaan=("penguasaan", "mean"),
        total_gol=("gol", "sum"), total_xg=("xg", lambda s: s.sum(min_count=1)))


def kepala_klub(df: pd.DataFrame, klub: str) -> str:
    from halaman.history import klasemen
    from halaman.klasemen_liga import _form
    papan = klasemen(df, MUSIM_BERJALAN)
    if klub not in set(papan.klub):
        return ""
    pos = int(papan.index[papan.klub == klub][0]) + 1
    r = papan[papan.klub == klub].iloc[0]
    k = _baca(str(JALUR_KLASTER))
    kat = k[(k.musim == MUSIM_BERJALAN) & (k.klub == klub)].kategori if not k.empty else []
    gaya = f'<span class="ov-chip">{escape(kat.iloc[0])}</span>' if len(kat) else ""
    form = _form(df[df.musim == MUSIM_BERJALAN], klub)
    return (f'<div class="ov-kepala-klub"><span class="ov-pos">{pos}</span>'
            f'<span>Peringkat <b>{pos}</b> · <b>{r.poin}</b> poin · {r.main} laga</span>{gaya}<span class="ov-form">{form}</span></div>')


def kpi_klub(df: pd.DataFrame, klub: str) -> str:
    t = tabel_klub(df)
    if klub not in t.index:
        return ""
    r, n = t.loc[klub], len(t)
    sel = [("Gol per laga", "gol", False, 2, ""), ("Kebobolan per laga", "kebobolan", True, 2, ""),
           ("xG per laga", "xg", False, 2, ""), ("Penguasaan bola", "penguasaan", False, 1, "%")]
    bagian = []
    for label, kol, kecil, d, akhir in sel:
        if pd.isna(r[kol]):
            continue
        rank = int(t[kol].rank(ascending=kecil, method="min")[klub])
        kelas = "atas" if rank <= 4 else "bawah" if rank > n - 4 else ""
        bagian.append(
            f'<div class="kpi-sel kpi-lengkap"><div class="label">{label}</div><div class="kpi-baris">'
            f'<div class="nilai">{_koma(r[kol], d)}<small>{akhir}</small></div>'
            f'<div class="kpi-peringkat {kelas}">ke-{rank}<small> dari {n}</small></div></div>'
            f'<div class="kpi-liga">liga {_koma(t[kol].mean(), d)}{akhir}</div></div>')
    return '<div class="kpi">' + "".join(bagian) + "</div>"


def proyeksi_klub(klub: str) -> str:
    s = _baca(str(JALUR_SIMULASI))
    if s.empty or klub not in set(s.tim):
        return _kartu("Proyeksi akhir musim", "", '<div class="kartu-kosong">Belum ada simulasi.</div>')
    r = s[s.tim == klub].iloc[0]
    bar = "".join(
        f'<div class="ov-bar"><span>{label}</span><div><i style="width:{100 * v:.1f}%"></i></div>'
        f'<b>{round(100 * v)}%</b></div>'
        for label, v in [("Juara", r.peluang_juara), ("Empat besar", r.peluang_empat_besar),
                         ("Degradasi", r.peluang_degradasi)])
    bawah, atas = int(r.posisi_rata_rata), -int(-r.posisi_rata_rata // 1)
    posisi = f"{bawah}–{atas}" if atas != bawah else f"{bawah}"
    isi = (bar + f'<div class="ov-poin">Perkiraan poin akhir: <b>{round(r.poin_harapan)}</b> · '
           f'Perkiraan posisi: <b>{posisi}</b></div>')
    return _kartu("Proyeksi akhir musim", "Berdasarkan simulasi sisa musim", isi)


def gol_vs_xg(df: pd.DataFrame, klub: str) -> None:
    sub = df[(df.musim == MUSIM_BERJALAN) & ((df.tim_kandang == klub) | (df.tim_tandang == klub))]
    sub = sub.sort_values("tanggal")
    if sub.empty:
        return
    kandang = sub.tim_kandang == klub
    d = pd.DataFrame({"laga": range(1, len(sub) + 1),
                      "Gol": sub.gol_kandang.where(kandang, sub.gol_tandang).cumsum().to_numpy(),
                      "xG": _xg(sub, "kandang").where(kandang, _xg(sub, "tandang")).cumsum().to_numpy()})
    if d.xG.isna().all():
        return
    selisih = d.Gol.iloc[-1] - d.xG.iloc[-1]
    nada = (" · Lebih tajam dari xG-nya" if selisih > 1.5
            else " · Banyak peluang terbuang" if selisih < -1.5 else "")
    st.markdown(f'<div class="ov-judul-grafik"><b>Gol vs xG kumulatif</b>'
                f'<span>{int(d.Gol.iloc[-1])} gol dari xG {_koma(d.xG.iloc[-1], 1)}{nada}</span></div>', unsafe_allow_html=True)
    panjang = d.melt("laga", var_name="seri", value_name="nilai")
    grafik = alt.Chart(panjang).mark_line(point=True, strokeWidth=2.5).encode(
        x=alt.X("laga:Q", title="Laga ke-", axis=alt.Axis(tickMinStep=1)),
        y=alt.Y("nilai:Q", title=None),
        color=alt.Color("seri:N", title=None, scale=alt.Scale(domain=["Gol", "xG"], range=["#0F766E", "#94A3B8"]),
                        legend=alt.Legend(orient="top-left")),
        strokeDash=alt.StrokeDash("seri:N", legend=None,
                                  scale=alt.Scale(domain=["Gol", "xG"], range=[[1, 0], [5, 4]])),
        tooltip=["laga", "seri", alt.Tooltip("nilai:Q", format=".1f")]).properties(height=220)
    st.altair_chart(grafik, use_container_width=True)


def laga_berikut(klub: str, n: int = 5) -> str:
    j = _baca(str(JALUR_JADWAL), tanggal=True)
    if j.empty:
        return ""
    j = j[(j.musim == MUSIM_BERJALAN) & ~j.sudah_main.astype(str).str.lower().eq("true")
          & ((j.tim_kandang == klub) | (j.tim_tandang == klub))].sort_values("tanggal").head(n)
    baris, total = [], 0.0
    for r in j.itertuples():
        kandang = r.tim_kandang == klub
        lawan = r.tim_tandang if kandang else r.tim_kandang
        p = prediksi_ensemble(r.tim_kandang, r.tim_tandang)
        peluang = ""
        if p:
            m = p["p_menang_kandang"] if kandang else p["p_menang_tandang"]
            k = p["p_menang_tandang"] if kandang else p["p_menang_kandang"]
            s = p["p_seri"]
            total += 3 * m + s
            peluang = (f'<span class="ov-mini" title="menang {round(100 * m)}%, seri {round(100 * s)}%, '
                       f'kalah {round(100 * k)}%"><i class="form-M" style="flex:{m:.3f}"></i>'
                       f'<i class="form-S" style="flex:{s:.3f}"></i><i class="form-K" style="flex:{k:.3f}"></i>'
                       f'</span><b>{round(100 * m)}%</b>')
        baris.append(f'<div class="ov-jadwal"><small>{_tgl(r.tanggal)}</small>'
                     f'<span>{_logo(lawan)} {escape(lawan)} '
                     f'<em class="{"di-kandang" if kandang else "di-tandang"}">{"Kandang" if kandang else "Tandang"}</em>'
                     f'</span>{peluang}</div>')
    if not baris:
        return ""
    kepala = '<div class="ov-jadwal ov-jadwal-kepala"><span></span><b>Menang</b></div>'
    return _kartu(f"{len(baris)} laga berikutnya", f"Perkiraan {round(total)} poin", kepala + "".join(baris))


# ---------------------------------------------------------------- tampilan liga

def perburuan() -> str:
    s = _baca(str(JALUR_SIMULASI))
    if s.empty:
        return ""
    kartu = []
    for judul, kol in [("Perburuan gelar", "peluang_juara"), ("Perburuan empat besar", "peluang_empat_besar"),
                       ("Ancaman degradasi", "peluang_degradasi")]:
        top = s.sort_values(kol, ascending=False).head(5)
        isi = "".join(
            f'<div class="ov-bar"><span>{_logo(r.tim)} {escape(r.tim)}</span>'
            f'<div><i style="width:{100 * getattr(r, kol):.1f}%"></i></div>'
            f'<b>{round(100 * getattr(r, kol))}%</b></div>' for r in top.itertuples())
        kartu.append(_kartu(judul, "", isi))
    return '<div class="ov-tiga">' + "".join(kartu) + "</div>"


def tajam_boros(df: pd.DataFrame) -> str:
    t = tabel_klub(df)
    t = t[t.total_xg.notna()].copy()
    if t.empty:
        return ""
    t["selisih"] = t.total_gol - t.total_xg
    urut = t.selisih.sort_values(ascending=False)

    def daftar(bagian: pd.Series) -> str:
        return "".join(f'<div class="ov-jadwal"><span>{_logo(k)} {escape(k)}</span>'
                       f'<b>{"+" if v > 0 else ""}{_koma(v, 1)}</b></div>' for k, v in bagian.items())
    isi = (f'<div class="ov-dua"><div><small>Gol di atas xG</small>{daftar(urut.head(5))}</div>'
           f'<div><small>Gol di bawah xG</small>{daftar(urut.tail(5)[::-1])}</div></div>')
    return _kartu("Paling tajam vs paling boros", "Gol dibanding xG", isi)


def sorotan_pekan() -> str:
    p = _baca(str(JALUR_PREDIKSI))
    if p.empty:
        return ""
    p = p[(p.musim == MUSIM_BERJALAN) & p.sudah_main.astype(str).str.lower().eq("true") & p.peluang_seri.notna()]
    if p.empty:
        return ""
    pekan = p.pekan.max()
    p = p[p.pekan == pekan].copy()
    kol = {"H": "peluang_menang_kandang", "D": "peluang_seri", "A": "peluang_menang_tandang"}
    p["peluang_hasil"] = [r[kol[r.hasil]] for _, r in p.iterrows()]
    p["total_gol"] = p.gol_kandang + p.gol_tandang
    kejutan = p.sort_values("peluang_hasil").iloc[0]
    seru = p.sort_values("total_gol", ascending=False).iloc[0]

    def laga(r) -> str:
        return (f'{_logo(r.tim_kandang)} {escape(r.tim_kandang)} <b>{int(r.gol_kandang)}-{int(r.gol_tandang)}</b> '
                f'{escape(r.tim_tandang)} {_logo(r.tim_tandang)}')
    isi = (f'<div class="ov-sorot"><small>Kejutan terbesar</small><div>{laga(kejutan)}</div>'
           f'<em>Peluang menurut model: {round(100 * kejutan.peluang_hasil)}%</em></div>'
           f'<div class="ov-sorot"><small>Laga paling banyak gol</small><div>{laga(seru)}</div>'
           f'<em>{int(seru.total_gol)} gol</em></div>')
    return _kartu(f"Sorotan pekan {int(pekan)}", "", isi)
