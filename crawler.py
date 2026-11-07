import json
import urllib.request
import ssl
import re
from datetime import datetime
from urllib.parse import urljoin

# Bỏ qua xác thực SSL để kết nối mượt mà với server trường
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def get_html(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Lỗi truy cập {url}: {e}")
        return ""

def extract_date(text):
    match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{4}', str(text))
    if match: return match.group().replace('-', '/')
    return datetime.now().strftime("%d/%m/%Y") # Mặc định ngày hôm nay nếu bài không ghi ngày

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%d/%m/%Y")
    except:
        return datetime(2020, 1, 1)

def auto_categorize(title, default_cat):
    """Bộ lọc thông minh thế hệ mới, phân loại chuẩn xác hơn"""
    t = title.lower()
    # Ưu tiên 1: Học tập
    if any(kw in t for kw in ['tiếng trung', 'tiếng hàn', 'ngoại ngữ', 'lớp học', 'học phần', 'lịch thi', 'điểm', 'thời khóa biểu', 'đăng ký', 'đào tạo', 'chứng chỉ']):
        return 'Học tập'
    # Ưu tiên 2: Tài chính
    if any(kw in t for kw in ['học phí', 'miễn giảm', 'nộp tiền', 'bảo hiểm', 'tài chính', 'thu tiền', 'học bổng']):
        return 'Tài chính'
    # Ưu tiên 3: Hướng nghiệp
    if any(kw in t for kw in ['việc làm', 'thực tập', 'tuyển dụng', 'doanh nghiệp', 'hướng nghiệp', 'tuyển kỹ sư']):
        return 'Hướng nghiệp'
    # Ưu tiên 4: Thư viện
    if any(kw in t for kw in ['sách', 'thư viện', 'giáo trình', 'tài liệu', 'phòng đọc', 'mượn']):
        return 'Thư viện'
    return default_cat

def crawl_general(url, base_cat, source_name="Website"):
    html = get_html(url)
    items = []
    # Quét mạnh tay mọi thẻ a
    links = re.findall(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.IGNORECASE | re.DOTALL)
    
    for href, title_html in links:
        title = re.sub(r'<[^>]+>', '', title_html).strip() 
        title = " ".join(title.split())
        
        # Bỏ qua các link quá ngắn hoặc rác
        if len(title) > 15 and len(title.split()) >= 3 and not href.startswith(('javascript', '#', 'mailto')):
            full_url = urljoin(url, href)
            if any(ext in full_url.lower() for ext in ['.jpg', '.png', '.pdf', '.doc']): continue
            if 'login' in full_url.lower() or 'search' in full_url.lower(): continue

            if not any(item['originalUrl'] == full_url for item in items):
                final_cat = auto_categorize(title, base_cat)
                
                items.append({
                    "id": f"id_{len(items)}_{hash(full_url)}",
                    "title": title,
                    "category": final_cat,
                    "source": source_name,
                    "date": extract_date(html), 
                    "summary": f"[{final_cat}] Xem chi tiết tại liên kết đính kèm.",
                    "originalUrl": full_url
                })
    return items

def main():
    print("Bắt đầu cào dữ liệu cải tiến (Unlimited & Auto Categorize)...")
    all_news = []
    
    sources = [
        ("https://tnut.edu.vn/tin-tuc-su-kien", "Thông báo chung", "Website"),
        ("https://tnut.edu.vn/thong-bao-dao-tao", "Học tập", "Website"),
        ("https://tnut.edu.vn/thong-bao-sv", "Công tác SV", "Website"),
        ("https://tnut.edu.vn/dao-tao", "Học tập", "Website"),
        ("https://thuvien.tnut.edu.vn/tin-tuc", "Thư viện", "Website"),
        ("http://htdn.tnut.edu.vn/", "Hướng nghiệp", "Website"),
        ("http://portal.tnut.edu.vn/Notices.aspx", "Học tập", "Portal")
    ]
    
    for url, cat, source in sources:
        crawled = crawl_general(url, cat, source)
        all_news.extend(crawled)
        print(f"Quét {url} -> Được {len(crawled)} tin.")

    # Lọc trùng lặp
    unique_news = []
    seen_urls = set()
    for item in all_news:
        if item['originalUrl'] not in seen_urls:
            seen_urls.add(item['originalUrl'])
            unique_news.append(item)

    # SẮP XẾP TIN MỚI LÊN ĐẦU
    unique_news.sort(key=lambda x: parse_date(x['date']), reverse=True)

    with open('news.json', 'w', encoding='utf-8') as f:
        json.dump(unique_news, f, ensure_ascii=False, indent=4)
    print(f"Hoàn tất! Đã lưu tổng cộng {len(unique_news)} tin tức.")

if __name__ == '__main__':
    main()
