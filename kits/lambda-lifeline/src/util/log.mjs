// Tiny logger with colors when the terminal supports them.
const isTTY = process.stdout.isTTY && !process.env.NO_COLOR;
const c = (code, s) => isTTY ? `\x1b[${code}m${s}\x1b[0m` : s;
export const color = {
  red: s => c(31, s),
  green: s => c(32, s),
  yellow: s => c(33, s),
  blue: s => c(34, s),
  magenta: s => c(35, s),
  cyan: s => c(36, s),
  gray: s => c(90, s),
  bold: s => c(1, s),
};

export const log = {
  info:  (m) => console.log(color.cyan('ℹ'), m),
  ok:    (m) => console.log(color.green('✓'), m),
  warn:  (m) => console.log(color.yellow('⚠'), m),
  err:   (m) => console.error(color.red('✗'), m),
  hdr:   (m) => console.log('\n' + color.bold(color.magenta('▸ ' + m))),
  dim:   (m) => console.log(color.gray(m)),
  json:  (o) => console.log(JSON.stringify(o, null, 2)),
};

export function dryRunBanner(active) {
  if (active) log.warn(color.bold('DRY RUN — no changes written. Pass --apply to execute.'));
}