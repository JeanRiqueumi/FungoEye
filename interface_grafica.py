import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import threading
import os
import cv2
import time
import numpy as np

# Importação ATUALIZADA
from servidor_pc import latest_prediction_result, data_lock, load_ml_model, fetch_and_process

class App:
    def __init__(self, master):
        self.master = master
        master.title("Detector de Fungos - Monitor Web RPi")
        master.geometry("800x650")
        
        # 1. Tenta carregar o modelo de ML
        if not load_ml_model():
            master.destroy()
            return
            
        self.create_widgets()
        
        # 2. Inicia a thread que buscará os dados da RPi periodicamente
        self.processing_thread = threading.Thread(target=self.start_processor, daemon=True)
        self.processing_thread.start()

        # 3. Atualiza a GUI periodicamente (chama update_gui a cada 100ms)
        self.master.after(100, self.update_gui)

    def create_widgets(self):
        # ... (Mantido como antes) ...
        self.info_frame = ttk.LabelFrame(self.master, text="Status e Sensores")
        self.info_frame.pack(pady=10, padx=10, fill="x")

        self.status_label = ttk.Label(self.info_frame, text="Iniciando...", font=("Helvetica", 14, "bold"))
        self.status_label.pack(pady=5)

        self.temp_label = ttk.Label(self.info_frame, text="Temperatura: N/A", font=("Helvetica", 12))
        self.temp_label.pack(pady=2)

        self.hum_label = ttk.Label(self.info_frame, text="Umidade: N/A", font=("Helvetica", 12))
        self.hum_label.pack(pady=2)
        
        self.prob_label = ttk.Label(self.info_frame, text="Prob. Saudável: N/A", font=("Helvetica", 12))
        self.prob_label.pack(pady=2)


        self.image_frame = ttk.LabelFrame(self.master, text="Última Imagem Capturada")
        self.image_frame.pack(pady=10, padx=10, expand=True, fill="both")

        self.image_label = ttk.Label(self.image_frame)
        self.image_label.pack(expand=True)
        
        self.display_placeholder_image()

    def display_placeholder_image(self):
        """Exibe uma imagem placeholder."""
        blank_img = Image.new('RGB', (300, 300), color = 'lightgray')
        self.photo = ImageTk.PhotoImage(blank_img)
        self.image_label.config(image=self.photo)
        self.image_label.image = self.photo
        
    def start_processor(self):
        """Nova função: Roda a busca e processamento em loop."""
        while True:
            # Chama a função de processamento no servidor_pc.py
            fetch_and_process() 
            time.sleep(3) # Intervalo para não sobrecarregar a rede

    def update_gui(self):
        """Atualiza a interface gráfica com os últimos dados."""
        
        with data_lock: # Usa o Lock para ler os dados de forma segura
            data = latest_prediction_result.copy()

        self.status_label.config(text=f"Resultado: {data['status']}")
        self.temp_label.config(text=f"Temperatura: {data['temperature']}°C" if data['temperature'] is not None else "Temperatura: N/A")
        self.hum_label.config(text=f"Umidade: {data['humidity']}%" if data['humidity'] is not None else "Umidade: N/A")
        
        prob = data['prediction_prob']
        self.prob_label.config(text=f"Prob. Saudável: {prob*100:.2f}%" if prob is not None else "Prob. Saudável: N/A")


        # Atualiza a imagem se houver um novo frame
        frame_array = data.get('image_frame')
        if frame_array is not None and isinstance(frame_array, np.ndarray):
            try:
                # O frame array é em BGR (padrão OpenCV), converte para RGB para Pillow
                cv2image = cv2.cvtColor(frame_array, cv2.COLOR_BGR2RGB)
                
                # Redimensiona para exibição na GUI (300x300 é um bom tamanho)
                img = Image.fromarray(cv2image)
                img = img.resize((300, 300), Image.LANCZOS)
                
                self.photo = ImageTk.PhotoImage(img)
                self.image_label.config(image=self.photo)
                self.image_label.image = self.photo
            except Exception as e:
                print(f"Erro ao carregar imagem para GUI: {e}")
                self.image_label.config(text="Erro ao carregar imagem")
        else:
            # Se não houver imagem, mantenha o placeholder (se já estiver exibindo)
            pass

        # Agenda a próxima atualização da GUI
        self.master.after(100, self.update_gui)

if __name__ == "__main__":
    root = tk.Tk()
    # Adicionando tratamento de erro básico para iniciar
    try:
        app = App(root)
        root.mainloop()
    except Exception as e:
        print(f"Erro ao iniciar aplicação GUI: {e}")
        root.destroy()