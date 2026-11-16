import re
import colorsys
from pathlib import Path

import altair as alt
import pandas as pd
import pytest

from gaya.komponen import (
    BACA_CSS,
    bar_atribut,
    grafik_dasar,
    papan_skor,
    pasang_tema,
    warna_aksen,
)
from inti.data import klub_musim, muat_pertandingan
from inti.klub import NETRAL, WARNA, logo_klub, singkatan, warna_klub

LATAR = "#F4F6F2"
GARIS = "#CFD6CC"
ARSENAL = warna_aksen("#EF0107")  # sudah lolos 4,5:1 setelah digelapkan


def _luminans(heks: str) -> float:
    kanal = []
    for i in (1, 3, 5):
        c = int(heks[i:i + 2], 16) / 255
        kanal.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * kanal[0] + 0.7152 * kanal[1] + 0.0722 * kanal[2]


def kontras(a: str, b: str = LATAR) -> float:
    la, lb = sorted((_luminans(a), _luminans(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _hue(heks: str) -> float:
    r, g, b = (int(heks[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hls(r, g, b)[0]


def _cari(obj, kunci):
    hasil = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == kunci:
                hasil.append(v)
            hasil.extend(_cari(v, kunci))
    elif isinstance(obj, list):
        for v in obj:
            hasil.extend(_cari(v, kunci))
    return hasil


# ---------------------------------------------------------------- warna_aksen

def test_kontras_dihitung_benar():
    assert kontras("#000000", "#FFFFFF") == pytest.approx(21.0)
    assert kontras("#FFFFFF", "#FFFFFF") == pytest.approx(1.0)


@pytest.mark.parametrize("klub", sorted(WARNA))
def test_aksen_setiap_klub_lolos_kontras_45(klub):
    assert kontras(warna_aksen(warna_klub(klub))) >= 4.5


def test_warna_yang_sudah_lolos_tidak_diubah():
    lolos = [h for h in WARNA.values() if kontras(h) >= 4.5]
    assert lolos, "harus ada klub yang sudah lolos"
    for h in lolos:
        assert warna_aksen(h) == h


def test_warna_pucat_digelapkan_dengan_rona_tetap():
    for klub in ["Watford", "Hull", "Man City", "Wolves", "Norwich"]:
        asli = warna_klub(klub)
        aksen = warna_aksen(asli)
        assert aksen != asli
        assert abs(_hue(aksen) - _hue(asli)) < 0.02
        assert _luminans(aksen) < _luminans(asli)


def test_aksen_idempoten_dan_netral_lolos():
    for h in WARNA.values():
        assert warna_aksen(warna_aksen(h)) == warna_aksen(h)
    assert kontras(warna_aksen(NETRAL)) >= 4.5


# ------------------------------------------------------------------------ css

def test_css_memuat_token_warna_dan_tanpa_bayangan():
    css = BACA_CSS()
    for nilai in re.findall(r"box-shadow\s*:\s*([^;}]+)", css):
        assert nilai.replace("!important", "").strip() == "none"
    assert "text-shadow" not in css and "drop-shadow" not in css
    assert "IBM Plex Sans Condensed" in css and "IBM Plex Sans" in css
    assert "fonts.googleapis.com" in css
    assert "tabular-nums" in css


def test_css_token_di_root_dan_aksen_dapat_ditulis_ulang():
    css = BACA_CSS()
    root = re.search(r":root\s*\{([^}]*)\}", css).group(1)
    for token in ["--latar", "--teks", "--aksen", "--garis"]:
        assert token in root


def test_css_tanpa_hal_yang_dilarang():
    css = BACA_CSS().lower()
    assert "gradient" not in css
    assert "uppercase" not in css
    assert ":hover" not in css
    assert "#0b0b0b" not in css and not re.search(r"#111(?![0-9a-f])", css)
    assert not re.search("[\U0001F300-\U0001FAFF←-⇿☀-➿]", css)
    assert "prefers-reduced-motion" in css
    assert "dark" not in css


def test_css_radius_empat_piksel_dan_jarak_kelipatan_delapan():
    css = BACA_CSS()
    for r in re.findall(r"border-radius\s*:\s*([^;}]+)", css):
        assert r.strip() in {"4px", "50%", "0"}
    for ukuran in re.findall(r"(?:margin|padding|gap)[a-z-]*\s*:\s*([^;}]+)", css):
        for angka in re.findall(r"(\d+)px", ukuran):
            assert int(angka) % 8 == 0 or int(angka) == 4, ukuran


def test_css_hanya_satu_gerakan():
    css = BACA_CSS()
    assert css.count("@keyframes") == 1
    assert "transition" not in css


def test_tema_dikunci_terang():
    cfg = Path(__file__).resolve().parent.parent / ".streamlit" / "config.toml"
    assert 'base = "light"' in cfg.read_text(encoding="utf-8")


def test_pasang_tema_menyuntik_css_dengan_aksen_terjamin(monkeypatch):
    kiriman = []
    import gaya.komponen as k
    monkeypatch.setattr(k.st, "markdown", lambda s, **kw: kiriman.append((s, kw)))
    pasang_tema("#FBEE23")  # kuning Watford: harus digelapkan
    assert len(kiriman) == 1
    teks, kw = kiriman[0]
    assert kw.get("unsafe_allow_html") is True
    ekor = teks[teks.rfind(":root"):]
    aksen = re.search(r"--aksen\s*:\s*(#[0-9A-Fa-f]{6})", ekor).group(1)
    assert aksen.upper() == warna_aksen("#FBEE23").upper()
    assert kontras(aksen) >= 4.5


# ----------------------------------------------------------------- papan_skor

PELUANG = {"menang": 0.54, "seri": 0.24, "kalah": 0.22}


def test_papan_skor_memuat_kedua_klub_dan_tiga_peluang():
    h = papan_skor("Arsenal", "Tottenham", (2, 1), PELUANG, ARSENAL)
    assert "Arsenal" in h and "Tottenham" in h
    assert "54" in h and "24" in h and "22" in h
    assert "→" not in h


def test_papan_skor_kandang_sebelum_skor_sebelum_tamu():
    h = papan_skor("Arsenal", "Tottenham", (2, 1), PELUANG, ARSENAL)
    assert h.index("Arsenal") < h.index(">2<") < h.index(">1<") < h.index("Tottenham")


def test_papan_skor_tanpa_gambar_dan_nama_di_escape():
    h = papan_skor("A<b>", "C&D", (0, 0), PELUANG, ARSENAL)
    assert "<svg" not in h.lower() and h.lower().count("<img") <= 2
    assert "<b>" not in h and "&lt;b&gt;" in h and "C&amp;D" in h


# ---------------------------------------------------------------- bar_atribut

def _terisi(h):
    return h.count("terisi")


def test_bar_atribut_delapan_ruas_terisi_proporsional():
    assert bar_atribut(99, ARSENAL).count("ruas") == 8
    assert _terisi(bar_atribut(99, ARSENAL)) == 8
    assert _terisi(bar_atribut(50, ARSENAL)) == 4
    assert _terisi(bar_atribut(0, ARSENAL)) == 0
    assert _terisi(bar_atribut(99, ARSENAL)) > _terisi(bar_atribut(20, ARSENAL))


def test_bar_atribut_angka_di_samping_dan_nilai_di_luar_batas():
    assert ">80<" in bar_atribut(80, ARSENAL)
    assert _terisi(bar_atribut(150, ARSENAL)) == 8
    assert _terisi(bar_atribut(-5, ARSENAL)) == 0


def test_bar_atribut_lawan_abu_dan_klub_saya_aksen():
    assert "#65736C" in bar_atribut(80, None)
    assert ARSENAL not in bar_atribut(80, None)
    assert ARSENAL in bar_atribut(80, ARSENAL)


def test_bar_atribut_aksen_pucat_digelapkan():
    h = bar_atribut(80, "#FBEE23")
    assert "#FBEE23" not in h.upper()
    assert warna_aksen("#FBEE23") in h


# ---------------------------------------------------------------- grafik_dasar

@pytest.fixture
def data():
    baris = []
    for klub, dasar in [("Arsenal", 1.8), ("Chelsea", 1.9), ("Everton", 1.3)]:
        for i, m in enumerate(range(2015, 2020)):
            baris.append({"musim": m, "gol_per_laga": dasar + 0.05 * i, "klub": klub})
    return pd.DataFrame(baris)


def _skala(spec):
    return [v for v in _cari(spec, "scale") if isinstance(v, dict) and "range" in v][0]


def test_grafik_dasar_judul_dari_pemanggil_dan_tanpa_bingkai(data):
    j = "Arsenal mencetak lebih banyak gol tiap musim"
    g = grafik_dasar(data, "musim", "gol_per_laga", j, "Arsenal", ARSENAL,
                     label_x="Musim", label_y="Gol per pertandingan")
    assert isinstance(g, alt.TopLevelMixin)
    s = g.to_dict()
    judul = s["title"]["text"] if isinstance(s["title"], dict) else s["title"]
    assert judul == j
    assert s["config"]["view"]["stroke"] is None


def test_grafik_dasar_kisi_horizontal_saja_warna_garis(data):
    s = grafik_dasar(data, "musim", "gol_per_laga", "J", "Arsenal", ARSENAL).to_dict()
    assert s["config"]["axisX"]["grid"] is False
    assert s["config"]["axisY"]["grid"] is True
    assert s["config"]["axisY"]["gridColor"] == GARIS


def test_grafik_dasar_satu_deret_aksen_sisanya_abu(data):
    s = grafik_dasar(data, "musim", "gol_per_laga", "J", "Arsenal", ARSENAL).to_dict()
    sk = _skala(s)
    peta = dict(zip(sk["domain"], sk["range"]))
    assert peta["Arsenal"].upper() == ARSENAL
    assert peta["Chelsea"] == GARIS and peta["Everton"] == GARIS
    assert None in _cari(s, "legend")


def test_grafik_dasar_aksen_pucat_digelapkan(data):
    s = grafik_dasar(data, "musim", "gol_per_laga", "J", "Arsenal", "#FBEE23").to_dict()
    sk = _skala(s)
    assert dict(zip(sk["domain"], sk["range"]))["Arsenal"] == warna_aksen("#FBEE23")


def test_grafik_dasar_tanpa_sorotan_semua_abu(data):
    s = grafik_dasar(data, "musim", "gol_per_laga", "J", None, ARSENAL).to_dict()
    assert set(_skala(s)["range"]) == {GARIS}


def test_grafik_dasar_sumbu_berkata_bukan_singkatan(data):
    s = grafik_dasar(data, "musim", "gol_per_laga", "J", "Arsenal", ARSENAL,
                     label_x="Musim", label_y="Gol per pertandingan").to_dict()
    judul = {v for v in _cari(s, "title") if isinstance(v, str)}
    assert "Gol per pertandingan" in judul and "Musim" in judul


# --------------------------------------------- CSS: nilai menurut peran (di-parse)

def _aturan():
    css = re.sub(r"/\*.*?\*/", "", BACA_CSS(), flags=re.S)
    css = re.sub(r"@media[^{]*\{.*?\}\s*\}", "", css, flags=re.S)
    css = re.sub(r"@import url\([^)]*\);", "", css)
    css = re.sub(r"@keyframes[^{]*\{.*?\}\s*\}", "", css, flags=re.S)
    hasil = []
    for pemilih, isi in re.findall(r"([^{}]+)\{([^}]*)\}", css):
        props = dict((k.strip(), v.strip().replace("!important", "").strip())
                     for k, v in re.findall(r"([\w-]+)\s*:\s*([^;]+);?", isi))
        hasil.append(([s.strip() for s in pemilih.split(",")], props))
    return hasil


def _prop(pemilih, nama):
    nilai = None
    for daftar, props in _aturan():
        if pemilih in daftar and nama in props:
            nilai = props[nama]
    assert nilai is not None, f"{pemilih} tidak punya {nama}"
    return nilai


def _sempit(pemilih):
    kel = _prop(pemilih, "font-family")
    if kel.startswith("var("):
        kel = _prop(":root", kel[4:-1])
    return "IBM Plex Sans Condensed" in kel.split(",")[0]


def _normal(pemilih):
    kel = _prop(pemilih, "font-family")
    if kel.startswith("var("):
        kel = _prop(":root", kel[4:-1])
    return kel.split(",")[0].strip('" ') == "IBM Plex Sans"


def test_token_root_menurut_peran():
    harapan = {
        "--latar": "#F4F6F2", "--teks": "#0E1F18", "--teks-2": "#65736C",
        "--garis": "#CFD6CC", "--permukaan": "#FFFFFF",
        "--peringatan": "#8A6400", "--bahaya": "#A4161A",
    }
    for token, nilai in harapan.items():
        assert _prop(":root", token) == nilai
    assert _prop(".stApp", "background") == "var(--latar)"
    assert _prop(".stApp", "color") == "var(--teks)"


def test_secondary_text_lolos_kontras_aa():
    assert kontras(_prop(":root", "--teks-2")) >= 4.5


def test_skala_tipografi_papan_skor():
    assert _prop(".papan-lingkaran", "font-size") == "64px"
    assert _prop(".papan-lingkaran", "font-weight") == "600"
    assert _sempit(".papan-lingkaran")
    assert _prop(".papan-nama", "font-size") == "24px"
    assert _prop(".papan-nama", "font-weight") == "500"
    assert _sempit(".papan-nama")


def test_skala_tipografi_judul_prosa_label_tabel():
    assert _prop(".stApp h2", "font-size") == "22px"
    assert _prop(".stApp h2", "font-weight") == "600"
    assert _normal(".stApp h2")
    prosa = '.stApp [data-testid="stMarkdownContainer"] p'
    assert _prop(prosa, "font-size") == "16px"
    assert _prop(prosa, "line-height") == "1.6"
    assert _prop(prosa, "font-weight") == "400"
    assert _prop(prosa, "max-width") == "68ch"
    for label in [".stApp label p", '.stApp [data-testid="stCaptionContainer"] p']:
        assert _prop(label, "font-size") == "13px"
        assert _prop(label, "font-weight") == "400"
    assert _prop("table.tabel td", "font-size") == "15px"
    assert _prop("table.tabel td", "font-weight") == "500"
    assert _sempit("table.tabel td")
    assert _prop("table.tabel td", "text-align") == "right"
    assert _prop("table.tabel td.teks", "text-align") == "left"


def test_label_tidak_dikalahkan_aturan_prosa():
    # p di dalam label/keterangan harus lebih spesifik atau setara dan datang kemudian
    daftar = [d for d, _ in _aturan()]
    urut = {}
    for i, d in enumerate(daftar):
        for s in d:
            urut[s] = i
    prosa = '.stApp [data-testid="stMarkdownContainer"] p'
    for label in [".stApp label p", '.stApp [data-testid="stCaptionContainer"] p']:
        assert urut[label] > urut[prosa]
    assert ".stApp p" not in urut


def test_jarak_dan_bentuk():
    assert _prop(".bagian", "margin-top") == "48px"
    assert _prop(".dalam", "margin-top") == "16px"
    assert _prop('.stApp [data-testid="stVerticalBlock"]', "gap") == "16px"
    assert _prop(".stApp h2", "margin").startswith("48px")
    assert _prop(".panel", "border-radius") == "4px"
    assert _prop(".panel", "padding") == "16px"


def test_tabel_tanpa_garis_tegak_dan_belang():
    assert _prop("table.tabel", "border-collapse") == "collapse"
    assert _prop("table.tabel td", "border") == "0"
    assert _prop("table.tabel th", "border-bottom") == "1px solid var(--garis)"
    assert _prop("table.tabel td", "background") == "transparent"


# ------------------------------------------------------------ gerakan tunggal

def test_papan_skor_berubah_hanya_bila_diminta():
    biasa = papan_skor("Arsenal", "Tottenham", (2, 1), PELUANG, ARSENAL)
    assert "berubah" not in biasa
    h = papan_skor("Arsenal", "Tottenham", (2, 1), PELUANG, ARSENAL, berubah=True)
    assert h.count("angka-prediksi berubah") == 3


# ------------------------------------------------------------- warna klub

def test_arsenal_memakai_merah_aslinya_dan_digelapkan_oleh_aksen():
    assert warna_klub("Arsenal") == "#EF0107"
    assert kontras("#EF0107") < 4.5
    assert warna_aksen("#EF0107") != "#EF0107"


def test_aksen_klub_musim_berjalan_unik_dan_bukan_merah_kartu():
    klub = klub_musim(muat_pertandingan(), "2026/27")
    aksen = {k: warna_aksen(warna_klub(k)) for k in klub}
    assert len(set(aksen.values())) == len(klub)
    assert warna_klub("Bournemouth") != warna_klub("Liverpool")
    assert warna_klub("Bournemouth").upper() != "#C8102E"  # merah asli Liverpool


# ------------------------------------------------------------------- logo

def test_logo_ada_untuk_semua_20_klub_musim_berjalan():
    klub = klub_musim(muat_pertandingan(), "2026/27")
    assert len(klub) == 20
    for k in klub:
        jalur = logo_klub(k)
        assert jalur is not None and jalur.is_file() and jalur.suffix == ".png", k


def test_logo_pemetaan_nama_dataset_ke_manifest():
    assert logo_klub("Hull").name == "hull_city.png"
    assert logo_klub("Nott'm Forest").name == "nottingham_forest.png"
    assert logo_klub("Man City").name == "manchester_city.png"
    assert logo_klub("Bournemouth").name == "afc_bournemouth.png"


def test_logo_klub_tanpa_logo_mengembalikan_none():
    assert logo_klub("Bolton") is None
    assert logo_klub("Klub Antah Berantah") is None


def test_papan_skor_memuat_logo_kecil_atau_singkatan_sebagai_cadangan():
    h = papan_skor("Arsenal", "Bolton", (1, 0), PELUANG, ARSENAL)
    assert h.count("<img") == 1 and "data:image/png;base64," in h
    assert "alt=\"\"" in h
    assert singkatan("Bolton") in h
    assert "width=\"24\"" in h  # tidak lebih besar dari nama klub (24 px)


# ------------------------------------------------- palet: kontras dan pemisahan

def test_setiap_warna_pembawa_makna_lolos_kontras_45():
    for token in ["--teks", "--teks-2", "--peringatan", "--bahaya"]:
        warna = _prop(":root", token)
        assert kontras(warna) >= 4.5, f"{token} {warna} = {kontras(warna):.2f}"


def test_aksen_tidak_ada_klub_yang_sama_dengan_peringatan_atau_bahaya():
    cadangan = {_prop(":root", "--peringatan").upper(), _prop(":root", "--bahaya").upper()}
    for klub in WARNA:
        assert warna_klub(klub).upper() not in cadangan, klub
        assert warna_aksen(warna_klub(klub)).upper() not in cadangan, klub
