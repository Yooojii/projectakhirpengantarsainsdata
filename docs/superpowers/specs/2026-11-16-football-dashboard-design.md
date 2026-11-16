# Desain Dashboard Liga Inggris — Ruang Kerja Pelatih

Tanggal: 16 November 2026
Mata kuliah: Pengantar Sains Data — Tugas Projek Sesi UAS
Status: menunggu persetujuan

---

## 1. Maksud dan alasannya

Ini dashboard kelompok untuk UAS Pengantar Sains Data. Tapi kalau dibangun sebagai laporan praktikum yang dipindah ke layar, hasilnya akan sama dengan punya kelompok lain: tujuh bab berurutan, satu grafik per bab, tidak ada yang betul-betul dipakai orang.

Jadi dashboard ini dibangun untuk satu orang yang jelas: **pelatih klub Liga Inggris yang sedang menyiapkan pertandingan akhir pekan.** Setiap keputusan desain dijawab dengan pertanyaan "apakah ini membantu dia hari Selasa pagi?". Poin-poin rubrik tetap tercakup seluruhnya, tapi disusun mengikuti cara pelatih bekerja, bukan mengikuti urutan bab.

Yang membuatnya berbeda dari dashboard sepakbola biasa: dashboard ini tidak berhenti di "berapa prediksi skornya". Pelatih bisa menggeser atribut pemainnya sendiri dan melihat prediksi bergerak — seperti Football Manager, tapi angkanya berakar pada 9.880 pertandingan nyata.

### Pembagian kerja

| Bagian | Penanggung jawab |
|---|---|
| Pemilihan algoritma, pelatihan, penyetelan, evaluasi | rekan satu kelompok |
| **Perhitungan fitur (`inti/fitur.py`)** | penulis dokumen ini — lihat 8.2 untuk alasannya |
| Desain, dashboard Streamlit, lapisan simulasi | penulis dokumen ini |

Dokumen ini berisi satu bagian yang **harus dibaca rekan yang memegang model** (bagian 8). Ada syarat teknis di sana yang kalau dilewat, halaman Simulasi tidak bisa dibangun sama sekali.

### Asal dan status data

Seluruh isi `liga_inggris_gabungan.csv` adalah hasil scraping dari sumber resmi Liga Inggris. Hasil pertandingan, tembakan, pelanggaran, kartu, dan odds adalah angka sebenarnya — bukan dibangkitkan. Klaim "9.880 pertandingan nyata" di halaman Overview sah.

Scraping **belum selesai.** Kolom statistik lanjutan masih tipis dan musim berjalan baru terisi sampai 2 November 2026. Dashboard dibangun di atas data yang ada sekarang, dan dirancang supaya bertambah lengkap sendiri ketika berkas CSV ditukar dengan hasil scraping yang final. Batas lapisan buatan diatur di 7.7, dan batas itu tidak boleh digeser tanpa menulis ulang bagian ini.

---

## 2. Pengguna

**Pelatih klub Liga Inggris.** Paham sepakbola luar dalam, tidak paham dan tidak peduli istilah statistik. Membaca di ruang kerja, kadang di layar besar dari jarak satu meter. Waktunya sedikit. Pertanyaannya tiga: *seberapa berat lawan berikutnya, pola apa yang berulang, dan apa yang berubah kalau susunan saya diubah.*

**Pengguna kedua: dosen penguji.** Dia tidak dilayani lewat navigasi, tapi lewat kelengkapan isi. Semua poin rubrik harus bisa ditunjuk dalam hitungan detik saat presentasi.

---

## 3. Tujuan, bukan tujuan, dan kegagalan

**Tujuan**

1. Mencakup tujuh poin rubrik secara utuh dan bisa ditunjuk saat presentasi.
2. Memprediksi hasil dan skor pertandingan mendatang dari model yang dilatih rekan kelompok.
3. Menyediakan ruang simulasi: ubah atribut pemain, prediksi ikut bergerak, dan perubahannya masuk akal.
4. Terbaca oleh orang yang tidak pernah kuliah statistik.

**Bukan tujuan**

- Bukan aplikasi taruhan. Odds dipakai hanya sebagai pembanding akurasi model, tidak pernah sebagai saran bertaruh.
- Bukan basis data pemain. Lapisan pemain adalah simulasi, dan selalu diberi label demikian.
- Bukan multi-liga. Hanya Liga Inggris.
- Tidak ada autentikasi, tidak ada penyimpanan di server, tidak ada akun pengguna.

**Yang membuatnya gagal walaupun secara teknis jalan**

- Dosen tidak bisa menemukan satu poin rubrik.
- Slider digeser, angka prediksi tidak bergerak, atau bergerak ke arah yang berlawanan dengan akal sehat.
- Tampilannya seperti template Streamlit bawaan: abu-abu, serba kotak, judul besar tanpa alasan.
- Pelatih harus membaca definisi istilah sebelum bisa memakai halamannya.

---

## 4. Batasan

| Batasan | Konsekuensi |
|---|---|
| Streamlit | Tata letak terbatas pada kolom dan kontainer. Gaya visual lewat penyuntikan CSS. Tidak ada animasi rumit. |
| Data level pertandingan saja | Tidak ada satu pun baris data pemain. Seluruh lapisan pemain harus dibangkitkan. Lihat bagian 7. |
| Dataset berhenti di pekan 9 musim 2026/27 | Tidak ada jadwal laga mendatang. Harus dibangkitkan. Lihat 6.4. |
| Scraping belum selesai | Dashboard dibangun di atas data yang ada dan bertambah lengkap sendiri saat CSV ditukar. Batas lapisan buatan di 7.7. |
| Statistik kaya hanya 102 laga (1%) | Possession, umpan, dan xG dari API tidak bisa dipakai melatih model. Hanya boleh tampil sebagai catatan di Overview. |
| `xg_kandang` dan `xg_tandang` hanya ada di 2026/27 | Kolom terpisah dari `xg_api_*`. Terisi 90 dari 90 laga musim berjalan, nol di 26 musim lain. Tidak boleh jadi fitur. Lihat 8.4. |
| Musim 2003/04 dan 2004/05 masing-masing hanya 335 laga | Kurang 45 laga, tersebar bukan satu blok. Grafik tren per musim akan menampilkan cekungan palsu. Lihat 6.4. |
| Kolom `pekan` tidak terpakai | Hanya 102 baris terisi, semuanya di 2024/25, bernilai 1–11. Penomoran pekan dibuang dari seluruh antarmuka. Lihat 6.5 dan 7.6. |
| Odds lengkap sejak 2019/20, tapi tidak ada untuk laga mendatang | Model **tidak boleh** memakai odds sebagai fitur. Lihat 8.3. |
| Tenggat UAS | Lingkup dikunci pada empat halaman. Tidak ada penambahan halaman. |

