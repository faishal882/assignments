import hmac
import hashlib
import time
import struct
import base64


def generate_totp(secret_key, time_step=30, digits=6):
    """
    Generate a Time-Based One-Time Password (TOTP).
    :param secret_key: The shared secret key (Base32 encoded).
    :param time_step: Time step in seconds (default is 30 seconds).
    :param digits: Number of digits in the OTP (default is 6).
    :return: The generated OTP as a string.
    """
    # Get the current timestamp and calculate the counter
    timestamp = int(time.time())
    counter = timestamp // time_step

    # Convert the counter to bytes
    counter_bytes = struct.pack(">Q", counter)

    # Decode the Base32 secret key
    secret_key_bytes = base64.b32decode(secret_key)

    # Generate HMAC-SHA1 hash using the secret key and counter
    hmac_hash = hmac.new(secret_key_bytes, counter_bytes,
                         hashlib.sha1).digest()

    # Perform dynamic truncation to get the OTP
    offset = hmac_hash[-1] & 0x0F
    truncated_hash = hmac_hash[offset:offset + 4]
    otp = struct.unpack(">I", truncated_hash)[0] & 0x7FFFFFFF
    # Ensure the OTP has the correct number of digits
    otp = otp % (10 ** digits)

    return f"{otp:0{digits}d}"


# Example Usage
secret_key = "JBSWY3DPEHPK3PXP"  # Shared secret key
otp = generate_totp(secret_key)
print(f"Generated OTP: {otp}")
