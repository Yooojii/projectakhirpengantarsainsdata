"""Grafik SVG untuk halaman Overview.

Altair dipakai di halaman lain, tapi kisi yang harus muat satu layar butuh tinggi
yang ditentukan sampai piksel. SVG dengan viewBox tetap memberi itu; Altair tidak,
karena ia menambah tinggi sendiri untuk judul dan sumbu.
"""
import math
from html import escape

NAVY = "#0E3A52"
TEAL = "#157D7B"
KABUT = "#8FA6B0"
GARIS = "#CFD6CC"
PUDAR = "#D9E1E5"

_HURUF = "IBM Plex Sans Condensed, IBM Plex Sans, sans-serif"


def _bingkai(isi: str, w: int, h: int, label: str) -> str:
    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" height="100%" preserveAspectRatio="none" '
        f'role="img" aria-label="{escape(label)}">{isi}</svg>'
    )


def _bingkai_pas(isi: str, w: int, h: int, label: str) -> str:
    """Seperti _bingkai tapi menjaga rasio; untuk bentuk bulat yang tidak boleh gepeng."""
    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" height="100%" '
        f'role="img" aria-label="{escape(label)}">{isi}</svg>'
    )


# --------------------------------------------------------- sparkline KPI mini

def garis_mini(nilai: list[float], naik: bool | None) -> str:
    """Sparkline 60×18 untuk sel KPI; warna mengikuti arah delta."""
    w, h, pad = 60, 18, 2
    if len(nilai) < 2:
        return ""
    lo, hi = min(nilai), max(nilai)
    rentang = (hi - lo) or 1.0
    titik = []
    for i, v in enumerate(nilai):
        x = pad + i * (w - 2 * pad) / (len(nilai) - 1)
        y = h - pad - (v - lo) / rentang * (h - 2 * pad)
        titik.append((x, y))
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in titik)
    warna = "#15803D" if naik is True else ("#B91C1C" if naik is False else KABUT)
    return (
        f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'style="display:inline-block;vertical-align:middle;flex-shrink:0">'
        f'<polyline class="garis-mini" pathLength="1" fill="none" stroke="{warna}" stroke-width="1.6" '
        f'opacity="0.55" stroke-linejoin="round" stroke-linecap="round" points="{pts}"/>'
        f'<circle class="titik-mini" cx="{titik[-1][0]:.1f}" cy="{titik[-1][1]:.1f}" r="2.5" fill="{warna}"/>'
        f'</svg>'
    )


# ------------------------------------------------------------------ garis tren

def garis_tren(nilai: list[float], label: str) -> str:
    """Garis satu deret, kisi mendatar dua garis, titik pada puncak dan nilai terakhir."""
    w, h, pad = 200, 100, 8
    if len(nilai) < 2:
        return _bingkai("", w, h, label)
    lo, hi = min(nilai), max(nilai)
    rentang = (hi - lo) or 1.0
    titik = []
    for i, v in enumerate(nilai):
        x = pad + i * (w - 2 * pad) / (len(nilai) - 1)
        y = h - pad - (v - lo) / rentang * (h - 2 * pad)
        titik.append((x, y))
    garis = " ".join(f"{x:.1f},{y:.1f}" for x, y in titik)
    i_puncak = nilai.index(hi)
    return _bingkai(
        f'<line x1="0" y1="{h - pad:.0f}" x2="{w}" y2="{h - pad:.0f}" stroke="{GARIS}" stroke-width="0.8"/>'
        f'<line x1="0" y1="{h / 2:.0f}" x2="{w}" y2="{h / 2:.0f}" stroke="{PUDAR}" stroke-width="0.8"/>'
        f'<polyline fill="none" stroke="{TEAL}" stroke-width="2.4" stroke-linejoin="round" '
        f'stroke-linecap="round" points="{garis}"/>'
        f'<circle cx="{titik[i_puncak][0]:.1f}" cy="{titik[i_puncak][1]:.1f}" r="3" fill="{NAVY}"/>'
        f'<circle cx="{titik[-1][0]:.1f}" cy="{titik[-1][1]:.1f}" r="3" fill="{NAVY}"/>',
        w, h, label,
    )


# ------------------------------------------------------- kandang vs tandang

def _koma(v: float, desimal: int) -> str:
    return f"{v:.{desimal}f}".replace(".", ",")


