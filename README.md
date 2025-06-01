# Proyek Portofolio: Sistem Streaming Data Real-time dan Batch ETL dengan Apache Kafka & Airflow

## Deskripsi Proyek

Proyek ini mendemonstrasikan pembangunan pipeline data modern yang mengambil data pengguna dari API publik (`randomuser.me`), mengalirkannya secara real-time menggunakan Apache Kafka, melakukan validasi dan pembersihan data (data validation & cleansing), menyimpan data terverifikasi ke PostgreSQL secara batch dengan penjadwalan menggunakan Apache Airflow, dan menampilkan sebagian data (sapaan pengguna) secara live di website.

Proyek ini dirancang untuk menunjukkan pemahaman konsep streaming data real-time sekaligus batch processing dalam satu pipeline terpadu, serta penerapan best practice data engineering.

## Fitur Utama

* Pengambilan data periodik dari API publik.
* Streaming data real-time menggunakan Apache Kafka.
* Validasi data (misalnya, format email, field wajib tidak kosong).
* Pembersihan data (misalnya, normalisasi nama, standarisasi format).
* Orkestrasi dan penjadwalan proses ETL batch (setiap 5 menit) menggunakan Apache Airflow.
* Penyimpanan data bersih ke database PostgreSQL.
* Tampilan data pengguna ("Hello {nama lengkap}!") secara real-time di website menggunakan Flask-SocketIO dan WebSockets.
* Seluruh aplikasi dijalankan dalam lingkungan Docker yang terisolasi dan mudah direplikasi menggunakan Docker Compose.
* Monitoring pipeline ETL melalui UI Airflow.

## Direktori Projek
```
user-registration-ETL
├── docker-compose.yml
├── producer/
│   ├── Dockerfile
│   ├── producer.py
│   └── requirements.txt
├── consumer_validator/
│   ├── Dockerfile
│   ├── consumer_validator.py
│   └── requirements.txt
├── website_backend/
│   ├── Dockerfile
│   ├── app_realtime_website.py
│   ├── templates/
│   │   └── index.html
│   └── requirements.txt
├── airflow/
│   ├── Dockerfile
│   ├── dags/
│   │   └── user_etl_dag.py
│   ├── logs/                   # Dibuat oleh Docker saat runtime
│   ├── plugins/                # Kosongkan jika tidak ada plugin custom         
│   └── airflow.env.example     # Contoh file environment untuk Airflow, untuk dijalankan maka edit agar menjadi airflow.env
│   └── requirements_airflow.txt
├── postgres_app_data/          # Dibuat oleh Docker (volume untuk data aplikasi)
├── postgres_airflow_data/      # Dibuat oleh Docker (volume untuk metadata Airflow)
├── schema.sql
└── README.md
```
## Alur Kerja Data

1.  **Producer (`producer.py`)**: Mengambil data dari API `randomuser.me` setiap 10 detik dan mengirimkannya ke topik Kafka `randomuser-topic`.
2.  **Validasi & Pembersihan (`consumer_validator.py`)**: Mengkonsumsi pesan dari `randomuser-topic`, melakukan validasi dan pembersihan, lalu mengirimkan data bersih ke topik Kafka `randomuser-topic-clean`.
3.  **ETL Batch dengan Airflow (`user_etl_dag.py`)**: Setiap 5 menit, DAG Airflow mengambil data bersih dari `randomuser-topic-clean` dan menyimpannya ke tabel `users` di database PostgreSQL (`postgres_app_db`).
4.  **Tampilan Real-time Website**:
    * **Backend (`app_realtime_website.py`)**: Server Flask dengan Socket.IO secara kontinu mengkonsumsi data dari `randomuser-topic-clean`.
    * **Frontend (`templates/index.html`)**: Setiap kali backend menerima data baru, ia mengirimkannya ke semua klien web yang terhubung melalui WebSocket, yang kemudian menampilkan pesan "Hello {nama lengkap}!".
5.  **Penyimpanan Data**: Database PostgreSQL (`postgres_app_db`) menyimpan data pengguna yang sudah bersih, dan `postgres_airflow_db` menyimpan metadata untuk Airflow.

## Teknologi yang Digunakan

* **Bahasa Pemrograman**: Python
* **Streaming Data**: Apache Kafka
* **Orkestrasi ETL**: Apache Airflow
* **Database**: PostgreSQL
* **Backend Website**: Flask, Flask-SocketIO, Eventlet
* **Frontend Website**: HTML, JavaScript, Socket.IO Client
* **Kontainerisasi**: Docker, Docker Compose
* **Library Python Utama**: `kafka-python`, `requests`, `psycopg2-binary` (via provider Airflow)

