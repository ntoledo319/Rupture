// Example Lambda handler that shows every Node 20→22 compatibility hazard we test for.
import config from './config.json' assert { type: 'json' };
import settings from './settings.json' assert { type: 'json' };

// dynamic import with assert — also flagged
async function loadFeatureFlags() {
  const flags = await import('./flags.json', { assert: { type: 'json' } });
  return flags.default;
}

// Buffer.toString with a negative end index — throws RangeError on Node 22
export function decodeLastByte(buf) {
  return buf.toString('utf8', 0, -1);
}

// Stream constructor with no explicit highWaterMark — lint warning
import { Readable } from 'node:stream';
export function makeStream(data) {
  return new Readable({
    read() { this.push(data); this.push(null); }
  });
}

export const handler = async (event) => {
  const flags = await loadFeatureFlags();
  return {
    statusCode: 200,
    body: JSON.stringify({ config, settings, flags, event }),
  };
};