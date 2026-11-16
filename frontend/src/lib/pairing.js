// Zobrazenie párovacieho kódu a stavu headsetu. Časy sú v sekundách (Unix).

export const spacedCode = (code) => `${code.slice(0, 3)} ${code.slice(3)}`;

// Zostávajúca platnosť kódu ako m:ss. Po vypršaní null.
export function countdown(expiresAt, now) {
  const left = Math.ceil(expiresAt - now);
  if (left <= 0) return null;
  return `${Math.floor(left / 60)}:${String(left % 60).padStart(2, "0")}`;
}

export function deviceStatus(device, now) {
  if (device.connected) return "Pripojený, posiela dáta";
  if (device.last_seen == null) return "Spárovaný, zatiaľ sa nepripojil";
  const age = now - device.last_seen;
  const ago = age < 3600 ? `${Math.max(1, Math.round(age / 60))} min` : age < 86400 ? `${Math.round(age / 3600)} h` : `${Math.round(age / 86400)} d`;
  return `Odpojený, naposledy pred ${ago}`;
}
