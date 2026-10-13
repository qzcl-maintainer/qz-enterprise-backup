# TLS certificate

`cert.pem` / `key.pem` are a **self-signed** certificate (CN=localhost, SAN=localhost/127.0.0.1, valid ~825 days) generated for local/convenience HTTPS. Browsers will show an untrusted-certificate warning — that's expected for a self-signed cert; proceed past it (or import `cert.pem` into your OS/browser trust store if you want the warning gone for local use).

**Do not use this cert for a real deployment reachable by anyone other than you.** Since it's committed to the repo, the private key is not secret. For production, replace both files with a certificate from a real CA (e.g. Let's Encrypt) or your org's internal PKI — same filenames, same mount point (`/ssl` in `docker-compose.yml`).

To regenerate a fresh self-signed pair:

```sh
openssl req -x509 -nodes -newkey rsa:2048 -days 825 \
  -keyout ssl/key.pem -out ssl/cert.pem \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
chmod 600 ssl/key.pem
```
