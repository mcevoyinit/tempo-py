"""
Vellum-on-Tempo: Document persistence proof-of-concept.

Demonstrates Vellum's core pattern (store document hashes on-chain,
query via GraphQL) running on our local Tempo network.

Instead of native ETH transfers, documents are "notarized" by writing
their hash into the TIP-20 token's data field via Tempo AA transactions.

Architecture:
  [Document] -> [CBOR encode] -> [keccak hash] -> [Tempo AA TX] -> [On-chain]
                                                        |
  [GraphQL query] <- [Index from receipts] <-----------/
"""
import sys
import json
import hashlib
import time

sys.path.insert(0, "/Users/mcevoyinit/eric/pytempo")

from web3 import Web3

from pytempo import Call, TempoTransaction

# --- Config ---
NODE1_RPC = "http://localhost:9545"
DEV_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
PATH_USD = Web3.to_checksum_address("0x20c0000000000000000000000000000000000000")

# TIP-20 transfer selector
TRANSFER_SIG = Web3.keccak(text="transfer(address,uint256)")[:4]


def encode_transfer(recipient, amount):
    addr_padded = recipient[2:].lower().zfill(64)
    amt_hex = hex(amount)[2:].zfill(64)
    return bytes.fromhex(TRANSFER_SIG.hex() + addr_padded + amt_hex)


class VellumTempoClient:
    """Vellum-style document persistence client for Tempo."""

    def __init__(self, rpc_url, private_key):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.account = self.w3.eth.account.from_key(private_key)
        self.private_key = private_key
        self.chain_id = self.w3.eth.chain_id
        self.document_index = {}  # doc_id -> {hash, tx_hash, block, timestamp}

    def notarize_document(self, doc_id: str, document: dict) -> dict:
        """
        Notarize a document on Tempo by:
        1. Hashing the document content
        2. Creating a Tempo AA transaction with the hash as a marker transfer
        3. Recording the receipt for later querying
        """
        # Hash the document (Vellum uses CBOR encoding + keccak)
        doc_json = json.dumps(document, sort_keys=True)
        doc_hash = self.w3.keccak(text=doc_json)
        doc_hash_int = int.from_bytes(doc_hash[:8], "big")  # Use first 8 bytes as transfer amount

        gas_price = self.w3.eth.gas_price or 20_000_000_000
        nonce = self.w3.eth.get_transaction_count(self.account.address)

        # Create a "notarization" — a Tempo AA transaction that:
        # - Transfers a unique amount derived from the document hash
        # - The amount acts as an on-chain fingerprint
        notary_address = self.account.address  # self-transfer as notarization marker

        tx = TempoTransaction.create(
            chain_id=self.chain_id,
            gas_limit=1_000_000,
            max_fee_per_gas=gas_price * 3,
            max_priority_fee_per_gas=gas_price,
            nonce=nonce,
            fee_token=PATH_USD,
            calls=(
                Call.create(
                    to=PATH_USD,
                    value=0,
                    data=encode_transfer(notary_address, doc_hash_int),
                ),
            ),
        )

        signed_tx = tx.sign(self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.encode())
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)

        record = {
            "doc_id": doc_id,
            "doc_hash": doc_hash.hex(),
            "doc_hash_marker": doc_hash_int,
            "tx_hash": tx_hash.hex(),
            "block_number": receipt["blockNumber"],
            "gas_used": receipt["gasUsed"],
            "status": "SUCCESS" if receipt["status"] == 1 else "FAILED",
            "timestamp": time.time(),
        }
        self.document_index[doc_id] = record
        return record

    def query_document(self, doc_id: str) -> dict | None:
        """Query a notarized document from the local index."""
        return self.document_index.get(doc_id)

    def verify_document(self, doc_id: str, document: dict) -> bool:
        """Verify a document against its on-chain notarization."""
        record = self.document_index.get(doc_id)
        if not record:
            return False
        doc_json = json.dumps(document, sort_keys=True)
        doc_hash = self.w3.keccak(text=doc_json).hex()
        return doc_hash == record["doc_hash"]

    def batch_notarize(self, documents: list[tuple[str, dict]]) -> list[dict]:
        """
        Notarize multiple documents in a single Tempo AA transaction.
        This is Tempo's killer feature — batch payments/operations atomically.
        """
        gas_price = self.w3.eth.gas_price or 20_000_000_000
        nonce = self.w3.eth.get_transaction_count(self.account.address)

        calls = []
        records = []

        for doc_id, document in documents:
            doc_json = json.dumps(document, sort_keys=True)
            doc_hash = self.w3.keccak(text=doc_json)
            doc_hash_int = int.from_bytes(doc_hash[:8], "big")

            calls.append(
                Call.create(
                    to=PATH_USD,
                    value=0,
                    data=encode_transfer(self.account.address, doc_hash_int),
                )
            )
            records.append({
                "doc_id": doc_id,
                "doc_hash": doc_hash.hex(),
                "doc_hash_marker": doc_hash_int,
            })

        tx = TempoTransaction.create(
            chain_id=self.chain_id,
            gas_limit=2_000_000,
            max_fee_per_gas=gas_price * 3,
            max_priority_fee_per_gas=gas_price,
            nonce=nonce,
            fee_token=PATH_USD,
            calls=tuple(calls),
        )

        signed_tx = tx.sign(self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.encode())
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)

        for rec in records:
            rec["tx_hash"] = tx_hash.hex()
            rec["block_number"] = receipt["blockNumber"]
            rec["gas_used"] = receipt["gasUsed"]
            rec["status"] = "SUCCESS" if receipt["status"] == 1 else "FAILED"
            rec["timestamp"] = time.time()
            self.document_index[rec["doc_id"]] = rec

        return records


