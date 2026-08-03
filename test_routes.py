from app import app

client = app.test_client()
routes = ['/', '/compliance', '/risks', '/policies', '/audits', '/vendors',
          '/assets', '/access-reviews', '/training', '/trust-center', '/settings']

all_ok = True
for r in routes:
    resp = client.get(r)
    status = "OK" if resp.status_code == 200 else "FAIL"
    if resp.status_code != 200:
        all_ok = False
    print(f"  {status} [{resp.status_code}] {r}")

print("\nAll routes passed!" if all_ok else "\nSome routes failed!")
