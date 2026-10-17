// Node 24+; no project Python dependency. Supports the Lichess PZstandard export.
// Metadata frames supply the following compressed frame size.
// https://github.com/facebook/zstd/tree/dev/contrib/pzstd
// Usage: node scripts/decompress-puzzles.mjs input.csv.zst output.csv
import { open, unlink } from 'node:fs/promises';
import { zstdDecompressSync } from 'node:zlib';

if (process.argv.length !== 4) {
  throw new Error('Usage: node decompress-puzzles.mjs input.csv.zst output.csv');
}
const input = await open(process.argv[2], 'r');
let output;
let succeeded = false;
try {
  output = await open(process.argv[3], 'wx');
  const { size } = await input.stat();
  let offset = 0;
  while (offset < size) {
    const header = Buffer.alloc(12);
    const read = await input.read(header, 0, header.length, offset);
    if (read.bytesRead !== 12 || header.readUInt32LE(0) !== 0x184d2a50 ||
        header.readUInt32LE(4) !== 4) {
      throw new Error('Expected PZstandard metadata frame');
    }
    const length = header.readUInt32LE(8);
    if (length === 0 || length > 64 * 1024 * 1024 || offset + 12 + length > size) {
      throw new Error('Invalid PZstandard frame length');
    }
    const frame = Buffer.alloc(length);
    const frameRead = await input.read(frame, 0, length, offset + 12);
    if (frameRead.bytesRead !== length) throw new Error('Truncated data frame');
    await output.writeFile(zstdDecompressSync(frame, { maxOutputLength: 64 * 1024 * 1024 }));
    offset += 12 + length;
  }
  succeeded = true;
} finally {
  await input.close();
  if (output) {
    await output.close();
    if (!succeeded) await unlink(process.argv[3]);
  }
}
