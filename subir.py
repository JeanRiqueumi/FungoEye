from flask import Flask, Response, jsonify, render_template_string
import cv2
import serial
import time
import imutils
import threading
import numpy as np

# ... (Configurações e a função get_arduino_data() e sensor_thread são mantidas) ...

# =================================================================
# VARIÁVEIS GLOBAIS DE CAPTURA
# =================================================================
last_frame = None # O último frame lido pela câmera (em array numpy)
last_frame_lock = threading.Lock() 

# Armazena a última imagem e dados do sensor CONGELADOS
captured_data = {"image_data": None, "temperature": None, "humidity": None, "timestamp": None}
capture_lock = threading.Lock()

# =================================================================
# THREAD DE LEITURA E STREAM DA CÂMERA (Atualização)
# =================================================================

def camera_thread_loop():
    """Lê a câmera continuamente e armazena o último frame."""
    global last_frame
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("Erro: Não foi possível abrir a webcam.")
        return
        
    while True:
        ret, frame = cap.read()
        if ret:
            # Redimensiona e armazena o último frame
            frame = cv2.resize(frame, (IMAGE_WIDTH, IMAGE_HEIGHT))
            with last_frame_lock:
                last_frame = frame.copy()
        
        time.sleep(0.05) # Pequeno atraso para não sobrecarregar
    
    cap.release()

# Inicia a thread de leitura contínua da câmera
camera_thread = threading.Thread(target=camera_thread_loop, daemon=True)
camera_thread.start()

def generate_frames():
    """Gera frames JPEG do stream para visualização ao vivo."""
    while True:
        with last_frame_lock:
            frame = last_frame
        
        if frame is None:
            continue
            
        # Codifica o frame para JPEG (para o stream ao vivo)
        (flag, encodedImage) = cv2.imencode(".jpg", frame)
        if not flag:
            continue

        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')
        time.sleep(0.05)

# =================================================================
# NOVAS ROTAS FLASK
# =================================================================

@app.route("/")
def index():
    """Página com o stream de vídeo ao vivo e o botão de captura."""
    # O PC Servidor não precisa mais disso, mas é útil para testar a RPi.
    return render_template_string("""
        <html>
        <head><title>Monitor RPi</title></head>
        <body>
            <h1>Monitoramento de Fungos ao Vivo</h1>
            <img src="{{ url_for('video_feed') }}" width="320" height="240"><br>
            <button onclick="capture()">Fazer Captura Manual</button>
            <p id="status">Aguardando Captura...</p>

            <script>
                function capture() {
                    fetch('/capture')
                        .then(response => response.json())
                        .then(data => {
                            if (data.status === 'OK') {
                                document.getElementById('status').innerText = 'Captura Congelada com sucesso! Pronto para o PC Server.';
                            } else {
                                document.getElementById('status').innerText = 'Erro na Captura: ' + data.message;
                            }
                        })
                        .catch(error => {
                            document.getElementById('status').innerText = 'Erro na Requisição: ' + error;
                        });
                }
            </script>
        </body>
        </html>
    """)

@app.route("/capture")
def capture_endpoint():
    """ENDPOINT CHAMADO AO CLICAR NO BOTÃO: Congela o frame e os dados do sensor."""
    with last_frame_lock, sensor_lock, capture_lock:
        if last_frame is None or sensor_data["temperature"] is None:
            return jsonify({"status": "ERROR", "message": "Dados da câmera/sensor indisponíveis."}), 500
            
        # CONGELA os dados no momento exato
        captured_data["image_data"] = last_frame.tolist() # Converte array numpy para lista serializável
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
        
        # O PC Servidor deve converter a lista de volta para array numpy.
        return jsonify({"status": "OK", "data": data_to_send})

@app.route("/video_feed")
def video_feed():
    """Rota para o stream de vídeo MJPEG (visualização ao vivo)."""
    return Response(generate_frames(), mimetype = "multipart/x-mixed-replace; boundary=frame")

# ... (o main continua rodando o app) ...