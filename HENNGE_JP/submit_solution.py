import time
import hmac
import hashlib
import struct
import base64
import json
import urllib.request


def generate_totp(userid):
    # Build the shared secret
    secret = (userid + "HENNGECHALLENGE003").encode("ascii")
    # TOTP settings: time step of 30 seconds, T0 = 0
    timestep = 30
    T = int(time.time() // timestep)
    # Pack T as an 8-byte big-endian integer
    msg = struct.pack(">Q", T)
    # Create HMAC-SHA512 digest
    hmac_digest = hmac.new(secret, msg, hashlib.sha512).digest()
    # Dynamic truncation: take the last nibble as offset
    offset = hmac_digest[-1] & 0x0F
    # Extract 4 bytes starting at offset and convert to integer
    truncated = struct.unpack(">I", hmac_digest[offset:offset+4])[0]
    truncated &= 0x7fffffff  # 31-bit integer
    # Reduce modulo 10^10 to get a 10-digit code
    otp = truncated % 10000000000
    return str(otp).zfill(10)


def send_mission3():
    # Fill in your credentials and GitHub Gist URL
    contact_email = "faishalmanzar@gmail.com"  # Replace with your email
    # Replace with your secret gist URL
    github_url = "https://gist.github.com/faishal882/8615308f38513bb53db9f927e19ca645"
    solution_language = "python"

    # Generate the TOTP password for the given email
    totp = generate_totp(contact_email)

    # Prepare the Basic Authentication header
    auth_str = f"{contact_email}:{totp}"
    auth_bytes = auth_str.encode("ascii")
    auth_b64 = base64.b64encode(auth_bytes).decode("ascii")

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Basic " + auth_b64
    }

    # Construct the JSON payload
    payload = {
        "github_url": github_url,
        "contact_email": contact_email,
        "solution_language": solution_language
    }
    json_data = json.dumps(payload).encode("utf-8")

    url = "https://api.challenge.hennge.com/challenges/003"
    req = urllib.request.Request(
        url, data=json_data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as response:
            print(response.read().decode("utf-8"))
    except Exception as e:
        print("Request failed:", e)


if __name__ == "__main__":
    send_mission3()
