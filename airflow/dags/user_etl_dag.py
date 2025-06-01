from datetime import datetime, timedelta
import json
import logging
import os # Impor os
import time

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from kafka import KafkaConsumer, TopicPartition # Pastikan KafkaConsumer diimpor
from kafka.errors import KafkaError

# Konfigurasi dari Environment Variables (dengan fallback jika tidak diset)
KAFKA_BROKER_URL = os.getenv('KAFKA_BROKER_URL_FOR_DAG', 'kafka:29092')
KAFKA_TOPIC_CLEAN = 'randomuser-topic-clean'
CONSUMER_GROUP_ID_AIRFLOW = 'airflow-postgres-etl-group'
# ID Koneksi Airflow untuk DB Aplikasi, akan dibuat otomatis oleh AIRFLOW_CONN_POSTGRES_APP_CONN
POSTGRES_APP_CONN_ID = 'postgres_app_conn' 

MAX_MESSAGES_PER_RUN = 100 
CONSUMER_POLL_TIMEOUT_MS = 5000 

log = logging.getLogger(__name__)

def connect_kafka_consumer_dag(broker_url, topic, group_id, timeout_ms):
    consumer = None
    retry_count = 0
    max_retries = 3
    while retry_count < max_retries:
        try:
            consumer = KafkaConsumer(
                # topic, # Topik akan di-assign nanti
                bootstrap_servers=[broker_url],
                group_id=group_id,
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                auto_offset_reset='earliest', 
                consumer_timeout_ms=timeout_ms,
                # enable_auto_commit=False # Jika ingin kontrol commit manual
            )
            log.info(f"Kafka Consumer DAG terhubung ke broker {broker_url} untuk grup {group_id}.")

            # Cek dan assign partisi
            partitions = consumer.partitions_for_topic(topic)
            if not partitions:
                log.warning(f"Tidak ada partisi ditemukan untuk topik {topic} di broker {broker_url}. Menutup consumer.")
                consumer.close()
                return None # Tidak ada partisi, tidak bisa lanjut

            topic_partitions = [TopicPartition(topic, p) for p in partitions]
            consumer.assign(topic_partitions)
            log.info(f"Consumer DAG di-assign ke partisi topik '{topic}'.")
            return consumer
        except KafkaError as e:
            log.error(f"Gagal terhubung Kafka Consumer DAG (percobaan {retry_count+1}): {e}")
            retry_count += 1
            if retry_count < max_retries:
                time.sleep(3)
            else:
                log.error(f"Gagal terhubung Kafka Consumer DAG setelah {max_retries} percobaan.")
                return None

