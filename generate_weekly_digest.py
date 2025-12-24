import os
import resend
from datetime import datetime, timedelta
from google import genai
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# 1. SETUP
load_dotenv()
resend.api_key = os.getenv("RESEND_API_KEY")
MODEL_ID = "gemini-2.5-flash-lite-preview-09-2025"

if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccount.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

def fetch_weekly_signals():
    print("📚 Gathering history for the Insider Brief...")
    start_date = datetime.now() - timedelta(days=7)
    
    # Fetch Signals
    query = db.collection("signals").where(filter=FieldFilter("timestamp", ">=", start_date))
    docs = query.stream()
    
    signals_text = []
    for doc in docs:
        data = doc.to_dict()
        entry = (
            f"DATE: {data['timestamp'].strftime('%Y-%m-%d')}\n"
            f"TOPIC: {data.get('industry', 'General')}\n"
            f"ANALYSIS: {data.get('analysis', '')}\n"
            f"SCORE: {data.get('score', 0)}\n"
            "---"
        )
        signals_text.append(entry)
    
    return "\n".join(signals_text)

def write_insider_brief(raw_signals):
    print("✍️  Drafting the Insider Brief...")
    
    prompt = f"""
    You are the "VTA Insider," writing a high-stakes intelligence brief for Vancouver business leaders.
    
    CRITICAL FORMATTING INSTRUCTION:
    - Return the response as raw HTML code. 
    - Do NOT use Markdown (no **, no ##). 
    - Use the specific Tailwind CSS classes provided below to ensure it looks beautiful.

    HTML TEMPLATE TO USE:
    
    <div class="space-y-6 font-serif text-stone-800">
        
        <div class="border-b border-stone-200 pb-6">
            <h2 class="text-2xl font-bold text-stone-900 uppercase tracking-tight mb-2">
                [Insert Catchy Title Here, e.g., The January Permit Freeze]
            </h2>
            <div class="flex items-center gap-3 text-sm font-sans text-stone-500">
                <span class="bg-stone-100 px-2 py-0.5 rounded text-stone-600 font-bold">VTA INTEL</span>
                <span>{datetime.now().strftime('%B %d, %Y')}</span>
            </div>
        </div>

        <div>
            <h3 class="text-lg font-bold text-red-700 uppercase tracking-widest mb-2 font-sans">
                The Big Squeeze
            </h3>
            <p class="text-lg leading-relaxed text-stone-800">
                [Write the main story here. Make it punchy.]
            </p>
        </div>

        <div class="bg-stone-50 p-6 rounded-lg border border-stone-100">
            <h3 class="text-sm font-bold text-stone-400 uppercase tracking-widest mb-4 font-sans">
                By The Numbers
            </h3>
            <ul class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <li class="flex flex-col">
                    <span class="text-3xl font-black text-stone-900 font-sans">[Number]</span>
                    <span class="text-sm text-stone-500 font-medium leading-tight">[Description]</span>
                </li>
            </ul>
        </div>

        <div>
            <h3 class="text-sm font-bold text-stone-900 uppercase tracking-widest mb-3 font-sans border-b border-stone-200 pb-1">
                On The Radar
            </h3>
            <ul class="space-y-3">
                <li class="flex gap-3">
                    <span class="text-blue-600 font-bold">▸</span>
                    <span class="text-stone-700 leading-relaxed">
                        <strong class="text-stone-900">[Board Name]:</strong> [Action/Analysis]
                    </span>
                </li>
            </ul>
        </div>

        <div class="bg-red-50 p-5 rounded border-l-4 border-red-500">
            <h3 class="text-xs font-bold text-red-800 uppercase tracking-widest mb-1 font-sans">
                Blind Spot
            </h3>
            <p class="text-stone-800 text-sm leading-relaxed">
                [The low-scoring risk analysis]
            </p>
        </div>

    </div>

    CONTENT TO ADAPT:
    {raw_signals}
    
    If data is empty, write about the "Calm Before the Storm" in January.
    """

    response = client.models.generate_content(model=MODEL_ID, contents=prompt)
    
    # Clean up any Markdown fences if the model adds them
    clean_html = response.text.replace("```html", "").replace("```", "").strip()
    return clean_html

def save_and_publish_digest(content):
    """
    Saves to Firestore (Latest & History).
    """
    # Dynamic Title based on content vibe
    if "Calm Before" in content:
        title = "VTA Brief: The January Backlog"
    else:
        title = f"VTA Brief: {datetime.now().strftime('%b %d')} Intel"
    
    # 1. SAVE TO DB
    digest_ref = db.collection("newsletters").document("latest")
    digest_ref.set({
        "title": title,
        "content": content,
        "timestamp": datetime.now(),
        "week_start": datetime.now() - timedelta(days=7),
        "week_end": datetime.now()
    })
    
    # History Copy
    history_id = datetime.now().strftime("%Y%m%d")
    db.collection("newsletters").document(history_id).set({
        "title": title,
        "content": content,
        "timestamp": datetime.now()
    })
    print("💾 Insider Brief saved to Firestore.")

if __name__ == "__main__":
    signals = fetch_weekly_signals()
    letter = write_insider_brief(signals)
    save_and_publish_digest(letter)