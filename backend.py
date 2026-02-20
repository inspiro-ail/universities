from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import os
from openai import OpenAI
import math

app = Flask(__name__)
CORS(app)

# Твой клиент OpenAI
client = OpenAI(api_key="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")

def fix_nan(value):
    if value is None:
        return ''
    if isinstance(value, float) and math.isnan(value):
        return ''
    return value

def load_university_data():
    try:
        print("Пытаюсь загрузить universities.xlsx...")
        
        # Загрузка файлов
        df_names = pd.read_excel('universities.xlsx')
        df_data = pd.read_excel('university_data.xlsx')

        universities = []
        # Используем df_names как основной список
        for i in range(len(df_names)):
            # Добавлены проверки на наличие индекса в df_data, чтобы избежать IndexError
            uni = {
                'id': i,
                'name': fix_nan(df_names.iloc[i, 0] if i < len(df_names) else ''),
                'description': fix_nan(df_data.iloc[i, 1] if i < len(df_data) else ''),
                'specialties': fix_nan(df_data.iloc[i, 2] if i < len(df_data) else ''),
                'website': fix_nan(df_data.iloc[i, 3] if i < len(df_data) else ''),
                'contacts': fix_nan(df_data.iloc[i, 4] if i < len(df_data) else ''),
                'address': fix_nan(df_data.iloc[i, 5] if i < len(df_data) and len(df_data.columns) > 5 else '')
            }
            universities.append(uni)
        
        print(f"✅ Загружено {len(universities)} университетов")
        return universities

    except Exception as e:
        print(f"❌ Ошибка загрузки данных: {e}")
        return []

# Инициализация данных
universities_data = load_university_data()

def get_chatgpt_info(university_data, info_type):
    prompts = {
        'general': f"Предоставь общую информацию и советы об университете '{university_data['name']}'. Описание: {university_data['description']}. Дай полезные советы для абитуриентов.",
        'academic': f"Расскажи подробно об академических программах университета '{university_data['name']}'. Специальности: {university_data['specialties']}. Опиши преимущества каждого направления.",
        'admission': f"Предоставь подробную информацию о процессе приема и поступления в университет '{university_data['name']}'. Расскажи о требованиях, сроках, документах и советах для поступающих.",
        'international': f"Расскажи о возможностях международного сотрудничества в университете '{university_data['name']}'. Упомяни программы обмена, партнерства, двойные дипломы и международные стажировки."
    }
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=[
                {"role": "system", "content": "Ты эксперт по высшему образованию в Казахстане. Предоставляй подробную и полезную информацию для студентов и абитуриентов."},
                {"role": "user", "content": prompts[info_type]}
            ],
            max_tokens=800,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Ошибка получения информации: {str(e)}"

@app.route('/api/universities', methods=['GET'])
def get_universities():
    search = request.args.get('search', '').lower()
    if search:
        filtered = [u for u in universities_data if search in u['name'].lower()]
        return jsonify(filtered)
    return jsonify(universities_data)

@app.route('/api/university/<int:uni_id>', methods=['GET'])
def get_university_details(uni_id):
    if uni_id < 0 or uni_id >= len(universities_data):
        return jsonify({'error': 'Университет не найден'}), 404
    
    university = universities_data[uni_id]
    chatgpt_data = {
        'general_info': get_chatgpt_info(university, 'general'),
        'academic_programs': get_chatgpt_info(university, 'academic'),
        'admission_info': get_chatgpt_info(university, 'admission'),
        'international_cooperation': get_chatgpt_info(university, 'international')
    }
    
    response = {**university, 'chatgpt_data': chatgpt_data}
    return jsonify(response)

@app.route('/api/chat', methods=['POST'])
def chat_with_gpt():
    data = request.json
    uni_id = data.get('university_id')
    message = data.get('message')
    conversation_history = data.get('history', [])
    
    if uni_id is None or uni_id < 0 or uni_id >= len(universities_data):
        return jsonify({'error': 'Университет не найден'}), 404
    
    university = universities_data[uni_id]
    system_message = f"Ты помощник по университету '{university['name']}'. Описание: {university['description']}"
    
    messages = [{"role": "system", "content": system_message}]
    for msg in conversation_history:
        messages.append({"role": msg['role'], "content": msg['content']})
    messages.append({"role": "user", "content": message})
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=messages,
            max_tokens=500,
            temperature=0.8
        )
        return jsonify({'response': response.choices[0].message.content, 'role': 'assistant'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/compare', methods=['POST'])
def compare_universities():
    data = request.json
    uni1_id = data.get('university1_id')
    uni2_id = data.get('university2_id')
    
    if uni1_id >= len(universities_data) or uni2_id >= len(universities_data):
        return jsonify({'error': 'Университет не найден'}), 404
    
    uni1, uni2 = universities_data[uni1_id], universities_data[uni2_id]
    prompt = f"Сравни {uni1['name']} и {uni2['name']}."
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500
        )
        return jsonify({
            'university1': uni1['name'],
            'university2': uni2['name'],
            'comparison': response.choices[0].message.content
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'universities_loaded': len(universities_data)})

if __name__ == '__main__':
    # Исправлена строка запуска (удалено слово "исправь")
    app.run(debug=True, port=5000, host='0.0.0.0')