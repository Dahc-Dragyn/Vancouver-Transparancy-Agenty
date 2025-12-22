import os
import hashlib
import resend
from datetime import datetime
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# 1. Setup & Environment
load_dotenv()
resend.api_key = os.getenv("RESEND_API_KEY")

if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccount.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

def get_content_hash(subscriber_id, analysis_text):
    """Creates a unique fingerprint for a signal to prevent duplicates."""
    # We hash the subscriber ID + the first 100 chars of analysis 
    # to identify if we've sent this specific info to this specific person before.
    combined = f"{subscriber_id}_{analysis_text[:100]}"
    return hashlib.sha256(combined.encode()).hexdigest()

def dispatch_alerts():
    print(f"📧 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Dispatcher...")
    
    # Fetch all signals that are 'unread'
    query = db.collection("signals").where(filter=FieldFilter("status", "==", "unread"))
    new_signals = query.stream()
    
    count = 0
    for doc in new_signals:
        count += 1
        sig = doc.to_dict()
        sig_id = doc.id
        sub_id = sig.get('subscriber_id')
        
        # A. Look up the subscriber
        sub_doc = db.collection("subscribers").document(sub_id).get()
        if not sub_doc.exists:
            print(f"⚠️  Subscriber {sub_id} not found. Skipping.")
            continue
        
        sub_data = sub_doc.to_dict()
        email_address = sub_data.get("email")
        
        # B. DEDUPLICATION CHECK
        # We check a 'sent_notifications' log to ensure this content is fresh for this user
        content_hash = get_content_hash(sub_id, sig['analysis'])
        log_ref = db.collection("sent_notifications").document(content_hash)
        
        if log_ref.get().exists:
            print(f"⏭️  Already sent similar info to {email_address}. Marking notified and skipping email.")
            db.collection("signals").document(sig_id).update({"status": "notified"})
            continue

        # C. SEND THE PROFESSIONAL BRIEFING
        print(f"✉️  Dispatching to {email_address} (Industry: {sig.get('industry', 'General')})...")
        
        try:
            resend.Emails.send({
                "from": "VTA Intelligence <alerts@aiyoda.app>",
                "to": [email_address],
                "subject": f"🚨 ACTION REQUIRED: {sig.get('industry', 'New Signal')} Update",
                "html": f"""
                <div style="font-family: sans-serif; max-width: 600px; margin: auto; border: 1px solid #eee; border-top: 4px solid #2c3e50; padding: 20px; color: #333;">
                    <h2 style="color: #2c3e50; margin-top: 0;">Vancouver Transparency Agent</h2>
                    <p style="color: #7f8c8d; font-size: 14px; margin-bottom: 20px;">Bespoke Intelligence Briefing for {sig.get('industry')}</p>
                    
                    <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; line-height: 1.6;">
                        {sig['analysis'].replace('\n', '<br>')}
                    </div>
                    
                    <p style="margin-top: 25px; font-size: 13px; color: #95a5a6;">
                        <em>Source: Vancouver Municipal Portal (CivicClerk)</em>
                    </p>
                    
                    <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                    
                    <footer style="font-size: 11px; color: #bdc3c7; text-align: center;">
                        You received this because your Interest Profile matches recent City Council activity. 
                        Manage your alerts at <a href="https://aiyoda.app" style="color: #3498db; text-decoration: none;">aiyoda.app</a>
                    </footer>
                </div>
                """
            })
            
            # D. LOG SUCCESS & UPDATE STATE
            # Update the signal to notified
            db.collection("signals").document(sig_id).update({"status": "notified"})
            
            # Log the hash so we never send this specific info to this user again
            log_ref.set({
                "subscriber_id": sub_id,
                "sent_at": datetime.now(),
                "signal_id": sig_id
            })
            
            print(f"✅ Success! User notified and de-dupe log created.")
            
        except Exception as e:
            print(f"❌ Resend Error: {e}")

    if count == 0:
        print("ℹ️  No unread signals found.")

if __name__ == "__main__":
    dispatch_alerts()