## Prasyarat

* Git
* Docker Desktop (untuk Windows, macOS, atau Linux) yang sudah terinstal dan berjalan.

## Petunjuk Setup dan Menjalankan Aplikasi

1.  **Clone Repositori**:
    ```bash
    git clone [https://github.com/Mahogra/user-registration-ETL.git](https://github.com/Mahogra/user-registration-ETL.git)
    cd user-registration-ETL
    ```

2.  **Siapkan File Environment untuk Airflow**:
    * Salin file contoh environment Airflow:
        ```bash
        cp airflow/airflow.env.example airflow/airflow.env
        ```
    * Buka file `airflow/airflow.env` dengan editor teks.
    * Ganti placeholder `GANTI_DENGAN_KUNCI_RAHASIA_PANJANG_DAN_ACAK_ANDA` untuk `AIRFLOW__WEBSERVER__SECRET_KEY` dengan kunci acak yang kuat dan unik buatan Anda sendiri. Anda bisa menggunakan generator password online atau perintah seperti `openssl rand -hex 32` (jika tersedia) untuk membuatnya.

3.  **Build dan Jalankan Semua Layanan dengan Docker Compose**:
    Dari direktori root proyek, jalankan:
    ```bash
    docker-compose up --build -d
    ```
    * `--build`: Akan membangun image Docker kustom Anda (untuk producer, consumer, website, dan airflow) jika belum ada atau jika Dockerfile berubah.
    * `-d`: Menjalankan kontainer di background (detached mode).
    Proses build pertama kali mungkin memakan waktu beberapa menit.

4.  **Tunggu Semua Layanan Siap**:
    Setelah menjalankan `docker-compose up`, berikan waktu beberapa menit (2-5 menit) agar semua layanan (terutama Kafka dan Airflow) sepenuhnya terinisialisasi dan siap. Anda bisa memantau log masing-masing layanan jika perlu.

5.  **Periksa Status Kontainer**:
    ```bash
    docker-compose ps
    ```
    Pastikan semua layanan memiliki status `Up` atau `Running`, dan layanan Airflow (setelah beberapa saat) menunjukkan `healthy`.

## Mengakses Layanan

* **Website Real-time**:
    * URL: `http://localhost:5000`
    * Anda akan melihat sapaan "Hello {nama lengkap}!" muncul dan diperbarui secara periodik.

* **UI Webserver Apache Airflow**:
    * URL: `http://localhost:8080`
    * Login: Gunakan kredensial default `admin` / `admin`.
    * **Penting**: Setelah login, cari DAG `user_data_kafka_to_postgres_etl`. Jika statusnya "paused" (tombol toggle abu-abu/mati), klik tombol tersebut untuk mengaktifkannya (Unpause). DAG akan mulai berjalan sesuai jadwal (setiap 5 menit).

* **Database Aplikasi PostgreSQL (`user_data_db`)**:
    * Host: `localhost`
    * Port: `5432`
    * Database: `user_data_db`
    * User: `appuser`
    * Password: `apppassword`
    (Bisa diakses menggunakan tool database seperti DBeaver, pgAdmin, atau `psql` via `docker-compose exec postgres_app_db psql -U appuser -d user_data_db`)

* **Database Metadata Airflow (`airflow_db`)**:
    * Host: `localhost`
    * Port: `5433`
    * Database: `airflow_db`
    * User: `airflow`
    * Password: `airflow`

## Cara Memverifikasi Fungsionalitas

1.  **Website**: Buka `http://localhost:5000` dan lihat apakah pesan "Hello..." muncul dan diperbarui.
2.  **Airflow**: Buka `http://localhost:8080`, unpause DAG `user_data_kafka_to_postgres_etl`, dan tunggu beberapa menit. Periksa apakah DAG runs berhasil (berwarna hijau). Lihat log task untuk detail.
3.  **PostgreSQL**: Setelah DAG Airflow berjalan sukses, konek ke `postgres_app_db` (seperti cara di atas) dan jalankan query `SELECT * FROM users ORDER BY ingestion_timestamp DESC LIMIT 10;` untuk melihat data yang masuk.

## Menghentikan Aplikasi

Untuk menghentikan semua layanan yang berjalan:
```bash
docker-compose down
