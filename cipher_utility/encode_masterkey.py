import codecs
from Crypto.Hash import SHA256
from Crypto.Cipher import AES


def bytes_to_str(b):
    return codecs.encode(b, 'hex_codec').decode('ascii')


def hex_str_to_bytes(h):
    return bytes.fromhex(h)


def encode_from_input():
    masterkey = input('Enter the master key: ')
    masterkey_2 = input('Enter it again: ')
    if masterkey != masterkey_2:
        raise ValueError('keys are not equal')

    print()

    key = input('Enter the ciphering password for master key: ')
    key_2 = input('Enter it again: ')
    if key != key_2:
        raise ValueError('keys are not equal')

    key_b = key.encode('utf-8')
    masterkey_b = masterkey.encode('utf-8')

    key_digest = SHA256.new(key_b).digest()

    cipher = AES.new(key_digest, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(masterkey_b)

    ciphered_masterkey_h = bytes_to_str(ciphertext)
    tag_h = bytes_to_str(tag)
    nonce_h = bytes_to_str(cipher.nonce)

    print()
    print(f'Ciphered master key: {ciphered_masterkey_h}')
    print(f'Authenticated encryption tag: {tag_h}')
    print(f'Nonce: {nonce_h}')


if __name__ == '__main__':
    encode_from_input()
