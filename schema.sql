CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_uuid TEXT,
    title VARCHAR(50),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    street_address VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    postcode VARCHAR(30),
    phone_cleaned VARCHAR(50),
    cell_cleaned VARCHAR(50),
    dob_date DATE,
    age_at_ingestion INTEGER,
    picture_thumbnail_url TEXT,
    raw_cleaned_data JSONB,
    ingestion_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    airflow_run_id VARCHAR(255)
);

CREATE INDEX IF NOT EXIST idx_users_email ON users(email);
CREATE INDEX IF NOT EXIST idx_users_country ON users(country);
CREATE INDEX IF NOT EXIST idx_users_ingestion_timestamp ON users(ingestion_timestamp);

COMMENT ON COLUMN users.user_uuid IS 'UUID unik pengguna dari sumber data (jika ada).';
COMMENT ON COLUMN users.title IS 'Gelar pengguna (Mr, Ms, etc.).';
COMMENT ON COLUMN users.first_name IS 'Nama depan pengguna.';
COMMENT ON COLUMN users.last_name IS 'Nama belakang pengguna.';
COMMENT ON COLUMN users.email IS 'Alamat email pengguna (unik).';
COMMENT ON COLUMN users.street_address IS 'Alamat jalan lengkap (nomor dan nama jalan).';
COMMENT ON COLUMN users.city IS 'Kota tempat tinggal pengguna.';
COMMENT ON COLUMN users.state IS 'Negara bagian/provinsi tempat tinggal pengguna.';
COMMENT ON COLUMN users.country IS 'Negara tempat tinggal pengguna.';
COMMENT ON COLUMN users.postcode IS 'Kode pos pengguna.';
COMMENT ON COLUMN users.phone_cleaned IS 'Nomor telepon rumah yang sudah dibersihkan.';
COMMENT ON COLUMN users.cell_cleaned IS 'Nomor telepon seluler yang sudah dibersihkan.';
COMMENT ON COLUMN users.dob_date IS 'Tanggal lahir pengguna.';
COMMENT ON COLUMN users.age_at_ingestion IS 'Usia pengguna saat data dimasukkan (berdasarkan field dob.age dari API).';
COMMENT ON COLUMN users.picture_thumbnail_url IS 'URL ke gambar thumbnail pengguna.';
COMMENT ON COLUMN users.raw_cleaned_data IS 'Data JSON lengkap yang sudah dibersihkan dan divalidasi.';
COMMENT ON COLUMN users.ingestion_timestamp IS 'Timestamp kapan data ini dimasukkan ke database.';
COMMENT ON COLUMN users.airflow_run_id IS 'ID dari Airflow DAG run yang memproses data ini.';