import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    cred = credentials.Certificate('convo/firebase-service-account.json')
    firebase_admin.initialize_app(cred)
db = firestore.client()

print('=== EMAILS ===')
all_emails = list(db.collection('emails').stream())
print(f'Total emails: {len(all_emails)}')

# Check which have scraped_at
scraped = [e for e in all_emails if e.to_dict().get('scraped_at')]
print(f'Emails with scraped_at: {len(scraped)}')

print('\n=== PEOPLE ===')
people = list(db.collection('people').stream())
print(f'Total people: {len(people)}')
for doc in people[:5]:
    d = doc.to_dict()
    print(f"  - {d.get('email', 'N/A')}: score={d.get('importance_score', 'N/A')}")

print('\n=== TRAINING FEEDBACK ===')
feedback = list(db.collection('training_feedback').stream())
print(f'Total feedback entries: {len(feedback)}')

print('\n=== LEARNED RULES ===')
rules = list(db.collection('learned_rules').stream())
print(f'Total learned rules: {len(rules)}')
