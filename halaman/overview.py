"""Halaman Overview: papan ringkas satu layar untuk liga, menyempit ke satu klub bila difilter."""
from html import escape

import altair as alt
import pandas as pd
import streamlit as st

from gaya import panel
from gaya.komponen import _uri_logo, warna_aksen
from inti.data import KELOMPOK_KOLOM, muat_pertandingan
from inti.klub import logo_klub, singkatan, warna_klub
from inti.liga import (
    distribusi_gol,
    gol_vs_xg,
    juara,
    laga_klub,
    proporsi_hasil,
    radar,
    ringkas_kpi,
    SUMBU_RADAR,
    tren_musim,
)
from inti.sesi import JALUR_DATA

SEMUA = "Semua klub"


def _angka(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _koma(v: float, desimal: int = 1) -> str:
    """Angka desimal bergaya Indonesia: koma sebagai pemisah pecahan."""
    return f"{v:.{desimal}f}".replace(".", ",")

# nama kolom di tren_musim -> label pilihan, satuan untuk liga, satuan untuk satu klub
METRIK = [
    ("gol", "Gol", "gol per laga (dua tim)", "gol dicetak per laga"),
    ("kandang", "Menang kandang", "persen laga dimenangi tuan rumah", "persen menang di kandang"),
    ("tembakan", "Tembakan", "tembakan per tim per laga", "tembakan per laga"),
    ("kartu", "Kartu", "kartu kuning per tim per laga", "kartu kuning per laga"),
    ("konversi", "Konversi", "persen tembakan jadi gol", "persen tembakan jadi gol"),
]
FORMAT_METRIK = {"gol": ".2f", "kandang": ".1f", "tembakan": ".1f", "kartu": ".2f", "konversi": ".1f"}
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


def _kpi(ringkas: dict) -> str:
    sel = [
        ("Gol", _angka(ringkas["gol"]), ""),
        ("Tembakan", _angka(ringkas["tembakan"]), ""),
        ("Tepat sasaran", _angka(ringkas["tembakan_tepat"]), ""),
        ("Laga", _angka(ringkas["laga"]), ""),
        ("Kartu kuning", _angka(ringkas["kartu_kuning"]), ""),
        ("Pelanggaran berkartu", f'{ringkas["kartu_per_pelanggaran"]:.1f}'.replace(".", ","), "%"),
    ]
    return '<div class="kpi">' + "".join(
        f'<div class="kpi-sel"><div class="label">{escape(label)}</div>'
        f'<div class="nilai">{nilai}{f"<small>{sat}</small>" if sat else ""}</div></div>'
        for label, nilai, sat in sel
    ) + "</div>"


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
        nama = "liga" if klub is None else klub
        return _kartu("Performa", "", _kosong(f"Tidak ada laga {nama} di rentang musim ini."))
    grafik = panel.radar(seri, SUMBU_RADAR, aksen)
    if klub is None:
        ket_html = '<div class="ket">Empat klub dengan poin terbanyak di rentang ini</div>'
        kaki = ('<div class="radar-kaki">' + "".join(
            f'<span><i style="background:{panel.NETRAL_RADAR[i % len(panel.NETRAL_RADAR)]}">'
            f'</i>{escape(s["nama"])}</span>' for i, s in enumerate(seri)) + '</div>')
    else:
        ket_html = f'<div class="ket">{escape(klub)} dibanding rata-rata liga</div>'
        kaki = (f'<div class="radar-kaki">'
                f'<span><i style="background:{aksen}"></i>{escape(klub)}</span>'
                f'<span><i style="background:{panel.KABUT}"></i>Rata-rata liga</span></div>')
    isi = (f'<div class="radar-isi">{_lencana_besar(klub, aksen)}'
           f'<div class="radar-grafik">{grafik}</div></div>')
    return (f'<div class="kartu"><div class="judul">Performa</div>'
            f'{ket_html}'
            f'<div class="isi">{isi}</div>{kaki}</div>')


def _panel_tren(df: pd.DataFrame, klub: str | None) -> None:
    with st.container(key="panel-tren"):
        _isi_panel_tren(df, klub)


def _isi_panel_tren(df: pd.DataFrame, klub: str | None) -> None:
    """Grafik tren interaktif; rentang musim mengikuti filter global dashboard."""
    tren = tren_musim(laga_klub(df, klub), klub)
    if tren.empty:
        nama = "liga" if klub is None else klub
        st.info(f"Tidak ada laga {nama} di rentang musim ini.")
        return

    judul_tren = "Tren Liga" if klub is None else f"Tren {escape(klub)}"
    n_musim = tren["musim"].nunique()

    kolom_judul, kolom_metrik = st.columns([2, 1], vertical_alignment="top")
    with kolom_judul:
        st.markdown(
            f'<div class="judul-tren">{judul_tren}'
            f'<span class="sub-tren">{n_musim} musim</span></div>',
            unsafe_allow_html=True,
        )
    with kolom_metrik:
        label_terpilih = st.selectbox(
            "Metrik", [m[1] for m in METRIK], key="tren_metrik",
            label_visibility="collapsed",
        )
    metrik = next(item for item in METRIK if item[1] == label_terpilih)
    kolom, _, satuan_liga, satuan_klub = metrik
    satuan = satuan_liga if klub is None else satuan_klub
    format_angka = FORMAT_METRIK[kolom]

    pilihan = tren.dropna(subset=[kolom]).copy()
    pilihan["musim"] = pilihan["musim"].astype(str)
    pilihan["tahun"] = pilihan["musim"].str.slice(0, 4)
    tahun = pilihan["tahun"].tolist()
    if not tahun:
        st.info("Tidak ada musim pada rentang yang dipilih.")
        return

    jarak_tanda = max(1, (len(tahun) - 1) // 7)
    tanda = tahun[::jarak_tanda]
    if tanda[-1] != tahun[-1]:
        tanda.append(tahun[-1])
    chart = (
        alt.Chart(pilihan)
        .mark_line(color=panel.TEAL, strokeWidth=3, point=alt.OverlayMarkDef(filled=True, size=52))
        .encode(
            x=alt.X(
                "tahun:O", title="Tahun", sort=tahun,
                scale=alt.Scale(domain=tahun),
                axis=alt.Axis(values=tanda, labelAngle=-45, labelAlign="right",
                              labelBaseline="middle", labelOverlap=False,
                              domain=True, domainColor=panel.GARIS, domainWidth=1.5,
                              tickColor=panel.GARIS, tickSize=6, tickWidth=1.5,
                              labelPadding=7, grid=False),
            ),
            y=alt.Y(
                f"{kolom}:Q", title=satuan, scale=alt.Scale(zero=False, nice=True),
                axis=alt.Axis(format=format_angka, domain=True, domainColor=panel.GARIS, domainWidth=1.5,
                              tickColor=panel.GARIS, tickSize=5, tickWidth=1.2,
                              grid=True, gridColor=panel.PUDAR, gridWidth=1,
                              titlePadding=10),
            ),
            tooltip=[alt.Tooltip("musim:N", title="Musim"),
                     alt.Tooltip(f"{kolom}:Q", title=satuan, format=format_angka),
                     alt.Tooltip("laga:Q", title="Laga")],
        )
        .properties(height=208, background="transparent",
                    padding={"left": 8, "right": 8, "top": 4, "bottom": 20})
        .configure(background="transparent", locale=LOKAL_ID)
        .configure_view(fill="transparent", stroke=None)
        .configure_axis(labelColor=panel.KABUT, titleColor=panel.KABUT,
                        labelFont="IBM Plex Sans Condensed", titleFont="IBM Plex Sans",
                        labelFontSize=12, titleFontSize=12)
    )
    st.altair_chart(chart, width="stretch", theme=None)


def _panel_xg(df: pd.DataFrame, klub: str | None, aksen: str) -> str:
    data = gol_vs_xg(df)
    titik = data.to_dict("records")
    # dihitung langsung dari baris, bukan dari jumlah laga per klub dibagi dua,
    # karena klub dengan kurang dari 10 laga ber-xG tidak masuk sebaran
    laga = int((df["xg_bbc_kandang"].notna() & df["xg_bbc_tandang"].notna()).sum())
    if not titik:
        return _kartu("Gol dibanding gol harapan", "Data xG BBC baru ada sejak 2024/25",
                      _kosong("Belum ada laga ber-xG di rentang musim ini."))
    isi = panel.sebar_xg(titik, klub, aksen)
    ket = f"Di atas garis berarti klinis. {_angka(laga)} laga ber-xG pada rentang terpilih"
    if klub is not None and klub not in data["klub"].tolist():
        ket = f"{klub} belum punya cukup laga ber-xG di rentang ini (xG baru ada sejak 2024/25)"
    return _kartu("Gol dibanding gol harapan", ket, isi)


def _panel_hasil(df: pd.DataFrame, klub: str | None, musim: str | None, aksen: str) -> str:
    laga = laga_klub(df if musim is None else df[df["musim"] == musim], klub)
    if laga.empty:
        nama = "liga" if klub is None else klub
        return _kartu("Proporsi hasil", "", _kosong(f"Tidak ada laga {nama} di rentang musim ini."))
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
    return _kartu("Proporsi hasil", ket, isi)


def _panel_juara(df: pd.DataFrame, klub: str | None, aksen: str) -> str:
    """Lima gelar terbanyak. Klub terfilter di luar lima besar ditambahkan di bawah garis."""
    data = juara(df)
    if data.empty:
        return _kartu("Paling sering juara", "0 musim penuh",
                      _kosong("Belum ada musim yang selesai di rentang ini."))
    lima = [{"klub": r["klub"], "nilai": int(r["gelar"])} for r in data.head(5).to_dict("records")]
    tambahan = None
    if klub is not None and klub not in [b["klub"] for b in lima]:
        punya = data[data["klub"] == klub]
        tambahan = {"klub": klub,
                    "nilai": int(punya.iloc[0]["gelar"]) if not punya.empty else 0}
    html = panel.batang_mendatar(lima, aksen, sorot=klub, tambahan=tambahan)
    ket = f"{int(data['gelar'].sum())} musim penuh"
    return _kartu("Paling sering juara", ket, html)


def _panel_gol(df: pd.DataFrame, klub: str | None, musim: str | None, aksen: str) -> str:
    judul = "Berapa gol yang wajar" if klub is None else f"Gol per laga {klub}"
    if laga_klub(df if musim is None else df[df["musim"] == musim], klub).empty:
        nama = "liga" if klub is None else klub
        return _kartu(judul, "", _kosong(f"Tidak ada laga {nama} di rentang musim ini."))
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

def _simpan_rentang() -> None:
    st.session_state["rentang_overview"] = tuple(st.session_state["rentang_musim_global"])


def _kepala(df: pd.DataFrame) -> tuple[str | None, pd.DataFrame]:
    """Filter klub dan rentang musim global; hasilnya dipakai oleh seluruh KPI dan chart."""
    musim_daftar = sorted(df["musim"].dropna().astype(str).unique())
    klub_daftar = sorted(set(df["tim_kandang"].dropna()) | set(df["tim_tandang"].dropna()))

    judul_kol, klub_kol, musim_kol = st.columns([3.7, 1.35, 2.2], vertical_alignment="center")
    with klub_kol:
        st.selectbox(
            "Kompetisi / Klub", [SEMUA] + klub_daftar,
            format_func=lambda nama: "Premier League" if nama == SEMUA else nama,
            key="fokus",
        )
    if not musim_daftar:
        return None, df.iloc[0:0].copy()
    with musim_kol:
        # Pilihan rentang disalin ke kunci biasa "rentang_overview" lewat on_change.
        # Nilai widget sendiri dihapus Streamlit saat pengguna membuka halaman lain,
        # jadi tanpa salinan ini rentang kembali ke awal setiap balik ke Overview.
        rentang = st.session_state.get("rentang_overview")
        if not (isinstance(rentang, (tuple, list)) and len(rentang) == 2
                and all(m in musim_daftar for m in rentang)):
            rentang = (musim_daftar[0], musim_daftar[-1])
        awal, akhir = st.select_slider(
            "Rentang musim",
            options=musim_daftar,
            value=tuple(rentang),
            key="rentang_musim_global",
            on_change=_simpan_rentang,
        )
    pilihan = st.session_state.get("fokus", SEMUA)
    klub = None if pilihan == SEMUA else pilihan
    with judul_kol:
        lingkup = "Seluruh liga" if klub is None else klub
        st.markdown(
            f'<div class="dasbor-kepala"><h2>{escape(lingkup)}</h2>'
            f'<span class="ruang">{escape(awal)}–{escape(akhir)} · rentang berlaku untuk seluruh KPI dan chart</span></div>',
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
    with st.container(key="dasbor-overview"):
        st.markdown(_kpi(ringkas), unsafe_allow_html=True)
        with st.container(key="baris-radar-tren"):
            radar_col, tren_col = st.columns(2, gap="small", vertical_alignment="top")
            with radar_col:
                st.markdown(_panel_radar(df_aktif, klub, None, aksen), unsafe_allow_html=True)
            with tren_col:
                _panel_tren(df_aktif, klub)
        with st.container(key="baris-xg-hasil"):
            xg_col, hasil_col = st.columns(2, gap="small", vertical_alignment="top")
            with xg_col:
                st.markdown(_panel_xg(df_aktif, klub, aksen), unsafe_allow_html=True)
            with hasil_col:
                st.markdown(_panel_hasil(df_aktif, klub, None, aksen), unsafe_allow_html=True)
        with st.container(key="baris-juara-gol"):
            juara_col, gol_col = st.columns(2, gap="small", vertical_alignment="top")
            with juara_col:
                st.markdown(_panel_juara(df_aktif, klub, aksen), unsafe_allow_html=True)
            with gol_col:
                st.markdown(_panel_gol(df_aktif, klub, None, aksen), unsafe_allow_html=True)
    _dokumentasi(df)