---

## 5. Pendekatan yang dipertimbangkan

Tiga susunan navigasi diajukan sebelum keputusan diambil.

**A — Laporan linear dengan simulator terpisah.** Tujuh menu mengikuti urutan rubrik persis, ditambah menu kedelapan khusus simulator.
*Untung:* paling aman dinilai, paling cepat dibangun.
*Rugi:* delapan menu terasa seperti PDF yang dipaginasi, dan simulatornya yatim — tidak ada bab yang menjelaskan kenapa dia ada.

**B — Bab Modeling menjadi ruang simulasi.** Tujuh menu, satu banding satu dengan rubrik, tapi bab Modeling dipecah jadi tiga sub-tab: Model, Evaluasi, Match Lab.
*Untung:* simulasi jadi bukti bab Modeling, bukan lampiran.
*Rugi:* masih tujuh menu. Navigasinya tetap bicara bahasa rubrik, bukan bahasa pelatih.

**C — Hub bertema permainan.** Navigasi memakai metafora klub: Ruang Ganti, Papan Data, Scouting, Lab Taktik, Match Day.
*Untung:* paling imersif dan paling berbeda.
*Rugi:* penguji harus menebak bab mana yang mana. Metafora berisiko menelan isi.

**D — Yang dipilih: empat halaman, penjelasan ditumpuk di depan.**
Navigasi dipotong jadi **Overview, EDA Liga, History, Prediksi & Simulasi**. Seluruh penjelasan akademik — latar belakang, tujuan, gambaran data, pembersihan data, spesifikasi model — ditumpuk di halaman Overview, sebagian terbuka dan sebagian terlipat, tanpa memakan slot navigasi.

**Alasan dipilih:** pendekatan A dan B menyusun navigasi menurut kebutuhan penilai, padahal penilai hanya datang sekali. C menyusunnya menurut tema, yang menyenangkan tapi menyembunyikan isi. D menyusunnya menurut cara pelatih berpikir, dan menyelesaikan kebutuhan rubrik lewat kedalaman halaman, bukan lewat lebar navigasi. Empat kata di sidebar adalah bentuk paling minimalis yang masih mencakup segalanya.

---

## 6. Arsitektur informasi

### 6.1 Peta rubrik ke halaman

| Poin rubrik | Letaknya |
|---|---|
| 1. Project Overview — judul, latar belakang, tujuan | Overview, bagian atas, terbuka |
| 2. Data Overview | Overview, bagian tengah, terbuka |
| 3. Exploratory Data Analysis | Halaman EDA Liga, seluruhnya |
| 4. Data Preprocessing | Overview, blok terlipat "Bagaimana data dibersihkan" |
| 5. Modeling | Spesifikasi di Overview, blok terlipat "Model yang dipakai". Hasil dan evaluasinya di halaman Prediksi & Simulasi |
| 6. Key insights | Prediksi & Simulasi, bagian bawah, judul "Apa yang kami temukan" |
| 7. Kesimpulan dan rekomendasi | Prediksi & Simulasi, bagian paling bawah, judul "Rekomendasi untuk pelatih" |

Keputusan penulis: poin 6 dan 7 diletakkan di akhir halaman Prediksi, bukan di Overview, karena temuan adalah hasil, bukan pengantar. Untuk pelatih urutannya juga lebih masuk akal — ini prediksinya, ini artinya, ini sarannya.

### 6.2 Kerangka yang tetap ada di setiap halaman

Sidebar ramping berisi, dari atas ke bawah:

1. **Pemilih klub.** Satu dropdown, 20 klub musim berjalan. Pilihan ini menentukan warna aksen seluruh aplikasi dan menjadi "klub saya" di setiap halaman. Ini satu-satunya tempat warna bermain.
2. **Empat tautan halaman.** Hanya teks, tanpa ikon.
3. **Satu baris keterangan data** di kaki sidebar: cakupan dan tanggal terakhir.

Tidak ada header global, tidak ada logo, tidak ada breadcrumb. Setiap halaman mulai dengan isinya sendiri.

### 6.3 Halaman Overview

```
┌──────────┬────────────────────────────────────────────────┐
│          │ Sabtu, 21 November 2026                        │
│ Arsenal ▾│                                                │
│          │ ARSENAL           2 – 1            TOTTENHAM   │
│ Overview │ ───────────────────( )──────────────────────   │
│ EDA Liga │ menang 54%      seri 24%        kalah 22%      │
│ History  │                                                │
│ Prediksi │ Sembilan ribu delapan ratus delapan puluh      │
│          │ pertandingan sejak tahun 2000. Dashboard ini   │
│          │ memerasnya jadi satu hal: apa yang masuk akal  │
│          │ dilakukan hari Sabtu.                          │
│          │                                                │
│          │ Yang bisa dijawab di sini                      │
│          │   Seberapa berat lawan berikutnya              │
│          │   Pola apa yang berulang di liga               │
│          │   Apa yang berubah kalau form pemain naik      │
│          │                                                │
│          │ Data                                           │
│          │ 9.880 laga   27 musim   46 klub   56 kolom     │
│          │ [tabel kelengkapan per kelompok kolom]         │
│          │                                                │
│          │ ▸ Bagaimana data dibersihkan                   │
│          │ ▸ Model yang dipakai dan cara mengujinya       │
└──────────┴────────────────────────────────────────────────┘
```

**Hero.** Laga berikutnya klub yang dipilih, bukan judul besar. Alasannya: itu hal pertama yang dicari pelatih, dan sekaligus memperlihatkan kemampuan utama dashboard dalam satu tatapan. Judul proyek muncul sebagai baris kecil di atas tanggal.

**Latar belakang dan tujuan** ditulis sebagai prosa pendek berbahasa pelatih, maksimal dua paragraf, lebar baris di bawah 70 karakter.

**Data Overview** berisi empat angka ringkas, lalu satu tabel kelengkapan yang mengelompokkan 56 kolom jadi lima kelompok: identitas laga, hasil, statistik dasar, odds, statistik lanjutan. Kolom terakhir tabel itu jujur menyebutkan statistik lanjutan hanya terisi satu persen, dan karena itu tidak dipakai melatih model.

