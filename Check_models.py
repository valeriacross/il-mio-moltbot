import os
from google import genai

# Carica la tua chiave
API_KEY = os.environ.get("GOOGLE_API_KEY")
client = genai.Client(api_key=API_KEY)

def verifica_motori():
    print("--- 🔍 LISTA COMPLETA MODELLI DISPONIBILI ---", flush=True)
    try:
        # Stampiamo solo il nome di ogni modello per evitare errori di attributi
        for model in client.models.list():
            print(f"ID: {model.name}", flush=True)
    except Exception as e:
        print(f"❌ Errore critico: {e}", flush=True)

if __name__ == "__main__":
    verifica_motori()
    
