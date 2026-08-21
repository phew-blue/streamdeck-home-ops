// plugin/src/png.ts
//
// A minimal PNG encoder.
//
// Stream Deck ignores every SVG form we tried -- raw markup, base64 SVG and a
// charset=utf8 data URI were all accepted without error and none appeared,
// leaving the manifest's default image on the key. Base64 PNG works, so the
// artwork has to be raster.
//
// Pre-rendering it was the obvious answer and the wrong one: a gauge at 1%
// resolution is 400-odd files and megabytes of base64 checked into the repo.
// Node ships zlib, and a PNG is four chunks around a deflate stream, so the
// plugin encodes its own and draws any value exactly.
import { deflateSync } from "node:zlib";

const CRC_TABLE = (() => {
  const t = new Int32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c;
  }
  return t;
})();

function crc32(buf: Buffer): number {
  let c = -1;
  for (let i = 0; i < buf.length; i++) c = CRC_TABLE[(c ^ buf[i]!) & 0xff]! ^ (c >>> 8);
  return (c ^ -1) >>> 0;
}

function chunk(type: string, data: Buffer): Buffer {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length, 0);
  const body = Buffer.concat([Buffer.from(type, "ascii"), data]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(body), 0);
  return Buffer.concat([len, body, crc]);
}

/**
 * Encode RGB pixels as a base64 PNG data URI, in the form setImage accepts.
 *
 * `rgb` is width*height*3 bytes. Colour type 2 (truecolour, no alpha) keeps the
 * encoder short; the tiles are opaque anyway, and a key is composited onto the
 * deck's own black.
 */
export function encodePng(width: number, height: number, rgb: Uint8Array): string {
  // Each scanline is prefixed with its filter type; 0 means "none", which
  // costs a little size and saves a great deal of code.
  const stride = width * 3;
  const raw = Buffer.alloc((stride + 1) * height);
  for (let y = 0; y < height; y++) {
    raw[y * (stride + 1)] = 0;
    Buffer.from(rgb.buffer, rgb.byteOffset + y * stride, stride)
      .copy(raw, y * (stride + 1) + 1);
  }

  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8;   // bit depth
  ihdr[9] = 2;   // colour type: truecolour
  ihdr[10] = 0;  // deflate
  ihdr[11] = 0;  // adaptive filtering
  ihdr[12] = 0;  // no interlace

  const png = Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk("IHDR", ihdr),
    chunk("IDAT", deflateSync(raw, { level: 9 })),
    chunk("IEND", Buffer.alloc(0)),
  ]);
  return `data:image/png;base64,${png.toString("base64")}`;
}
