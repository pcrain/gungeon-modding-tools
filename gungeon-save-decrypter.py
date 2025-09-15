#!/usr/bin/python
#Gungeon save decrypter

import sys, hashlib, pprint, json

SECRET = "Putting in a super basic encryption pass so our saves are a little harder to edit than just opening a text or hex editor.  Need a secret key or some such... so here's some nonsense."
SLEN = len(SECRET)
VS = "version: 0\n"

def md5(string):
  return hashlib.md5(string.encode('utf-8')).hexdigest()
def xor(s):
  return ''.join([chr(s[i] ^ ord(SECRET[i % SLEN])) for i in range(len(s))])
def decrypt(s):
  return json.dumps(json.loads(xor(s[len(VS):])), indent=2)
def encrypt(s):
  return VS.encode("ascii") + xor(json.dumps(json.loads(s), separators=(',', ':')).strip().encode("ascii")).encode("ascii")

with open(sys.argv[1], 'rb') as dd:
  raw = dd.read()
encrypted = raw[:len(VS)].decode() == VS
if encrypted:
  decrypted = decrypt(raw)
  if md5(raw.decode()) == md5(encrypt(decrypted).decode()):
    print(decrypted)
  else:
    print("decryption failed")
else:
  encrypted = raw.decode().strip()
  newraw = encrypt(encrypted)
  if md5(encrypted) == md5(decrypt(newraw)):
    print(newraw)
  else:
    print("encryption failed")
