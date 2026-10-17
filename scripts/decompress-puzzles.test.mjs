// Optional tool integration check: node --test scripts/decompress-puzzles.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { zstdCompressSync } from 'node:zlib';

test('PZstandard frames, overwrite protection, and corrupt-input cleanup', () => {
  mkdirSync('artifacts', { recursive: true });
  const dir = mkdtempSync(resolve('artifacts/zstd-test-'));
  const input = join(dir, 'input.zst');
  const output = join(dir, 'output.csv');
  const payloads = [Buffer.from('header\nfirst\n'), Buffer.from('second\n')];
  const frames = payloads.map(payload => {
    const compressed = zstdCompressSync(payload);
    const header = Buffer.alloc(12);
    header.writeUInt32LE(0x184d2a50, 0);
    header.writeUInt32LE(4, 4);
    header.writeUInt32LE(compressed.length, 8);
    return Buffer.concat([header, compressed]);
  });
  const run = () => spawnSync(process.execPath, [
    'scripts/decompress-puzzles.mjs', input, output,
  ], { encoding: 'utf8' });
  writeFileSync(input, Buffer.concat(frames));
  assert.equal(run().status, 0);
  assert.deepEqual(readFileSync(output), Buffer.concat(payloads));
  assert.notEqual(run().status, 0);
  assert.deepEqual(readFileSync(output), Buffer.concat(payloads));
  const badOutput = join(dir, 'bad.csv');
  writeFileSync(input, Buffer.from('corrupt frame'));
  const bad = spawnSync(process.execPath, [
    'scripts/decompress-puzzles.mjs', input, badOutput,
  ]);
  assert.notEqual(bad.status, 0);
  assert.equal(existsSync(badOutput), false);
});