**Dua blok terlipat** memuat preprocessing dan spesifikasi model. Terlipat secara bawaan supaya pelatih tidak menabrak dinding teks, tapi tetap satu klik dari permukaan saat presentasi.

### 6.4 Halaman EDA Liga

Satu halaman, menggulir, tanpa tab. Setiap bagian adalah satu pertanyaan pelatih yang dijawab satu grafik dan satu kalimat temuan. Urutannya:

1. **Berapa gol yang wajar?** Distribusi gol per laga, tuan rumah dan tamu.
2. **Seberapa nyata keuntungan main di kandang?** Tingkat kemenangan kandang per musim, 27 musim. Apakah menurun?
3. **Apakah menembak banyak berarti menang?** Tembakan terhadap gol, dan akurasi tembakan terhadap gol. Mana yang lebih menentukan.
4. **Kapan gol terjadi?** Perbandingan skor babak pertama dengan skor akhir.
5. **Apakah disiplin berpengaruh?** Kartu dan pelanggaran terhadap hasil.
6. **Siapa yang konsisten?** Rata-rata poin per laga tiap musim untuk klub yang bertahan lama di liga.

Dua bagian lagi sudah ditulis tapi **tidur** sampai scraping selesai, sesuai 7.7: **"Apakah menguasai bola berarti menang?"** (possession terhadap hasil) dan **"Seberapa dekat gol dengan peluang yang diciptakan?"** (xG terhadap gol). Keduanya muncul sendiri begitu cakupan kolomnya lewat 60%.

Kontrol yang disediakan: satu penggeser rentang musim di atas halaman, berlaku untuk semua grafik. Tidak ada filter lain. Satu kontrol untuk satu halaman adalah batas minimalis yang dipegang.

**Dua musim yang datanya tidak utuh.** Musim 2003/04 dan 2004/05 masing-masing hanya berisi 335 dari 380 laga. Kalau dibiarkan, grafik nomor 2 dan nomor 6 akan menunjukkan penurunan di dua musim itu yang disebabkan baris hilang, bukan oleh sepakbola — dan karena judul grafik ditulis sebagai kalimat temuan (9.7), grafiknya akan menyatakan hal yang tidak benar dalam kalimat utuh.

Keputusan penulis: semua grafik tren per musim memakai **ukuran per laga**, bukan jumlah total. Tingkat kemenangan kandang sudah berupa rasio sehingga aman. Grafik nomor 6 diubah dari total poin per musim menjadi **rata-rata poin per laga**. Kedua musim itu tetap ditampilkan, dengan penanda kecil dan satu catatan kaki yang menyebutkan jumlah laganya. Musim 2026/27 yang baru berjalan 90 laga diperlakukan sama.

Setiap grafik menyorot klub yang dipilih di sidebar dengan warna aksen klub, sisanya abu-abu. Ini membuat halaman EDA terasa personal tanpa menambah kontrol.

### 6.5 Halaman History

Menjawab "saya pernah ketemu mereka, bagaimana hasilnya".

1. **Pemilih lawan.** Satu dropdown berisi 19 klub lain di musim berjalan, bukan 46 klub sepanjang masa. Klub saya sudah ditentukan dari sidebar.
2. **Rekor pertemuan.** Satu baris: menang–seri–kalah sepanjang masa, dipisah garis tengah lapangan.
3. **Sepuluh pertemuan terakhir** sebagai daftar ringkas: tanggal, kandang, skor, tandang. Hasil klub saya ditandai dengan satu titik warna aksen di tepi kiri, bukan dengan latar belakang berwarna.
4. **Bentuk permainan.** Rangkaian hasil sepuluh laga terakhir kedua klub, berdampingan.
5. **Klasemen musim berjalan** sampai tanggal terakhir yang tersedia, klub saya disorot.

**Ketika riwayatnya tipis atau tidak ada.** Dari 190 pasangan klub musim ini, **6 pasangan belum pernah bertemu sama sekali** dan **33 pasangan punya kurang dari empat pertemuan** — hampir semuanya melibatkan Coventry, Hull, dan Ipswich yang baru naik kasta. Halaman yang seluruh gunanya menjawab "saya pernah ketemu mereka, bagaimana hasilnya" tidak boleh menyodorkan tabel kosong.

Keputusan penulis, tiga keadaan:

| Jumlah pertemuan | Yang ditampilkan |
|---|---|
| 0 | Rekor pertemuan diganti satu kalimat: "Belum pernah bertemu di Liga Inggris." Daftar pertemuan disembunyikan. Bentuk permainan dan klasemen tetap tampil — itu yang tersisa dan itu yang berguna. |
| 1–3 | Rekor dan daftar tetap tampil, disertai satu baris peringatan: "Baru tiga kali bertemu. Terlalu sedikit untuk jadi pola." Peringatan memakai warna kuning kartu. |
| 4 ke atas | Tampilan penuh seperti di atas. |

**Penomoran pekan dibuang.** Kolom `pekan` di dataset hanya terisi 102 baris dan tidak bisa dipakai, sementara tanggal pertandingan tidak jatuh dalam blok mingguan yang rapi — ada jeda dua pekan pada September dan satu laga tunggal pada 2 November. Membangun aturan pengelompokan tanggal menjadi pekan akan menghasilkan angka yang dibaca pelatih sebagai fakta padahal hasil tebakan. Jadi di seluruh antarmuka, waktu disebut dengan tanggal: "Klasemen sampai 2 November 2026."

### 6.6 Halaman Prediksi & Simulasi

```
┌──────────┬────────────────────────────────────────────────┐
│ Arsenal ▾│ Laga  [ Arsenal vs Tottenham  ▾ ]              │
│          │                                                │
│ Overview │ ARSENAL           2 – 1            TOTTENHAM   │
│ EDA Liga │ ───────────────────( )──────────────────────   │
│ History  │ menang 54%      seri 24%        kalah 22%      │
│▸Prediksi │                                                │
│          │ Susunan pemain                                 │
│          │ Saka        KA   penyelesaian  ▇▇▇▇▇▇▇░  82    │
│          │ Havertz     PT   penyelesaian  ▇▇▇▇▇░░░  71    │
│          │ Ødegaard    GT   kreativitas   ▇▇▇▇▇▇▇▇  85    │
│          │ Rice        GT   rebutan bola  ▇▇▇▇▇▇▇░  80    │
│          │                                                │
│          │ Geser angkanya, skor di atas ikut bergerak.    │
│          │                                                │
│          │ Dibanding susunan asli                         │
│          │ Menang  48% → 54%     Gol diharapkan 1,6 → 2,1 │
│          │ [ Kembalikan ke susunan asli ]                 │
│          │                                                │
│          │ Apa yang kami temukan                          │
│          │ Rekomendasi untuk pelatih                      │
└──────────┴────────────────────────────────────────────────┘
```

