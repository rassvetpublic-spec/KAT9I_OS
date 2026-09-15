import json
from pathlib import Path
from datetime import datetime

# Каталог, где лежат разговоры всех воркеров Antigravity
BRAIN_DIR = Path(r"C:\Antigravity\Common\.gemini\antigravity\brain")
# Файл, куда будет сохранен объединенный текст
OUTPUT_FILE = Path(r"C:\GIT\KAT9I_OS\История\workers_sync.md")

def collect_logs():
    print(f"Поиск логов воркеров в {BRAIN_DIR}...")
    
    if not BRAIN_DIR.exists():
        print("Каталог brain не найден!")
        return

    output_content = f"# Сводный лог воркеров (сгенерирован {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n\n"
    
    # Ищем все файлы transcript.jsonl во всех подпапках
    transcripts_found = 0
    for transcript_file in BRAIN_DIR.rglob(".system_generated/logs/transcript.jsonl"):
        transcripts_found += 1
        worker_id = transcript_file.parent.parent.parent.name
        
        output_content += f"## Сессия (Воркер ID): {worker_id}\n\n"
        
        try:
            with open(transcript_file, 'r', encoding='utf-8') as f:
                for line in f:
                    data = json.loads(line)
                    
                    # Захватываем ответы воркера
                    if data.get('source') == 'MODEL' and data.get('type') == 'PLANNER_RESPONSE':
                        content = data.get('content', '')
                        if content:
                            output_content += f"**🤖 Воркер:**\n{content}\n\n"
                            
                    # Захватываем первоначальные задачи/сообщения
                    elif data.get('source') == 'USER_EXPLICIT' and data.get('type') == 'USER_INPUT':
                        content = data.get('content', '')
                        if content:
                            output_content += f"**👤 Команда/Ввод:**\n{content}\n\n"
                            
        except Exception as e:
            print(f"Ошибка при чтении {transcript_file}: {e}")
            
        output_content += "---\n\n"

    if transcripts_found == 0:
        print("Файлы с логами не найдены.")
        return

    # Создаем папку, если ее нет, и сохраняем результат
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(output_content)
        
    print(f"Успешно! Собрано логов: {transcripts_found}. Все разговоры сохранены в файл: {OUTPUT_FILE}")

if __name__ == "__main__":
    collect_logs()
"""Сбор логов воркеров из .gemini\antigravity\brain в единый Markdown-файл."""
