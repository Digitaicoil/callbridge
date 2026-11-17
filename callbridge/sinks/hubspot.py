"""HubSpot CRM: find or create the contact by phone number, then attach the call summary as a note.
Needs a private app token with crm.objects.contacts.read/write (HUBSPOT_TOKEN)."""
import time

import httpx

API = "https://api.hubapi.com/crm/v3/objects"
NOTE_TO_CONTACT = 202   # HubSpot-defined association type


def _client(env: dict) -> httpx.Client:
    return httpx.Client(headers={"Authorization": f"Bearer {env['HUBSPOT_TOKEN']}"}, timeout=30)


def find_or_create_contact(c: httpx.Client, phone: str, name: str = "") -> str:
    r = c.post(f"{API}/contacts/search", json={"filterGroups": [{"filters": [
        {"propertyName": "phone", "operator": "EQ", "value": phone}]}], "limit": 1})
    r.raise_for_status()
    hits = r.json().get("results", [])
    if hits:
        return hits[0]["id"]
    first, _, last = name.partition(" ")
    props = {"phone": phone, **({"firstname": first} if first else {}), **({"lastname": last} if last else {})}
    r = c.post(f"{API}/contacts", json={"properties": props})
    r.raise_for_status()
    return r.json()["id"]


def send(record, env: dict) -> None:
    with _client(env) as c:
        contact = find_or_create_contact(c, record.number, record.data.get("caller_name", ""))
        r = c.post(f"{API}/notes", json={
            "properties": {"hs_timestamp": int(time.time() * 1000),
                           "hs_note_body": record.text().replace("\n", "<br>")},
            "associations": [{"to": {"id": contact}, "types": [
                {"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": NOTE_TO_CONTACT}]}]})
        r.raise_for_status()
