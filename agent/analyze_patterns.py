import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    cred = credentials.Certificate('../convo/firebase-service-account.json')
    firebase_admin.initialize_app(cred)
db = firestore.client()

print('📧 Analyzing your REAL Gmail emails...\n')
emails = []
for doc in db.collection('emails').limit(100).stream():
    data = doc.to_dict()
    emails.append(data)

from_domains = {}
subjects = []
for email in emails:
    sender = email.get('from', '')
    domain = sender.split('@')[-1] if '@' in sender else 'unknown'
    from_domains[domain] = from_domains.get(domain, 0) + 1
    
    subject = email.get('subject', '')
    if subject:
        subjects.append(subject)

print(f'Top sender domains in your Gmail:')
for domain, count in sorted(from_domains.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f'  {domain}: {count} emails')

print(f'\nSample subjects:')
for subject in subjects[:15]:
    print(f'  - {subject}')

print(f'\n✅ Total real emails analyzed: {len(emails)}')
print(f'✅ Ready to run simulation with realistic patterns!')