def kandang_tandang(baris: list[dict], aksen: str, tandang: str = "#5A8FA3") -> str:
    """Grafik kupu-kupu: label di tengah, batang kandang tumbuh ke kiri, tandang ke kanan.

    Panjang batang dihitung terhadap nilai terbesar di barisnya sendiri, jadi sisi yang
    lebih besar selalu penuh. Sisi yang lebih baik ditebalkan (untuk kartu kuning, yang
    lebih sedikit). Saat baris disorot, labelnya bergeser dan memperlihatkan selisihnya.
    """
    from gaya.komponen import angka_hitung  # impor lokal: komponen memuat Streamlit

    isi = [
        '<div class="kt-kepala" aria-hidden="true">'
        f'<span><i style="background:{aksen}"></i>Kandang</span>'
        f'<span>Tandang<i style="background:{tandang}"></i></span></div>'
    ]
    for i, b in enumerate(baris):
        k, t, d = b["kandang"], b["tandang"], b["desimal"]
        puncak = max(k, t) or 1
        unggul_k = (k >= t) if b["lebih_baik_naik"] else (k <= t)
        besar = "Kandang" if k >= t else "Tandang"
        selisih = f"{besar} +{_koma(abs(k - t), d)}"
        teks = f'{b["label"]}: kandang {_koma(k, d)}, tandang {_koma(t, d)}'
        isi.append(
            f'<div class="kt-baris" style="--i:{i}" tabindex="0" aria-label="{escape(teks)}">'
            f'<b class="kt-angka kiri{" kuat" if unggul_k else ""}">{angka_hitung(k, d, 200 + 90 * i)}</b>'
            f'<span class="kt-lajur kiri"><span style="width:{100 * k / puncak:.1f}%;background:{aksen}"></span></span>'
            f'<span class="kt-label"><span class="kt-geser">'
            f'<span>{escape(b["label"])}</span><span class="kt-selisih">{escape(selisih)}</span>'
            f'</span></span>'
            f'<span class="kt-lajur kanan"><span style="width:{100 * t / puncak:.1f}%;background:{tandang}"></span></span>'
            f'<b class="kt-angka kanan{"" if unggul_k else " kuat"}">{angka_hitung(t, d, 260 + 90 * i)}</b>'
            '</div>'
        )
    return f'<div class="kt" role="group" aria-label="Kandang dibanding tandang">{"".join(isi)}</div>'


# ------------------------------------------------------------------ donat

def donat(irisan: list[dict], aksen: str) -> str:
    """Tiga irisan; lubang di tengah selalu berisi irisan pertama (menang / kandang menang).

    Dulu yang ditulis angka terbesar, sehingga klub yang lebih sering kalah tampil
    dengan angka besar yang terbaca seperti persen menang.
    """
    w = 120
    r = 42
    keliling = 2 * math.pi * r
    warna = [aksen, "#5A8FA3", PUDAR]
    bentuk = [f'<circle cx="{w / 2}" cy="{w / 2}" r="{r}" fill="none" stroke="#EEF2F0" stroke-width="17"/>']
    mulai = 0.0
    for i, bagian in enumerate(irisan):
        panjang = keliling * bagian["nilai"] / 100
        bentuk.append(
            # ukuran busur lewat style supaya transisi CSS ikut jalan saat filter diganti
            f'<circle class="busur" cx="{w / 2}" cy="{w / 2}" r="{r}" fill="none" '
            f'stroke="{warna[i]}" stroke-width="17" '
            f'style="--i:{i};stroke-dasharray:{panjang:.2f} {keliling - panjang:.2f};'
            f'stroke-dashoffset:{-mulai:.2f}" transform="rotate(-90 {w / 2} {w / 2})"/>'
        )
        mulai += panjang
    utama = irisan[0]
    bentuk.append(
        f'<g class="donat-teks"><text x="{w / 2}" y="{w / 2 + 3}" text-anchor="middle" font-family="{_HURUF}" '
        f'font-size="22" font-weight="600" fill="{NAVY}">{utama["nilai"]:.0f}%</text>'
        f'<text x="{w / 2}" y="{w / 2 + 16}" text-anchor="middle" font-family="{_HURUF}" '
        f'font-size="7.5" fill="{KABUT}">{escape(utama["label"].lower())}</text></g>'
    )
    label = "Proporsi hasil pertandingan"
    return _bingkai_pas("".join(bentuk), w, w, label)


