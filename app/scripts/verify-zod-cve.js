// Repro CVE-2023-54404 (GHSA-mrhx-c7xc-m3x5): zod exhausts memory by
// accumulating one validation issue per element of an oversized constrained
// collection instead of failing the leading size bound first.
// Exits 0 when an oversized array/map/set yields exactly ONE too_big issue
// with ZERO element parses (fixed), exits 1 otherwise (vulnerable).
const path = require('path');
const zodPath = process.argv[2] || path.resolve(__dirname, '..', 'node_modules', 'zod');
const { z } = require(zodPath);

let failures = 0;
function check(name, makeSchema, input) {
  let parsed = 0;
  const el = z.string().refine(() => { ++parsed; return false; });
  const r = makeSchema(el).safeParse(input);
  const ok = !r.success && r.error.issues.length === 1
    && r.error.issues[0].code === 'too_big' && parsed === 0;
  console.log(`${ok ? 'PASS' : 'FAIL'} ${name}: parsed=${parsed} issues=${r.success ? 0 : r.error.issues.length}`);
  if (!ok) failures++;
}

check('array .max(2) rejects 3 items first', (el) => z.array(el).max(2, 'too many'), [1, 2, 3]);
check('set .max(1) rejects 2 items first', (el) => z.set(el).max(1), new Set([1, 2]));
// z.map .max() only exists in v4 (part of the #6652 fix); on v3 just assert
// the unbounded baseline: one issue per bad entry instead of a single cap.
{
  const hasMax = typeof z.map(z.string(), z.string()).max === 'function';
  const schema = hasMax ? z.map(z.string(), z.string()).max(1) : z.map(z.string(), z.string());
  const r = schema.safeParse(new Map([[1, 1], [2, 2]]));
  const ok = hasMax
    ? (!r.success && r.error.issues.length === 1 && r.error.issues[0].code === 'too_big')
    : (!r.success && r.error.issues.length > 1);
  console.log(`${ok ? 'PASS' : 'FAIL'} map oversized: issues=${r.success ? 0 : r.error.issues.length} (v4 .max API: ${hasMax})`);
  if (!ok) failures++;
}

const version = require(path.join(zodPath, 'package.json')).version;
console.log(`zod ${version}: ${failures === 0 ? 'bounded (fixed)' : 'unbounded (VULNERABLE)'}`);
process.exit(failures === 0 ? 0 : 1);