**Pemilih laga.** Dua sumber, dalam satu dropdown bertingkat: laga terjadwal dari jadwal sisa musim, atau pasangan klub bebas untuk eksperimen.

**Papan prediksi.** Skor paling mungkin dicetak besar dengan angka rata lebar, dipisah lingkaran tengah lapangan. Di bawahnya tiga peluang hasil. Di bawahnya lagi, satu baris kecil: distribusi lima skor teratas beserta peluangnya.

**Dari mana skornya datang, dan kenapa ia tidak boleh bertengkar dengan peluang di bawahnya.** Kontrak model di 8.1 mengembalikan tiga peluang hasil dan dua angka gol harapan — tidak ada distribusi skor di dalamnya. Distribusi skor diturunkan di sisi dashboard dari dua sebaran Poisson atas gol harapan. Masalahnya, skor paling mungkin menurut Poisson bisa saja menyiratkan hasil yang berbeda dari hasil paling mungkin menurut model. Papan yang menulis "2 – 1" di atas "kalah 46%" akan langsung dipertanyakan penguji, dan memang pantas dipertanyakan.

Keputusan penulis: **skor besar adalah skor paling mungkin di antara skor-skor yang menghasilkan hasil terkuat menurut model.** Model menentukan hasilnya, Poisson menentukan skornya di dalam hasil itu. Lima skor teratas di baris bawah diambil dari seluruh distribusi tanpa penyaringan, supaya pelatih tetap melihat kemungkinan lain. Dengan aturan ini angka besar dan tiga peluang di bawahnya tidak pernah saling membantah.

**Susunan pemain.** Sebelas pemain per klub, dalam tabel ringkas. Setiap baris: nama, posisi, satu atribut utama sesuai posisinya, bar atribut, dan angka. Atribut selain yang utama muncul saat baris dibuka. Ini menjaga permukaan tetap sebelas baris, bukan enam puluh enam penggeser.

Susunan **klub saya terbuka**, susunan **lawan terlipat** dan bisa dibuka kalau pelatih ingin memodelkan ancaman lawan. Keduanya bisa diubah. Alasan lawan dilipat: permukaan bawaan halaman ini harus sebelas baris, bukan dua puluh dua. Tombol "Kembalikan ke susunan asli" mengembalikan keduanya sekaligus.

**Umpan balik perubahan.** Satu blok yang hanya muncul setelah ada yang digeser, menampilkan selisih dari keadaan awal. Ini satu-satunya gerakan di seluruh aplikasi, dan gerakannya menjawab perbuatan pengguna.

**Evaluasi model.** Di bagian bawah, sebelum temuan: akurasi model terhadap data uji, dibandingkan dengan dua pembanding — selalu menebak tuan rumah menang, dan menebak mengikuti odds bandar. Pembanding odds inilah yang membuat angka akurasi punya makna.

**Apa yang kami temukan** dan **Rekomendasi untuk pelatih** menutup halaman. Ditulis sebagai kalimat lengkap, bukan daftar berpoin tanpa konteks.

---

## 7. Lapisan pemain simulasi

Dataset tidak punya data pemain. Lapisan ini dibangkitkan, dan cara membangkitkannya adalah inti kejujuran proyek ini.

### 7.1 Prinsip kalibrasi

**Kalau semua penggeser berada di posisi awal, prediksi harus sama persis dengan prediksi model dari data nyata.** Simulasi adalah penyimpangan dari titik nol yang nyata, bukan dunia paralel.

### 7.2 Bentuk datanya

Setiap klub punya 11 pemain inti dan 7 cadangan, formasi bawaan 4-3-3. Setiap pemain punya enam atribut berskala 1–99:

| Atribut | Artinya bagi pelatih | Menggerakkan |
|---|---|---|
| penyelesaian | mengubah peluang jadi gol | akurasi tembakan, konversi |
| kreativitas | menciptakan peluang | jumlah tembakan, sepak pojok |
| penguasaan | menjaga dan mengalirkan bola | jumlah tembakan lawan |
| rebutan bola | merebut dan menghentikan | tembakan lawan, pelanggaran |
| antisipasi | membaca permainan, bertahan | gol kebobolan |
| ketenangan | disiplin di bawah tekanan | kartu |

Kiper memakai satu atribut tambahan, **refleks**, yang menggerakkan penyelamatan dan gol kebobolan.

### 7.3 Cara angkanya dibangkitkan

Untuk setiap klub, hitung rata-rata per laga atas sepuluh laga terakhir menurut definisi jendela di 8.2: tembakan, tembakan tepat, gol, kebobolan, sepak pojok, pelanggaran, kartu kuning. Ubah tiap angka itu jadi persentil klub di dalam liga. Persentil itu menjadi pusat sebaran atribut yang relevan; tiap pemain mendapat simpangan kecil menurut posisinya, dengan benih acak tetap supaya hasilnya sama setiap kali dibuka.

Hasilnya: klub dengan konversi tembakan terbaik di liga mendapat penyerang berpenyelesaian tinggi, bukan karena dikarang, tapi karena itu yang terbaca dari 9.880 laga.

### 7.4 Jalan pulang dari pemain ke model

Fungsi agregasi mengubah 11 pemain kembali menjadi vektor fitur setingkat tim yang dimengerti model:

```
fitur_tim = f(atribut 11 pemain, bobot posisi)
```

Konstanta penskalaan di dalam `f` dipasang sekali per klub sehingga, pada atribut awal, keluarannya **sama persis** dengan rata-rata nyata klub itu dari CSV. Setelah itu setiap pergeseran penggeser menghasilkan pergeseran yang proporsional dan berarah benar.

Keputusan penulis: pemain yang tidak diturunkan ke lapangan tidak berpengaruh sama sekali. Penggantian pemain inti dengan cadangan menghitung ulang fitur tim. Kelelahan, cedera, dan kartu akumulatif tidak dimodelkan — terlalu jauh untuk lingkup UAS.

