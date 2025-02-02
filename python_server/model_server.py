from flask import Flask, request, jsonify
from transformers import GPT2LMHeadModel, GPT2Tokenizer
import sqlite3
import threading

app = Flask(__name__)

# Загрузка модели и токенизатора
model = GPT2LMHeadModel.from_pretrained('/app/fine_tuned_model')
tokenizer = GPT2Tokenizer.from_pretrained('/app/fine_tuned_model')

# Подключение к базе данных
conn = sqlite3.connect('/app/data/data.db')
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

        # Подготовка данных
        encodings_dict = tokenizer('\n\n'.join(texts), truncation=True, padding=True, return_tensors='pt')

        # Обучение модели
        model.train()
        optimizer = torch.optim.Adam(model.parameters(), lr=5e-5)

        for epoch in range(3):
            for i in range(len(texts)):
                input_ids = encodings_dict['input_ids'][i]
                attention_mask = encodings_dict['attention_mask'][i]
                outputs = model(input_ids.unsqueeze(0), attention_mask=attention_mask.unsqueeze(0), labels=input_ids.unsqueeze(0))
                loss = outputs.loss
                loss.backward()
                optimizer.step()
                optimizer.zero_grad()

        # Сохранение модели
        model.save_pretrained('/app/fine_tuned_model')
        tokenizer.save_pretrained('/app/fine_tuned_model')
        print("Model trained and saved.")

        time.sleep(86400)  # Обновляем модель раз в день

@app.route('/generate', methods=['POST'])
def generate_text():
    data = request.json
    text = data.get('text', '')
    if not text:
        return jsonify({'error': 'No text provided'}), 400

    try:
        inputs = tokenizer(text, return_tensors='pt')
        outputs = model.generate(**inputs, max_length=50)
        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
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
