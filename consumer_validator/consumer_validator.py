# consumer_validator/consumer_validator.py
import json
import re
import logging
import time # Pastikan time sudah diimpor
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

# Konfigurasi logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')

# Konfigurasi Kafka
KAFKA_BROKER_URL = 'kafka:29092' # Disesuaikan untuk Docker
KAFKA_TOPIC_RAW = 'randomuser-topic'
KAFKA_TOPIC_CLEAN = 'randomuser-topic-clean'
CONSUMER_GROUP_ID = 'user-data-validator-group' # Pastikan group ID unik jika ada beberapa instance
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

def validate_email(email_str):
    """Memvalidasi format email."""
    return bool(email_str and isinstance(email_str, str) and re.match(EMAIL_REGEX, email_str))

def validate_data(user_data):
    """Melakukan validasi dasar pada data user."""
    errors = []
    if not user_data or not isinstance(user_data, dict):
        errors.append("Data user kosong atau bukan format dictionary.")
        return False, errors

    name_info = user_data.get('name', {})
    if not isinstance(name_info, dict):
        errors.append("Informasi 'name' bukan dictionary.")
    else:
        if not (name_info.get('first') and isinstance(name_info.get('first'), str) and name_info.get('first').strip()):
            errors.append("Nama depan tidak boleh kosong atau bukan string.")
        if not (name_info.get('last') and isinstance(name_info.get('last'), str) and name_info.get('last').strip()):
            errors.append("Nama belakang tidak boleh kosong atau bukan string.")

    email = user_data.get('email')
    if not (email and isinstance(email, str)): # Cek apakah email ada dan string
        errors.append("Email tidak boleh kosong atau bukan string.")
    elif not validate_email(email):
        errors.append(f"Format email '{email}' tidak valid.")

    location_info = user_data.get('location', {})
    if not isinstance(location_info, dict):
         errors.append("Informasi 'location' bukan dictionary.")
    else:
        # Validasi lokasi bisa lebih longgar atau disesuaikan dengan kebutuhan data yang pasti ada
        # street_info = location_info.get('street', {})
        # if not isinstance(street_info, dict) or not street_info.get('name') or not street_info.get('number'):
        #      errors.append("Informasi jalan (nama atau nomor) pada lokasi tidak lengkap atau bukan dictionary.")
        if not (location_info.get('city') and isinstance(location_info.get('city'), str) and location_info.get('city').strip()):
            errors.append("Informasi kota pada lokasi tidak boleh kosong atau bukan string.")
        if not (location_info.get('country') and isinstance(location_info.get('country'), str) and location_info.get('country').strip()):
            errors.append("Informasi negara pada lokasi tidak boleh kosong atau bukan string.")
            
    return (not errors), errors

def clean_data(user_data):
    """Membersihkan dan menormalisasi data user."""
    cleaned_data = user_data.copy() # Bekerja dengan salinan data

    name_info = cleaned_data.get('name', {})
    if isinstance(name_info, dict):
        if 'first' in name_info and isinstance(name_info['first'], str):
            name_info['first'] = name_info['first'].strip().title()
        if 'last' in name_info and isinstance(name_info['last'], str):
            name_info['last'] = name_info['last'].strip().title()
        cleaned_data['name'] = name_info

    if 'email' in cleaned_data and isinstance(cleaned_data['email'], str):
        cleaned_data['email'] = cleaned_data['email'].strip().lower()

    location_info = cleaned_data.get('location', {})
    if isinstance(location_info, dict):
        street_info = location_info.get('street', {})
        if isinstance(street_info, dict):
            street_name = street_info.get('name', '').strip() if isinstance(street_info.get('name'), str) else ''
            street_number_val = street_info.get('number')
            street_number = str(street_number_val).strip() if street_number_val is not None else ''
            location_info['street_address'] = f"{street_number} {street_name}".strip()
            if 'street' in location_info: 
                del location_info['street']
        cleaned_data['location'] = location_info

    if 'phone' in cleaned_data and isinstance(cleaned_data['phone'], str):
        cleaned_data['phone'] = re.sub(r'\D', '', cleaned_data['phone'])
    if 'cell' in cleaned_data and isinstance(cleaned_data['cell'], str):
        cleaned_data['cell'] = re.sub(r'\D', '', cleaned_data['cell'])
        
    return cleaned_data

def connect_kafka_consumer(broker_url, topic, group_id):
    """Mencoba terhubung ke Kafka sebagai consumer dengan retry."""
    consumer = None
    retry_count = 0
    max_retries = 5 
    wait_seconds = 5 
    while retry_count < max_retries:
        try:
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=[broker_url],
                auto_offset_reset='earliest', 
                group_id=group_id,
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                consumer_timeout_ms=20000 # Timeout 20 detik jika tidak ada pesan baru
            )
            logging.info(f"Kafka Consumer (validator) terhubung ke topic '{topic}' dengan group_id '{group_id}'.")
            return consumer
        except KafkaError as e:
            logging.error(f"Gagal terhubung Kafka Consumer (validator) ke {topic} (percobaan {retry_count+1}/{max_retries}): {e}")
            retry_count += 1
            if retry_count < max_retries:
                time.sleep(wait_seconds)
            else:
                logging.error(f"Gagal terhubung Kafka Consumer (validator) ke {topic} setelah {max_retries} percobaan.")
                return None

