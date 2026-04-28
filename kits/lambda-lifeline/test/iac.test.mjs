import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const CLI = join(__dirname, '..', 'bin', 'cli.mjs');

function run(args) {
  return spawnSync('node', [CLI, ...args], { encoding: 'utf8' });
}
function scratch() {
  const dir = mkdtempSync(join(tmpdir(), 'll-iac-'));
  return { dir, cleanup: () => rmSync(dir, { recursive: true, force: true }) };
}

test('iac dry-run finds SAM runtime references without modifying', () => {
  const { dir, cleanup } = scratch();
  try {
    const tmpl = join(dir, 'template.yaml');
    const original = `Transform: AWS::Serverless-2016-10-31
Resources:
  Fn:
    Type: AWS::Serverless::Function
    Properties:
      Runtime: nodejs20.x
`;
    writeFileSync(tmpl, original);
    const r = run(['iac', '--path', dir]);
    assert.equal(r.status, 0, r.stderr);
    assert.match(r.stdout, /SAM\/CFN|SAM/);
    assert.match(r.stdout, /nodejs20\.x/);
    assert.equal(readFileSync(tmpl, 'utf8'), original);
  } finally { cleanup(); }
});

test('iac --apply rewrites SAM runtime', () => {
  const { dir, cleanup } = scratch();
  try {
    const tmpl = join(dir, 'template.yaml');
    writeFileSync(tmpl, `Transform: AWS::Serverless-2016-10-31
Resources:
  Fn:
    Type: AWS::Serverless::Function
    Properties:
      Runtime: nodejs20.x
`);
    const r = run(['iac', '--path', dir, '--apply']);
    assert.equal(r.status, 0, r.stderr);
    const result = readFileSync(tmpl, 'utf8');
    assert.match(result, /Runtime: nodejs22\.x/);
    assert.doesNotMatch(result, /nodejs20\.x/);
  } finally { cleanup(); }
});

test('iac --apply rewrites Terraform runtime', () => {
  const { dir, cleanup } = scratch();
  try {
    const tf = join(dir, 'main.tf');
    writeFileSync(tf, `resource "aws_lambda_function" "a" {
  runtime = "nodejs18.x"
}
resource "aws_lambda_function" "b" {
  runtime = "nodejs20.x"
}
`);
    const r = run(['iac', '--path', dir, '--apply']);
    assert.equal(r.status, 0, r.stderr);
    const result = readFileSync(tf, 'utf8');
    assert.match(result, /runtime = "nodejs22\.x"/);
    assert.doesNotMatch(result, /nodejs20\.x/);
    assert.doesNotMatch(result, /nodejs18\.x/);
  } finally { cleanup(); }
});

test('iac --apply rewrites CDK runtime enum', () => {
  const { dir, cleanup } = scratch();
  try {
    const stack = join(dir, 'stack.ts');
    writeFileSync(stack, `import * as lambda from 'aws-cdk-lib/aws-lambda';
new lambda.Function(this, 'A', { runtime: lambda.Runtime.NODEJS_22_X });
new lambda.Function(this, 'B', { runtime: lambda.Runtime.NODEJS_22_X });
`);
    const r = run(['iac', '--path', dir, '--apply']);
    assert.equal(r.status, 0, r.stderr);
    const result = readFileSync(stack, 'utf8');
    assert.match(result, /NODEJS_22_X/);
    assert.doesNotMatch(result, /NODEJS_20_X/);
    assert.doesNotMatch(result, /NODEJS_18_X/);
  } finally { cleanup(); }
});

test('iac is idempotent', () => {
  const { dir, cleanup } = scratch();
  try {
    const tmpl = join(dir, 'template.yaml');
    writeFileSync(tmpl, `Transform: AWS::Serverless-2016-10-31
Resources:
  Fn: { Type: AWS::Serverless::Function, Properties: { Runtime: nodejs22.x } }
`);
    const r1 = run(['iac', '--path', dir, '--apply']);
    const r2 = run(['iac', '--path', dir, '--apply']);
    assert.equal(r1.status, 0);
    assert.equal(r2.status, 0);
    assert.match(r2.stdout, /No IaC runtime references needed patching/);
  } finally { cleanup(); }
});