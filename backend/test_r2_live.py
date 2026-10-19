"""Test real Cloudflare R2 connectivity: upload, download, presigned URL, and delete.

Never logs or prints secret keys, tokens, or credentials.
"""
import os
import sys
import uuid
from pathlib import Path
from dotenv import load_dotenv

# Ensure backend root is on sys.path and load environment
ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))

import r2_storage
import requests


def run_live_test():
    print("=" * 60)
    print("  CLOUDFLARE R2 LIVE INTEGRATION TEST")
    print("=" * 60)

    is_configured = r2_storage.configured()
    bucket = r2_storage.bucket()
    endpoint = r2_storage.endpoint()
    region = r2_storage.REGION

    print(f"1. Configuration Check:")
    print(f"   Configured: {is_configured}")
    print(f"   Bucket:     {bucket}")
    print(f"   Endpoint:   {endpoint}")
    print(f"   Region:     {region}")

    if not is_configured:
        print("FAIL: R2 is not fully configured.")
        return False

    probe_id = uuid.uuid4().hex[:12]
    object_name = f"tests/live_probe_{probe_id}.txt"
    test_payload = f"BharatChitra AI live R2 storage test probe: {probe_id}\n".encode("utf-8")
    content_type = "text/plain"

    print(f"\n2. Uploading Test Object: {object_name} ({len(test_payload)} bytes)...")
    try:
        upload_res = r2_storage.upload(object_name, test_payload, content_type)
        print(f"   Upload successful: path={upload_res.get('path')}")
    except Exception as e:
        print(f"   FAIL: Upload failed: {e}")
        return False

    print(f"\n3. Verifying Object Existence (HEAD request)...")
    try:
        object_exists = r2_storage.exists(object_name)
        print(f"   Object exists in R2: {object_exists}")
        if not object_exists:
            print("   FAIL: head_object reported object does not exist.")
            return False
    except Exception as e:
        print(f"   FAIL: head_object call failed: {e}")
        return False

    print(f"\n4. Downloading Object from R2...")
    try:
        data, ct = r2_storage.download(object_name)
        print(f"   Downloaded {len(data)} bytes, ContentType={ct}")
        if data != test_payload:
            print("   FAIL: Downloaded content does not match uploaded payload.")
            return False
        print("   Integrity Check: MATCH (100% byte identical)")
    except Exception as e:
        print(f"   FAIL: Download failed: {e}")
        return False

    print(f"\n5. Generating Time-Limited Presigned URL...")
    try:
        signed_url = r2_storage.presigned_url(object_name, expires_in=300, filename="test_probe.txt")
        has_sig = "X-Amz-Signature=" in signed_url
        print(f"   Presigned URL generated: {has_sig} (valid AWS S3v4 signature)")
        if not has_sig:
            print("   FAIL: Presigned URL missing signature.")
            return False

        # Test direct HTTP GET fetch through Cloudflare R2
        r = requests.get(signed_url, timeout=15)
        print(f"   Direct HTTP GET status: {r.status_code} (length: {len(r.content)})")
        if r.status_code != 200 or r.content != test_payload:
            print(f"   FAIL: Direct HTTP GET failed with status {r.status_code}")
            return False
        print("   Direct Presigned Download: SUCCESS (HTTP 200 OK)")
    except Exception as e:
        print(f"   FAIL: Presigned URL download failed: {e}")
        return False

    print(f"\n6. Deleting Test Object from R2...")
    try:
        r2_storage.delete(object_name)
        exists_after = r2_storage.exists(object_name)
        print(f"   Object exists after delete: {exists_after}")
        if exists_after:
            print("   FAIL: Object still exists after delete.")
            return False
        print("   Cleanup: SUCCESS (Object deleted)")
    except Exception as e:
        print(f"   FAIL: Delete failed: {e}")
        return False

    print("\n" + "=" * 60)
    print("  ALL R2 TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = run_live_test()
    sys.exit(0 if success else 1)
