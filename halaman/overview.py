"""Halaman Overview: papan ringkas satu layar untuk liga, menyempit ke satu klub bila difilter."""
from html import escape

import altair as alt
import pandas as pd
import streamlit as st

from gaya import panel
from gaya.komponen import _uri_logo, angka_hitung, warna_aksen
from inti.data import KELOMPOK_KOLOM, muat_pertandingan
from inti.klub import logo_klub, singkatan, warna_klub
from inti.liga import (
    distribusi_gol,
    juara,
    kandang_tandang,
    kpi_tren_per_musim,
    laga_klub,
    proporsi_hasil,
    radar,
    ringkas_kpi,
    SUMBU_RADAR,
    tren_musim,
)
from inti.sesi import JALUR_DATA

SEMUA = "Semua klub"
# isi kotak kosong di tiap panel; penjelasan lengkapnya ada di pemberitahuan di atas KPI
PESAN_KOSONG = "Tidak ada laga di rentang ini."


def _angka(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _koma(v: float, desimal: int = 1) -> str:
    """Angka desimal bergaya Indonesia: koma sebagai pemisah pecahan."""
    return f"{v:.{desimal}f}".replace(".", ",")

# nama kolom di tren_musim -> label pilihan, satuan untuk liga, satuan untuk satu klub
METRIK = [
    ("tembakan", "Tembakan", "tembakan di liga per laga", "tembakan per laga"),
    ("poin", "Poin per Laga", "poin di liga per laga", "poin per laga"),
    ("pelanggaran", "Pelanggaran", "pelanggaran di liga per laga", "pelanggaran per laga"),
    ("pojok", "Sepak Pojok", "sepak pojok di liga per laga", "sepak pojok per laga"),
]
# metrik yang membaik saat angkanya turun; warnanya dibalik seperti kartu kuning di KPI
LEBIH_BAIK_TURUN = {"pelanggaran"}
MERAH_TURUN = "#B91C1C"  # sama dengan delta turun di kartu KPI
FORMAT_METRIK = {"tembakan": ".1f", "poin": ".2f",
                 "pelanggaran": ".1f", "pojok": ".1f"}
# angka di grafik Altair memakai koma desimal, sama seperti KPI
LOKAL_ID = {"number": {"decimal": ",", "thousands": ".", "grouping": [3], "currency": ["Rp", ""]}}


def _musim_awal(df: pd.DataFrame, kolom: str) -> str:
    musim = df.loc[df[kolom].notna(), "musim"]
    return str(musim.min()) if not musim.empty else "-"


def tabel_kelengkapan(df: pd.DataFrame) -> pd.DataFrame:
    """Tabel kelengkapan kolom per kelompok beserta status dan alasannya untuk model.

    Angka di dalam alasan (jumlah laga, musim awal odds dan xG) dihitung dari data,
    supaya tidak basi ketika CSV hasil scraping diperbarui.
    """
    cakupan = {k: round(100.0 * float(df[v].notna().to_numpy().mean()), 1)
               for k, v in KELOMPOK_KOLOM.items()}
    laga = _angka(len(df))
    dasar = (f"terisi {_koma(cakupan['statistik_dasar'])}% pada seluruh {laga} pertandingan"
             + (" tanpa data bolong." if cakupan["statistik_dasar"] == 100.0 else "."))
    alasan_dict = {
        "identitas": (
            "Hanya penanda identitas laga, jadwal, wasit, dan pemisah temporal; "
            "bukan fitur masukan model."
        ),
        "hasil": (
            "Target label klasifikasi (menang/seri/kalah) dan skor aktual; "
            "bukan variabel prediktor."
        ),
        "statistik_dasar": f"Fitur utama agregasi 10 laga terakhir, {dasar}",
        "odds": (
            f"Hanya tersedia untuk laga lampau (sejak {_musim_awal(df, 'odds_kandang')}); "
            "dilarang sebagai fitur agar model dapat memprediksi laga mendatang."
        ),
        "statistik_lanjutan": (
            f"Cakupan tipis ({_koma(cakupan['statistik_lanjutan'])}% sel terisi; statistik "
            f"lanjutan baru ada sejak {_musim_awal(df, 'tembakan_melenceng_kandang')}, xG sejak "
            f"{_musim_awal(df, 'xg_bbc_kandang')}); dilarang sebagai fitur agar model tidak "
            "belajar dari data bolong."
        ),
    }

    baris = []
    for kelompok in KELOMPOK_KOLOM:
        dipakai = kelompok == "statistik_dasar"
        baris.append({
            "kelompok": kelompok,
            "cakupan": cakupan[kelompok],
            "dipakai_model": dipakai,
            "alasan": alasan_dict[kelompok],
        })
    df_res = pd.DataFrame(baris)
    df_res["dipakai_model"] = df_res["dipakai_model"].astype(object)
    return df_res


# ---------------------------------------------------------------- potongan HTML


def _delta_badge(seri: list[float], lebih_baik_naik: bool = True) -> tuple[str, bool | None]:
    """Hitung delta persen antara musim terakhir dan sebelumnya; kembalikan (badge_html, naik)."""
    if len(seri) < 2 or seri[-2] == 0:
        return "", None
    pct = (seri[-1] - seri[-2]) / abs(seri[-2]) * 100
    naik_metrik = pct > 0
    naik_visual = naik_metrik if lebih_baik_naik else not naik_metrik
    kelas = "naik" if naik_visual else "turun"
    panah = "▲" if naik_metrik else "▼"
    teks = f"{panah} {_koma(abs(pct))}%"
    return f'<span class="kpi-delta {kelas}">{teks}</span>', naik_visual


def _kpi(ringkas: dict, tren: dict[str, list[float]]) -> str:
    if ringkas["laga"] == 0:
        label = ["Gol per Laga", "Efisiensi Tembakan", "Akurasi Tembakan", "Kartu Kuning per Laga"]
        return '<div class="kpi">' + "".join(
            f'<div class="kpi-sel"><div class="label">{escape(teks)}</div>'
            f'<div class="nilai">-</div></div>' for teks in label
        ) + "</div>"

    n = max(ringkas["laga"], 1)
    gol_pl = ringkas["gol"] / n
    efisiensi = 100 * ringkas["gol"] / ringkas["tembakan"] if ringkas["tembakan"] else 0.0
    akurasi = 100 * ringkas["tembakan_tepat"] / ringkas["tembakan"] if ringkas["tembakan"] else 0.0
    krt_pl = ringkas["kartu_kuning"] / n

    # (label, nilai_html, kunci_tren, lebih_baik_naik)
    sel = [
        ("Gol per Laga",          angka_hitung(gol_pl, 2),                       "gol_per_laga",   True),
        ("Efisiensi Tembakan",    angka_hitung(efisiensi, 1) + "<small>%</small>", "efisiensi",      True),
        ("Akurasi Tembakan",      angka_hitung(akurasi, 1) + "<small>%</small>",   "akurasi",        True),
        ("Kartu Kuning per Laga", angka_hitung(krt_pl, 2),                       "kartu_per_laga", False),
    ]
    bagian = []
    for label, nilai_html, kunci, lebih_baik_naik in sel:
        seri = tren.get(kunci, [])
        badge, naik = _delta_badge(seri, lebih_baik_naik) if seri else ("", None)
        spark = panel.garis_mini(seri, naik) if len(seri) >= 2 else ""
        meta = f'<div class="kpi-meta">{spark}{badge}</div>' if (spark or badge) else ""
        bagian.append(
            f'<div class="kpi-sel">'
            f'<div class="label">{escape(label)}</div>'
            f'<div class="kpi-baris">'
            f'<div class="nilai">{nilai_html}</div>'
            f'{meta}'
            f'</div>'
            f'</div>'
        )
    return '<div class="kpi">' + "".join(bagian) + "</div>"


def _lencana_besar(klub: str | None, aksen: str = "") -> str:
    """Logo klub terpilih, atau logo Premier League untuk cakupan seluruh liga."""
    if klub is None:
        logo_liga = JALUR_DATA.parent / "premier league logo.png"
        if logo_liga.is_file():
            gambar = f'<img class="logo-kompetisi" src="{_uri_logo(str(logo_liga))}" alt="Premier League">'
        else:
            gambar = '<span class="kode">PL</span>'
        return f'<div class="lencana-besar">{gambar}</div>'
    jalur = logo_klub(klub)
    if jalur is not None:
        gambar = f'<img src="{_uri_logo(str(jalur))}" alt="{escape(klub)}">'
    else:
        warna = f'style="border-color:{aksen};color:{aksen}"' if aksen else ""
        gambar = f'<span class="kode" {warna}>{escape(singkatan(klub))}</span>'
    return f'<div class="lencana-besar">{gambar}</div>'


def _kosong(teks: str) -> str:
    return f'<div class="kartu-kosong">{escape(teks)}</div>'


def _kartu(judul: str, ket: str, isi: str) -> str:
    return (f'<div class="kartu"><div class="judul">{escape(judul)}</div>'
            f'<div class="ket">{escape(ket)}</div><div class="isi">{isi}</div></div>')


def _panel_radar(df: pd.DataFrame, klub: str | None, musim: str | None, aksen: str) -> str:
    seri = radar(df, musim, klub)
    if not seri:
        return _kartu("Profil Performa", "", _kosong(PESAN_KOSONG))
    grafik = panel.radar(seri, SUMBU_RADAR, aksen)
    if klub is None:
        ket_html = '<div class="ket">Premier League</div>'
        kaki = (f'<div class="radar-kaki">'
                f'<span><i style="background:{aksen}"></i>Premier League</span></div>')
    else:
        ket_html = f'<div class="ket">{escape(klub)} dibanding Premier League</div>'
        kaki = (f'<div class="radar-kaki">'
                f'<span><i style="background:{aksen}"></i>{escape(klub)}</span>'
                f'<span><i style="background:{panel.KABUT}"></i>Premier League</span></div>')
    isi = (f'<div class="radar-isi">{_lencana_besar(klub, aksen)}'
           f'<div class="radar-grafik">{grafik}</div></div>')
    return (f'<div class="kartu"><div class="judul">Profil Performa</div>'
            f'{ket_html}'
            f'<div class="isi">{isi}</div>{kaki}</div>')


def _panel_tren(df: pd.DataFrame, klub: str | None) -> None:
    with st.container(key="panel-tren"):
        _isi_panel_tren(df, klub)


def _isi_panel_tren(df: pd.DataFrame, klub: str | None) -> None:
    """Grafik tren interaktif; rentang musim mengikuti filter global dashboard."""
    tren = tren_musim(laga_klub(df, klub), klub)
    judul_tren = "Tren Liga" if klub is None else f"Tren {escape(klub)}"
    if tren.empty:
        st.markdown(f'<div class="judul-tren">{judul_tren}</div>{_kosong(PESAN_KOSONG)}',
                    unsafe_allow_html=True)
        return

    n_musim = tren["musim"].nunique()

    kolom_judul, kolom_metrik = st.columns([2, 1], vertical_alignment="top")
    label_metrik = [m[1] for m in METRIK]
    # pilihan lama dari sesi (mis. "Gol" sebelum daftar diganti) kembali ke metrik pertama
    if st.session_state.get("tren_metrik") not in label_metrik:
        st.session_state["tren_metrik"] = label_metrik[0]
    with kolom_metrik:
        label_terpilih = st.selectbox(
            "Metrik", label_metrik, key="tren_metrik",
            label_visibility="collapsed",
        )
    metrik = next(item for item in METRIK if item[1] == label_terpilih)
    kolom, _, satuan_liga, satuan_klub = metrik
    satuan = satuan_liga if klub is None else satuan_klub
    format_angka = FORMAT_METRIK[kolom]

    pilihan = tren.dropna(subset=[kolom]).copy()
    pilihan["musim"] = pilihan["musim"].astype(str)
    pilihan["tahun"] = pilihan["musim"].str.slice(0, 4)
    # aturan sama dengan KPI: musim terakhir dibanding musim sebelumnya
    lencana, membaik = _delta_badge(pilihan[kolom].tolist(), kolom not in LEBIH_BAIK_TURUN)
    warna = MERAH_TURUN if membaik is False else panel.TEAL
    with kolom_judul:
        # satuan pindah ke subjudul, jadi sumbu Y tidak perlu judul miring
        st.markdown(
            f'<div class="judul-tren"><span class="judul-baris">{judul_tren}{lencana}</span>'
            f'<span class="sub-tren" title="{n_musim} musim, {escape(satuan)}">'
            f'{n_musim} musim, {escape(satuan)}</span></div>',
            unsafe_allow_html=True,
        )
    if pilihan.empty:
        st.info("Tidak ada musim pada rentang yang dipilih.")
        return

    st.vega_lite_chart(_spek_tren(pilihan, kolom, satuan, format_angka, warna),
                       width="stretch", theme=None)


@st.cache_data(show_spinner=False, max_entries=64)
def _spek_tren(data: pd.DataFrame, kolom: str, satuan: str, format_angka: str, warna: str) -> dict:
    """Spesifikasi Vega-Lite grafik tren; dihitung sekali untuk tiap kombinasi filter."""
    return grafik_tren(data, kolom, satuan, format_angka, warna).to_dict()


def grafik_tren(data: pd.DataFrame, kolom: str, satuan: str, format_angka: str,
                warna: str = panel.TEAL) -> alt.LayerChart:
    """Garis tren halus dengan area memudar, garis bidik saat kursor bergerak, dan label nilai terakhir.

    `data` berisi kolom `tahun` (string awal musim), `musim`, `laga`, dan `kolom`.
    `warna` dipakai garis, area, dan titik; merah bila tren memburuk.
    """
    r, g_, b = (int(warna[i:i + 2], 16) for i in (1, 3, 5))
    tahun = data["tahun"].tolist()
    jarak = max(1, -(-(len(tahun) - 1) // 5))  # paling banyak sekitar enam label tahun
    tanda = tahun[::jarak]
    if tanda[-1] != tahun[-1]:
        if len(tanda) > 1 and tahun.index(tahun[-1]) - tahun.index(tanda[-1]) < jarak / 2:
            tanda[-1] = tahun[-1]  # label terakhir terlalu dekat: ganti, jangan bertumpuk
        else:
            tanda.append(tahun[-1])

    x = alt.X("tahun:O", title=None, sort=tahun, scale=alt.Scale(domain=tahun, paddingOuter=0.1),
              # tinggi area label X dikunci supaya sumbu X selalu di posisi yang sama
              axis=alt.Axis(values=tanda, labelAngle=0, domain=False, ticks=False,
                            labelPadding=8, grid=False, minExtent=24, maxExtent=24))
    # sumbu Y selalu mulai dari 0 supaya besar perubahan tidak terlihat berlebihan
    y = alt.Y(f"{kolom}:Q", title=None, stack=None, scale=alt.Scale(zero=True, nice=True),
              # lebar area label Y dikunci: "0,0", "10,0", dan "0,00" tidak lagi menggeser sumbu
              axis=alt.Axis(format=format_angka, domain=False, ticks=False, tickCount=4,
                            minExtent=40, maxExtent=40,
                            labelPadding=8, grid=True, gridColor="#E1E6DF", gridDash=[3, 4]))
    dasar = alt.Chart(data).encode(x=x, y=y)
    bidik = alt.selection_point(fields=["tahun"], nearest=True, on="pointerover",
                                clear="pointerout", empty=False)

    area = dasar.mark_area(
        interpolate="monotone", clip=True,
        color=alt.Gradient(gradient="linear", x1=1, x2=1, y1=1, y2=0, stops=[
            alt.GradientStop(color=f"rgba({r},{g_},{b},0)", offset=0),
            alt.GradientStop(color=f"rgba({r},{g_},{b},0.24)", offset=1),
        ]),
    )
    garis = dasar.mark_line(interpolate="monotone", color=warna, strokeWidth=2.5,
                            strokeCap="round", strokeJoin="round")
    # titik tak terlihat selebar kolom: penangkap kursor dan pembawa tooltip
    penangkap = dasar.mark_point(size=400, opacity=0).encode(
        tooltip=[alt.Tooltip("musim:N", title="Musim"),
                 alt.Tooltip(f"{kolom}:Q", title=satuan, format=format_angka),
                 alt.Tooltip("laga:Q", title="Laga")],
    ).add_params(bidik)
    garis_bidik = alt.Chart(data).mark_rule(color=panel.KABUT, strokeWidth=1, strokeDash=[4, 4]).encode(
        x=x).transform_filter(bidik)
    titik_bidik = dasar.mark_point(filled=True, fill="#FFFFFF", stroke=warna, strokeWidth=2.5,
                                   size=90, opacity=1).transform_filter(bidik)

    akhir = data.tail(1)
    halo = alt.Chart(akhir).mark_point(filled=True, color=warna, size=320, opacity=0.15).encode(x=x, y=y)
    titik_akhir = alt.Chart(akhir).mark_point(filled=True, color=warna, size=64, opacity=1).encode(x=x, y=y)
    label_akhir = alt.Chart(akhir).mark_text(
        # di bawah titik: garis datang dari kiri atas, jadi label di atas tertimpa garis
        align="right", baseline="top", dx=-8, dy=8, font="IBM Plex Sans Condensed", fontSize=13,
        fontWeight=600, color=panel.NAVY,
    ).encode(x=x, y=y, text=alt.Text(f"{kolom}:Q", format=format_angka))

    return (
        alt.layer(area, garis, garis_bidik, halo, titik_akhir, label_akhir, titik_bidik, penangkap)
        .properties(height=208, background="transparent",  # mengisi kotak 290px sampai jarak tepi bawah
                    padding={"left": 4, "right": 12, "top": 12, "bottom": 4})
        .configure(background="transparent", locale=LOKAL_ID)
        .configure_view(fill="transparent", stroke=None)
        .configure_axis(labelColor=panel.KABUT, labelFont="IBM Plex Sans Condensed",
                        labelFontSize=12)
    )


def _panel_kandang(df: pd.DataFrame, klub: str | None, aksen: str) -> str:
    """Kandang dibanding tandang: liga dari sisi tuan rumah dan tamu, klub dari sisinya sendiri."""
    judul = "Kandang vs Tandang"
    baris = kandang_tandang(df, klub)
    if not baris:
        return _kartu(judul, "", _kosong(PESAN_KOSONG))
    poin = next(b for b in baris if b["label"] == "Poin per laga")
    pk, pt = _koma(poin["kandang"], 2), _koma(poin["tandang"], 2)
    if klub is None:
        ket = f"Tuan rumah meraih {pk} poin per laga, tamu {pt}"
    else:
        ket = f"{klub} meraih {pk} poin per laga di kandang, {pt} di tandang"
    return _kartu(judul, ket, panel.kandang_tandang(baris, aksen))


def _panel_hasil(df: pd.DataFrame, klub: str | None, musim: str | None, aksen: str) -> str:
    laga = laga_klub(df if musim is None else df[df["musim"] == musim], klub)
    if laga.empty:
        return _kartu("Proporsi Hasil", "", _kosong(PESAN_KOSONG))
    irisan = proporsi_hasil(df, musim, klub)
    warna = [aksen, "#5A8FA3", panel.PUDAR]
    legenda = "".join(
        f'<div><span><i style="background:{warna[i]}"></i>{escape(b["label"])}</span>'
        f'<b>{_koma(b["nilai"])}%</b></div>'
        for i, b in enumerate(irisan)
    )
    isi = (f'<div class="donat-isi"><div class="donat-grafik">{panel.donat(irisan, aksen)}</div>'
           f'<div class="legenda">{legenda}</div></div>')
    jumlah_musim = laga["musim"].nunique()  # musim yang benar-benar dimainkan klub
    rentang = f"{jumlah_musim} musim, {_angka(len(laga))} laga" if musim is None else f"musim {musim}"
    ket = f"Liga, {rentang}" if klub is None else f"Hasil {klub}, {rentang}"
    return _kartu("Proporsi Hasil", ket, isi)


def _panel_juara(df: pd.DataFrame, klub: str | None, aksen: str) -> str:
    """Lima gelar terbanyak. Klub terfilter di luar lima besar ditambahkan di bawah garis."""
    data = juara(df)
    if data.empty:
        return _kartu("Gelar Terbanyak", "0 musim penuh",
                      _kosong("Belum ada musim yang selesai di rentang ini."))
    lima = [{"klub": r["klub"], "nilai": int(r["gelar"])} for r in data.head(5).to_dict("records")]
    tambahan = None
    if klub is not None and klub not in [b["klub"] for b in lima]:
        punya = data[data["klub"] == klub]
        tambahan = {"klub": klub,
                    "nilai": int(punya.iloc[0]["gelar"]) if not punya.empty else 0}
    html = panel.batang_mendatar(lima, aksen, sorot=klub, tambahan=tambahan)
    ket = f"{int(data['gelar'].sum())} musim penuh"
    return _kartu("Gelar Terbanyak", ket, html)


def _panel_gol(df: pd.DataFrame, klub: str | None, musim: str | None, aksen: str) -> str:
    judul = "Presentase Gol" if klub is None else f"Gol per laga {klub}"
    if laga_klub(df if musim is None else df[df["musim"] == musim], klub).empty:
        return _kartu(judul, "", _kosong(PESAN_KOSONG))
    data = distribusi_gol(df, klub, musim)
    items = data.to_dict("records")
    tertinggi = max(items, key=lambda b: b["persen"])
    isi = panel.batang_tegak(items, aksen)
    persen = f'{tertinggi["persen"]:.1f}'.replace(".", ",")
    ket = f'Paling sering {tertinggi["gol"]} gol (dua tim), {persen}% laga'
    return _kartu(judul, ket, isi)


# ---------------------------------------------------------------- dokumentasi

def _dokumentasi(df: pd.DataFrame) -> None:
    """Materi rubrik 2 dan 4 dipindah ke sidebar supaya kisi tetap muat satu layar."""
    with st.sidebar:
        with st.expander("Gambaran data"):
            tabel = tabel_kelengkapan(df)
            for row in tabel.itertuples():
                tanda = "dipakai model" if row.dipakai_model else "tidak dipakai"
                st.markdown(
                    f"**{row.kelompok}** — {row.cakupan}% · {tanda}  \n"
                    f'<span style="font-size:13px;color:var(--teks-2)">{row.alasan}</span>',
                    unsafe_allow_html=True,
                )
        with st.expander("Bagaimana data dibersihkan"):
            st.markdown(
                "1. **Jendela 10 laga melintasi batas musim.** Fitur tim dihitung dari 10 laga "
                "terakhir sebelum tanggal pertandingan; untuk klub promosi, jendela itu menjangkau "
                "musim-musim sebelumnya.\n\n"
                "2. **Musim tak utuh.** 2003/04 dan 2004/05 masing-masing hanya 335 laga, jadi "
                "seluruh tren memakai ukuran per laga, bukan total musiman.\n\n"
                "3. **Kolom pekan dibuang.** Hanya terisi 102 baris; seluruh waktu disebut dengan tanggal.\n\n"
                "4. **Odds dan statistik lanjutan tidak jadi fitur.** Odds tidak ada untuk laga "
                "mendatang, dan statistik lanjutan terlalu tipis untuk melatih 27 musim.\n\n"
                "5. **Tembakan tepat diklem.** Tiga baris mencatat tembakan tepat melebihi total "
                "tembakan, jadi dibatasi agar rasio akurasi tidak melampaui 1,0."
            )
        with st.expander("Model yang dipakai"):
            st.markdown(
                "Model memprediksi peluang `H`, `D`, dan `A` dari 10 fitur dasar per tim. "
                "Hasil pipeline rekan kelompok berupa ensemble Poisson dan LightGBM; bila "
                "berkasnya tidak ada, dashboard jatuh ke lapisan Poisson sendiri.\n\n"
                "Data uji dipisah menurut waktu, bukan acak, supaya pembanding odds bisa "
                "dihitung pada baris yang sama persis."
            )


# ---------------------------------------------------------------------- tampil

def rentang_minimal(baru, lama, musim_daftar: list[str]) -> tuple[str, str]:
    """Rentang musim selalu minimal dua musim.

    Kalau kedua ujung slider bertemu di satu musim, ujung yang barusan digeser
    dimundurkan satu musim (atau ujung satunya, kalau sudah mentok di tepi).
    """
    if not (isinstance(baru, (tuple, list)) and len(baru) == 2
            and all(m in musim_daftar for m in baru)):
        return musim_daftar[0], musim_daftar[-1]
    awal, akhir = baru
    if awal != akhir or len(musim_daftar) < 2:
        return awal, akhir
    i = musim_daftar.index(awal)
    geser_awal = isinstance(lama, (tuple, list)) and len(lama) == 2 and lama[0] != awal
    if geser_awal:
        return (musim_daftar[i - 1], akhir) if i > 0 else (awal, musim_daftar[i + 1])
    return (awal, musim_daftar[i + 1]) if i + 1 < len(musim_daftar) else (musim_daftar[i - 1], akhir)


def _simpan_rentang(kunci: str, musim_daftar: list[str]) -> None:
    baru = tuple(st.session_state[kunci])
    rentang = rentang_minimal(baru, st.session_state.get("rentang_overview"), musim_daftar)
    st.session_state["rentang_overview"] = rentang
    if rentang != baru:
        # Nilai widget tidak boleh ditimpa lewat Session State selagi value= dipakai,
        # jadi slider dibuat ulang dengan kunci baru yang langsung memakai rentang hasil koreksi.
        st.session_state["versi_rentang"] = st.session_state.get("versi_rentang", 0) + 1


def _musim_klub(df: pd.DataFrame, klub: str) -> str:
    musim = sorted(laga_klub(df, klub)["musim"].astype(str).unique())
    if not musim:
        return f"{klub} tidak ada di data ini."
    if len(musim) <= 3:
        daftar = musim[0] if len(musim) == 1 else ", ".join(musim[:-1]) + f" dan {musim[-1]}"
        return f"{klub} main di Premier League pada {daftar}."
    return f"{klub} main di {len(musim)} musim Premier League, antara {musim[0]} dan {musim[-1]}."


def _pemberitahuan_absen(df: pd.DataFrame, df_rentang: pd.DataFrame, klub: str | None) -> str:
    """Satu pesan di atas KPI saat klub terpilih tidak bermain di rentang musim terpilih."""
    if klub is None or not laga_klub(df_rentang, klub).empty or df_rentang.empty:
        return ""
    musim = df_rentang["musim"].astype(str)
    return (f'<div class="pemberitahuan"><b>{escape(klub)} tidak main di rentang '
            f'{escape(musim.min())} sampai {escape(musim.max())}.</b> '
            f'{escape(_musim_klub(df, klub))} Geser rentang musim untuk melihat datanya.</div>')


def _kepala(df: pd.DataFrame) -> tuple[str | None, pd.DataFrame]:
    """Filter klub dan rentang musim global; hasilnya dipakai oleh seluruh KPI dan chart."""
    musim_daftar = sorted(df["musim"].dropna().astype(str).unique())
    klub_daftar = sorted(set(df["tim_kandang"].dropna()) | set(df["tim_tandang"].dropna()))

    judul_kol, klub_kol, musim_kol = st.columns([3.7, 1.35, 2.2], vertical_alignment="top")
    with klub_kol:
        st.selectbox(
            "Klub", [SEMUA] + klub_daftar,
            format_func=lambda nama: "Premier League" if nama == SEMUA else nama,
            key="fokus",
        )
    if not musim_daftar:
        return None, df.iloc[0:0].copy()
    with musim_kol:
        # Pilihan rentang disalin ke kunci biasa "rentang_overview" lewat on_change.
        # Nilai widget sendiri dihapus Streamlit saat pengguna membuka halaman lain,
        # jadi tanpa salinan ini rentang kembali ke awal setiap balik ke Overview.
        rentang = rentang_minimal(st.session_state.get("rentang_overview"), None, musim_daftar)
        kunci = f"rentang_musim_global_{st.session_state.get('versi_rentang', 0)}"
        awal, akhir = st.select_slider(
            "Rentang musim",
            options=musim_daftar,
            value=rentang,
            key=kunci,
            on_change=_simpan_rentang,
            args=(kunci, musim_daftar),
        )
    pilihan = st.session_state.get("fokus", SEMUA)
    klub = None if pilihan == SEMUA else pilihan
    with judul_kol:
        lingkup = "Premier League" if klub is None else klub
        st.markdown(
            f'<div class="dasbor-kepala"><h2>{escape(lingkup)}</h2>'
            f'<span class="ruang">Musim {escape(awal)} sampai {escape(akhir)}</span></div>',
            unsafe_allow_html=True,
        )

    musim_terpilih = df["musim"].astype(str).between(awal, akhir)
    df_rentang = df.loc[musim_terpilih].copy()
    return klub, df_rentang


def tampil() -> None:
    df = muat_pertandingan(str(JALUR_DATA))
    klub, df_aktif = _kepala(df)
    aksen = panel.TEAL if klub is None else warna_aksen(warna_klub(klub))

    ringkas = ringkas_kpi(df_aktif, None, klub)
    tren_kpi = kpi_tren_per_musim(df_aktif, klub)
    with st.container(key="dasbor-overview"):
        st.markdown(_pemberitahuan_absen(df, df_aktif, klub) + _kpi(ringkas, tren_kpi), unsafe_allow_html=True)
        with st.container(key="baris-radar-tren"):
            radar_col, tren_col = st.columns(2, gap="small", vertical_alignment="top")
            with radar_col:
                st.markdown(_panel_radar(df_aktif, klub, None, aksen), unsafe_allow_html=True)
            with tren_col:
                _panel_tren(df_aktif, klub)
        with st.container(key="baris-kandang-hasil"):
            kandang_col, hasil_col = st.columns(2, gap="small", vertical_alignment="top")
            with kandang_col:
                st.markdown(_panel_kandang(df_aktif, klub, aksen), unsafe_allow_html=True)
            with hasil_col:
                st.markdown(_panel_hasil(df_aktif, klub, None, aksen), unsafe_allow_html=True)
        with st.container(key="baris-juara-gol"):
            juara_col, gol_col = st.columns(2, gap="small", vertical_alignment="top")
            with juara_col:
                st.markdown(_panel_juara(df_aktif, klub, aksen), unsafe_allow_html=True)
            with gol_col:
                st.markdown(_panel_gol(df_aktif, klub, None, aksen), unsafe_allow_html=True)
        from halaman.klasemen_liga import panel_klasemen
        st.markdown(panel_klasemen(df, klub), unsafe_allow_html=True)
    _dokumentasi(df)
