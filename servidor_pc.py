import numpy as np
import cv2
import requests
import time
import os
import threading
from tensorflow.keras.models import load_model # type: ignore
import logging

# Desabilita logs irritantes do TensorFlow
logging.getLogger("tensorflow").setLevel(logging.ERROR)

# =================================================================
# CONFIGURAÇÕES GLOBAIS
# =================================================================
# Mude este IP para o IP REAL da sua Raspberry Pi
RPi_IP = '192.168.0.14' 
RPi_CAPTURE_URL = f"http://{RPi_IP}:8080/api/captured_data"
MODELO_PATH = 'modelo_fungo.h5'      
IMAGE_WIDTH, IMAGE_HEIGHT = 128, 128

# =================================================================
# VARIÁVEIS GLOBAIS COMPARTILHADAS (Com Lock para segurança)
# =================================================================

# Lock para controlar o acesso seguro entre a thread de busca e a thread da GUI
data_lock = threading.Lock() 
model = None

# Variável que armazena o último resultado processado para ser lido pela GUI
latest_prediction_result = {
    "status": "Conectando à RPi...", 
    "temperature": None, 
    "humidity": None,
    "image_frame": None, # Armazena o frame numpy
    "prediction_prob": None
}

# =================================================================
# FUNÇÕES DE ML
# =================================================================

def load_ml_model():
    """Carrega o modelo de Machine Learning."""
    global model
    try:
        model = load_model(MODELO_PATH)
        print(f"Modelo '{MODELO_PATH}' carregado com sucesso!")
        return True
    except Exception as e:
        print(f"Erro ao carregar o modelo: {e}")
        return False

def predict_image(image_array):
    """Faz a predição em uma imagem 128x128x3."""
    if model is None:
        return "Erro: Modelo não carregado.", 0.0
    
    # Pré-processamento: normalizar e expandir dimensões (como no treino)
    processed_image = image_array.astype('float32') / 255.0 
    processed_image = np.expand_dims(processed_image, axis=0) # Adiciona dimensão de batch

    prediction = model.predict(processed_image, verbose=0)
    prediction_prob = prediction[0][0] # P(Classe 1: Saudável)
    
    threshold = 0.5 

    if prediction_prob >= threshold:
        result = f"Saudável ({prediction_prob*100:.2f}%)"
    else: 
        result = f"Fungo detectado! (Prob. Saudável: {prediction_prob*100:.2f}%)"
    
    return result, prediction_prob

# =================================================================
# FUNÇÃO DE BUSCA E PROCESSAMENTO (Chamada pela thread da GUI)
# =================================================================

def fetch_and_process():
    """Busca dados CONGELADOS da RPi via API e faz a predição."""
    global latest_prediction_result
    
    status_msg = latest_prediction_result["status"]
    temp, hum, frame, prediction_prob = None, None, None, None
    
    # 1. Buscar Dados de Captura da API
    try:
        response = requests.get(RPi_CAPTURE_URL, timeout=5)
        response.raise_for_status() 
        data_json = response.json()
        data = data_json.get('data')

        if not data or data.get('image_data') is None:
            status_msg = "Aguardando Captura Manual na RPi..."
        else:
            # Converte a lista serializada de volta para um array numpy (np.uint8)
            image_list = data.get('image_data')
            frame = np.array(image_list, dtype=np.uint8)
            temp = data.get('temperature')
            hum = data.get('humidity')
            
            # 2. Processar Imagem
            if model is not None:
                prediction_text, prediction_prob = predict_image(frame)
                status_msg = prediction_text
            else:
                status_msg = "❌ Modelo não carregado no PC."

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
             status_msg = "Aguardando Captura Manual na RPi..."
        else:
            status_msg = f"❌ Erro HTTP: {e}"
    except requests.exceptions.RequestException as e:
        status_msg = f"❌ Erro de Conexão com RPi: {e}"
    except Exception as e:
        status_msg = f"❌ Erro de Processamento: {e}"

    # 3. Atualizar Variável Global (com Lock)
    with data_lock:
        latest_prediction_result.update({
            "status": status_msg,
            "temperature": temp,
            "humidity": hum,
            "image_frame": frame,
            "prediction_prob": prediction_prob
        })

    # print(f"[{time.strftime('%H:%M:%S')}] Status: {latest_prediction_result['status']}")


if __name__ == '__main__':
    # Este script é primariamente um MÓDULO.
    # A função principal é chamada pela thread da GUI (interface_grafica.py).
    print("Módulo servidor_pc carregado. Iniciando modelo...")
    load_ml_model()