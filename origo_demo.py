#!/usr/bin/env python3
"""
Origo reference core (educational, not production-grade).

Demonstrates: canonical event IDs, Ed25519 signatures, a provenance DAG
(ore -> silicon -> chip -> phone -> shelf), mass-balance and double-spend
rules, and Merkle anchoring with inclusion proofs.

Run:  python3 origo_demo.py
"""
import hashlib, json
from collections import defaultdict

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    from cryptography.hazmat.primitives import serialization as S
    REAL_SIG = True
except ImportError:  # demo fallback only: NOT a real signature scheme
    import hmac, os
    REAL_SIG = False

def canon(o) -> bytes:
    """Simplified canonicalization (the spec uses RFC 8785 JCS)."""
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()

def H(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

class Actor:
    def __init__(self, name):
        self.name = name
        if REAL_SIG:
            self._sk = Ed25519PrivateKey.generate()
            self.pk = self._sk.public_key().public_bytes(S.Encoding.Raw, S.PublicFormat.Raw).hex()
        else:
            self._sk = os.urandom(32); self.pk = self._sk.hex()
        self.did = f"did:origo:{H(self.pk.encode())[:16]}"
    def sign(self, msg: bytes) -> str:
        return (self._sk.sign(msg) if REAL_SIG else hmac.new(self._sk, msg, "sha256").digest()).hex()

def verify_sig(pk_hex, sig_hex, msg: bytes) -> bool:
    try:
        if REAL_SIG:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(pk_hex)).verify(bytes.fromhex(sig_hex), msg); return True
        return hmac.compare_digest(hmac.new(bytes.fromhex(pk_hex), msg, "sha256").digest(), bytes.fromhex(sig_hex))
    except Exception:
        return False

def make_event(actor, etype, inputs, outputs, process=None, time="2026-01-01T00:00:00Z"):
    body = {"type": etype, "actor": actor.did, "time": time, "process": process,
            "inputs": inputs, "outputs": outputs}
    eid = "ev:" + H(canon(body))
    return {**body, "id": eid, "signature": actor.sign(eid.encode())}

def lot(pid, qty, unit="kg"): return {"id": pid, "qty": qty, "unit": unit}

MAX_YIELD = {"smelting": 0.5, "fab": 1.0, "assembly": 1.0, None: 1.0}  # output mass / input mass

class Ledger:
    def __init__(self): self.events, self.keys, self.names = {}, {}, {}
    def register(self, a): self.keys[a.did] = a.pk; self.names[a.did] = a.name
    def add(self, ev): self.events[ev["id"]] = ev

    def validate(self):
        errs, consumed, produced = [], defaultdict(float), {}
        for ev in self.events.values():
            body = {k: ev[k] for k in ("type", "actor", "time", "process", "inputs", "outputs")}
            if "ev:" + H(canon(body)) != ev["id"]: errs.append(f"{ev['id'][:12]}: ID does not match content")
            if not verify_sig(self.keys.get(ev["actor"], "00" * 32), ev["signature"], ev["id"].encode()):
                errs.append(f"{ev['id'][:12]}: invalid signature")
            for o in ev["outputs"]: produced[o["id"]] = produced.get(o["id"], 0) + o["qty"]
            tin, tout = sum(i["qty"] for i in ev["inputs"]), sum(o["qty"] for o in ev["outputs"])
            if ev["inputs"] and tout > tin * MAX_YIELD.get(ev["process"], 1.0) + 1e-9:
                errs.append(f"{ev['id'][:12]}: mass balance violated ({tout} kg out of {tin} kg in, process={ev['process']})")
            for i in ev["inputs"]: consumed[i["id"]] += i["qty"]
        for pid, q in consumed.items():
            if q > produced.get(pid, 0) + 1e-9: errs.append(f"lot {pid}: double spend ({q} > {produced.get(pid, 0)})")
        return errs

    def trace(self, pid, depth=0, seen=None):
        seen = seen if seen is not None else set()
        for ev in self.events.values():
            if any(o["id"] == pid for o in ev["outputs"]) and ev["id"] not in seen:
                seen.add(ev["id"])
                print("  " * depth + f"└ {ev['type']:<14} {self.names.get(ev['actor'], ev['actor']):<12} -> {pid}")
                for i in ev["inputs"]: self.trace(i["id"], depth + 1, seen)

