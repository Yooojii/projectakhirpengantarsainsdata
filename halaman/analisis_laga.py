"""Halaman Match Analysis: simulasi dua klub dan analisis laga yang sudah dimainkan.

Kolom kiri berisi dua pintu masuk: kartu "Simulasi match" (pilih dua klub, jalankan
model) dan daftar laga yang bisa diklik. Kolom kanan selalu menampilkan satu hal,
yaitu pilihan terakhir pengguna dari salah satu pintu itu.
"""
from html import escape

import numpy as np
import pandas as pd
import streamlit as st

from gaya.komponen import _uri_logo, angka_hitung, logo_kecil, warna_aksen
from halaman.history import rekor_pertemuan
from halaman.prediksi_simulasi import hitung_prediksi, siapkan_sesi
from inti.data import klub_musim, muat_pertandingan
from inti.klub import logo_klub, singkatan, warna_klub
from inti.model import prediksi_ensemble
from inti.sesi import BULAN, JALUR_DATA

MUSIM_BERJALAN = "2026/27"
SEMUA_KLUB = "Semua klub"
JUMLAH_AWAL = 12
KABUT = "#8FA6B0"

# label, nama kolom dasar (tanpa _kandang/_tandang), jumlah desimal
STAT = [
    ("Total tembakan", "tembakan", 0),
    ("Tembakan tepat sasaran", "tembakan_tepat", 0),
    ("Sepak pojok", "sepak_pojok", 0),
    ("Pelanggaran", "pelanggaran", 0),
    ("Kartu kuning", "kartu_kuning", 0),
    ("Kartu merah", "kartu_merah", 0),
]


# ------------------------------------------------------------------ bantuan

def _tgl(ts: pd.Timestamp, pendek: bool = False) -> str:
    bulan = BULAN[ts.month - 1]
    return f"{ts.day} {bulan[:3] if pendek else bulan} {ts.year}"


def _koma(v: float, desimal: int = 0) -> str:
    return f"{v:.{desimal}f}".replace(".", ",")


def _ada(nilai) -> bool:
    return nilai is not None and not pd.isna(nilai)


def _warna_pasangan(klub_k: str, klub_t: str) -> tuple[str, str]:
    """Warna kedua klub; tamu jatuh ke abu kabut bila warnanya terlalu mirip tuan rumah."""
    wk, wt = warna_aksen(warna_klub(klub_k)), warna_aksen(warna_klub(klub_t))
    rgb = lambda h: np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)])
    if np.linalg.norm(rgb(wk) - rgb(wt)) < 90:
        wt = KABUT
    return wk, wt


def _logo_besar(klub: str) -> str:
    jalur = logo_klub(klub)
    if jalur is None:
        return f'<span class="kode-besar">{escape(singkatan(klub))}</span>'
    return f'<img src="{_uri_logo(str(jalur))}" alt="">'


def _hasil_untuk(klub: str, kandang: str, hasil: str) -> str:
    if hasil == "D":
        return "S"
    menang_kandang = hasil == "H"
    return "M" if (klub == kandang) == menang_kandang else "K"


def bentuk_sebelum(df: pd.DataFrame, klub: str, sebelum: pd.Timestamp, n: int = 5) -> list[str]:
    """Hasil n laga terakhir klub sebelum tanggal tertentu, urut lama ke baru."""
    sub = df[((df["tim_kandang"] == klub) | (df["tim_tandang"] == klub)) & (df["tanggal"] < sebelum)]
    sub = sub.sort_values("tanggal", kind="stable").tail(n)
    return [_hasil_untuk(klub, r.tim_kandang, r.hasil) for r in sub.itertuples()]


def rata_terakhir(df: pd.DataFrame, klub: str, sebelum: pd.Timestamp, n: int = 10) -> dict:
    """Rata-rata statistik yang dibuat dan yang diterima klub pada n laga sebelum tanggal."""
    sub = df[((df["tim_kandang"] == klub) | (df["tim_tandang"] == klub)) & (df["tanggal"] < sebelum)]
    sub = sub.sort_values("tanggal", kind="stable").tail(n)
    kandang = (sub["tim_kandang"] == klub).to_numpy()
    hasil = {}
    for _, kol, _ in STAT:
        k, t = sub[f"{kol}_kandang"].to_numpy(float), sub[f"{kol}_tandang"].to_numpy(float)
        buat, terima = np.where(kandang, k, t), np.where(kandang, t, k)
        hasil[kol] = (float(np.nanmean(buat)) if len(sub) else 0.0,
                      float(np.nanmean(terima)) if len(sub) else 0.0)
    return hasil


