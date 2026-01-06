import os
import time
import json
import warnings
import random
import yt_dlp
from flask import Flask, render_template, request, jsonify, send_from_directory
from google import genai
from google.genai import types

# --- ⚙️ CONFIGURATION FLASK & IA ---
app = Flask(__name__)
warnings.filterwarnings("ignore")

# 🔴 TA CLÉ API (Je l'ai remise ici)
API_KEY = "AIzaSyAaQhD0HJsbZNHdWFphgjJYgLNqLCPGEjE" 
client = genai.Client(api_key=API_KEY)
MODEL_NAME = "gemini-2.5-flash"
DB_FOLDER = "databases"

# Création du dossier de stockage si inexistant
if not os.path.exists(DB_FOLDER):
    os.makedirs(DB_FOLDER)

# --- 🧠 FONCTION IA ---
def generate_smart_queries(niche):
    prompt = f"""
    Tu es un expert en SEO YouTube. Donne une liste Python de 5 termes de recherche 
    pour trouver des Shorts viraux dans la niche : "{niche}".
    Format: ["terme 1", "terme 2"]
    """
    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        text = response.text.strip().replace("```json", "").replace("```python", "").replace("```", "")
        return eval(text)
    except:
        return [f"{niche} viral shorts", f"{niche} edit"]

# --- 🛠️ UTILITAIRES ---
def get_db_path(niche):
    clean_niche = niche.lower().replace(" ", "_").strip()
    return os.path.join(DB_FOLDER, f"db_{clean_niche}.json")

def load_existing_urls(db_path):
    if not os.path.exists(db_path): return []
    try:
        with open(db_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [item['meta']['url'] for item in data if 'meta' in item]
    except: return []

# --- 🦅 LE CHASSEUR & ANALYSTE (Core Logic) ---
def process_scan(niche, nb_videos, min_views):
    db_path = get_db_path(niche)
    queries = generate_smart_queries(niche)
    existing_urls = load_existing_urls(db_path)
    
    results = []
    count_success = 0
    max_duration = 60
    
    # Pour l'exemple Web, on simplifie la boucle pour éviter le timeout navigateur
    # (Dans une version V2, on mettrait ça en tâche de fond)
    
    for _ in range(nb_videos * 3): # On essaie 3x plus de recherches que nécessaire
        if count_success >= nb_videos: break
        
        query = random.choice(queries)
        ydl_opts = {'quiet': True, 'extract_flat': True, 'ignoreerrors': True}
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch5:{query}", download=False)
            if 'entries' not in info: continue
            
            entries = list(info['entries'])
            random.shuffle(entries)
            
            for entry in entries:
                if not entry: continue
                url = entry.get('url')
                title = entry.get('title', 'N/A')
                
                if url in existing_urls: continue
                
                # DL & VERIFY
                video_filename = f"temp_{random.randint(1000,9999)}.mp4"
                dl_opts = {'format': 'best[ext=mp4]', 'outtmpl': video_filename, 'quiet': True}
                
                try:
                    with yt_dlp.YoutubeDL(dl_opts) as ydl_dl:
                        vid_info = ydl_dl.extract_info(url, download=True)
                        if vid_info.get('view_count', 0) < min_views:
                            if os.path.exists(video_filename): os.remove(video_filename)
                            continue
                        
                        # UPLOAD GEMINI
                        file_ref = client.files.upload(file=video_filename, config={'mime_type': 'video/mp4'})
                        while client.files.get(name=file_ref.name).state == "PROCESSING": time.sleep(1)
                        
                        # ANALYSE
                        analysis_prompt = """
                        Analyse cette vidéo frame par frame.
                        Format JSON OBLIGATOIRE :
                        {
                          "1_VISUAL_HOOK": { "scene_intro": "...", "techniques": "..." },
                          "2_RYTHME": { "bpm": "...", "cuts": "..." },
                          "3_VFX": { "list": "..." },
                          "4_AUDIO": { "sfx": "..." },
                          "5_PROMPT": { "midjourney": "...", "conseil": "..." }
                        }
                        """
                        res_ia = client.models.generate_content(
                            model=MODEL_NAME, 
                            contents=[file_ref, analysis_prompt],
                            config=types.GenerateContentConfig(response_mime_type="application/json")
                        )
                        final_data = json.loads(res_ia.text)
                        
                        # MÉTADONNÉES
                        final_data['meta'] = {
                            'niche': niche, 'url': url, 'title': title, 'views': vid_info.get('view_count')
                        }
                        
                        # SAVE
                        current_db = []
                        if os.path.exists(db_path):
                            with open(db_path, 'r', encoding='utf-8') as f: current_db = json.load(f)
                        
                        current_db.append(final_data)
                        with open(db_path, 'w', encoding='utf-8') as f:
                            json.dump(current_db, f, indent=4, ensure_ascii=False)
                        
                        results.append(final_data)
                        existing_urls.append(url)
                        count_success += 1
                        
                        if os.path.exists(video_filename): os.remove(video_filename)
                        break # Sortir de la boucle entries pour changer de query
                except Exception as e:
                    print(f"Erreur process: {e}")
                    if os.path.exists(video_filename): os.remove(video_filename)

    return results

# --- 🌐 ROUTES WEB ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scan', methods=['POST'])
def scan():
    niche = request.form.get('niche')
    nb_videos = int(request.form.get('nb_videos'))
    min_views = int(request.form.get('min_views'))
    
    # Lancement du process
    data = process_scan(niche, nb_videos, min_views)
    
    # Création du lien API
    clean_niche = niche.lower().replace(" ", "_").strip()
    api_link = f"{request.host_url}api/json/{clean_niche}"
    
    return jsonify({"status": "success", "data": data, "api_link": api_link})

# --- 🔌 ROUTE API SPECIALE (Ce que tu as demandé) ---
@app.route('/api/json/<niche_id>', methods=['GET'])
def get_json_api(niche_id):
    """
    Cette URL permet à n'importe quel autre logiciel de récupérer
    le JSON brut de la niche analysée.
    Exemple: [http://ton-site.com/api/json/anime](http://ton-site.com/api/json/anime)
    """
    filename = f"db_{niche_id}.json"
    try:
        return send_from_directory(DB_FOLDER, filename, as_attachment=False)
    except FileNotFoundError:
        return jsonify({"error": "Base de données introuvable pour cette niche."}), 404

if __name__ == '__main__':
    # Mode debug activé pour voir les erreurs
    app.run(debug=True, host='0.0.0.0', port=5000)