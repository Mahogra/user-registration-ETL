# website_backend/app_realtime_website.py
from flask import Flask, render_template, request 
from flask_socketio import SocketIO
from kafka import KafkaConsumer
from kafka.errors import KafkaError
import json
import logging
import time 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'website_secret_key_ganti_ini_juga_dengan_yang_unik_dan_aman!' 
socketio = SocketIO(
    app, 
    async_mode='eventlet', 
    cors_allowed_origins="*",
    ping_timeout=30,      
    ping_interval=15,     
    logger=False,         
    engineio_logger=False 
)

KAFKA_BROKER_URL = 'kafka:29092' 
KAFKA_TOPIC_CLEAN = 'randomuser-topic-clean'
CONSUMER_GROUP_ID_WEBSITE = 'website-realtime-display-group-v4' 

def get_full_name(user_data):
    if not isinstance(user_data, dict):
        logging.warning(f"[WebsiteBackend] get_full_name menerima data yang bukan dictionary: {type(user_data)}")
        return "Pengguna Anonim"
    name_info = user_data.get('name', {})
    if not isinstance(name_info, dict):
        logging.warning(f"[WebsiteBackend] name_info bukan dictionary di dalam get_full_name: {type(name_info)}")
        return "Pengguna Anonim (Nama Error)"
    title = name_info.get('title', '').strip() if isinstance(name_info.get('title'), str) else ''
    first_name = name_info.get('first', '').strip() if isinstance(name_info.get('first'), str) else ''
    last_name = name_info.get('last', '').strip() if isinstance(name_info.get('last'), str) else ''
    full_name_parts = [p for p in [title, first_name, last_name] if p] 
    return " ".join(full_name_parts) if full_name_parts else "Pengguna Misterius"

def connect_kafka_consumer_website(broker_url, topic, group_id):
    consumer = None
    retry_count = 0
    max_retries = 7 
    wait_seconds = 5 
    while retry_count < max_retries:
        try:
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=[broker_url],
                group_id=group_id,
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                auto_offset_reset='earliest', 
                consumer_timeout_ms=30000 
            )
            logging.info(f"[WebsiteBackend] Kafka consumer terhubung ke topic '{topic}' dengan group_id '{group_id}'.")
            return consumer
        except KafkaError as e:
            logging.error(f"[WebsiteBackend] Gagal menghubungkan Website Kafka consumer ke {topic} (percobaan {retry_count + 1}/{max_retries}): {e}")
            retry_count += 1
            if retry_count < max_retries:
                socketio.sleep(wait_seconds) 
            else:
                logging.error(f"[WebsiteBackend] Gagal total menghubungkan Website Kafka consumer ke {topic} setelah {max_retries} percobaan.")
                return None
        except Exception as e_conn: 
            logging.error(f"[WebsiteBackend] Error umum saat mencoba menghubungkan Kafka consumer (percobaan {retry_count + 1}/{max_retries}): {e_conn}", exc_info=True)
            retry_count += 1
            if retry_count < max_retries:
                socketio.sleep(wait_seconds) 
            else:
                logging.error(f"[WebsiteBackend] Gagal total menghubungkan Website Kafka consumer (error umum) setelah {max_retries} percobaan.")
                return None

