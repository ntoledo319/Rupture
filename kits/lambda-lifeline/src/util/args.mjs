// Minimal zero-dep arg parser — supports --flag value, --flag=value, --boolean, positional.
export function parseArgs(argv) {
  const flags = {};
  const positional = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const eq = a.indexOf('=');
      if (eq > -1) {
        flags[a.slice(2, eq)] = a.slice(eq + 1);
      } else {
        const next = argv[i + 1];
        if (!next || next.startsWith('--')) {
          flags[a.slice(2)] = true;
        } else {
          flags[a.slice(2)] = next;
          i++;
        }
      }
    } else {
      positional.push(a);
    }
  }
  return { flags, positional };
}

export function boolFlag(flags, name, envVar = null) {
  if (envVar && process.env[envVar] === '1') return true;
  return flags[name] === true || flags[name] === 'true';
}

export function list(val) {
  if (!val || val === true) return [];
  return String(val).split(',').map(s => s.trim()).filter(Boolean);
}

export function requireFlag(flags, name) {
  if (flags[name] === undefined) {
    throw new Error(`Missing required flag: --${name}`);
  }
  return flags[name];
}

export function isDryRun(flags) {
  if (process.env.LAMBDA_LIFELINE_DRY_RUN === '1') return true;
  if (flags.apply === true) return false;
  return true; // default: dry-run for safety
}