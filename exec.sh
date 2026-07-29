#!/bin/bash
set -euo pipefail

# Utwórz katalog na dane na hoście, jeśli nie istnieje
mkdir -p data

# Zbuduj i uruchom kontener z podmontowanym wolumenem
sudo docker build -t macro-diet-app .
sudo docker run --rm -p 8501:8501 -v "$(pwd)/data:/app/data" macro-diet-app
