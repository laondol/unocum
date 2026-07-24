import { openDB } from 'idb'

const DID_DB = 'yp_did'
const DID_STORE = 'keys'
const DID_VERSION = 1

interface DIDKeyStore {
  did: string
  publicKeyJwk: JsonWebKey
  privateKeyJwk: JsonWebKey
  createdAt: string
}

async function getDB() {
  return openDB(DID_DB, DID_VERSION, {
    upgrade(db) {
      if (!db.objectStoreNames.contains(DID_STORE)) {
        db.createObjectStore(DID_STORE, { keyPath: 'did' })
      }
    },
  })
}

export async function generateDIDKey(): Promise<CryptoKeyPair> {
  return crypto.subtle.generateKey(
    { name: 'ECDSA', namedCurve: 'P-256' },
    true,
    ['sign', 'verify']
  )
}

export async function exportPublicKeyJwk(key: CryptoKey): Promise<JsonWebKey> {
  return crypto.subtle.exportKey('jwk', key)
}

export async function exportPrivateKeyJwk(key: CryptoKey): Promise<JsonWebKey> {
  return crypto.subtle.exportKey('jwk', key)
}

export async function importPublicKey(jwk: JsonWebKey): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    'jwk', jwk,
    { name: 'ECDSA', namedCurve: 'P-256' },
    true, ['verify']
  )
}

export async function importPrivateKey(jwk: JsonWebKey): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    'jwk', jwk,
    { name: 'ECDSA', namedCurve: 'P-256' },
    true, ['sign']
  )
}

export async function saveDIDKey(did: string, keyPair: CryptoKeyPair): Promise<void> {
  const db = await getDB()
  const [publicKeyJwk, privateKeyJwk] = await Promise.all([
    exportPublicKeyJwk(keyPair.publicKey),
    exportPrivateKeyJwk(keyPair.privateKey),
  ])
  await db.put(DID_STORE, {
    did,
    publicKeyJwk,
    privateKeyJwk,
    createdAt: new Date().toISOString(),
  } as DIDKeyStore)
}

export async function getDIDKey(did: string): Promise<CryptoKeyPair | null> {
  const db = await getDB()
  const stored: DIDKeyStore | undefined = await db.get(DID_STORE, did)
  if (!stored) return null
  const [publicKey, privateKey] = await Promise.all([
    importPublicKey(stored.publicKeyJwk),
    importPrivateKey(stored.privateKeyJwk),
  ])
  return { publicKey, privateKey }
}

export async function deleteDIDKey(did: string): Promise<void> {
  const db = await getDB()
  await db.delete(DID_STORE, did)
}

export async function listDIDs(): Promise<DIDKeyStore[]> {
  const db = await getDB()
  return db.getAll(DID_STORE)
}

export async function signPayload(did: string, payload: string): Promise<string> {
  const keyPair = await getDIDKey(did)
  if (!keyPair) throw new Error('DID key not found: ' + did)
  const encoder = new TextEncoder()
  const signature = await crypto.subtle.sign(
    { name: 'ECDSA', hash: { name: 'SHA-256' } },
    keyPair.privateKey,
    encoder.encode(payload)
  )
  return arrayBufferToBase64(signature)
}

export async function verifySignature(
  publicKeyJwk: JsonWebKey,
  payload: string,
  signatureBase64: string
): Promise<boolean> {
  const publicKey = await importPublicKey(publicKeyJwk)
  const encoder = new TextEncoder()
  return crypto.subtle.verify(
    { name: 'ECDSA', hash: { name: 'SHA-256' } },
    publicKey,
    base64ToArrayBuffer(signatureBase64),
    encoder.encode(payload)
  )
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i])
  return btoa(binary)
}

function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  return bytes.buffer
}
