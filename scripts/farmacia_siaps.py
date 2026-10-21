"""Catálogo público BNAFAR/SIAPS: descobrimento sem inventar indicadores.
O painel mensal Looker Studio e o SIAPS exigem exportação/contrato público
verificado antes de publicar valores por município.
"""
from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public/data/farmacia_siaps.json"
BNAFAR_PAGE = "https://bnafar.github.io/statusenvio/"
LOG = logging.getLogger("farmacia_siaps")


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            target = dict(attrs).get("href", "")
            if target:
                self.links.append(target)


def latest_qualifar(html):
    parser = Links()
    parser.feed(html)
    matches = []
    for target in parser.links:
        url = urljoin(BNAFAR_PAGE, target)
        parts = urlparse(url)
        if parts.scheme != "https" or parts.netloc != "bnafar.github.io":
            continue
        if not re.fullmatch(r"/statusenvio/arquivos/qualifarsus/ciclo_0[1-4]_20\d{2}/20\d{2}\.\d{2}\.\d{2}_Status_Qualifar_SUS_[1-4]_ciclo_20\d{2}\.xlsx", parts.path, re.I):
            continue
        date_text = Path(parts.path).name[:10]
        try:
            date = datetime.strptime(date_text, "%Y.%m.%d").date()
        except ValueError:
            continue
        if date > datetime.now(timezone.utc).date():
            continue
        matches.append((date, url))
    if not matches:
        raise ValueError("Nenhuma planilha Qualifar-SUS válida encontrada no catálogo")
    latest = max(matches, key=lambda pair: (pair[0], pair[1]))
    return latest[0].isoformat(), latest[1]


def load():
    payload = json.loads(OUT.read_text(encoding="utf-8"))
    if payload.get("schemaVersion") != "1.0" or payload.get("municipality") != "4304606":
        raise ValueError("Contrato de dados municipal inválido")
    return payload


def run():
    payload = load()
    req = Request(BNAFAR_PAGE, headers={"User-Agent": "WebGIS-Saude-Canoas/1.0 (fontes-publicas)"})
    with urlopen(req, timeout=25) as response:
        if response.status != 200:
            raise RuntimeError("Catálogo BNAFAR HTTP " + str(response.status))
        html = response.read(1024 * 1024 + 1)
        if len(html) > 1024 * 1024:
            raise ValueError("Página do catálogo excedeu limite de tamanho")
        charset = response.headers.get_content_charset() or "utf-8"
    reference, url = latest_qualifar(html.decode(charset, errors="replace"))
    entry = payload["sources"]["qualifar_monitoramento"]
    # A planilha foi localizada, mas sua linha para Canoas ainda não foi validada.
    # Não trocar status para 'ok' nem fabricar valores, estoque ou dispensações.
    changed = (entry.get("reference"), entry.get("url")) != (reference, url)
    if changed:
        entry["reference"] = reference
        entry["url"] = url
        entry["status"] = "partial"
        entry["retrievedAt"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        payload["updatedAt"] = entry["retrievedAt"]
        fd, tmp = tempfile.mkstemp(prefix="farmacia_siaps-", suffix=".json", dir=OUT.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as out:
                json.dump(payload, out, ensure_ascii=False, indent=2, allow_nan=False)
                out.write("\n")
            os.replace(tmp, OUT)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    LOG.info("Qualifar-SUS catálogo: %s (%s) %s", reference, "atualizado" if changed else "sem alterações", url)
    LOG.info("SIAPS: portal público registrado; nenhuma API ou exportação municipal foi presumida")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        run()
    except Exception as err:
        LOG.warning("Catálogo farmacêutico não atualizado; snapshot anterior preservado: %s", err)
