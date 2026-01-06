import os
import time
import json
import warnings
import random
import yt_dlp
from flask import Flask, render_template, request, jsonify, send_from_directory
from google import genai
from google.genai import types

# --- ⚙️ CONFIGURATION FLASK ---
# On définit template_folder="." pour chercher index.html à la racine
app = Flask(__name__, template_folder=".") 
warnings.filterwarnings("ignore")

# 🔴 TA CLÉ API
API_KEY = "AIzaSyAaQhD0HJsbZNHdWFphgjJYgLNqLCPGEjE" 
client = genai.Client(api_key=API_KEY)
MODEL_NAME = "gemini-2.5-flash"
DB_FOLDER = "databases"
COOKIE_FILE = "youtube_cookies.txt" # Nom du fichier à mettre sur ton GitHub

if not os.path.exists(DB_FOLDER):
    os.makedirs(DB_FOLDER)

# --- 🧠 FONCTION IA RECHERCHE ---
def generate_smart_queries(niche):
    prompt = f"Tu es un expert en SEO YouTube. Donne une liste Python de 5 termes de recherche pour trouver des Shorts viraux dans la niche : '{niche}'. Format: ['terme 1', 'terme 2']"
    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        text = response.text.strip().replace("```json", "").replace("```python", "").replace("```", "")
        return eval(text)
    except:
        return [f"{niche} viral shorts", f"{niche} edit"]

