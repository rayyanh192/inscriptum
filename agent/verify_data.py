import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    cred = credentials.Certificate('convo/firebase-service-account.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()

print('🔍 Checking what we created:')
print()
print('Learned Rules:')
for doc in db.collection('learned_rules').limit(5).stream():
    data = doc.to_dict()
    print(f'  {doc.id}: {data.get("pattern", "N/A")[:60]}...')
print()
print('Performance Metrics:')
for doc in db.collection('performance_metrics').stream():
    data = doc.to_dict()
    print(f'  Week {data.get("week")}: {data.get("accuracy")*100:.0f}% ({data.get("correct_predictions")}/{data.get("total_emails")})')
print()
print('Exploration Hypotheses:')
for doc in db.collection('exploration_hypotheses').limit(3).stream():
    data = doc.to_dict()
    print(f'  {doc.id}: {data.get("status")} - {data.get("alternative_action")} (was {data.get("original_action")})')