def connect_kafka_producer(broker_url):
    """Mencoba terhubung ke Kafka sebagai producer dengan retry."""
    producer = None
    retry_count = 0
    max_retries = 5
    wait_seconds = 5
    while retry_count < max_retries:
        try:
            producer = KafkaProducer(
                bootstrap_servers=[broker_url],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                retries=5, 
                acks='all' 
            )
            logging.info("Kafka Producer (validator, clean data) terhubung.")
            return producer
        except KafkaError as e:
            logging.error(f"Gagal terhubung Kafka Producer (validator, clean data) (percobaan {retry_count+1}/{max_retries}): {e}")
            retry_count += 1
            if retry_count < max_retries:
                time.sleep(wait_seconds)
            else:
                logging.error(f"Gagal terhubung Kafka Producer (validator, clean data) setelah {max_retries} percobaan.")
                return None

def main():
    logging.info("Memulai Consumer Validator App...")
    while True: 
        consumer_raw = connect_kafka_consumer(KAFKA_BROKER_URL, KAFKA_TOPIC_RAW, CONSUMER_GROUP_ID)
        producer_clean = connect_kafka_producer(KAFKA_BROKER_URL)

        if not consumer_raw or not producer_clean:
            logging.error("Gagal menginisialisasi Kafka Consumer atau Producer di consumer_validator. Mencoba lagi dalam 30 detik...")
            if consumer_raw: consumer_raw.close()
            if producer_clean: producer_clean.close()
            time.sleep(30) 
            continue 

        logging.info(f"Consumer Validator menunggu pesan dari Kafka topic '{KAFKA_TOPIC_RAW}'...")
        message_count_this_session = 0
        try:
            for message in consumer_raw: 
                message_count_this_session += 1
                logging.info(f"Pesan diterima (validator) ke-{message_count_this_session} dari partisi {message.partition} offset {message.offset}")
                
                raw_data = None
                try:
                    raw_data = message.value # value_deserializer sudah melakukan json.loads
                    if not isinstance(raw_data, dict): # Tambahan pengecekan tipe
                        logging.error(f"Format data tidak terduga setelah deserialisasi (bukan dict): {type(raw_data)}. Melewati pesan ini.")
                        continue
                except Exception as e_deserialize:
                    logging.error(f"Gagal deserialisasi pesan dari Kafka: {e_deserialize}. Pesan mentah: {message.value}. Melewati pesan ini.")
                    continue

                is_valid, errors = validate_data(raw_data)
                if is_valid:
                    logging.info(f"Data untuk email '{raw_data.get('email', 'N/A')}' valid (validator), melanjutkan ke pembersihan...")
                    cleaned_data = clean_data(raw_data)
                    logging.debug(f"Data setelah dibersihkan (validator): {json.dumps(cleaned_data, indent=2)}") # Log detail, bisa diubah ke INFO jika perlu
                    try:
                        producer_clean.send(KAFKA_TOPIC_CLEAN, value=cleaned_data)
                        logging.info(f"Data bersih (validator) untuk email '{cleaned_data.get('email')}' berhasil dikirim ke topic '{KAFKA_TOPIC_CLEAN}'.")
                    except KafkaError as e_prod: 
                        logging.error(f"Gagal mengirim data bersih (validator) untuk email '{cleaned_data.get('email')}' ke Kafka: {e_prod}")
                    except Exception as e_send:
                        logging.error(f"Error tak terduga saat mengirim data bersih (validator) untuk email '{cleaned_data.get('email')}': {e_send}", exc_info=True)
                else:
                    logging.warning(f"Data TIDAK VALID (validator) untuk (dugaan) email '{raw_data.get('email', 'N/A')}'. Errors: {errors}. Data mentah: {raw_data}")
            
            if message_count_this_session == 0:
                logging.info(f"Tidak ada pesan baru diterima dari '{KAFKA_TOPIC_RAW}' selama {consumer_raw.config['consumer_timeout_ms']/1000} detik.")
            else:
                logging.info(f"Selesai memproses {message_count_this_session} pesan dalam sesi ini. Consumer timeout tercapai, akan memeriksa lagi.")


        except KeyboardInterrupt: 
            logging.info("Consumer Validator dihentikan oleh pengguna (KeyboardInterrupt).")
            break 
        except Exception as e_loop: 
            logging.error(f"Terjadi error tak terduga pada loop utama consumer_validator: {e_loop}", exc_info=True)
        finally:
            if consumer_raw: 
                consumer_raw.close()
                logging.info("Kafka Consumer (validator) untuk sesi ini ditutup.")
            if producer_clean: 
                producer_clean.flush() 
                producer_clean.close()
                logging.info("Kafka Producer (clean data, validator) untuk sesi ini ditutup.")
        
        logging.info("Consumer Validator akan mencoba koneksi ulang atau memeriksa pesan baru dalam 5 detik...")
        time.sleep(5)

    logging.info("Consumer Validator App telah berhenti.")

if __name__ == "__main__":
    main()