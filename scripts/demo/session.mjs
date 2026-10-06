// Local demo only: seal a `connection` cookie for an address with this stack's SESSION_KEY,
// standing in for the Google OAuth callback. Usage: node scripts/demo/session.mjs you@example.com
import { readFileSync } from 'node:fs';
import { connectorId, seal } from '../../frontend/server/auth.mjs';

const email = process.argv[2];
const key = process.env.SESSION_KEY || readFileSync(new URL('../../.env', import.meta.url), 'utf8').match(/^SESSION_KEY=(\w+)/m)?.[1];
if (!email || !key) throw new Error('usage: node scripts/demo/session.mjs <email> (needs SESSION_KEY or .env)');
process.stdout.write(seal({ kind: 'connection', email, connector: connectorId(email), expires: Date.now() + 8 * 3_600_000 },
  Buffer.from(key, 'hex')));