GOL_MAKS = 4      # skor di atas ini digabung ke 4 supaya tiap kelompok punya cukup laga
PENYUSUT = 30     # kelompok skor dengan sedikit laga ditarik ke faktor netral 1,0


@st.cache_data(show_spinner=False)
def _tabel_faktor(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Rata-rata tiap statistik per skor akhir, dibagi rata-rata seluruh laga."""
    kolom = [f"{kol}_{sisi}" for _, kol, _ in STAT for sisi in ("kandang", "tandang")]
    d = df[kolom].copy()
    d["gk"] = df["gol_kandang"].clip(upper=GOL_MAKS).astype(int)
    d["gt"] = df["gol_tandang"].clip(upper=GOL_MAKS).astype(int)
    grup = d.groupby(["gk", "gt"])
    return grup[kolom].mean() / d[kolom].mean(), grup.size()


def faktor_skor(df: pd.DataFrame, skor: tuple[int, int]) -> dict[str, tuple[float, float]]:
    """Seberapa jauh statistik laga dengan skor ini menyimpang dari laga rata-rata, per sisi.

    Contoh: laga 3-0 rata-rata punya lebih banyak tembakan tuan rumah dan lebih sedikit
    tembakan tamu. Kelompok skor yang jarang terjadi disusutkan ke 1,0.
    """
    rasio, jumlah = _tabel_faktor(df)
    kunci = (min(int(skor[0]), GOL_MAKS), min(int(skor[1]), GOL_MAKS))
    if kunci not in rasio.index:
        return {kol: (1.0, 1.0) for _, kol, _ in STAT}
    bobot = jumlah[kunci] / (jumlah[kunci] + PENYUSUT)
    baris = rasio.loc[kunci]
    susut = lambda f: 1.0 + (float(f) - 1.0) * bobot if pd.notna(f) else 1.0
    return {kol: (susut(baris[f"{kol}_kandang"]), susut(baris[f"{kol}_tandang"]))
            for _, kol, _ in STAT}


def perkiraan_statistik(df: pd.DataFrame, klub_k: str, klub_t: str, sebelum: pd.Timestamp,
                        skor: tuple[int, int] | None = None) -> list[tuple[str, float, float, int]]:
    """Statistik laga simulasi: rata-rata apa yang biasa dibuat satu klub dan diterima lawannya.

    Bila `skor` diberikan, angka itu disesuaikan dengan pola historis laga yang berakhir
    dengan skor tersebut.
    """
    rk, rt = rata_terakhir(df, klub_k, sebelum), rata_terakhir(df, klub_t, sebelum)
    faktor = faktor_skor(df, skor) if skor is not None else None
    baris = []
    for label, kol, _ in STAT:
        k = (rk[kol][0] + rt[kol][1]) / 2
        t = (rt[kol][0] + rk[kol][1]) / 2
        if faktor is not None:
            k, t = k * faktor[kol][0], t * faktor[kol][1]
        baris.append((label, k, t, 2 if kol == "kartu_merah" else 1))
    return baris


# ------------------------------------------------------------- potongan HTML

def _kartu_laga(r, aktif: bool, i: int) -> str:
    gk, gt = int(r.gol_kandang), int(r.gol_tandang)
    kelas_k = "kalah" if gk < gt else ""
    kelas_t = "kalah" if gt < gk else ""
    kelas = "laga aktif" if aktif else "laga"
    return (
        f'<div class="{kelas}" style="--i:{min(i, 12)}">'
        f'<div class="laga-meta"><span>{_tgl(r.tanggal, pendek=True)}</span><span>Selesai</span></div>'
        f'<div class="laga-tim">'
        f'<div class="{kelas_k}">{logo_kecil(r.tim_kandang)}<span>{escape(r.tim_kandang)}</span></div>'
        f'<div class="{kelas_t}">{logo_kecil(r.tim_tandang)}<span>{escape(r.tim_tandang)}</span></div>'
        f'</div>'
        f'<div class="laga-skor"><span>{gk}</span><span>{gt}</span></div>'
        f'</div>'
    )


def _baris_stat(label: str, vk: float, vt: float, desimal: int, wk: str, wt: str, i: int,
                akhiran: str = "") -> str:
    puncak = max(vk, vt)
    lk = 100 * vk / puncak if puncak > 0 else 0
    lt = 100 * vt / puncak if puncak > 0 else 0
    lemah_k = ' class="lemah"' if vk < vt else ""
    lemah_t = ' class="lemah"' if vt < vk else ""
    return (
        f'<div class="stat"><div class="stat-kepala">'
        f'<b{lemah_k}>{_koma(vk, desimal)}{akhiran}</b><span>{escape(label)}</span>'
        f'<b{lemah_t}>{_koma(vt, desimal)}{akhiran}</b></div>'
        f'<div class="stat-lajur">'
        f'<div><span style="width:{lk:.1f}%;background:{wk};--i:{i}"></span></div>'
        f'<div><span style="width:{lt:.1f}%;background:{wt};--i:{i}"></span></div>'
        f'</div></div>'
    )


def _bentuk_html(hasil: list[str]) -> str:
    if not hasil:
        return '<span class="keterangan">Belum ada laga sebelumnya</span>'
    isi = "".join(f'<span class="{h}" style="--i:{i}">{h}</span>' for i, h in enumerate(hasil))
    return f'<div class="bentuk">{isi}</div>'


def _bentuk_duo(df: pd.DataFrame, klub_k: str, klub_t: str, sebelum: pd.Timestamp) -> str:
    return (
        '<div class="bentuk-duo">'
        f'<div><small>{escape(klub_k)}, lima laga sebelumnya</small>'
        f'{_bentuk_html(bentuk_sebelum(df, klub_k, sebelum))}</div>'
        f'<div><small>{escape(klub_t)}, lima laga sebelumnya</small>'
        f'{_bentuk_html(bentuk_sebelum(df, klub_t, sebelum))}</div>'
        '</div>'
    )


def _catatan(baris: list[str]) -> str:
    if not baris:
        return ""
    isi = "".join(f'<div style="--i:{i}"><i></i><span>{t}</span></div>' for i, t in enumerate(baris))
    return f'<div class="catatan">{isi}</div>'


def _sorotan(klub_k: str, klub_t: str, skor: tuple[int, int], lencana: str, kelas_lencana: str,
             meta: str, kaki: str) -> str:
    return (
        '<div class="sorotan">'
        f'<span class="sorotan-lencana {kelas_lencana}">{escape(lencana)}</span>'
        f'<div class="sorotan-meta">{meta}</div>'
        '<div class="sorotan-baris">'
        f'<div class="sorotan-tim">{_logo_besar(klub_k)}<b>{escape(klub_k)}</b><small>Kandang</small></div>'
        f'<div class="skor-besar">{angka_hitung(skor[0], tunda_ms=200)}'
        f'<span class="pemisah">:</span>{angka_hitung(skor[1], tunda_ms=320)}</div>'
        f'<div class="sorotan-tim">{_logo_besar(klub_t)}<b>{escape(klub_t)}</b><small>Tandang</small></div>'
        '</div>'
        + (f'<div class="sorotan-kaki">{kaki}</div>' if kaki else '')
        + '</div>'
    )


# ------------------------------------------------------------ analisis laga

def catatan_laga(r: pd.Series) -> list[str]:
    """Hingga tiga kalimat temuan dari satu laga yang sudah selesai."""
    k, t = escape(r["tim_kandang"]), escape(r["tim_tandang"])
    gk, gt = int(r["gol_kandang"]), int(r["gol_tandang"])
    tk, tt = float(r["tembakan_kandang"]), float(r["tembakan_tandang"])
    pk, pt = float(r["tembakan_tepat_kandang"]), float(r["tembakan_tepat_tandang"])
    catatan = []

    if max(tk, tt) >= 1.5 * max(min(tk, tt), 1):
        dominan, kalah = (k, t) if tk > tt else (t, k)
        catatan.append(
            f"<b>{dominan}</b> menguasai serangan dengan {_koma(max(tk, tt))} tembakan, "
            f"berbanding {_koma(min(tk, tt))} milik {kalah}."
        )
    else:
        catatan.append(f"Serangan relatif berimbang: {_koma(tk)} lawan {_koma(tt)} tembakan.")

    xk = r.get("xg_kandang") if _ada(r.get("xg_kandang")) else r.get("xg_api_kandang")
    xt = r.get("xg_tandang") if _ada(r.get("xg_tandang")) else r.get("xg_api_tandang")
    if _ada(xk) and _ada(xt):
        xk, xt = float(xk), float(xt)
        if gk - xk >= 0.8 or gt - xt >= 0.8:
            nama, g, x = (k, gk, xk) if gk - xk >= gt - xt else (t, gt, xt)
            catatan.append(f"<b>{nama}</b> klinis: {g} gol dari peluang senilai xG {_koma(x, 2)}.")
        elif xk - gk >= 0.8 or xt - gt >= 0.8:
            nama, g, x = (k, gk, xk) if xk - gk >= xt - gt else (t, gt, xt)
            catatan.append(f"<b>{nama}</b> boros peluang: xG {_koma(x, 2)} hanya menjadi {g} gol.")
        else:
            catatan.append(f"Skor sesuai kualitas peluang: xG {_koma(xk, 2)} lawan {_koma(xt, 2)}.")
    elif pk + pt > 0:
        akurasi_k = 100 * pk / max(tk, 1)
        akurasi_t = 100 * pt / max(tt, 1)
        catatan.append(
            f"Akurasi tembakan {k} {_koma(akurasi_k)}%, {t} {_koma(akurasi_t)}%."
        )

    hk, ht = r.get("gol_kandang_babak1"), r.get("gol_tandang_babak1")
    if _ada(hk) and _ada(ht):
        hk, ht = int(hk), int(ht)
        tanda_ht = (hk > ht) - (hk < ht)
        tanda_ft = (gk > gt) - (gk < gt)
        if tanda_ht != 0 and tanda_ft == -tanda_ht:
            pemenang = k if tanda_ft > 0 else t
            catatan.append(f"<b>{pemenang}</b> membalikkan keadaan setelah tertinggal {hk}-{ht} di babak pertama.")
        elif tanda_ht == 0 and tanda_ft != 0:
            pemenang = k if tanda_ft > 0 else t
            catatan.append(f"Imbang {hk}-{ht} saat jeda; gol penentu {pemenang} lahir di babak kedua.")

    mk, mt = int(r.get("kartu_merah_kandang", 0) or 0), int(r.get("kartu_merah_tandang", 0) or 0)
    if mk or mt:
        nama, n = (k, mk) if mk >= mt else (t, mt)
        catatan.append(f"<b>{nama}</b> harus bermain dengan {n} kartu merah.")
    return catatan[:3]


def panel_laga(df: pd.DataFrame, indeks: int) -> str:
    r = df.loc[indeks]
    k, t = r["tim_kandang"], r["tim_tandang"]
    wk, wt = _warna_pasangan(k, t)
    meta = _tgl(r["tanggal"]) + ", Premier League " + escape(str(r["musim"]))
    if _ada(r.get("stadion")):
        meta += f", {escape(str(r['stadion']))}"
    kaki = []
    if _ada(r.get("gol_kandang_babak1")):
        kaki.append(f"Babak pertama {int(r['gol_kandang_babak1'])}-{int(r['gol_tandang_babak1'])}")
    if _ada(r.get("wasit")):
        kaki.append(f"wasit {escape(str(r['wasit']))}")
    sorotan = _sorotan(k, t, (int(r["gol_kandang"]), int(r["gol_tandang"])), "Selesai", "",
                       meta, ", ".join(kaki))

    baris = []
    xk = r.get("xg_kandang") if _ada(r.get("xg_kandang")) else r.get("xg_api_kandang")
    xt = r.get("xg_tandang") if _ada(r.get("xg_tandang")) else r.get("xg_api_tandang")
    if _ada(xk) and _ada(xt):
        baris.append(("Gol harapan (xG)", float(xk), float(xt), 2, ""))
    if _ada(r.get("penguasaan_bola_kandang")) and _ada(r.get("penguasaan_bola_tandang")):
        baris.append(("Penguasaan bola", float(r["penguasaan_bola_kandang"]),
                      float(r["penguasaan_bola_tandang"]), 0, "%"))
    for label, kol, desimal in STAT:
        baris.append((label, float(r[f"{kol}_kandang"]), float(r[f"{kol}_tandang"]), desimal, ""))
    if _ada(r.get("umpan_kandang")) and _ada(r.get("umpan_tandang")):
        baris.append(("Jumlah umpan", float(r["umpan_kandang"]), float(r["umpan_tandang"]), 0, ""))
    stat = "".join(_baris_stat(l, a, b, d, wk, wt, i, s) for i, (l, a, b, d, s) in enumerate(baris))

    return (
        '<div class="analisis">'
        f'{sorotan}'
        f'<div class="bagian-stat"><div class="stat-judul">Statistik pertandingan<span>{escape(k)} kiri, {escape(t)} kanan</span></div>{stat}</div>'
        f'{_bentuk_duo(df, k, t, r["tanggal"])}'
        f'{_catatan(catatan_laga(r))}'
        '</div>'
    )


# ---------------------------------------------------------- simulasi laga

def _prediksi(df: pd.DataFrame, klub_k: str, klub_t: str, tanggal: pd.Timestamp) -> dict:
    """Prediksi model untuk pasangan klub, disimpan per sesi supaya tidak dihitung ulang."""
    simpanan = st.session_state.setdefault("cache_simulasi", {})
    kunci = (klub_k, klub_t, tanggal)
    if kunci not in simpanan:
        sesi = siapkan_sesi(df, klub_k, klub_t, tanggal)
        sesi["model"] = st.session_state.get("model")
        ens = prediksi_ensemble(klub_k, klub_t)
        if ens:
            dasar = hitung_prediksi(sesi)
            sesi["ensemble"] = ens
            sesi["acuan_gol"] = (dasar["gol_harapan_kandang"], dasar["gol_harapan_tandang"])
        simpanan[kunci] = hitung_prediksi(sesi)
    return simpanan[kunci]


def catatan_simulasi(df: pd.DataFrame, klub_k: str, klub_t: str, p: dict,
                     tanggal: pd.Timestamp) -> list[str]:
    k, t = escape(klub_k), escape(klub_t)
    peluang = {"k": p["p_menang_kandang"], "s": p["p_seri"], "t": p["p_menang_tandang"]}
    terkuat = max(peluang, key=peluang.get)
    persen = round(100 * peluang[terkuat])
    if terkuat == "s":
        catatan = [f"Model condong ke hasil imbang ({persen}%); kedua klub nyaris setara."]
    else:
        nama = k if terkuat == "k" else t
        selisih = round(100 * abs(peluang["k"] - peluang["t"]))
        catatan = [f"<b>{nama}</b> diunggulkan dengan peluang menang {persen}%, "
                   f"selisih {selisih} poin persen dari lawannya."]

    rekor = rekor_pertemuan(df, klub_k, klub_t)
    if rekor["total"]:
        catatan.append(
            f"Dari {rekor['total']} pertemuan di Premier League, {k} menang {rekor['menang']}, "
            f"seri {rekor['seri']}, dan {t} menang {rekor['kalah']}."
        )
    else:
        catatan.append(f"{k} dan {t} belum pernah bertemu di Premier League.")

    poin = lambda b: sum(3 if h == "M" else 1 if h == "S" else 0 for h in b)
    pk = poin(bentuk_sebelum(df, klub_k, tanggal))
    pt = poin(bentuk_sebelum(df, klub_t, tanggal))
    if pk != pt:
        lebih, kurang = (k, t) if pk > pt else (t, k)
        catatan.append(f"Bentuk terkini {lebih} lebih baik: {max(pk, pt)} poin dari lima laga, "
                       f"{kurang} {min(pk, pt)} poin.")
    else:
        catatan.append(f"Bentuk terkini sama kuat: masing-masing {pk} poin dari lima laga.")
    return catatan


def blok_peluang(klub_k: str, klub_t: str, p: dict, wk: str, wt: str) -> str:
    """Batang peluang tiga arah; label seri diletakkan di tengah segmen abu-abunya."""
    pk, ps, pt = p["p_menang_kandang"], p["p_seri"], p["p_menang_tandang"]
    batang = "".join(
        f'<span style="flex:{max(v, 0.01):.3f};background:{w};--i:{i}"></span>'
        for i, (v, w) in enumerate([(pk, wk), (ps, "#CFD6CC"), (pt, wt)])
    )
    total = (pk + ps + pt) or 1.0
    # dijepit supaya label seri tidak menabrak label menang di kedua ujung
    tengah_seri = min(max(100 * (pk + ps / 2) / total, 20.0), 80.0)
    label = (
        f'<div class="kiri"><b>{angka_hitung(100 * pk, tunda_ms=240)}%</b>{escape(klub_k)} menang</div>'
        f'<div class="tengah" style="left:{tengah_seri:.1f}%">'
        f'<b>{angka_hitung(100 * ps, tunda_ms=360)}%</b>Seri</div>'
        f'<div class="kanan"><b>{angka_hitung(100 * pt, tunda_ms=480)}%</b>{escape(klub_t)} menang</div>'
    )
    return (f'<div class="peluang"><div class="peluang-batang">{batang}</div>'
            f'<div class="peluang-label">{label}</div></div>')


def _teks_skor(skor) -> str:
    return f"{int(skor[0])}-{int(skor[1])}"


def tampil_simulasi(df: pd.DataFrame, klub_k: str, klub_t: str) -> None:
    """Panel simulasi. Chip perkiraan skor bisa diklik: papan skor dan statistik ikut berubah."""
    tanggal = df["tanggal"].max() + pd.Timedelta(days=1)
    p = _prediksi(df, klub_k, klub_t, tanggal)
    wk, wt = _warna_pasangan(klub_k, klub_t)
    sumber = "model ensemble" if p.get("sumber") == "ensemble" else "model Poisson"
    meta = f"Perkiraan {sumber}, laga di kandang {escape(klub_k)}"

    peluang_skor = {_teks_skor(s): ps for s, ps in p["lima_teratas"]}
    utama = _teks_skor(p["skor"])
    pilihan = list(peluang_skor)
    if utama not in pilihan:
        pilihan.insert(0, utama)

    with st.container(key="panel-sim"):
        tempat_atas = st.empty()  # diisi setelah skor dipilih, tapi tampil di atas pemilih
        dipilih = st.pills(
            "Perkiraan Skor", pilihan, default=utama, key=f"skor-{klub_k}-{klub_t}",
            format_func=lambda s: f"{s}   {_koma(100 * peluang_skor.get(s, 0), 1)}%",
        ) or utama
        skor = tuple(int(x) for x in dipilih.split("-"))
        tempat_atas.markdown(
            _sorotan(klub_k, klub_t, skor, "Simulasi", "prediksi", meta, "")
            + blok_peluang(klub_k, klub_t, p, wk, wt),
            unsafe_allow_html=True,
        )

        stat = "".join(_baris_stat(l, a, b, d, wk, wt, i) for i, (l, a, b, d)
                       in enumerate(perkiraan_statistik(df, klub_k, klub_t, tanggal, skor)))
        st.markdown(
            '<div class="bagian-stat"><div class="stat-judul">Statistik pertandingan (perkiraan)</div>'
            f'{stat}</div>'
            f'{_bentuk_duo(df, klub_k, klub_t, tanggal)}'
            f'{_catatan(catatan_simulasi(df, klub_k, klub_t, p, tanggal))}',
            unsafe_allow_html=True,
        )


# -------------------------------------------------------------------- tampil

def _pilih(pilihan: dict) -> None:
    st.session_state["analisis"] = pilihan


def _tambah_batas() -> None:
    st.session_state["ma_batas"] = st.session_state.get("ma_batas", JUMLAH_AWAL) + JUMLAH_AWAL


def _kartu_simulasi(klub20: list[str], klub_saya: str) -> None:
    with st.container(key="kartu-simulasi"):
        st.markdown('<div class="judul-blok"><b>Simulasi match</b>'
                    f'<span>Musim {MUSIM_BERJALAN}</span></div>', unsafe_allow_html=True)
        if st.session_state.get("sim_kandang") not in klub20:
            st.session_state["sim_kandang"] = klub_saya if klub_saya in klub20 else klub20[0]
        kol_k, kol_vs, kol_t = st.columns([5, 1.4, 5], vertical_alignment="bottom")
        with kol_k:
            klub_k = st.selectbox("Tuan rumah", klub20, key="sim_kandang")
        lawan = [k for k in klub20 if k != klub_k]
        if st.session_state.get("sim_tamu") not in lawan:
            st.session_state["sim_tamu"] = lawan[0]
        with kol_vs:
            st.markdown('<div class="vs-bulat">vs</div>', unsafe_allow_html=True)
        with kol_t:
            klub_t = st.selectbox("Tamu", lawan, key="sim_tamu")
        st.button("Jalankan simulasi", type="primary", key="tombol-simulasi",
                  on_click=_pilih, args=({"mode": "sim", "k": klub_k, "t": klub_t},))


def _daftar_laga(df: pd.DataFrame, klub_saya: str) -> pd.DataFrame:
    with st.container(key="kartu-daftar"):
        st.markdown('<div class="judul-blok"><b>Jadwal & hasil terbaru</b>'
                    '<span>Klik kartu untuk analisis</span></div>', unsafe_allow_html=True)
        semua_musim = sorted(df["musim"].unique(), reverse=True)
        kol_m, kol_k = st.columns(2)
        with kol_m:
            musim = st.selectbox("Musim", semua_musim, key="ma_musim")
        pilihan_klub = [SEMUA_KLUB] + klub_musim(df, musim)
        if st.session_state.get("ma_klub") not in pilihan_klub:
            st.session_state["ma_klub"] = klub_saya if klub_saya in pilihan_klub else SEMUA_KLUB
        with kol_k:
            klub = st.selectbox("Klub", pilihan_klub, key="ma_klub")

        laga = df[df["musim"] == musim]
        if klub != SEMUA_KLUB:
            laga = laga[(laga["tim_kandang"] == klub) | (laga["tim_tandang"] == klub)]
        laga = laga.sort_values("tanggal", ascending=False, kind="stable")

        pilihan = st.session_state.get("analisis")
        if laga.empty:
            st.markdown('<div class="kartu-kosong">Tidak ada laga untuk musim dan klub ini.</div>',
                        unsafe_allow_html=True)
            return laga
        if (pilihan is None or (pilihan["mode"] == "laga" and pilihan["id"] not in laga.index)):
            st.session_state["analisis"] = {"mode": "laga", "id": int(laga.index[0])}
        pilihan = st.session_state["analisis"]
        aktif_id = pilihan["id"] if pilihan["mode"] == "laga" else None

        batas = st.session_state.get("ma_batas", JUMLAH_AWAL)
        st.caption(f"{len(laga)} pertandingan")
        with st.container(key="daftar-laga"):
            for i, r in enumerate(laga.head(batas).itertuples()):
                with st.container(key=f"kartu-laga-{r.Index}"):
                    st.markdown(_kartu_laga(r, r.Index == aktif_id, i), unsafe_allow_html=True)
                    st.button(f"Lihat analisis {r.tim_kandang} lawan {r.tim_tandang}",
                              key=f"pilih-laga-{r.Index}", on_click=_pilih,
                              args=({"mode": "laga", "id": int(r.Index)},))
        if len(laga) > batas:
            st.button(f"Tampilkan {min(JUMLAH_AWAL, len(laga) - batas)} laga lagi",
                      key="tambah-laga", on_click=_tambah_batas, width="stretch")
        return laga


def tampil() -> None:
    df = muat_pertandingan(str(JALUR_DATA))
    klub_saya = st.session_state.get("klub", "Arsenal")
    klub20 = klub_musim(df, MUSIM_BERJALAN)

    st.markdown(
        '<div class="kepala-hal"><div><h2>Match Analysis</h2>'
        '<p>Simulasikan laga dua klub, atau buka statistik laga yang sudah dimainkan.</p></div></div>',
        unsafe_allow_html=True,
    )
    kol_kiri, kol_kanan = st.columns([1, 1.7], gap="medium")
    with kol_kiri:
        with st.container(key="kolom-laga"):
            _kartu_simulasi(klub20, klub_saya)
            _daftar_laga(df, klub_saya)
    with kol_kanan:
        with st.container(key="kolom-analisis"):
            pilihan = st.session_state.get("analisis")
            if pilihan is None:
                st.markdown('<div class="kartu-kosong">Pilih laga di kiri atau jalankan simulasi.</div>',
                            unsafe_allow_html=True)
            elif pilihan["mode"] == "sim":
                tampil_simulasi(df, pilihan["k"], pilihan["t"])
            else:
                st.markdown(panel_laga(df, pilihan["id"]), unsafe_allow_html=True)