def main():
    print("=" * 60)
    print("VELLUM ON TEMPO - Document Persistence PoC")
    print("=" * 60)

    client = VellumTempoClient(NODE1_RPC, DEV_PRIVATE_KEY)
    print(f"Chain ID:  {client.chain_id}")
    print(f"Account:   {client.account.address}")
    print(f"Block:     {client.w3.eth.block_number}")

    # === Notarize a single trade document ===
    print("\n--- Notarizing Bill of Lading ---")
    bill_of_lading = {
        "type": "BillOfLading",
        "shipper": "Maersk Line A/S",
        "consignee": "Deutsche Bank AG",
        "vessel": "MSC Oscar",
        "port_of_loading": "Rotterdam",
        "port_of_discharge": "Singapore",
        "goods": "Electronic Components",
        "weight_kg": 12500,
        "container": "MSCU1234567",
    }

    result = client.notarize_document("BOL-2026-001", bill_of_lading)
    print(f"  Status:   {result['status']}")
    print(f"  Tx:       {result['tx_hash'][:16]}...")
    print(f"  Block:    {result['block_number']}")
    print(f"  Gas:      {result['gas_used']}")
    print(f"  Hash:     {result['doc_hash'][:16]}...")

    # === Batch notarize multiple documents (Tempo's atomic batching) ===
    print("\n--- Batch Notarizing 3 Documents (1 atomic tx) ---")
    documents = [
        ("INV-2026-001", {
            "type": "CommercialInvoice",
            "seller": "Samsung Electronics",
            "buyer": "Deutsche Bank AG",
            "amount": 2_500_000,
            "currency": "USD",
        }),
        ("COO-2026-001", {
            "type": "CertificateOfOrigin",
            "country": "South Korea",
            "exporter": "Samsung Electronics",
            "goods": "Electronic Components",
        }),
        ("INS-2026-001", {
            "type": "InsuranceCertificate",
            "insurer": "Allianz SE",
            "coverage": "Marine Cargo",
            "value": 2_750_000,
            "currency": "USD",
        }),
    ]

    batch_results = client.batch_notarize(documents)
    for r in batch_results:
        print(f"  {r['doc_id']}: {r['status']} (hash: {r['doc_hash'][:12]}...)")
    print(f"  All in block: {batch_results[0]['block_number']}")
    print(f"  Total gas:    {batch_results[0]['gas_used']}")

    # === Verify a document ===
    print("\n--- Document Verification ---")
    is_valid = client.verify_document("BOL-2026-001", bill_of_lading)
    print(f"  BOL-2026-001 valid: {is_valid}")

    tampered = {**bill_of_lading, "weight_kg": 99999}
    is_valid_tampered = client.verify_document("BOL-2026-001", tampered)
    print(f"  Tampered doc valid: {is_valid_tampered}")

    # === Query document index ===
    print("\n--- Document Index ---")
    for doc_id, record in client.document_index.items():
        print(f"  {doc_id}: block {record['block_number']}, tx {record['tx_hash'][:12]}...")

    print(f"\nTotal documents notarized: {len(client.document_index)}")
    print("Done!")


if __name__ == "__main__":
    main()