# --------------------------------------------------------------- batang tegak

def batang_tegak(items: list[dict], aksen: str, sorot: str | None = None) -> str:
    """Distribusi gol per laga sebagai matriks titik: satu titik mewakili dua persen laga.

    Kolom dengan persen tertinggi memakai navy dan labelnya berpil gelap; sisanya teal
    pudar. Titik muncul dari bawah, kolom demi kolom, seperti papan yang terisi.
    """
    per_titik = 2.0
    puncak = max(b["persen"] for b in items) or 1
    kolom = []
    for k, b in enumerate(items):
        kuat = b["persen"] > 0 and b["persen"] >= puncak * 0.85
        if sorot is not None and b["gol"] == sorot:
            warna = aksen
        else:
            warna = NAVY if kuat else "#5A8FA3"
        utuh = int(b["persen"] // per_titik)
        sisa = b["persen"] - utuh * per_titik
        titik = [f'<i style="--i:{i}"></i>' for i in range(utuh)]
        if sisa >= per_titik / 2:  # setengah titik ke atas digambar pudar
            titik.append(f'<i class="lebih" style="--i:{utuh}"></i>')
        persen = f'{b["persen"]:.1f}'.replace(".", ",")
        info = f'{b["gol"]} gol: {persen}% laga ({b["laga"]} laga)'
        kelas = "matriks-kol puncak" if kuat else "matriks-kol"
        kolom.append(
            f'<div class="{kelas}" title="{escape(info)}" style="--warna:{warna};--k:{k}">'
            f'<span class="matriks-tumpuk">{"".join(titik)}'
            f'<span class="matriks-nilai">{b["persen"]:.0f}%</span></span>'
            f'<span class="matriks-label">{escape(b["gol"])}</span></div>'
        )
    return (f'<div class="matriks" role="img" aria-label="Distribusi jumlah gol per pertandingan, '
            f'satu titik sama dengan dua persen laga">{"".join(kolom)}</div>')


# -------------------------------------------------------------------- radar

def skor_lima(v: float) -> float:
    """Skor radar 0-1 (hasil normalisasi antarklub) menjadi skala 1-5."""
    return 1 + 4 * max(0.0, min(1.0, v))


def _koma1(v: float) -> str:
    return f"{v:.1f}".replace(".", ",")


def _d_radar(titik: str) -> str:
    """Bentuk radar sebagai path. Ditulis dua kali: atribut d untuk peramban mana pun, dan
    properti CSS d supaya bentuk bertransisi halus saat filter diganti (Chromium, Firefox)."""
    jalur = "M" + " L".join(titik.split(" ")) + " Z"
    return f"d=\"{jalur}\" style=\"d:path('{jalur}')\""


def radar(seri: list[dict], sumbu: list[str], aksen: str) -> str:
    """Segi lima berskala 1-5; deret bertanda sorot digambar penuh warna aksen, sisanya garis tipis.

    Lima cincin kisi menandai skor 1 sampai 5, dan menyorot sumbu memunculkan kotak
    berisi skor serta angka aslinya.
    """
    w, h = 380, 260
    pusat_x, pusat_y, jari = w / 2, h / 2, 96
    sudut = [(-90 + i * 72) * math.pi / 180 for i in range(len(sumbu))]

    def titik(nilai: list[float], skala: float = 1.0) -> str:
        p = []
        for a, v in zip(sudut, nilai):
            rr = jari * (0.18 + 0.82 * max(0.0, min(1.0, v))) * skala
            p.append(f"{pusat_x + rr * math.cos(a):.1f},{pusat_y + rr * math.sin(a):.1f}")
        return " ".join(p)

    bentuk = []
    # cincin skor 1-5 tanpa angka; skornya dibaca lewat kotak saat sumbu disorot
    for k in range(1, 6):
        v = (k - 1) / 4
        bentuk.append(
            f'<polygon points="{titik([v] * len(sumbu))}" fill="none" '
            f'stroke="{GARIS if k == 5 else PUDAR}" stroke-width="{1 if k == 5 else 0.8}"/>'
        )
    for a in sudut:
        bentuk.append(
            f'<line x1="{pusat_x}" y1="{pusat_y}" x2="{pusat_x + jari * math.cos(a):.1f}" '
            f'y2="{pusat_y + jari * math.sin(a):.1f}" stroke="{PUDAR}" stroke-width="0.8"/>'
        )
    netral = [NAVY, "#4C7F96", "#7FA6B5", "#A9C2CC"]
    for i, s in enumerate(seri):
        if s.get("sorot"):
            bentuk.append(
                f'<path class="radar-bentuk" {_d_radar(titik(s["nilai"]))} fill="{aksen}" fill-opacity="0.16" '
                f'stroke="{aksen}" stroke-width="2"/>'
            )
        else:
            warna = KABUT if len(seri) == 2 else netral[i % len(netral)]
            gaya = ' stroke-dasharray="4 3"' if len(seri) == 2 else ""
            bentuk.append(
                f'<path class="radar-bentuk kedua" {_d_radar(titik(s["nilai"]))} fill="none" stroke="{warna}" '
                f'stroke-width="1.5"{gaya}/>'
            )
    warna_seri = [aksen if s.get("sorot") else (KABUT if len(seri) == 2 else netral[i % len(netral)])
                  for i, s in enumerate(seri)]
    ada_angka = all("mentah" in s for s in seri)
    kotak_info = []
    for i, (a, nama) in enumerate(zip(sudut, sumbu)):
        kos, sin = math.cos(a), math.sin(a)
        lx, ly = pusat_x + (jari + 22) * kos, pusat_y + (jari + 22) * sin
        anchor = "middle" if abs(kos) < 0.2 else ("start" if kos > 0 else "end")
        label = (f'<text class="radar-label" x="{lx:.1f}" y="{ly + 5:.1f}" text-anchor="{anchor}" '
                 f'font-family="{_HURUF}" font-size="17" fill="{KABUT}">{escape(nama)}</text>')
        if not ada_angka:
            bentuk.append(label)
            continue
        # area sorot selebar 34 unit sepanjang sumbu sampai label, plus lingkaran di label
        penanda = "".join(
            f'<circle class="radar-penanda" cx="{pusat_x + jari * (0.18 + 0.82 * max(0.0, min(1.0, s["nilai"][i]))) * kos:.1f}" '
            f'cy="{pusat_y + jari * (0.18 + 0.82 * max(0.0, min(1.0, s["nilai"][i]))) * sin:.1f}" '
            f'r="4.5" fill="{warna_seri[j]}" stroke="#FFFFFF" stroke-width="1.5"/>'
            for j, s in enumerate(seri)
        )
        bentuk.append(
            f'<g class="radar-info" data-i="{i}" tabindex="0" role="button" '
            f'aria-label="{escape(_teks_radar(nama, seri, i))}">'
            f'<line x1="{pusat_x}" y1="{pusat_y}" x2="{lx:.1f}" y2="{ly:.1f}" stroke="transparent" '
            f'stroke-width="34" stroke-linecap="round"/>'
            f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="28" fill="transparent"/>'
            f'{penanda}{label}</g>'
        )
        kotak_info.append(_kotak_radar(nama, seri, warna_seri, i, lx, ly, w, h, pusat_y))
    # kotak angka digambar paling akhir supaya tidak tertutup label sumbu lain
    return _bingkai_pas("".join(bentuk + kotak_info), w, h, "Radar lima ukuran performa")


# satuan angka asli tiap sumbu radar dan jumlah desimalnya
SATUAN_RADAR = {
    "Serangan": ("tembakan per laga", 1, ""),
    "Ketajaman": ("tembakan jadi gol", 1, "%"),
    "Pertahanan": ("gol kebobolan per laga", 2, ""),
    "Disiplin": ("kartu kuning per laga", 2, ""),
    "Bola mati": ("sepak pojok per laga", 1, ""),
}


def _angka_radar(nama: str, nilai: float) -> str:
    _, desimal, akhiran = SATUAN_RADAR.get(nama, ("", 2, ""))
    return f"{nilai:.{desimal}f}".replace(".", ",") + akhiran


def _teks_radar(nama: str, seri: list[dict], i: int) -> str:
    satuan = SATUAN_RADAR.get(nama, ("",))[0]
    isi = ", ".join(f'{s["nama"]} skor {_koma1(skor_lima(s["nilai"][i]))} dari 5 '
                    f'({_angka_radar(nama, s["mentah"][i])} {satuan})' for s in seri)
    return f"{nama}: {isi}"


def _kotak_radar(nama: str, seri: list[dict], warna: list[str], i: int,
                 lx: float, ly: float, w: int, h: int, pusat_y: float) -> str:
    """Kotak skor 1-5 satu sumbu; muncul saat sumbunya disorot atau difokus."""
    # huruf setara label sumbu (17 unit): radar digambar kecil, huruf lebih kecil tak terbaca
    lebar, baris = 260, 26
    tinggi = 34 + baris * len(seri) + 26
    x = min(max(lx - lebar / 2, 2), w - lebar - 2)
    # di bawah label untuk sumbu atas, di atas label untuk sumbu bawah: tetap di dalam radar
    y = ly + 14 if ly < pusat_y else ly - tinggi - 16
    y = min(max(y, 2), h - tinggi - 2)
    isi = [
        f'<rect width="{lebar}" height="{tinggi}" rx="10" fill="#FFFFFF" stroke="#E1E6DF"/>',
        f'<text x="14" y="25" font-family="{_HURUF}" font-size="18" font-weight="600" '
        f'fill="#0E1F18">{escape(nama)}</text>',
    ]
    for j, s in enumerate(seri):
        yy = 34 + baris * j + 18
        isi.append(
            f'<circle cx="19" cy="{yy - 5}" r="5" fill="{warna[j]}"/>'
            f'<text x="32" y="{yy}" font-family="{_HURUF}" font-size="16" fill="#0E1F18">'
            f'{escape(s["nama"])}</text>'
            f'<text x="{lebar - 14}" y="{yy}" text-anchor="end" font-family="{_HURUF}" font-size="18" '
            f'font-weight="600" fill="#0E1F18">{_koma1(skor_lima(s["nilai"][i]))}'
            f'<tspan font-size="13" font-weight="400" fill="{KABUT}"> / 5</tspan></text>'
        )
    isi.append(
        f'<text x="14" y="{tinggi - 11}" font-family="{_HURUF}" font-size="12.5" fill="{KABUT}">'
        'Skor 1–5 dibanding klub lain</text>'
    )
    return f'<g class="radar-tip" data-i="{i}" transform="translate({x:.1f},{y:.1f})">{"".join(isi)}</g>'


# --------------------------------------------------------- batang mendatar

def batang_mendatar(items: list[dict], aksen: str, sorot: str | None = None,
                    tambahan: dict | None = None) -> str:
    """Daftar klub dengan batang proporsional. Dipakai untuk jumlah gelar.

    `tambahan` adalah klub yang sedang difilter tapi tidak masuk daftar; ia digambar
    di bawah garis putus-putus supaya tetap terlihat tanpa mengklaim masuk lima besar.
    """
    if not items:
        return ""
    puncak = max([b["nilai"] for b in items]
                 + ([tambahan["nilai"]] if tambahan else [])) or 1
    ada_sorot = (sorot is not None
                 and (any(b["klub"] == sorot for b in items) or tambahan is not None))
    baris = []
    for i, b in enumerate(items):
        aktif = sorot is not None and b["klub"] == sorot
        if aktif:
            warna = aksen
        elif ada_sorot:
            warna = PUDAR  # yang lain meredup supaya klub terpilih menonjol
        else:
            warna = NAVY if b is items[0] else "#5A8FA3"
        lebar = 100 * b["nilai"] / puncak
        kelas = "deret-baris sorot" if aktif else "deret-baris"
        baris.append(
            f'<div class="{kelas}"><span class="deret-nama">{escape(b["klub"])}</span>'
            f'<span class="deret-lajur"><span class="deret-isi" '
            f'style="width:{lebar:.1f}%;background:{warna};--i:{i}"></span></span>'
            f'<span class="deret-angka">{b["nilai"]}</span></div>'
        )
    if tambahan is not None:
        lebar = 100 * tambahan["nilai"] / puncak
        baris.append(
            f'<div class="deret-baris sorot tambahan">'
            f'<span class="deret-nama">{escape(tambahan["klub"])}</span>'
            f'<span class="deret-lajur"><span class="deret-isi" '
            f'style="width:{lebar:.1f}%;background:{aksen};--i:{len(items)}"></span></span>'
            f'<span class="deret-angka">{tambahan["nilai"]}</span></div>'
        )
    return f'<div class="deret">{"".join(baris)}</div>'
