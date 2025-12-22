import os
import resend
from datetime import datetime
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# 1. SETUP
load_dotenv()
resend.api_key = os.getenv("RESEND_API_KEY")

if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccount.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

def dispatch_high_value_alerts():
    print("📧 Scanning for High-Value (Score 7+) signals...")
    
    # 2. FILTER FOR QUALITY
    # Only pull signals marked as 'unread' with a score of 7 or higher
    query = db.collection("signals")\
        .where(filter=FieldFilter("status", "==", "unread"))\
        .where(filter=FieldFilter("score", ">=", 7))
    
    high_value_signals = query.stream()
    
    count = 0
    for doc in high_value_signals:
        count += 1
        sig = doc.to_dict()
        sig_id = doc.id
        
        # 3. LOOKUP SUBSCRIBER
        sub_doc = db.collection("subscribers").document(sig['subscriber_id']).get()
        if not sub_doc.exists:
            continue
        
        sub_data = sub_doc.to_dict()
        email_address = sub_data.get("email")
        industry = sig.get('industry', 'General Intelligence')
        score = sig.get('score', 0)
        
        print(f"✉️ Sending Executive Briefing ({score}/10) to {email_address}...")
        
        # 4. PREMIUM HTML TEMPLATE
        html_content = f"""
        <div style="background-color: #f4f7f9; padding: 40px 10px; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border-top: 6px solid #1a2a40;">
                
                <div style="padding: 30px; background-color: #ffffff;">
                    <p style="text-transform: uppercase; letter-spacing: 2px; color: #64748b; font-size: 12px; margin: 0 0 10px 0; font-weight: 700;">
                        Aiyoda Municipal Intelligence
                    </p>
                    <h1 style="color: #1a2a40; font-size: 24px; margin: 0; font-weight: 800;">
                        Executive Briefing: {industry}
                    </h1>
                </div>

                <div style="background-color: #1a2a40; padding: 20px 30px; color: #ffffff; display: flex;">
                    <div style="background-color: #e2e8f0; color: #1a2a40; border-radius: 4px; padding: 4px 12px; font-weight: 800; font-size: 14px; margin-right: 15px; height: fit-content;">
                        RELEVANCE: {score}/10
                    </div>
                    <div style="font-size: 13px; font-weight: 500; color: #94a3b8; text-transform: uppercase; padding-top: 4px;">
                        Priority Signal Detected
                    </div>
                </div>

                <div style="padding: 30px; color: #334155; line-height: 1.8; font-size: 16px;">
                    <div style="background-color: #f8fafc; border-radius: 6px; padding: 20px; border-left: 4px solid #cbd5e1; margin-bottom: 25px;">
                        <strong style="display: block; color: #1e293b; margin-bottom: 8px; font-size: 14px; text-transform: uppercase;">Summary of Impact</strong>
                        {sig['analysis'].replace('\n', '<br>')}
                    </div>
                    
                    <p style="font-size: 14px; color: #64748b;">
                        <strong>Source Authority:</strong> Vancouver City Records<br>
                        <strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    </p>
                </div>

                <div style="padding: 0 30px 40px 30px; text-align: center;">
                    <a href="https://vancouverwa.portal.civicclerk.com/" 
                       style="background-color: #1a2a40; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 5px; font-weight: 700; font-size: 14px; display: inline-block;">
                        View Original Document
                    </a>
                </div>

                <div style="padding: 20px; background-color: #f8fafc; text-align: center; border-top: 1px solid #e2e8f0;">
                    <p style="font-size: 11px; color: #94a3b8; margin: 0;">
                        © 2025 Aiyoda Transparency Agent. All rights reserved.<br>
                        This is a private intelligence briefing for authorized subscribers only.
                    </p>
                </div>
            </div>
        </div>
        """

        # 5. DISPATCH VIA PRODUCTION DOMAIN
        try:
            resend.Emails.send({
                "from": "Aiyoda Intelligence <alerts@aiyoda.app>",
                "to": [email_address],
                "subject": f"🚨 PRIORITY [{score}/10]: {industry} Intelligence Alert",
                "html": html_content
            })
            
            # 6. MARK AS NOTIFIED
            db.collection("signals").document(sig_id).update({"status": "notified"})
            print(f"   ✅ Alert successful. Signal {sig_id} moved to 'notified' status.")
            
        except Exception as e:
            print(f"   ❌ Dispatch failed: {e}")

    if count == 0:
        print("ℹ️ No high-scoring 'unread' signals found.")

if __name__ == "__main__":
    dispatch_high_value_alerts()