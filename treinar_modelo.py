import os
import numpy as np 
from tensorflow.keras.models import Sequential  # type: ignore
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout  # type: ignore
from tensorflow.keras.preprocessing.image import ImageDataGenerator  # type: ignore
from tensorflow.keras.callbacks import EarlyStopping # type: ignore
# Não precisamos mais do scikit-learn, pois a ponderação é manual e extrema
import logging 

# Desabilita logs irritantes do TensorFlow
logging.getLogger("tensorflow").setLevel(logging.ERROR)

# =================================================================
# CONFIGURAÇÕES DE TREINAMENTO 
# =================================================================

IMAGE_WIDTH, IMAGE_HEIGHT = 128, 128
CHANNELS = 3
BATCH_SIZE = 8
EPOCHS = 50
INPUT_SHAPE = (IMAGE_WIDTH, IMAGE_HEIGHT, CHANNELS)
DATA_DIR = 'data/treino'

# =================================================================
# 1. DATA AUGMENTATION (Geração de Dados) - MANTIDO NO MÁXIMO
# =================================================================

print("Configurando Data Augmentation...")

datagen = ImageDataGenerator(
    rescale=1./255, 
    shear_range=0.4, 
    zoom_range=0.4, 
    horizontal_flip=True,
    rotation_range=40, 
    width_shift_range=0.2, 
    height_shift_range=0.2
)

train_generator = datagen.flow_from_directory(
    DATA_DIR,
    target_size=(IMAGE_WIDTH, IMAGE_HEIGHT),
    batch_size=BATCH_SIZE,
    class_mode='binary', 
    shuffle=True
)

# =================================================================
# 2. CONSTRUÇÃO DO MODELO CNN
# =================================================================

print("Construindo o modelo CNN...")
modelo = Sequential([
    Conv2D(32, (3, 3), activation='relu', input_shape=INPUT_SHAPE),
    MaxPooling2D(pool_size=(2, 2)),
    
    Conv2D(64, (3, 3), activation='relu'),
    MaxPooling2D(pool_size=(2, 2)),
    Dropout(0.25),
    
    Flatten(),
    Dropout(0.5), 
    Dense(64, activation='relu'),
    Dense(1, activation='sigmoid') 
])

# =================================================================
# 3. COMPILAÇÃO E TREINAMENTO (Com Ponderação MANUAL, EXTREMA e CORRETA)
# =================================================================

print("Compilando o modelo...")
modelo.compile(
    loss='binary_crossentropy',
    optimizer='adam',
    metrics=['accuracy']
)

# PONDERAÇÃO INVERTIDA E EXTREMA: 
# {0: Saudável, 1: Fungo} é a ordem correta para seus dados.
# Penalizamos a classe 1 (Fungo) 20 vezes mais.
# PONDERAÇÃO FINAL CORRETA: O índice 0 é a classe Fungo (a que está em falta).
# O índice 1 é a classe Saudável.
# PONDERAÇÃO FINAL EXTREMA: O índice 0 é a classe Fungo (a que está em falta).
#lass_weights_final = {0: 50.0, 1: 1.0}
class_weights_final = {0: 20.0, 1: 1.0}

print(f"\n--- ATENÇÃO: PONDERAÇÃO FINAL CORRETA {class_weights_final} ATIVA ---")


# EarlyStopping e Treinamento
callbacks = [
    EarlyStopping(monitor='loss', patience=20, verbose=1, mode='min') # Paciência 20 para evitar parada precoce
]

print(f"\nIniciando treinamento por {EPOCHS} épocas...")

history = modelo.fit(
    train_generator,
    steps_per_epoch=train_generator.samples // BATCH_SIZE,
    epochs=EPOCHS,
    callbacks=callbacks,
    class_weight=class_weights_final, # Ponderação Extrema CORRETA
    verbose=1
)

# =================================================================
# 4. SALVAMENTO
# =================================================================

MODELO_FILENAME = 'modelo_fungo.h5'
print(f"\nTreinamento concluído. Salvando modelo em {MODELO_FILENAME}...")

try:
    modelo.save(MODELO_FILENAME)
    print("Modelo salvo com sucesso!")
except Exception as e:
    print(f"Erro ao salvar o modelo: {e}")