def consume_from_kafka_and_load_to_postgres(**kwargs):
    pg_hook = PostgresHook(postgres_conn_id=POSTGRES_APP_CONN_ID) # Gunakan ID koneksi baru
    conn = None
    cursor = None
    consumer = None
    airflow_run_id = kwargs.get('run_id', 'manual_run') 
    messages_processed = 0

    try:
        consumer = connect_kafka_consumer_dag(
            KAFKA_BROKER_URL, 
            KAFKA_TOPIC_CLEAN, 
            CONSUMER_GROUP_ID_AIRFLOW,
            CONSUMER_POLL_TIMEOUT_MS
        )

        if not consumer:
            log.warning("Consumer Kafka tidak dapat diinisialisasi. Task dilewati.")
            return

        conn = pg_hook.get_conn()
        cursor = conn.cursor()
        log.info(f"Consumer DAG menunggu pesan dari topik '{KAFKA_TOPIC_CLEAN}'...")

        for message in consumer:
            if messages_processed >= MAX_MESSAGES_PER_RUN:
                log.info(f"Mencapai batas maksimum ({MAX_MESSAGES_PER_RUN}) pesan per run DAG.")
                break

            data = message.value
            log.info(f"DAG menerima data dari Kafka: {data.get('email')}")

            name_info = data.get('name', {})
            location_info = data.get('location', {})
            dob_info = data.get('dob', {})
            picture_info = data.get('picture', {})

            dob_date_str = dob_info.get('date')
            parsed_dob_date = None
            if dob_date_str:
                try:
                    parsed_dob_date = datetime.strptime(dob_date_str.split('T')[0], '%Y-%m-%d').date()
                except ValueError:
                    log.warning(f"Format tanggal lahir tidak valid: {dob_date_str}")

            insert_query = """
            INSERT INTO users (
                user_uuid, title, first_name, last_name, email,
                street_address, city, state, country, postcode,
                phone_cleaned, cell_cleaned, dob_date, age_at_ingestion,
                picture_thumbnail_url, raw_cleaned_data, airflow_run_id
            ) VALUES (
                %(user_uuid)s, %(title)s, %(first_name)s, %(last_name)s, %(email)s,
                %(street_address)s, %(city)s, %(state)s, %(country)s, %(postcode)s,
                %(phone)s, %(cell)s, %(dob_date)s, %(age)s,
                %(picture_thumbnail)s, %(raw_cleaned_data)s, %(airflow_run_id)s
            )
            ON CONFLICT (email) DO UPDATE SET
                title = EXCLUDED.title, first_name = EXCLUDED.first_name, last_name = EXCLUDED.last_name,
                street_address = EXCLUDED.street_address, city = EXCLUDED.city, state = EXCLUDED.state,
                country = EXCLUDED.country, postcode = EXCLUDED.postcode, phone_cleaned = EXCLUDED.phone_cleaned,
                cell_cleaned = EXCLUDED.cell_cleaned, dob_date = EXCLUDED.dob_date,
                age_at_ingestion = EXCLUDED.age_at_ingestion, picture_thumbnail_url = EXCLUDED.picture_thumbnail_url,
                raw_cleaned_data = EXCLUDED.raw_cleaned_data, ingestion_timestamp = CURRENT_TIMESTAMP,
                airflow_run_id = EXCLUDED.airflow_run_id;
            """
            try:
                params = {
                    "user_uuid": data.get('login'), "title": name_info.get('title'),
                    "first_name": name_info.get('first'), "last_name": name_info.get('last'),
                    "email": data.get('email'), "street_address": location_info.get('street_address'),
                    "city": location_info.get('city'), "state": location_info.get('state'),
                    "country": location_info.get('country'), "postcode": location_info.get('postcode'),
                    "phone": data.get('phone'), "cell": data.get('cell'),
                    "dob_date": parsed_dob_date, "age": dob_info.get('age'),
                    "picture_thumbnail": picture_info.get('thumbnail'),
                    "raw_cleaned_data": json.dumps(data), "airflow_run_id": airflow_run_id
                }
                if not (params["first_name"] and params["last_name"] and params["email"]):
                    log.error(f"Data tidak lengkap untuk email {params['email']}. First_name, last_name, email wajib ada.")
                    continue
                cursor.execute(insert_query, params)
                messages_processed += 1
            except Exception as e_insert:
                log.error(f"Gagal memasukkan data untuk email {data.get('email')}: {e_insert}")
                if conn: conn.rollback() # Rollback jika error per pesan
            else:
                if conn: conn.commit() # Commit per pesan atau per batch

        if messages_processed > 0: 
            log.info(f"Berhasil memproses dan memuat {messages_processed} pesan ke PostgreSQL.")
        else: 
            log.info("Tidak ada pesan baru untuk diproses dalam run DAG ini atau batas waktu tercapai.")

    except Exception as e_outer:
        log.error(f"Error dalam task ETL Airflow: {e_outer}", exc_info=True)
        if conn: conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        if consumer:
            consumer.close()
            log.info("Kafka consumer dalam task Airflow DAG ditutup.")

default_args = {
    'owner': 'airflow', 
    'depends_on_past': False, 
    'email_on_failure': False,
    'email_on_retry': False, 
    'retries': 1, 
    'retry_delay': timedelta(minutes=2), # Naikkan sedikit retry delay
    'start_date': datetime(2024, 1, 1), # Sesuaikan tanggal mulai
}

with DAG(
    dag_id='user_data_kafka_to_postgres_etl', # Nama DAG
    default_args=default_args,
    description='ETL data pengguna dari Kafka ke PostgreSQL setiap 5 menit',
    schedule_interval=timedelta(minutes=5), 
    catchup=False, 
    tags=['data-engineering', 'kafka', 'postgres', 'etl_project'],
) as dag:

    consume_and_load_task = PythonOperator(
        task_id='consume_from_kafka_and_load_to_db',
        python_callable=consume_from_kafka_and_load_to_postgres,
    )