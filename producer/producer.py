import requests
import json
import time
from kafka import KafkaProducer
from kafka.errors import KafkaError
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

KAFKA_BROKER_URL = 'kafka:29092'
KAFKA_TOPIC_RAW = 'randomuser-topic'

producer = None 
try:
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_BROKER_URL],
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        retries=10,
        retry_backoff_ms=1000,
        acks='all'
    )
    logging.info("Kafka Producer berhasil terhubung.")
except KafkaError as e:
    logging.error(f"Gagal terhubung ke Kafka setelah beberapa percobaan: {e}")

API_URL = 'https://randomuser.me/api/?results=1'

def fetch_user_data():
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get('results'):
            return data['results'][0]
        else:
            logging.warning("data 'results' tidak ditemukan dalam respons API")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error saat mengambil data dari API: {e}")
        return None
    except json.JSONDecodeError:
        logging.error("Error saat parsing JSON dari API")
        return None
    
def send_to_kafka(data):
    if producer is None:
        logging.error("Producer tidak terinisialisasi, tidak bisa mengirim data.")
        return False
    
    if not data:
        logging.warning("Tidak ada data untuk dikirim ke Kafka.")
        return False
    
    try:
        user_info= {
            "name": data.get("name", {}),
             "location": data.get("location", {}),
             "email": data.get("email"),
             "login": data.get("login", {}).get("uuid"),
             "dob": data.get("dob", {}),
             "phone": data.get("phone"),
             "cell": data.get("cell"),
             "picture": data.get("picture", {})
        }
        future = producer.send(KAFKA_TOPIC_RAW, value=user_info)
        record_metadata = future.get(timeout=10)
        logging.info(f"Data user berhasil dikirim ke Kafka topic '{KAFKA_TOPIC_RAW}', "
                      f"partition {record_metadata.partition}, offset {record_metadata.offset}")
        return True
    except KafkaError as e:
        logging.error(f"Gagal mengirim data ke Kafka: {e}")
        return False
    except Exception as e:
        logging.error(f"Terjadi error tak terduga saat mengirim ke Kafka: {e}")
        return False
 
if __name__ == "__main__":
     # Tambahkan loop untuk mencoba koneksi producer jika awalnya gagal
    retry_count = 0
    max_retries = 5 # Jumlah percobaan ulang koneksi producer
    while producer is None and retry_count < max_retries:
        logging.info(f"Mencoba menghubungkan Kafka Producer (percobaan {retry_count + 1}/{max_retries})...")
        try:
            producer = KafkaProducer(
                bootstrap_servers=[KAFKA_BROKER_URL],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                retries=10,
                retry_backoff_ms=1000,
                acks='all',
                api_version_auto_timeout_ms=10000 # Timeout untuk handshake API version
             )
            logging.info("Kafka Producer berhasil terhubung.")
            break 
        except KafkaError as e:
            logging.error(f"Gagal menghubungkan Kafka Producer: {e}")
            retry_count += 1
            if retry_count < max_retries:
                time.sleep(5) # Tunggu 5 detik sebelum mencoba lagi
            else:
                logging.error("Gagal menghubungkan Kafka Producer setelah beberapa percobaan. Producer tidak akan berjalan.")
 
    if producer:
        try:
            while True:
                user_data = fetch_user_data()
                if user_data:
                    send_to_kafka(user_data)
                else:
                    logging.info("Tidak ada data user yang diambil, mencoba lagi...")
                time.sleep(10)
        except KeyboardInterrupt:
            logging.info("Producer dihentikan oleh pengguna.")
        finally:
            if producer:
                producer.flush()
                producer.close()
                logging.info("Kafka Producer ditutup.")
    else:
        logging.error("Producer tidak dapat dijalankan karena gagal terhubung ke Kafka.")
