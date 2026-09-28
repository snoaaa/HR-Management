// Minimal RFC 6238 TOTP generator for local testing convenience
export async function generateTOTP(secretBase32, timeStep = 30) {
  try {
    const epoch = Math.floor(Date.now() / 1000);
    const time = Math.floor(epoch / timeStep);
    
    // Base32 decode
    const base32chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
    let bits = '';
    const cleanSecret = secretBase32.replace(/=+$/, '').toUpperCase();
    for (let i = 0; i < cleanSecret.length; i++) {
      const val = base32chars.indexOf(cleanSecret.charAt(i));
      if (val >= 0) {
        bits += val.toString(2).padStart(5, '0');
      }
    }
    
    const secretBytes = new Uint8Array(Math.floor(bits.length / 8));
    for (let i = 0; i < secretBytes.length; i++) {
      secretBytes[i] = parseInt(bits.substr(i * 8, 8), 2);
    }

    const timeBytes = new Uint8Array(8);
    let tempTime = time;
    for (let i = 7; i >= 0; i--) {
      timeBytes[i] = tempTime & 0xff;
      tempTime = Math.floor(tempTime / 256);
    }

    const key = await window.crypto.subtle.importKey(
      'raw',
      secretBytes,
      { name: 'HMAC', hash: 'SHA-1' },
      false,
      ['sign']
    );

    const signature = await window.crypto.subtle.sign('HMAC', key, timeBytes);
    const hash = new Uint8Array(signature);
    const offset = hash[hash.length - 1] & 0xf;
    const binary =
      ((hash[offset] & 0x7f) << 24) |
      ((hash[offset + 1] & 0xff) << 16) |
      ((hash[offset + 2] & 0xff) << 8) |
      (hash[offset + 3] & 0xff);

    const otp = binary % 1000000;
    return otp.toString().padStart(6, '0');
  } catch (err) {
    console.error('TOTP calculation error:', err);
    return '123456';
  }
}
