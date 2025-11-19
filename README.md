 FungoEye: Sistema Inteligente de Detecção de Fungos em Bananas.
 
 🚀 Visão Geral do Projeto: FungoEye é um sistema de monitoramento inteligente desenvolvido para a detecção precoce de fungos em bananas usando Visão Computacional (CNN) e monitoramento ambiental em tempo real. O sistema utiliza uma arquitetura Cliente-Servidor distribuída, com uma Raspberry Pi (RPi) para captura de dados e um PC Host para processamento e análise. Este projeto adota um fluxo de trabalho profissional, onde as imagens capturadas são processadas por um modelo de Machine Learning e os resultados são arquivados automaticamente.
 
 🛠️ Divisão de Tarefas (Hardware):
 Lado A: Raspberry Pi + Arduino = Ele é o Servidor, sua função é a de capturar a realidade e disponibilizá-la na rede. Arduino: Lê o sensor de umidade/temperatura (DHT11 ou DHT22) e passa os números para a Raspberry via cabo USB. Raspberry Pi: Recebe os dados do Arduino. Tira fotos contínuas (stream) das bananas. Cria um site interno (Flask) para entregar esses dados a quem pedir.
 Lado B: Computador/PC = Este é o computador onde você vai ver os resultados. Ele é o Cliente, sua função é buscar os dados, pensar e exibir. Inteligência Artificial: Roda o modelo pesado (modelo_fungo.h5) para dizer se a banana tem fungo ou não. Interface: 
Mostra os gráficos de umidade e o vídeo com a detecção em tempo real.

🔁 Fluxo de Trabalho e Análise: O sistema FungoEye segue um fluxo de trabalho de análise de arquivos automatizado para garantir a rastreabilidade e organização dos dados: Ação do Usuário - O operador clica no botão "Fazer Captura Manual e Congelar" no painel web da RPi.Captura (RPi): A RPi congela o frame atual da câmera e os dados do sensor (Temperatura/Umidade) e armazena-os na memória.Busca (PC) - O servidor_pc.py (rodando em background via thread) detecta a nova captura.Salvamento RAW: O PC salva a imagem recém-adquirida na pasta Imagens_RAW/.Processamento ML: O PC executa a predição da CNN no frame, determinando se há Fungo Detectado ou se está Saudável.Movimentação e Arquivamento:O arquivo RAW original é movido para a pasta Analises_Concluidas/.O arquivo é renomeado automaticamente com o timestamp e o resultado da análise. Um registro detalhado é salvo no data_historico.csv para geração dos gráficos.

🖼️ Interface Gráfica: A interface gráfica (interface_grafica.py) é o painel de controle principal, oferecendo três abas com um design moderno e harmonizado: Monitoramento Atual - Exibe a imagem processada, os dados ambientais (Temperatura/Umidade) e o status da predição (Saudável/Fungo Detectado) em tempo real após cada captura. Relatórios e Histórico - Plota gráficos interativos baseados no data_historico.csv, permitindo visualizar tendências de temperatura e umidade ao longo do tempo. Fluxo de Arquivos e Config. - Informa os caminhos dos diretórios Imagens_RAW e Analises_Concluidas e contém opções futuras de configuração.

Projeto realizado como parte do projeto final para a matéria de Hardware Architecture na instituição superior ATITUS Educação.

RA e nomes dos integrantes:

Geraldo Konig - 1126596
Jean Canova - 1137244
João Vitor Spiller - 1137246
Marcos Ferreira - 1137201
Vinicius Hoffelder - 1137833
