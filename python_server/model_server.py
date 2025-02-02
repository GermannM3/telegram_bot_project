# model_server.py
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify
import threading
import sqlite3

app = Flask(__name__)

# Загрузка или создание модели Kenga_AI
class Kenga_AI:
    def __init__(self, input_size, hidden_size, output_size, learning_rate=0.01):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size
        self.learning_rate = learning_rate
        self.weights_input_hidden = np.random.randn(self.input_size, self.hidden_size)
        self.weights_hidden_output = np.random.randn(self.hidden_size, self.output_size)

    def sigmoid(self, x):
        return 1 / (1 + np.exp(-x))

    def sigmoid_derivative(self, x):
        return x * (1 - x)

    def feedforward(self, X):
        self.hidden_layer_input = np.dot(X, self.weights_input_hidden)
        self.hidden_layer_output = self.sigmoid(self.hidden_layer_input)
        self.output_layer_input = np.dot(self.hidden_layer_output, self.weights_hidden_output)
        self.output = self.sigmoid(self.output_layer_input)
        return self.output

    def backpropagate(self, X, y):
        output_error = y - self.output
        output_delta = output_error * self.sigmoid_derivative(self.output)

        hidden_error = output_delta.dot(self.weights_hidden_output.T)
        hidden_delta = hidden_error * self.sigmoid_derivative(self.hidden_layer_output)

        self.weights_hidden_output += self.hidden_layer_output.T.dot(output_delta) * self.learning_rate
        self.weights_input_hidden += X.T.dot(hidden_delta) * self.learning_rate

    def train(self, X, y, epochs=10000):
        for _ in range(epochs):
            self.feedforward(X)
            self.backpropagate(X, y)

# Загрузка или создание модели
try:
    weights_input_hidden = np.load('weights_input_hidden.npy')
    weights_hidden_output = np.load('weights_hidden_output.npy')
    model = Kenga_AI(input_size=weights_input_hidden.shape[0],
                    hidden_size=weights_input_hidden.shape[1],
                    output_size=weights_hidden_output.shape[1])
    model.weights_input_hidden = weights_input_hidden
    model.weights_hidden_output = weights_hidden_output
except FileNotFoundError:
    # Если файлы не найдены, создаём новую модель
    input_size = 2  # Измените в зависимости от ваших данных
    hidden_size = 5
    output_size = 1
    model = Kenga_AI(input_size, hidden_size, output_size)

# Подключение к базе данных
conn = sqlite3.connect('data.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        input_text TEXT,
        generated_text TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
''')
conn.commit()

def train_model():
    while True:
        # Сбор данных
        cursor.execute('SELECT input_text, generated_text FROM interactions')
        interactions = cursor.fetchall()
        texts = [interaction[0] + ' ' + interaction[1] for interaction in interactions]

        if len(texts) == 0:
            time.sleep(3600)  # Ждем час, если данных нет
            continue

        # Подготовка данных для обучения
        # Здесь нужно преобразовать текстовые данные в числовые, если это необходимо
        # Например, можно использовать кодирование или векторизацию

        # Обучение модели
        # Преобразуйте данные в формат, подходящий для модели Kenga_AI
        X = np.array([...])  # Преобразуйте данные здесь
        y = np.array([...])  # Преобразуйте данные здесь
        model.train(X, y)

        # Сохранение модели
        np.save('weights_input_hidden.npy', model.weights_input_hidden)
        np.save('weights_hidden_output.npy', model.weights_hidden_output)
        print("Model trained and saved.")

        time.sleep(86400)  # Обновляем модель раз в день

@app.route('/generate', methods=['POST'])
def generate_text():
    data = request.json
    text = data.get('text', '')
    if not text:
        return jsonify({'error': 'No text provided'}), 400

    try:
        # Преобразуйте текст в числовые данные для модели Kenga_AI
        X = np.array([...])  # Преобразуйте текст здесь

        # Прогнозирование
        output = model.feedforward(X)
        generated_text = str(output[0][0])  # Преобразуйте выходные данные в текст

        # Сохранение взаимодействия в базе данных
        cursor.execute('INSERT INTO interactions (input_text, generated_text) VALUES (?, ?)', (text, generated_text))
        conn.commit()
        return jsonify({'text': generated_text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Запуск потока для обучения модели
    thread = threading.Thread(target=train_model)
    thread.start()
    app.run(host='0.0.0.0', port=5000)
