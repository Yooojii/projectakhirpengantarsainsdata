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


# ------------------------------------------------------------- sebaran gol/xG

def sebar_xg(titik: list[dict], sorot: str | None, aksen: str) -> str:
    """Gol aktual terhadap gol harapan; garis putus-putus adalah titik impas."""
    # viewBox dibuat selebar kartu supaya sebaran mengisi ruang; rasio tetap dijaga
    # agar titiknya bulat, bukan lonjong.
    w, h, pad = 300, 116, 14
    label = "Gol aktual terhadap gol harapan tiap klub"
    if not titik:
        return _bingkai_pas("", w, h, label)
    semua = [t["gol"] for t in titik] + [t["xg"] for t in titik]
    lo, hi = min(semua), max(semua)
    marjin = (hi - lo) * 0.12 or 0.1
    lo, hi = lo - marjin, hi + marjin
    rentang = hi - lo

    def px(v: float) -> float:
        return pad + (v - lo) / rentang * (w - 2 * pad)

    def py(v: float) -> float:
        return h - pad - (v - lo) / rentang * (h - 2 * pad)

    bentuk = [
        f'<line x1="{px(lo):.1f}" y1="{py(lo):.1f}" x2="{px(hi):.1f}" y2="{py(hi):.1f}" '
        f'stroke="{KABUT}" stroke-width="1" stroke-dasharray="4 3"/>'
    ]
    for t in titik:
        aktif = sorot is not None and t["klub"] == sorot
        warna = aksen if aktif else (NAVY if t["selisih"] > 0 else KABUT)
        r = 4.6 if aktif else 3.2
        bentuk.append(
            f'<circle cx="{px(t["xg"]):.1f}" cy="{py(t["gol"]):.1f}" r="{r}" fill="{warna}"'
            + (' stroke="#FFFFFF" stroke-width="1.4"' if aktif else "") + "/>"
        )
    return _bingkai_pas("".join(bentuk), w, h, label)


# ------------------------------------------------------------------ donat

def donat(irisan: list[dict], aksen: str) -> str:
    """Tiga irisan, lubang di tengah berisi angka terbesar."""
    w = 120
    r = 42
    keliling = 2 * math.pi * r
    warna = [aksen, "#5A8FA3", PUDAR]
    bentuk = []
    mulai = 0.0
    for i, bagian in enumerate(irisan):
        panjang = keliling * bagian["nilai"] / 100
        bentuk.append(
            f'<circle cx="{w / 2}" cy="{w / 2}" r="{r}" fill="none" stroke="{warna[i]}" '
            f'stroke-width="17" stroke-dasharray="{panjang:.2f} {keliling - panjang:.2f}" '
            f'stroke-dashoffset="{-mulai:.2f}" transform="rotate(-90 {w / 2} {w / 2})"/>'
        )
        mulai += panjang
    utama = max(irisan, key=lambda b: b["nilai"])
    bentuk.append(
        f'<text x="{w / 2}" y="{w / 2 + 2}" text-anchor="middle" font-family="{_HURUF}" '
        f'font-size="22" font-weight="600" fill="{NAVY}">{utama["nilai"]:.0f}%</text>'
    )
    label = "Proporsi hasil pertandingan"
    return _bingkai_pas("".join(bentuk), w, w, label)


# --------------------------------------------------------------- batang tegak

def batang_tegak(items: list[dict], aksen: str, sorot: str | None = None) -> str:
    """Distribusi gol per laga; batang tertinggi memakai navy, sisanya memudar."""
    w, h = 200, 100
    dasar, atas = 86, 6
    puncak = max(b["persen"] for b in items) or 1
    lebar = w / len(items)
    bentuk = []
    for i, b in enumerate(items):
        tinggi = (b["persen"] / puncak) * (dasar - atas)
        x = i * lebar + lebar * 0.16
        bw = lebar * 0.68
        kuat = b["persen"] >= puncak * 0.85
        warna = aksen if (sorot is not None and b["gol"] == sorot) else (NAVY if kuat else "#5A8FA3")
        bentuk.append(
            f'<rect x="{x:.1f}" y="{dasar - tinggi:.1f}" width="{bw:.1f}" height="{tinggi:.1f}" '
            f'rx="2" fill="{warna}"/>'
            f'<text x="{x + bw / 2:.1f}" y="{h - 3}" text-anchor="middle" font-family="{_HURUF}" '
            f'font-size="11" fill="{KABUT}">{escape(b["gol"])}</text>'
        )
    return _bingkai("".join(bentuk), w, h, "Distribusi jumlah gol per pertandingan")


