"""
Scraper cho Chợ Tốt API — BĐS bán (st=s)
Output: data/chotot_scraped.jsonl (JSONL format)
"""

import json, time, argparse, os
from datetime import datetime
import urllib.request

BASE_URL = "https://gateway.chotot.com/v1/public/ad-listing"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "vi-VN,vi;q=0.9",
    "Referer": "https://www.chotot.com/",
}

LIMIT      = 50
SLEEP      = 0.8
RETRY      = 3
SAVE_EVERY = 200

CATEGORIES = [
    (1020, "nha_o"),
    (1010, "can_ho"),
    (1030, "dat"),
    (1040, "van_phong"),
]

REGIONS = {
    "hcm":        13000,
    "hanoi":      12000,
    "danang":      3017,
    "binh_duong":  2011,
    "dong_nai":    2013,
    "ba_ria":      2010,
    "long_an":     5032,
}


def fetch(url, retries=RETRY):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        except Exception as e:
            wait = 2 ** attempt
            print(f"    Lỗi (thử {attempt+1}/{retries}): {e} — chờ {wait}s")
            time.sleep(wait)
    return None


def parse_ad(ad):
    price = ad.get("price")
    area  = ad.get("area")

    if not price or not area:
        return None
    if price < 100_000_000 or price > 500_000_000_000:
        return None
    if area <= 0:
        return None

    return {
        "list_id":       ad.get("list_id"),
        "title":         ad.get("subject", ""),
        "description":   ad.get("body", ""),
        "price_vnd":     price,
        "price_string":  ad.get("price_string", ""),
        "area_m2":       area,
        "latitude":      ad.get("latitude"),
        "longitude":     ad.get("longitude"),
        "ward":          ad.get("ward_name", ""),
        "district":      ad.get("area_name", ""),
        "city":          ad.get("region_name", ""),
        "category_code": ad.get("category"),
        "category_name": ad.get("category_name", ""),
        "rooms":         ad.get("rooms"),
        "toilets":       ad.get("toilets"),
        "scraped_at":    datetime.now().isoformat(),
    }


def scrape_category(cg, cg_name, region_code, region_name,
                    max_pages, seen_ids, output_path):
    count = 0

    with open(output_path, "a", encoding="utf-8") as f:
        for page in range(1, max_pages + 1):
            offset = (page - 1) * LIMIT
            url = (f"{BASE_URL}?cg={cg}&region_v2={region_code}"
                   f"&o={offset}&limit={LIMIT}&st=s")

            resp = fetch(url)
            if resp is None:
                print(f"  [{cg_name}/{region_name}] page {page} — lỗi, dừng")
                break

            ads = resp.get("ads", [])
            if not ads:
                print(f"  [{cg_name}/{region_name}] page {page} — hết data")
                break

            total = resp.get("total", "?")
            new_count = 0
            for ad in ads:
                lid = ad.get("list_id")
                if lid in seen_ids:
                    continue
                record = parse_ad(ad)
                if record:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    seen_ids.add(lid)
                    new_count += 1
                    count += 1

            print(f"  [{cg_name}/{region_name}] page {page:3d} "
                  f"+{new_count} (API total: {total})")

            if len(ads) < LIMIT:
                break

            time.sleep(SLEEP)

    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-pages", type=int, default=200)
    parser.add_argument("--output", default="data/chotot_scraped.jsonl")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    # Load seen_ids từ checkpoint
    seen_ids = set()
    if os.path.exists(args.output):
        with open(args.output, encoding="utf-8") as f:
            for line in f:
                try:
                    seen_ids.add(json.loads(line)["list_id"])
                except Exception:
                    pass
        print(f"Resume: bỏ qua {len(seen_ids)} list_ids đã có")

    total_count = len(seen_ids)

    for region_name, region_code in REGIONS.items():
        for cg, cg_name in CATEGORIES:
            print(f"\n── {cg_name} / {region_name} ──")
            n = scrape_category(cg, cg_name, region_code, region_name,
                                args.max_pages, seen_ids, args.output)
            total_count += n
            print(f"  → Tổng tích lũy: {total_count} records")
            time.sleep(1.5)

    print(f"\n✓ Hoàn thành: {total_count} records → {args.output}")


if __name__ == "__main__":
    main()