# --- 🦅 LE CHASSEUR & ANALYSTE ---
def process_scan(niche, nb_videos, min_views):
    db_path = os.path.join(DB_FOLDER, f"db_{niche.lower().replace(' ', '_')}.json")
    queries = generate_smart_queries(niche)
    
    # Historique pour éviter les doublons
    existing_urls = []
    if os.path.exists(db_path):
        try:
            with open(db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                existing_urls = [item['meta']['url'] for item in data if 'meta' in item]
        except: pass

    results = []
    count_success = 0
    
    # --- TON PROMPT TECHNIQUE (INTACT) ---
    analysis_prompt = """
    Tu es un Expert Technique en Montage Vidéo (Anime Music Video / Edit).
    Ta mission est de décortiquer cette vidéo virale pour qu'un monteur puisse la reproduire.
    
    Sois EXTRÊMEMENT PRÉCIS et DÉTAILLÉ. Ne sois pas vague.
    
    Retourne UNIQUEMENT un objet JSON avec la structure exacte suivante :

    {
      "1_VISUAL_HOOK": {
        "scene_intro": "Description cinématique de la toute première seconde (personnages, actions, décor).",
        "effet_visuel_intro": "Liste les techniques exactes (ex: Zoom in brutal, Camera Shake, Flash blanc, Vignette, Aberration chromatique).",
        "texte_ecran": "Retranscris TOUT le texte qui apparaît à l'écran dans l'intro (sous-titres, onomatopées)."
      },
      "2_SYNC_FLOW": {
        "bpm_match": "Analyse la synchro : Est-ce que les transitions tombent sur les kicks ? Est-ce que les mouvements suivent la mélodie ?",
        "flow_type": "Décris la courbe d'intensité (ex: Intro calme -> Drop violent -> Ralenti Twixtor)."
      },
      "3_EFFECTS_LIST": {
        "vfx_utilises": [
          "Liste ici tous les effets techniques identifiés (ex: RSMB, Twixtor, Glow, S_Shake, Glitch, Masking)"
        ],
        "color_grading": "Analyse la colorimétrie (ex: Saturation poussée, teintes bleues, contraste fort)."
      },
      "4_AUDIO_DNA": {
        "style_musique": "Genre précis (ex: Phonk, Hyperpop, Breakcore).",
        "sfx_cle": [
           "Liste les bruitages ajoutés (ex: Sword slash, Gun cocking, Whoosh)"
        ]
      },
      "5_REPRODUCTION_GUIDE": {
        "prompt_image_gen": "Rédige un PROMPT DÉTAILLÉ en ANGLAIS pour générer une image clé de ce style (Midjourney/Stable Diffusion).",
        "conseil_montage": "Donne un conseil technique avancé pour cloner ce style."
      }
    }
    """

    for _ in range(nb_videos * 4): 
        if count_success >= nb_videos: break
        query = random.choice(queries)
        
        # AJOUT DES COOKIES POUR LA RECHERCHE
        ydl_opts = {
            'quiet': True, 
            'extract_flat': True, 
            'ignoreerrors': True,
            'cookiefile': COOKIE_FILE if os.path.exists(COOKIE_FILE) else None
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(f"ytsearch5:{query}", download=False)
                if 'entries' not in info: continue
                
                for entry in info['entries']:
                    if not entry or entry.get('url') in existing_urls: continue
                    url = entry.get('url')
                    
                    # Téléchargement
                    video_filename = f"temp_{random.randint(1000,9999)}.mp4"
                    
                    # AJOUT DES COOKIES POUR LE TELECHARGEMENT
                    dl_opts = {
                        'format': 'best[ext=mp4]', 
                        'outtmpl': video_filename, 
                        'quiet': True,
                        'cookiefile': COOKIE_FILE if os.path.exists(COOKIE_FILE) else None
                    }
                    
                    try:
                        with yt_dlp.YoutubeDL(dl_opts) as ydl_dl:
                            vid_info = ydl_dl.extract_info(url, download=True)
                            
                            # Vérification virale
                            views = vid_info.get('view_count', 0)
                            if views < min_views:
                                if os.path.exists(video_filename): os.remove(video_filename)
                                continue
                            
                            # Upload Gemini
                            file_ref = client.files.upload(file=video_filename, config={'mime_type': 'video/mp4'})
                            while client.files.get(name=file_ref.name).state == "PROCESSING":
                                time.sleep(1)
                            
                            # Analyse IA
                            res_ia = client.models.generate_content(
                                model=MODEL_NAME, 
                                contents=[file_ref, analysis_prompt],
                                config=types.GenerateContentConfig(response_mime_type="application/json")
                            )
                            
                            final_data = json.loads(res_ia.text)
                            final_data['meta'] = {
                                'niche': niche, 
                                'url': url, 
                                'title': vid_info.get('title', 'Sans titre'), 
                                'views': views
                            }
                            
                            # Sauvegarde JSON propre
                            current_db = []
                            if os.path.exists(db_path):
                                try:
                                    with open(db_path, 'r', encoding='utf-8') as f:
                                        current_db = json.load(f)
                                except: current_db = []
                            
                            current_db.append(final_data)
                            with open(db_path, 'w', encoding='utf-8') as f:
                                json.dump(current_db, f, indent=4, ensure_ascii=False)
                            
                            results.append(final_data)
                            existing_urls.append(url)
                            count_success += 1
                            
                            if os.path.exists(video_filename): os.remove(video_filename)
                            if count_success >= nb_videos: break
                            
                    except Exception as e:
                        print(f"Erreur téléchargement/analyse: {e}")
                        if os.path.exists(video_filename): os.remove(video_filename)
            except Exception as e:
                print(f"Erreur recherche YouTube: {e}")

    return results

# --- 🌐 ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scan', methods=['POST'])
def scan():
    niche = request.form.get('niche')
    nb_videos = int(request.form.get('nb_videos', 1))
    views_input = request.form.get('min_views', '1000000').lower()
    
    if 'm' in views_input: min_views = int(float(views_input.replace('m','')) * 1000000)
    elif 'k' in views_input: min_views = int(float(views_input.replace('k','')) * 1000)
    else: 
        try: min_views = int(views_input)
        except: min_views = 1000000

    data = process_scan(niche, nb_videos, min_views)
    api_link = f"{request.host_url}api/json/{niche.lower().replace(' ', '_')}"
    return jsonify({"status": "success", "data": data, "api_link": api_link})

@app.route('/api/json/<niche_id>', methods=['GET'])
def get_json_api(niche_id):
    filename = f"db_{niche_id}.json"
    return send_from_directory(DB_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
