/**
 * Quick script to re-authorize Gmail with send permissions
 * Run this once to get a new token
 */

import { authorize } from './auth.js';

console.log('🔐 Re-authorizing Gmail with send permissions...\n');
console.log('New scopes being requested:');
console.log('  - gmail.readonly (read emails)');
console.log('  - gmail.send (send emails)');
console.log('  - gmail.modify (modify labels)\n');

const auth = await authorize();
console.log('\n✅ Authorization complete! New token saved.');
console.log('You can now run the Discord bot with: npm start');