def kafka_consumer_background_task():
    logging.info("[WebsiteBackend] KAFKA CONSUMER BACKGROUND TASK telah dimulai oleh server.")
    # === TAMBAHKAN JEDA AWAL DI SINI ===
    initial_wait_seconds = 5 # Tunggu 5 detik sebelum koneksi Kafka pertama
    logging.info(f"[WebsiteBackend] (BG Task) Menunggu {initial_wait_seconds} detik sebelum mencoba koneksi Kafka pertama...")
    socketio.sleep(initial_wait_seconds)
    # === AKHIR PENAMBAHAN JEDA AWAL ===

    while True: 
        consumer_website = connect_kafka_consumer_website(KAFKA_BROKER_URL, KAFKA_TOPIC_CLEAN, CONSUMER_GROUP_ID_WEBSITE)
        
        if not consumer_website:
            logging.warning("[WebsiteBackend] (BG Task) Gagal menginisialisasi konsumen Kafka. Mencoba lagi dalam 30 detik.")
            socketio.sleep(30) 
            continue 

        logging.info(f"[WebsiteBackend] (BG Task) Website consumer menunggu pesan dari '{KAFKA_TOPIC_CLEAN}'...")
        message_count_session = 0
        try:
            for message in consumer_website: 
                message_count_session += 1
                logging.info(f"[WebsiteBackend] (BG Task) Pesan ke-{message_count_session} DITERIMA email: {message.value.get('email', 'EMAIL TIDAK ADA') if isinstance(message.value, dict) else 'DATA BUKAN DICT'}")
                
                user_data = None
                try:
                    user_data = message.value 
                    if not isinstance(user_data, dict):
                        logging.error(f"[WebsiteBackend] (BG Task) Format data tidak terduga (bukan dict): {type(user_data)}. Melewati.")
                        continue
                except Exception as e_deserialize:
                    logging.error(f"[WebsiteBackend] (BG Task) Gagal deserialisasi: {e_deserialize}. Melewati.")
                    continue

                full_name = get_full_name(user_data)
                greeting_message = f"Hello {full_name}!"
                
                try:
                    logging.info(f"[WebsiteBackend] (BG Task) AKAN MENGIRIM: '{greeting_message}'")
                    socketio.emit('new_user_greeting', {'message': greeting_message}) 
                    logging.info(f"[WebsiteBackend] (BG Task) TELAH MENGIRIM: '{greeting_message}'")
                    socketio.sleep(0.01) 
                except Exception as e_emit:
                    logging.error(f"[WebsiteBackend] (BG Task) Error saat socketio.emit atau socketio.sleep: {e_emit}", exc_info=True)

            if message_count_session == 0:
                logging.info(f"[WebsiteBackend] (BG Task) Tidak ada pesan baru selama timeout.")
            else:
                logging.info(f"[WebsiteBackend] (BG Task) Selesai memproses {message_count_session} pesan. Timeout tercapai.")

        except Exception as e_loop: 
            logging.error(f"[WebsiteBackend] (BG Task) Error tak terduga di loop Kafka: {e_loop}", exc_info=True)
        finally:
            if consumer_website: 
                consumer_website.close()
                logging.info("[WebsiteBackend] (BG Task) Kafka consumer sesi ini ditutup.")
        
        logging.info("[WebsiteBackend] (BG Task) Mencoba koneksi ulang konsumen Kafka dalam 5 detik...")
        socketio.sleep(5) 

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    sid = request.sid if request else "N/A" 
    logging.info(f"[WebsiteBackend] Klien {sid} terhubung ke WebSocket.")
    socketio.emit('connection_ack', {'message': 'Terhubung ke server real-time!'}, room=sid)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid if request else "N/A"
    logging.info(f"[WebsiteBackend] Klien {sid} terputus dari WebSocket.")

@app.route('/test_emit_manual')
def test_emit_manual_route():
    payload = {'message': 'MANUAL TEST DARI FLASK ROUTE! Hello!'}
    logging.info(f"[WebsiteBackend] Rute /test_emit_manual: AKAN MENGIRIM {payload}")
    try:
        socketio.emit('new_user_greeting', payload) 
        logging.info(f"[WebsiteBackend] Rute /test_emit_manual: TELAH MENGIRIM {payload}")
        socketio.sleep(0.01) 
        return "Pesan tes manual ('new_user_greeting') telah dikirim ke semua klien WebSocket!"
    except Exception as e_manual_emit:
        logging.error(f"[WebsiteBackend] Rute /test_emit_manual: Error saat emit: {e_manual_emit}", exc_info=True)
        return "Gagal mengirim pesan tes manual.", 500

if __name__ == '__main__':
    logging.info("[WebsiteBackend] Mempersiapkan dan memulai background task Kafka consumer...")
    socketio.start_background_task(target=kafka_consumer_background_task)
    # Tidak perlu lagi log "Background task Kafka consumer telah diminta untuk dimulai oleh server."
    # karena log awal di dalam kafka_consumer_background_task() sudah cukup.
    
    logging.info(f"[WebsiteBackend] Memulai Flask-SocketIO server di http://0.0.0.0:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, use_reloader=False)