# -------------------------------------------------------------------- radar

def radar(seri: list[dict], sumbu: list[str], aksen: str) -> str:
    """Segi lima; deret bertanda sorot digambar penuh warna aksen, sisanya garis tipis."""
    w, h = 380, 260
    pusat_x, pusat_y, jari = w / 2, h / 2, 96
    sudut = [(-90 + i * 72) * math.pi / 180 for i in range(len(sumbu))]

    def titik(nilai: list[float], skala: float = 1.0) -> str:
        p = []
        for a, v in zip(sudut, nilai):
            rr = jari * (0.18 + 0.82 * max(0.0, min(1.0, v))) * skala
            p.append(f"{pusat_x + rr * math.cos(a):.1f},{pusat_y + rr * math.sin(a):.1f}")
        return " ".join(p)

    satu = [1.0] * len(sumbu)
    bentuk = [
        f'<polygon points="{titik(satu)}" fill="none" stroke="{GARIS}" stroke-width="1"/>',
        f'<polygon points="{titik(satu, 0.6)}" fill="none" stroke="{PUDAR}" stroke-width="0.8"/>',
    ]
    for a in sudut:
        bentuk.append(
            f'<line x1="{pusat_x}" y1="{pusat_y}" x2="{pusat_x + jari * math.cos(a):.1f}" '
            f'y2="{pusat_y + jari * math.sin(a):.1f}" stroke="{PUDAR}" stroke-width="0.8"/>'
        )
    netral = [NAVY, "#4C7F96", "#7FA6B5", "#A9C2CC"]
    for i, s in enumerate(seri):
        if s.get("sorot"):
            bentuk.append(
                f'<polygon points="{titik(s["nilai"])}" fill="{aksen}" fill-opacity="0.16" '
                f'stroke="{aksen}" stroke-width="2"/>'
            )
        else:
            warna = KABUT if len(seri) == 2 else netral[i % len(netral)]
            gaya = ' stroke-dasharray="4 3"' if len(seri) == 2 else ""
            bentuk.append(
                f'<polygon points="{titik(s["nilai"])}" fill="none" stroke="{warna}" '
                f'stroke-width="1.5"{gaya}/>'
            )
    for a, nama in zip(sudut, sumbu):
        lx, ly = pusat_x + (jari + 25) * math.cos(a), pusat_y + (jari + 25) * math.sin(a)
        kos = math.cos(a)
        anchor = "middle" if abs(kos) < 0.2 else ("start" if kos > 0 else "end")
        bentuk.append(
            f'<text x="{lx:.1f}" y="{ly + 3.5:.1f}" text-anchor="{anchor}" '
            f'font-family="{_HURUF}" font-size="14" fill="{KABUT}">{escape(nama)}</text>'
        )
    return _bingkai_pas("".join(bentuk), w, h, "Radar lima ukuran performa")


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
    for b in items:
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
            f'style="width:{lebar:.1f}%;background:{warna}"></span></span>'
            f'<span class="deret-angka">{b["nilai"]}</span></div>'
        )
    if tambahan is not None:
        lebar = 100 * tambahan["nilai"] / puncak
        baris.append(
            f'<div class="deret-baris sorot tambahan">'
            f'<span class="deret-nama">{escape(tambahan["klub"])}</span>'
            f'<span class="deret-lajur"><span class="deret-isi" '
            f'style="width:{lebar:.1f}%;background:{aksen}"></span></span>'
            f'<span class="deret-angka">{tambahan["nilai"]}</span></div>'
        )
    return f'<div class="deret">{"".join(baris)}</div>'
