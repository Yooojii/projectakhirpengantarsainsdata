"""Identitas klub: warna aksen dan singkatan tiga huruf."""

NETRAL = "#6B7A72"

# Warna utama kostum. Klub yang warna utamanya putih/pucat (Tottenham, Fulham, Swansea,
# Derby, Leeds) memakai warna kedua (navy/hitam/biru) supaya
# aksen tetap terbaca di latar #F4F6F2.
WARNA = {
    "Arsenal": "#DB0007",
    "Aston Villa": "#7A003C",
    "Birmingham": "#0B3FA8",
    "Blackburn": "#2F6DB5",
    "Blackpool": "#E8731A",
    "Bolton": "#1B2A5C",
    "Bournemouth": "#C8102E",
    "Bradford": "#8C1D40",
    "Brentford": "#E30613",
    "Brighton": "#0057B8",
    "Burnley": "#6C1D45",
    "Cardiff": "#0070B5",
    "Charlton": "#D4021D",
    "Chelsea": "#034694",
    "Coventry": "#59B3E6",
    "Crystal Palace": "#1B458F",
    "Derby": "#1A1A1A",  # putih -> hitam
    "Everton": "#003399",
    "Fulham": "#1A1A1A",  # putih -> hitam
    "Huddersfield": "#0E63AD",
    "Hull": "#F5A12D",
    "Ipswich": "#3A64A3",
    "Leeds": "#1D428A",  # putih -> biru tua
    "Leicester": "#003090",
    "Liverpool": "#C8102E",
    "Luton": "#F78F1E",
    "Man City": "#6CABDD",
    "Man United": "#DA291C",
    "Middlesbrough": "#E21A23",
    "Newcastle": "#241F20",
    "Norwich": "#00A650",
    "Nott'm Forest": "#DD0000",
    "Portsmouth": "#001C58",
    "QPR": "#1D5BA4",
    "Reading": "#004494",
    "Sheffield United": "#EE2737",
    "Southampton": "#D71920",
    "Stoke": "#E03A3E",
    "Sunderland": "#EB172B",
    "Swansea": "#1A1A1A",  # putih -> hitam
    "Tottenham": "#132257",  # putih -> navy
    "Watford": "#FBEE23",
    "West Brom": "#122F67",
    "West Ham": "#7A263A",
    "Wigan": "#1F5FA8",
    "Wolves": "#FDB913",
}

# Kode eksplisit untuk semua klub yang akan bertabrakan bila diturunkan dari
# tiga huruf pertama (BLA, MAN, WES), plus yang kodenya berbeda dari konvensi.
SINGKATAN = {
    "Blackburn": "BLB",
    "Blackpool": "BLP",
    "Man City": "MCI",
    "Man United": "MUN",
    "West Brom": "WBA",
    "West Ham": "WHU",
    "Nott'm Forest": "NFO",
}


def warna_klub(nama: str) -> str:
    return WARNA.get(nama, NETRAL)


def singkatan(nama: str) -> str:
    return SINGKATAN.get(nama, nama[:3].upper())
