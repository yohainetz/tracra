import hashlib
from py_singleton import singleton
import urllib.parse
import random
import string
import base64
import zlib

SALT_LEN = 32

@singleton
class HashHelper:
    def __init__(self):
        self.hashCache = {}
        self.salt = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(SALT_LEN))
        self.salt = self.salt.encode("utf-8")

    def fill(self, email):
        encoded_email = email.encode("ascii")

        # plain
        self.hashCache[email] = "plain"

        # md5
        m = hashlib.md5()
        m.update(encoded_email)
        self.hashCache[m.hexdigest()] = "md5"

        #sha1
        sh1 = hashlib.sha1()
        sh1.update(encoded_email)
        self.hashCache[sh1.hexdigest()] = "sha1"

        # sha224
        sh224 = hashlib.sha224()
        sh224.update(encoded_email)
        self.hashCache[sh224.hexdigest()] = "sha224"

        # sha256
        sh256 = hashlib.sha256()
        sh256.update(encoded_email)
        self.hashCache[sh256.hexdigest()] = "sha256"

        # sha384
        sh384 = hashlib.sha384()
        sh384.update(encoded_email)
        self.hashCache[sh384.hexdigest()] = "sha384"

        # sha512
        sh512 = hashlib.sha512()
        sh512.update(encoded_email)
        self.hashCache[sh512.hexdigest()] = "sha512"



        #urlencode
        urlencoded2 = urllib.parse.quote_plus(email)
        self.hashCache[urlencoded2] = "urlencoded_quote"

        # crc
        crc_unsigned = str(hex(zlib.crc32(encoded_email) & 0xffffffff)).split("x")[1]
        crc_signed   = str(hex(zlib.crc32(encoded_email)).split("x"))[1]
        self.hashCache[crc_signed] = "crc_signed"
        self.hashCache[crc_unsigned] = "crc_unsigned"

        # adler34
        t = zlib.adler32(encoded_email)
        self.hashCache[str(t)] = "adler32"
        self.hashCache[str(hex(t))[2:]] = "adler32_hex"

        #base64 ascii
        b64ed = base64.b64encode(email.encode("ascii")).decode("ascii")
        self.hashCache[b64ed] = "base64_ascii"

    def hashed(self, email, teststr):
        if email not in self.hashCache:
            self.fill(email)
        if len(teststr) < 6:
            return None
        for key in self.hashCache.keys():
            if teststr in key:
                return str((self.hashCache[key], len(teststr)))
        return self.hashCache.get(teststr, None)

    def hashed_with_salt(self, value):
        bytestr = value
        if isinstance(bytestr, str):
            bytestr = bytestr.encode("utf-8")

        sha256 = hashlib.sha256()
        sha256.update(self.salt)
        sha256.update(bytestr)
        return sha256.hexdigest()

    def isBase64(self, s):
        try:
            return base64.b64decode(base64.b64encode(s.encode("utf8"))).decode("utf8")
        except Exception:
            return False

    def isAscii(self, s):
        try:
            return s.encode("ascii").decode("ascii") == s
        except:
            return False