#### Fitur mana yang digerakkan, dan mana yang tidak

Dari sepuluh fitur di 8.2, tidak semuanya pantas digerakkan oleh atribut pemain. Pemetaannya harus ditulis eksplisit, karena kalau tidak, dua hal buruk terjadi diam-diam: satu fitur digerakkan dua kali lewat jalur berbeda, atau sebuah fitur tertinggal di nilai aslinya dan meredam seluruh simulasi.

| Fitur | Digerakkan oleh | Cara |
|---|---|---|
| rata tembakan | kreativitas, penguasaan | langsung |
| rata tembakan tepat | tembakan × penyelesaian | **turunan**, bukan langsung |
| rasio konversi | penyelesaian | langsung |
| rata gol dicetak | konversi × tembakan | **turunan**, bukan langsung |
| rata sepak pojok | kreativitas | langsung |
| rata pelanggaran | rebutan bola, ketenangan | langsung |
| rata kartu kuning | ketenangan, pelanggaran | langsung |
| rata gol kebobolan | antisipasi, rebutan, refleks kiper | langsung, dari skuad lawan |
| poin lima laga terakhir | — | **dibekukan** |
| penanda kandang | — | ditentukan laga |

Fitur turunan tidak pernah dihitung sendiri dari atribut. Menaikkan penyelesaian menaikkan konversi, dan gol dicetak mengikuti dari konversi dikali tembakan. Kalau gol dicetak juga dihitung langsung dari penyelesaian, satu geseran akan dihitung dua kali dan simulasinya melebih-lebihkan.

**Kenapa bentuk permainan dibekukan.** Poin lima laga terakhir adalah sejarah. Mengubah susunan pemain hari ini tidak mengubah hasil pertandingan bulan lalu, dan memaksanya bergerak berarti mengarang ulang masa lalu. Di antarmuka, fitur ini ditampilkan sebagai angka tetap dengan keterangan: "Bentuk permainan diambil dari hasil nyata dan tidak bisa diubah."

#### Uji penerimaan yang wajib lulus sebelum presentasi

Pembekuan bentuk permainan membawa risiko nyata: kalau model bersandar berat pada fitur itu, seluruh penggeser jadi terasa tumpul, dan itu persis mode kegagalan nomor dua di bagian 3.

Dua uji yang harus lulus:

1. **Uji arah.** Untuk tiap atribut, naikkan 10 poin dari nilai awal pada seluruh pemain yang relevan, dengan sisanya tetap. Gol harapan dan peluang menang harus bergerak ke arah yang benar. Penyelesaian naik harus menaikkan gol harapan; antisipasi naik harus menurunkan gol kebobolan.
2. **Uji kepekaan.** Menyapu satu atribut dari nilai terendah ke tertinggi harus menggeser gol harapan **paling sedikit 0,5 gol**. Kalau tidak tercapai, bobot fitur bentuk permainan dalam model terlalu dominan, dan penanganannya dibicarakan dengan rekan pemodelan sebelum presentasi — bukan ditutupi dengan memperbesar pengali di sisi dashboard.

### 7.5 Nama pemain

Nama dibangkitkan, bukan nama pemain nyata. Alasannya: menempelkan atribut karangan pada nama orang sungguhan membuat angka simulasi mudah disalahartikan sebagai penilaian faktual, dan skuad nyata berubah tiap bursa transfer sehingga cepat meleset. Nama yang dibangkitkan memakai pola nama pesepakbola Inggris dan Eropa supaya tetap terasa wajar.

Di kaki halaman Simulasi, satu baris permanen: *"Atribut pemain adalah data simulasi yang dikalibrasi dari statistik tim, bukan penilaian pemain sungguhan."*

### 7.6 Jadwal laga mendatang

Dataset berhenti pada 2 November 2026 karena scraping belum sampai ke sana, dengan setiap klub sudah memainkan sembilan laga. Sisa jadwal dibangkitkan sebagai kompetisi setengah kompetisi ganda yang melengkapi seluruh pertemuan yang belum terjadi, ditempatkan pada hari Sabtu berurutan mulai 7 November 2026. Jadwal ini diberi label **jadwal simulasi** di antarmuka, dan laganya disebut dengan tanggal, bukan nomor pekan — alasannya ada di 6.5. Pelatih tetap bisa memilih pasangan klub bebas kalau hanya ingin bereksperimen.

### 7.7 Batas lapisan buatan

Scraping belum selesai, jadi godaannya besar untuk menambal setiap lubang dengan angka bangkitan supaya semua halaman terlihat penuh. Godaan itu ditolak. Aturannya satu kalimat:

> **Angka buatan hanya boleh ada di tempat yang memang tidak punya data sama sekali, dan tidak boleh satu pun menyentuh model.**

| Lubang | Keputusan | Alasan |
|---|---|---|
| Data pemain | **Dibangkitkan**, dikalibrasi menurut 7.3 | Nol baris tersedia. Sudah dilabeli simulasi sejak awal, dan kalibrasinya membuatnya bisa dipertanggungjawabkan. |
| Jadwal laga mendatang | **Dibangkitkan** menurut 7.6 | Nol baris tersedia. Dilabeli jadwal simulasi. |
| Statistik lanjutan (possession, umpan, akurasi umpan, xG) | **Dibiarkan kosong** | Mengisinya berarti model berpeluang belajar dari angka yang kita karang sendiri, dan akurasinya jadi mengukur seberapa baik ia menebak karangan kita. Pertanyaan penguji "xG ini dari mana?" harus punya jawaban. |
| 45 laga hilang di 2003/04 dan 2004/05 | **Dibiarkan hilang** | Menambalnya merusak grafik tren 27 musim dengan hasil pertandingan yang tidak pernah terjadi. Ditangani lewat ukuran per laga di 6.4. |

Model hanya memakai sepuluh fitur dasar di 8.2, yang **terisi 100% di seluruh 9.880 laga.** Tidak ada satu pun angka buatan yang masuk ke sana.

**Bagian yang tidur.** Bagian EDA yang membutuhkan statistik lanjutan tetap ditulis sekarang, tapi tidak ditampilkan selama cakupan kolomnya di bawah 60%. Pemeriksaan cakupan dilakukan saat pemuatan data. Begitu rekan kelompok menukar CSV dengan hasil scraping final, bagian-bagian itu muncul sendiri tanpa ada satu baris kode pun yang perlu diubah.

