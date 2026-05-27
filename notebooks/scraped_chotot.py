"""
Scraper cho Chợ Tốt API — BĐS bán (st=s)
Output: data/chotot_scraped.jsonl (JSONL format)
"""

import json, time, argparse, os
from datetime import datetime
import urllib.request
# Cài đặt cấu hình ban đầu
BASE_URL = "https://gateway.chotot.com/v1/public/ad-listing" #địa chỉ API cần gọi của Chợ Tốt - nơi gửi yêu cầu để nhận data về tin đăng
HEADERS = {  #thông tin đi kèm mỗi lần request
    "User-Agent": ( #giả lập trình duyệt chrome trên macos
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json", #yêu cầu trả về định dạng json
    "Accept-Language": "vi-VN,vi;q=0.9", #ngôn ngữ ưu tiên 
    "Referer": "https://www.chotot.com/", #giả lập đang browse từ trang chủ chotot.com - tạo độ tin cậy, giống người dùng thật đang lướt web
}

LIMIT      = 50 # mỗi lần lấy 50 tin
SLEEP      = 0.8 # nghỉ 0.8 giây giữa mỗi lần gọi
RETRY      = 3 # nếu lõi thì thử lại tối đa 3 lần
SAVE_EVERY = 200 # lưu file sau mỗi 200 tin

# Danh sách mục tiêu cần scrape
# 4 loại bất động sản
CATEGORIES = [
    (1020, "nha_o"),
    (1010, "can_ho"),
    (1030, "dat"),
    (1040, "van_phong"),
]

# 7 thành phố 
REGIONS = {
    "hcm":        13000,
    "hanoi":      12000,
    "danang":      3017,
    "binh_duong":  2011,
    "dong_nai":    2013,
    "ba_ria":      2010,
    "long_an":     5032,
}

# hàm fetch() - hàm gọi API 
def fetch(url, retries=RETRY):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        except Exception as e:
            wait = 2 ** attempt # Exponential Backoff - Lần 1 chờ 2s, lần 2 chờ 4s, lần 3 chờ 8s, chờ càng lâu hơn sau mỗi lần thất bại, tránh span server
            print(f"    Lỗi (thử {attempt+1}/{retries}): {e} — chờ {wait}s")
            time.sleep(wait)
    return None

# lọc và làm sạch data - loại bỏ tin rác, giá bất thường trước khi lưu
def parse_ad(ad):
    price = ad.get("price")
    area  = ad.get("area")

    if not price or not area:
        return None
    if price < 100_000_000 or price > 500_000_000_000:
        return None
    if area <= 0:
        return None

# Sau khi lọc điều kiện thì lấy các trường quan trọng
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

# Hàm scrape_category() - vòng lặp chính, idea:
# Với mỗi trang (page 1, 2, 3..):
# Tạo URL với offset (page 1 = offset 0, page 2 = offset 50,...)
# Gọi fetch() để lấy 50 tin:
# Với mỗi tin:
# - nếu đã thấy rồi (seen_ids) -> bỏ qua (tránh trùng)
# - chưa thấy -> parser -> ghi vào file.jsonl
# Nghỉ 0.8 giây
# Nếu trang trả về < 50 tin -> hết data -> dừng
def scrape_category(cg, cg_name, region_code, region_name,
                    max_pages, seen_ids, output_path):
    count = 0

    with open(output_path, "a", encoding="utf-8") as f: #ghi thằng vào file sau mỗi tin - nếu tắt máy đột ngột, data đã lưu không bị mất
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

# hàm main() - điều phối tổng thể
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-pages", type=int, default=200)
    parser.add_argument("--output", default="data/chotot_scraped.jsonl")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    # Load seen_ids từ checkpoint
    seen_ids = set()
    if os.path.exists(args.output): # nếu file đã tồn tại -> đọc list_id đã có -> bỏ qua khi scrape
        with open(args.output, encoding="utf-8") as f:
            for line in f:
                try:
                    seen_ids.add(json.loads(line)["list_id"])
                except Exception:
                    pass
        print(f"Resume: bỏ qua {len(seen_ids)} list_ids đã có") # nếu chạy bị dừng giữa chừng (mất mạng, tắt máy), chạy lại sẽ tiếp tục từ chỗ dừng thay vì làm lại từ đầu

    total_count = len(seen_ids) # đếm số tin đăng đã có sẵn từ lần chạy trước (nếu resume), nếu chạy lần đầu thì total_count = 0

    for region_name, region_code in REGIONS.items(): # vòng lặp lồng nhau (2 tầng) # tầng 1: thành phố
        for cg, cg_name in CATEGORIES:  # tầng 2: loại BĐS
            print(f"\n── {cg_name} / {region_name} ──") #In ra màng hình đang scrape cái gì, ví dụ: -- nha o/hcm --
            n = scrape_category(cg, cg_name, region_code, region_name, # gọi hàm scrape cho 1 tổ hợp, trả về số tin lấy được lưu vào n
                                args.max_pages, seen_ids, args.output) 
            total_count += n # cộng dồn tổng số tin
            print(f"  → Tổng tích lũy: {total_count} records")
            time.sleep(1.5) # nghỉ 1.5 giây giữ mỗi tổ hợp - tránh bị block

    print(f"\n✓ Hoàn thành: {total_count} records → {args.output}")


if __name__ == "__main__": #chạy trực tiếp --> python scraped_chotot.py, tranh trường hợp file bị chayk ngoài ý muốn khi import vào notebook hay file khác
    main()
