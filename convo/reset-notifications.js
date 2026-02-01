const admin = require('firebase-admin');
const serviceAccount = require('./firebase-service-account.json');

admin.initializeApp({
  credential: admin.credential.cert(serviceAccount)
});

const db = admin.firestore();

(async () => {
  // Get all emails and reset recent received ones
  const snapshot = await db.collection('emails')
    .orderBy('timestamp', 'desc')
    .limit(20)
    .get();
  
  console.log('Found', snapshot.size, 'emails');
  
  let count = 0;
  for (const doc of snapshot.docs) {
    const email = doc.data();
    // Only reset received emails (not sent)
    if (!email.is_sent && email.from) {
      console.log('Resetting:', email.subject?.slice(0, 50));
      await doc.ref.update({ discord_notified: false });
      count++;
      if (count >= 5) break;
    }
  }
  
  console.log('✅ Reset', count, 'emails');
  process.exit(0);
})();