Selama tidur, halaman Overview tetap menyebutkan keberadaan kolom-kolom itu beserta cakupan sebenarnya di tabel kelengkapan. Itu bukan kelemahan yang disembunyikan — itu isi poin rubrik nomor 2, dan menyebut keterbatasan data dengan angka adalah tanda analisis yang jujur.

---

## 8. Kontrak dengan model — untuk rekan yang memegang pemodelan

Bagian ini menentukan apakah halaman Simulasi bisa dibangun. Mohon dibaca sebelum model difinalkan.

### 8.1 Model harus menerima fitur, bukan nama klub

Kalau model dibuat sebagai "masukkan nama tuan rumah dan nama tamu, keluar prediksi", **simulasi tidak mungkin dibuat**, karena menggeser atribut pemain tidak mengubah nama klub. Model harus menerima vektor angka yang bisa dashboard ubah-ubah.

Antarmuka yang dibutuhkan:

```python
predict(fitur_kandang: dict, fitur_tandang: dict) -> {
    "p_menang_kandang": float,
    "p_seri":           float,
    "p_menang_tandang": float,
    "gol_harapan_kandang": float,
    "gol_harapan_tandang": float,
}
```

Disimpan sebagai berkas model terlatih (`joblib` atau `pickle`) beserta daftar nama fitur dan urutannya.

**Label kelas wajib berupa tiga huruf `"H"`, `"D"`, `"A"`** — bukan angka 0/1/2 dan bukan kata penuh. Alasannya bukan selera: scikit-learn mengurutkan label saat melatih, sehingga kolom keluaran `predict_proba` mengikuti urutan `model.classes_`, bukan urutan yang ditulis saat melatih. Dashboard memetakan kolom lewat `classes_`, jadi urutannya aman — tapi kalau labelnya bukan ketiga huruf itu, pemetaan tidak bisa dilakukan dan dashboard menolak memuat model dengan pesan galat yang menyebutkan label yang ditemukan. Gagal keras di awal jauh lebih baik daripada peluang menang kandang dan tandang tertukar diam-diam di layar pelatih.

### 8.2 Fitur yang diminta, dan siapa yang menghitungnya

**Dashboard yang menghitung fitur, bukan pipeline pelatihan.** Janji di 7.1 — penggeser di posisi awal menghasilkan prediksi yang sama persis dengan prediksi model dari data nyata — hanya berlaku kalau fitur yang dipakai saat melatih dan fitur yang dibangkitkan saat simulasi dihitung oleh **kode yang sama persis**. Kalau ada dua implementasi, perbedaan sekecil apa pun membuat titik nol simulasi meleset tanpa ada yang menyadarinya, dan tidak ada uji yang bisa menangkapnya.

Jadi pembagiannya dibalik dari yang biasa: `inti/fitur.py` ditulis lebih dulu di sisi dashboard, dan rekan pemodelan **mengimpor fungsi itu** untuk membangun tabel pelatihannya. Rekan pemodelan memilih algoritma, penyetelan, dan validasi; dia tidak menulis ulang perhitungan fiturnya.

Definisi jendela, dikunci:

- **Sepuluh laga terakhir klub itu, kandang dan tandang digabung**, diurutkan menurut tanggal.
- **Melintasi batas musim.** Setiap klub musim ini baru bermain sembilan laga, jadi jendela sepuluh laga pasti menjangkau musim sebelumnya. Untuk Coventry, laga kesepuluh jatuh pada Mei 2001 — dua puluh lima tahun ke belakang. Ini diterima apa adanya dan disebutkan di blok preprocessing Overview; mempersempit jendela ke dalam satu musim akan membuat klub promosi kehilangan fitur sama sekali.
- **Tidak termasuk laga yang sedang diprediksi.** Hanya laga yang tanggalnya lebih awal.
- Klub dengan kurang dari sepuluh laga sebelumnya memakai laga yang ada, minimum tiga. Di bawah tiga, dipakai rata-rata liga pada musim itu, dan barisnya dibuang dari data pelatihan.

| Fitur | Definisi tepat |
|---|---|
| rata tembakan | jumlah tembakan 10 laga dibagi 10 |
| rata tembakan tepat | jumlah tembakan tepat 10 laga dibagi 10 |
| rasio konversi | **jumlah gol 10 laga dibagi jumlah tembakan 10 laga**, bukan rata-rata dari rasio per laga |
| rata sepak pojok | jumlah dibagi 10 |
| rata pelanggaran | jumlah dibagi 10 |
| rata kartu kuning | jumlah dibagi 10 |
| rata gol dicetak | jumlah dibagi 10 |
| rata gol kebobolan | jumlah dibagi 10 |
| poin lima laga terakhir | 3 menang, 1 seri, 0 kalah, atas 5 laga terakhir. Maksimum 15 |
| penanda kandang | 1 untuk tuan rumah, 0 untuk tamu |

Kalau ada fitur yang dipakai model tapi tidak ada di daftar ini, fitur itu tidak akan bisa digerakkan oleh penggeser. Pemetaan atribut pemain ke fitur ada di 7.4.

### 8.3 Odds tidak boleh menjadi fitur

Odds hanya ada untuk laga yang sudah lewat. Laga mendatang tidak punya odds. Kalau model memakainya sebagai fitur, model tidak akan bisa memprediksi apa pun yang belum terjadi — dan itu seluruh gunanya dashboard ini.

Odds tetap dipakai, tapi di luar model: sebagai pembanding akurasi di bagian evaluasi.

### 8.4 Statistik lanjutan tidak boleh menjadi fitur

Ada **dua kelompok terpisah** yang sama-sama dilarang, dan keduanya perlu disebut karena pola kekosongannya berbeda:

| Kelompok | Kolom | Cakupan |
|---|---|---|
| Statistik API | possession, umpan, akurasi umpan, penyelamatan, offside, `xg_api_*`, `gol_dicegah_*` | 102 laga, seluruhnya 2024/25 |
| xG musim berjalan | `xg_kandang`, `xg_tandang` | 90 laga, seluruhnya 2026/27 |

Kelompok pertama terlalu sedikit untuk melatih. Kelompok kedua menggoda karena tersedia untuk **setiap** laga musim berjalan — tapi nol di 26 musim lainnya, jadi model yang memakainya hanya bisa dilatih pada 90 baris. Keduanya dilarang sebagai fitur.

