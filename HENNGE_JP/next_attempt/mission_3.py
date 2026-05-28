import requests
import hmac
import hashlib
import time
import struct
import json
from requests.auth import HTTPBasicAuth

USERID = "faishalmanzar+1@gmail.com"
ROOT = "https://api.challenge.hennge.com/challenges/backend-recursion/004"
CONTENT_TYPE = "application/json"
SECRET_SUFFIX = "HENNGECHALLENGE004"
SHARED_SECRET = USERID + SECRET_SUFFIX

TIMESTEP = 30
T0 = 0
DIGITS = 10

data = {
    "github_url": "https://gist.github.com/faishal882/862fe39727140e09a5d676a348d7ac99",
    "contact_email": "faishalmanzar+1@gmail.com",
    "solution_language": "python"
}


def HOTP(K, C, digits=10):
    """HTOP:
    K is the shared key
    C is the counter value
    digits control the response length
    """
    K_bytes = str.encode(K)
    C_bytes = struct.pack(">Q", C)
    hmac_sha512 = hmac.new(key=K_bytes, msg=C_bytes,
                           digestmod=hashlib.sha512).hexdigest()
    return Truncate(hmac_sha512)[-digits:]


def Truncate(hmac_sha512):
    """truncate sha512 value"""
    offset = int(hmac_sha512[-1], 16)
    binary = int(hmac_sha512[(offset * 2):((offset*2)+8)], 16) & 0x7FFFFFFF
    return str(binary)


def TOTP(K, digits=10, timeref=0, timestep=30):
    """TOTP, time-based variant of HOTP
    digits control the response length
    the C in HOTP is replaced by ( (currentTime - timeref) / timestep )
    """
    C = int(time.time() - timeref) // timestep
    return HOTP(K, C, digits=digits)


# Generate TOTP password
passwd = TOTP(SHARED_SECRET, DIGITS, T0, TIMESTEP).zfill(10)

# CORRECTED: Use json=data instead of data=json.dumps(data)
# This automatically sets Content-Type to application/json
resp = requests.post(ROOT, auth=HTTPBasicAuth(USERID, passwd), json=data)

print(f"Status Code: {resp.status_code}")
print(f"Response: {resp.text}")

if resp.status_code == 200:
    print("Challenge completed successfully!")
    print("You should receive an email to submit your CV and Cover Letter.")
else:
    print("Challenge failed. Check your implementation.")
    try:
        print(f"Response JSON: {resp.json()}")
    except:
        print("Could not parse response as JSON")