# Merkle tree with domain separation (RFC 6962 style)
def _leaf(b): return hashlib.sha256(b"\x00" + b).digest()
def _node(l, r): return hashlib.sha256(b"\x01" + l + r).digest()
def _up(lv): return [_node(lv[i], lv[i + 1]) if i + 1 < len(lv) else lv[i] for i in range(0, len(lv), 2)]

def merkle_root(leaves):
    lv = [_leaf(x) for x in leaves]
    while len(lv) > 1: lv = _up(lv)
    return lv[0]

def merkle_proof(leaves, idx):
    lv, proof = [_leaf(x) for x in leaves], []
    while len(lv) > 1:
        sib = idx ^ 1
        if sib < len(lv): proof.append(("L" if sib < idx else "R", lv[sib]))
        lv, idx = _up(lv), idx // 2
    return proof

def merkle_verify(leaf, proof, root):
    h = _leaf(leaf)
    for side, s in proof: h = _node(s, h) if side == "L" else _node(h, s)
    return h == root

def main():
    print(f"Signatures: {'Ed25519' if REAL_SIG else 'HMAC (demo mode; install `cryptography`)'}\n")
    mine, smelter, fab, oem, store = (Actor(n) for n in ("Mine-1", "Smelter-7", "ChipFab-3", "PhoneCo", "Retail-42"))
    L = Ledger()
    for a in (mine, smelter, fab, oem, store): L.register(a)
    chain = [
        make_event(mine, "Extraction", [], [lot("lot:ore-A", 1000)]),
        make_event(smelter, "Transformation", [lot("lot:ore-A", 1000)], [lot("lot:si-1", 400)], "smelting"),
        make_event(fab, "Transformation", [lot("lot:si-1", 400)], [lot("lot:chips-1", 300)], "fab"),
        make_event(oem, "Transformation", [lot("lot:chips-1", 300)], [lot("sgtin:phone-0001", 250)], "assembly"),
        make_event(store, "Transfer", [lot("sgtin:phone-0001", 250)], [lot("sgtin:phone-0001@shelf", 250)]),
    ]
    for e in chain: L.add(e)

    print("== Trace of sgtin:phone-0001@shelf ==")
    L.trace("sgtin:phone-0001@shelf")
    print("\nViolations:", L.validate() or "none ✔")

    print("\n== Attack 1: the same ore lot consumed twice (double spend) ==")
    fraud = make_event(smelter, "Transformation", [lot("lot:ore-A", 500)], [lot("lot:si-FAKE", 200)], "smelting")
    L.add(fraud)
    for e in L.validate(): print("  ✖", e)
    del L.events[fraud["id"]]

    print("\n== Attack 2: tampering with event content ==")
    victim = chain[1]; backup = dict(victim)
    L.events[victim["id"]] = {**victim, "outputs": [lot("lot:si-1", 999)]}
    for e in L.validate(): print("  ✖", e)
    L.events[victim["id"]] = backup

    print("\n== Anchoring: Merkle root and inclusion proof ==")
    leaves = [e["id"].encode() for e in chain]
    root = merkle_root(leaves)
    print("  root (goes on-chain):", root.hex()[:32] + "…")
    proof = merkle_proof(leaves, 3)
    print(f"  proof for event #3: {len(proof)} hashes, verified =", merkle_verify(leaves[3], proof, root))
    print("  forged event      ->", merkle_verify(b"ev:forged", proof, root))

if __name__ == "__main__":
    main()