Di tabel kelengkapan Overview, keduanya masuk kelompok "statistik lanjutan" sebagai dua baris terpisah, dengan cakupan apa adanya dan satu kalimat alasan kenapa tidak dipakai. Kejujuran tabel ini adalah isi poin rubrik nomor 2.

`xg_kandang` boleh **ditampilkan** di halaman History untuk laga musim berjalan sebagai keterangan tambahan, selama tidak masuk model dan diberi catatan bahwa ia hanya ada musim ini.

### 8.5 Evaluasi: apa yang harus rekan pemodelan serahkan

Bagian evaluasi di 6.6 membandingkan akurasi model dengan dua pembanding, dan pembanding odds-lah yang membuat angkanya bermakna. Tapi **odds sama sekali tidak ada sebelum musim 2019/20** dan lengkap sejak itu. Kalau data uji diambil acak dari 27 musim, pembanding odds hanya bisa dihitung pada sekitar 28% baris uji — dan dua angka yang dibandingkan jadi diukur pada sampel berbeda, yang justru meruntuhkan klaim yang ingin dibangun bagian itu.

Dua syarat:

1. **Pembagian data harus menurut waktu, bukan acak**, dan **seluruh data uji berada di dalam musim 2019/20 ke atas.** Usulan: latih pada 2000/01–2023/24, uji pada 2024/25–2025/26.
2. Dashboard **tidak menghitung ulang evaluasi.** Rekan pemodelan menyerahkan dua berkas:

```
model/metrik.json            akurasi, presisi, recall, F1, matriks kebingungan,
                             rentang tanggal data latih dan data uji,
                             kepentingan fitur (kalau algoritmanya menyediakan)
model/prediksi_uji.csv       satu baris per laga uji: tanggal, kedua klub,
                             hasil sebenarnya, hasil prediksi, tiga peluang
```

Dari `prediksi_uji.csv`, dashboard menghitung sendiri dua pembandingnya — selalu menebak tuan rumah menang, dan menebak mengikuti odds terendah — pada baris yang sama persis. Kepentingan fitur, kalau ada, ditampilkan sebagai jawaban atas pertanyaan "apa yang paling menentukan", bukan sebagai grafik berjudul istilah teknis.

### 8.6 Jalan mundur kalau kontrak tidak terpenuhi

Kalau model akhirnya tidak bisa menerima vektor fitur, dashboard memakai lapisan Poisson sederhana di atas gol harapan: gol harapan tiap klub dihitung dari fitur agregat, lalu distribusi skor diturunkan dari dua sebaran Poisson. Akurasinya lebih rendah, tapi halaman Simulasi tetap hidup. Ini jaring pengaman, bukan rencana utama.

---

## 9. Sistem desain

### 9.1 Gagasan dasarnya

**Papan taktik, bukan siaran televisi.** Pelatih tidak butuh gradien dan animasi; dia butuh angka yang terbaca dari jarak satu meter. Satu-satunya perangkat dekoratif yang diizinkan adalah **geometri lapangan**: garis tengah memisahkan tuan rumah dari tamu, lingkaran tengah menjadi tempat skor berdiri. Garis-garis itu membawa informasi — sisi kiri adalah kandang, sisi kanan adalah tamu — bukan menghias.

### 9.2 Warna

| Peran | Nilai | Keterangan |
|---|---|---|
| Latar | `#F4F6F2` | putih dingin bersemu hijau, seperti kertas program pertandingan |
| Teks utama | `#0E1F18` | hijau kehitaman, bukan abu-abu gelap |
| Teks sekunder | `#6B7A72` | |
| Garis | `#CFD6CC` | setipis rambut, dipakai sebagai garis lapangan |
| Permukaan terangkat | `#FFFFFF` | tanpa bayangan, dibedakan hanya oleh garis |
| Peringatan | `#E0A800` | kuning kartu, hanya untuk risiko |
| Bahaya | `#C8102E` | merah kartu, hanya untuk risiko |
| Aksen | warna klub terpilih | satu-satunya warna yang bebas |

Warna klub diambil dari warna utama tiap klub dan disimpan dalam satu tabel. Ia dipakai untuk: sorotan klub saya di grafik, bar atribut pemain klub saya, dan titik penanda hasil. Tidak untuk tombol, tidak untuk latar belakang blok.

Tema dikunci terang. Alasannya: kontras grafik dan bar atribut dirancang untuk satu latar, dan menjaga dua tema berarti menggandakan pekerjaan penyetelan tanpa manfaat bagi pengguna yang membaca di ruang kerja.

### 9.3 Tipografi

Satu keluarga, dua lebar.

- **IBM Plex Sans** — prosa, label, keterangan.
- **IBM Plex Sans Condensed** — angka, tabel, klasemen, papan skor.

Alasannya fungsional, bukan selera: klasemen dan susunan pemain butuh huruf sempit supaya nama klub dan nama pemain muat dalam satu baris tanpa dipotong, dan Plex punya angka rata lebar sehingga kolom skor tidak bergoyang saat angkanya berubah. Bukan Inter dan bukan Roboto, yang akan dipilih siapa pun untuk dashboard apa pun.

Tangga ukuran:

| Peran | Ukuran | Berat | Lebar |
|---|---|---|---|
| Papan skor | 64 px | 600 | condensed |
| Nama klub di papan | 24 px | 500 | condensed |
| Judul bagian | 22 px | 600 | normal |
| Prosa | 16 px, tinggi baris 1,6 | 400 | normal |
| Label dan keterangan | 13 px | 400 | normal |
| Angka dalam tabel | 15 px | 500 | condensed |

Panjang baris prosa dibatasi 68 karakter. Label ditulis dengan huruf kapital di awal kalimat saja — tidak ada label huruf kapital seluruhnya di mana pun.

### 9.4 Jarak dan bentuk

Kelipatan 8 piksel. Jarak antarbagian 48 piksel, jarak dalam bagian 16 piksel. Sudut membulat 4 piksel, seragam, dan hanya pada permukaan yang betul-betul berupa panel. Tidak ada bayangan sama sekali — pemisahan dikerjakan oleh garis dan ruang kosong.

### 9.5 Komponen

**Papan skor.** Nama kandang rata kanan, skor di tengah di dalam lingkaran, nama tamu rata kiri. Satu garis mendatar melintasi seluruh lebar, terputus di lingkaran. Di bawahnya tiga peluang hasil, sejajar dengan tiga posisi yang sama.

