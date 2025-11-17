from flask import Flask, Response, jsonify, render_template_string
import cv2
import serial
import time
import imutils
import threading
import numpy as np
import os # Adicionado para garantir compatibilidade

# =================================================================
# CONFIGURAÇÕES RASPBERRY PI
# =================================================================
ARDUINO_PORT = '/dev/ttyACM0'  # VERIFIQUE: Sua porta serial correta
ARDUINO_BAUDRATE = 9600
CAMERA_INDEX = 0               # Geralmente 0 para webcam USB
IMAGE_WIDTH = 128              # Deve corresponder ao modelo CNN
IMAGE_HEIGHT = 128

# =================================================================
# INICIALIZAÇÃO DO FLASK E VARIÁVEIS GLOBAIS
# =================================================================

# 🚩 ESTA LINHA INICIALIZA O OBJETO 'app' E RESOLVE O NameError
app = Flask(__name__) 

# Variável para armazenar o ultimo dado lido do sensor
sensor_data = {"temperature": None, "humidity": None, "timestamp": None}
sensor_lock = threading.Lock() 

# Variáveis da Câmera
last_frame = None 
last_frame_lock = threading.Lock() 

# Armazena a última imagem e dados do sensor CONGELADOS pela ação manual
captured_data = {"image_data": None, "temperature": None, "humidity": None, "timestamp": None}
capture_lock = threading.Lock()

# =================================================================
# THREADS DE LEITURA (Serial e Câmera)
# =================================================================

def get_arduino_data():
    """Lê continuamente os dados do Arduino e atualiza a variável global."""
    try:
        ser = serial.Serial(ARDUINO_PORT, ARDUINO_BAUDRATE, timeout=5)
        time.sleep(2) 
        ser.flushInput()
        print("Thread Serial: Conectada ao Arduino.")

        while True:
            try:
                line_bytes = ser.readline()
                line = line_bytes.decode('utf-8').strip()
                
                if "Temp:" in line and "Hum:" in line:
                    parts = line.split(',')
                    temp = float(parts[0].split(':')[1])
                    hum = float(parts[1].split(':')[1])
                    
                    with sensor_lock:
                        sensor_data.update({
                            "temperature": temp,
                            "humidity": hum,
                            "timestamp": time.time()
                        })
                
            except Exception as e:
                # Trata erros temporários de leitura/decodificação
                time.sleep(0.1) 
            
    except serial.SerialException as e:
        print(f"Erro Crítico Serial: {e}. Verifique se a porta está correta.")
    except Exception as e:
        print(f"Erro na thread serial: {e}")

def camera_thread_loop():
    """Lê a câmera continuamente e armazena o último frame para o stream."""
    global last_frame
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("Erro Câmera: Não foi possível abrir a webcam.")
        return
        
    print("Thread Câmera: Câmera iniciada.")
    while True:
        ret, frame = cap.read()
        if ret:
            frame = cv2.resize(frame, (IMAGE_WIDTH, IMAGE_HEIGHT))
            with last_frame_lock:
                last_frame = frame.copy()
        
        time.sleep(0.05)
    
    cap.release()

# Inicia as threads
sensor_thread = threading.Thread(target=get_arduino_data, daemon=True)
sensor_thread.start()
camera_thread = threading.Thread(target=camera_thread_loop, daemon=True)
camera_thread.start()


# =================================================================
# FUNÇÕES DE STREAM E ROTAS FLASK
# =================================================================

def generate_frames():
    """Gera frames JPEG do stream para visualização ao vivo."""
    while True:
        with last_frame_lock:
            frame = last_frame
        
        if frame is None:
            time.sleep(0.1)
            continue
            
        (flag, encodedImage) = cv2.imencode(".jpg", frame)
        if not flag:
            continue

        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')
        time.sleep(0.05)

@app.route("/")
def index():
    """Página com o stream de vídeo ao vivo e o botão de captura."""
    # Página HTML para acesso direto via navegador (ex: celular)
    return render_template_string("""
        <html>
        <head><title>Monitor RPi</title></head>
        <body>
            <h1>Monitoramento de Fungos ao Vivo</h1>
            <img src="{{ url_for('video_feed') }}" width="320" height="240"><br>
            <p>Temperatura: <span id="temp">...</span>°C | Umidade: <span id="hum">...</span>%</p>
            <button onclick="capture()">Fazer Captura Manual e Congelar</button>
            <p id="status">Aguardando Captura...</p>

            <script>
                // Atualiza dados do sensor (opcional, para visualização na RPi)
                function updateSensor() {
                    fetch('/api/sensor').then(r => r.json()).then(data => {
                        document.getElementById('temp').innerText = data.temperature || 'N/A';
                        document.getElementById('hum').innerText = data.humidity || 'N/A';
                    });
                }
                setInterval(updateSensor, 2000); 

                function capture() {
                    document.getElementById('status').innerText = 'Enviando comando de captura...';
                    fetch('/capture')
                        .then(response => response.json())
                        .then(data => {
                            if (data.status === 'OK') {
                                document.getElementById('status').innerText = '✅ Captura CONGELADA! PC Servidor pode buscar.';
                            } else {
                                document.getElementById('status').innerText = '❌ Erro na Captura: ' + data.message;
                            }
                        });
                }
            </script>
        </body>
        </html>
    """)

@app.route("/capture")
def capture_endpoint():
    """ENDPOINT CHAMADO PELO BOTÃO: Congela o frame e os dados do sensor."""
    with last_frame_lock, sensor_lock, capture_lock:
        if last_frame is None or sensor_data["temperature"] is None:
            return jsonify({"status": "ERROR", "message": "Dados da câmera/sensor indisponíveis."}), 500
            
        # CONGELA os dados no momento exato
        captured_data["image_data"] = last_frame.tolist() 
        captured_data["temperature"] = sensor_data["temperature"]
        captured_data["humidity"] = sensor_data["humidity"]
        captured_data["timestamp"] = time.time()
        
        return jsonify({"status": "OK", "message": "Dados congelados."})

@app.route("/api/captured_data")
def captured_data_api():
    """ENDPOINT CHAMADO PELO PC Servidor: Retorna o frame e dados CONGELADOS."""
    with capture_lock:
        if captured_data["image_data"] is None:
            return jsonify({"status": "ERROR", "message": "Nenhuma captura manual realizada."}), 404
        
        # Cria uma cópia para enviar
        data_to_send = captured_data.copy()
        return jsonify({"status": "OK", "data": data_to_send})

@app.route("/api/sensor")
def sensor_api():
    """Rota para a API de dados do DHT11 (ao vivo)."""
    with sensor_lock:
        return jsonify(sensor_data)

@app.route("/video_feed")
def video_feed():
    """Rota para o stream de vídeo MJPEG (visualização ao vivo)."""
    return Response(generate_frames(), mimetype = "multipart/x-mixed-replace; boundary=frame")

if __name__ == '__main__':
    print("\nIniciando servidor Flask na RPi. Acesse http://<IP_RPi>:8080/ no seu navegador.")
    app.run(host='0.0.0.0', port=8080, threaded=True, use_reloader=False)