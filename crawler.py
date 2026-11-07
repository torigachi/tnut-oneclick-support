import json
import urllib.request
import ssl
import re
from datetime import datetime
from urllib.parse import urljoin

# Bỏ qua xác thực SSL để tránh lỗi với server của trường
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def get_html(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Lỗi truy cập {url}: {e}")
        return ""

def extract_date(text):
    """Trích xuất ngày đăng (dd/mm/yyyy)"""
    match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{4}', str(text))
    if match:
        return match.group().replace('-', '/')
    return "01/01/2026" # Ngày mặc định nếu không tìm thấy để đảm bảo sắp xếp không bị lỗi

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%d/%m/%Y")
    except:
        return datetime(2020, 1, 1) # Nếu lỗi parse thì đẩy xuống cuối

def auto_categorize(title, default_cat):
    title_lower = title.lower()
    if any(kw in title_lower for kw in ['học phí', 'miễn giảm', 'nộp tiền', 'bảo hiểm', 'tài chính', 'thu tiền']):
        return 'Tài chính'
    if any(kw in title_lower for kw in ['học phần', 'lịch thi', 'điểm thi', 'thời khóa biểu', 'đăng ký', 'điểm']):
        return 'Học tập'
    if any(kw in title_lower for kw in ['việc làm', 'thực tập', 'tuyển dụng', 'doanh nghiệp', 'học bổng', 'hướng nghiệp']):
        return 'Hướng nghiệp'
    if any(kw in title_lower for kw in ['sách', 'thư viện', 'giáo trình', 'tài liệu']):
        return 'Thư viện'
    return default_cat

def crawl_general(url, base_cat, source_name="Website"):
    html = get_html(url)
    items = []
    # Biểu thức chính quy cào thẻ <a> cơ bản
    links = re.findall(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.IGNORECASE | re.DOTALL)
    
    for href, title_html in links:
        title = re.sub(r'<[^>]+>', '', title_html).strip() # Xóa tag HTML thừa
        title = " ".join(title.split())
        
        if len(title) > 15 and len(title.split()) >= 4 and not href.startswith(('javascript', '#', 'mailto')):
            full_url = urljoin(url, href)
            # Lọc bớt các link rác
            if any(ext in full_url.lower() for ext in ['.jpg', '.png', '.pdf', '.doc']):
                 continue
            if 'login' in full_url.lower() or 'search' in full_url.lower():
                 continue

            if not any(item['originalUrl'] == full_url for item in items):
                final_cat = auto_categorize(title, base_cat)
                
                # Quét 1 đoạn text xung quanh để tìm ngày (tối ưu tốc độ thay vì vào link gốc)
                date_str = extract_date(html) 
                
                items.append({
                    "id": f"id_{len(items)}_{hash(full_url)}",
                    "title": title,
                    "category": final_cat,
                    "source": source_name,
                    "date": date_str,
                    "summary": f"[{final_cat}] Xem chi tiết tại bài viết gốc.",
                    "originalUrl": full_url
                })
    return items

def main():
    print("Bắt đầu cào dữ liệu...")
    all_news = []
    
    # Danh sách nguồn cực lớn
    sources = [
        ("https://tnut.edu.vn/tin-tuc-su-kien", "Thông báo chung", "Website"),
        ("https://tnut.edu.vn/thong-bao-dao-tao", "Học tập", "Website"),
        ("https://tnut.edu.vn/thong-bao-sv", "Công tác SV", "Website"),
        ("https://thuvien.tnut.edu.vn/tin-tuc", "Thư viện", "Website"),
        ("http://htdn.tnut.edu.vn/", "Hướng nghiệp", "Website"),
        ("http://portal.tnut.edu.vn/Notices.aspx", "Học tập", "Portal")
    ]
    
    for url, cat, source in sources:
        print(f"Quét: {url}")
        crawled = crawl_general(url, cat, source)
        all_news.extend(crawled)
    
    # Bổ sung tin Facebook
    all_news.append({
        "id": "fb_1", "title": "Hoạt động Đoàn Hội TNUT", "category": "Thông báo chung",
        "source": "Facebook", "date": datetime.now().strftime("%d/%m/%Y"),
        "summary": "Cập nhật các phong trào, sự kiện sinh viên từ Fanpage chính thức.",
        "originalUrl": "https://www.facebook.com/Truongdhktcn"
    })

    # LỌC TRÙNG LẶP
    unique_news = []
    seen_urls = set()
    for item in all_news:
        if item['originalUrl'] not in seen_urls:
            seen_urls.add(item['originalUrl'])
            unique_news.append(item)

    # SẮP XẾP TIN MỚI LÊN ĐẦU (SORT BY DATE DESC)
    unique_news.sort(key=lambda x: parse_date(x['date']), reverse=True)

    with open('news.json', 'w', encoding='utf-8') as f:
        json.dump(unique_news, f, ensure_ascii=False, indent=4)
    print(f"Hoàn tất! Đã lưu {len(unique_news)} tin tức.")

if __name__ == '__main__':
    main()