**Bar atribut.** Lebar tetap, terbagi delapan ruas, terisi menurut nilai. Terisi dengan warna aksen klub untuk klub saya, abu-abu untuk lawan. Angka di sebelah kanan bar, rata kanan, huruf condensed.

**Tabel.** Tanpa garis vertikal. Garis mendatar setipis rambut hanya di bawah baris judul. Baris genap tidak diberi warna selang-seling. Angka rata kanan, teks rata kiri.

**Grafik.** Tanpa bingkai, tanpa kisi vertikal, kisi mendatar setipis rambut. Satu deret disorot dengan warna aksen, sisanya `#CFD6CC`. Sumbu ditulis dengan kata, bukan singkatan: "Gol per pertandingan", bukan "GPG". Judul grafik adalah kalimat temuan, bukan nama variabel.

**Blok terlipat.** Segitiga kecil dan judul kalimat. Tidak ada ikon lain.

### 9.6 Gerakan

Satu saja: angka prediksi berubah saat penggeser dilepas, dengan transisi warna singkat pada angka yang berubah. Tidak ada animasi masuk halaman, tidak ada efek saat kursor melewati kartu. Preferensi sistem untuk mengurangi gerakan dihormati.

### 9.7 Bahasa

Seluruh antarmuka berbahasa Indonesia, dengan istilah sepakbola yang lazim dipakai penonton Indonesia. Istilah statistik diterjemahkan ke bahasa pelatih: bukan "probabilitas kemenangan tuan rumah" tapi "peluang menang"; bukan "expected goals" tapi "gol yang diharapkan"; bukan "feature importance" tapi "apa yang paling menentukan".

Judul grafik ditulis sebagai temuan. Bukan "Distribusi Gol per Pertandingan", tapi "Lebih dari separuh pertandingan berakhir dengan dua gol atau kurang".

### 9.8 Yang sengaja dibuang

Ikon di navigasi, bayangan di bawah panel, label huruf kapital, animasi masuk, gradien, kartu seragam bersudut bulat sebagai wadah segala hal, dan emoji. Setiap satu dari itu adalah tanda dashboard yang dirakit dari template.

---

## 10. Teknis

```
Football Dashboard/
├── app.py                      # titik masuk, sidebar, routing halaman
├── halaman/
│   ├── overview.py
│   ├── eda_liga.py
│   ├── history.py
│   └── prediksi_simulasi.py
├── inti/
│   ├── data.py                 # pemuatan dan cache CSV
│   ├── fitur.py                # perhitungan fitur setingkat tim
│   ├── pemain.py               # pembangkit dan kalibrasi skuad
│   ├── agregasi.py             # pemain -> fitur tim
│   ├── jadwal.py               # pembangkit jadwal sisa musim
│   ├── model.py                # pemuat model rekan + jalan mundur Poisson
│   └── klub.py                 # nama, singkatan, warna klub
├── gaya/
│   ├── tema.css
│   └── komponen.py             # papan skor, bar atribut, tabel
├── model/
│   ├── model.joblib            # dari rekan kelompok
│   ├── metrik.json             # dari rekan kelompok, lihat 8.5
│   └── prediksi_uji.csv        # dari rekan kelompok, lihat 8.5
├── data/
│   └── liga_inggris_gabungan.csv
└── docs/
```

Pemuatan CSV dan pembangkitan skuad memakai cache Streamlit. Keadaan penggeser disimpan di `st.session_state`, dengan satu salinan nilai awal supaya tombol "Kembalikan ke susunan asli" dan blok selisih bisa bekerja. Benih acak dikunci agar skuad tidak berubah setiap halaman dimuat ulang.

CSS disuntikkan satu kali dari `gaya/tema.css`. Warna aksen klub disisipkan sebagai variabel CSS yang ditulis ulang setiap klub berganti.

---

## 11. Yang diserahkan kepada pembangun

- Pemilihan pustaka grafik, selama hasilnya memenuhi aturan di 9.5. Altair atau Plotly sama-sama bisa.
- Rincian bobot posisi di dalam fungsi agregasi 7.4, selama sifat kalibrasi 7.1 terpenuhi.
- Pola nama pemain yang dibangkitkan.
- Susunan tepat kolom Streamlit untuk mencapai tata letak di 6.3 dan 6.6.
- Isi kalimat temuan di EDA dan Key insights, karena bergantung pada hasil analisis rekan kelompok.

## 12. Risiko

| Risiko | Penanganan |
|---|---|
| Fitur dihitung dua kali, oleh dashboard dan oleh pipeline pelatihan | Satu sumber kebenaran: `inti/fitur.py` ditulis lebih dulu, rekan pemodelan mengimpornya. Lihat 8.2. |
| Bentuk permainan yang dibekukan meredam seluruh penggeser | Uji kepekaan wajib di 7.4: sapuan penuh satu atribut harus menggeser gol harapan minimal 0,5 gol. |
| Skor besar di papan bertentangan dengan peluang di bawahnya | Skor diambil dari dalam hasil terkuat menurut model. Lihat 6.6. |
| Grafik tren menampilkan cekungan palsu di 2003/04 dan 2004/05 | Semua tren per musim memakai ukuran per laga. Lihat 6.4. |
| Model rekan tidak menerima vektor fitur | Kontrak di bagian 8 disampaikan sekarang, sebelum model final. Jaring pengaman Poisson di 8.6. |
| Penggeser menggerakkan prediksi ke arah yang salah | Uji arah untuk tiap atribut: naikkan satu atribut, pastikan gol harapan bergerak ke arah yang benar. Wajib dijalankan sebelum presentasi. |
| Dosen menganggap rubrik tidak lengkap karena navigasi hanya empat | Peta rubrik di 6.1 dicetak sebagai satu slide pembuka presentasi. |
| Streamlit melawan tata letak yang diinginkan | Batasi penyesuaian CSS pada warna, huruf, jarak, dan garis. Jangan melawan sistem kolomnya. |
| Lapisan pemain dikira data nyata | Label permanen di 7.5, dan nama yang dibangkitkan, bukan nama pemain sungguhan. |
| Angka buatan merembes ke dalam model saat menambal lubang scraping | Batas tertulis di 7.7. Model dikunci pada sepuluh fitur dasar yang terisi 100%. |
| Bagian EDA yang tidur tidak pernah bangun karena scraping tak selesai sebelum tenggat | Ambang cakupan 60% diperiksa saat pemuatan. Kalau tidak tercapai, halaman tetap utuh tanpa bagian itu, dan Overview menyebutkan alasannya. |
