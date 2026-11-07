import json
import urllib.request
import ssl
import re
from datetime import datetime
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def get_html(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            return response.read().decode('utf-8', errors='ignore')
    except:
        return ""

def get_real_date(url):
    html = get_html(url)
    if not html: return None
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text(separator=' ', strip=True)
    
    # 1. Tìm cụm từ chỉ định ngày
    match_explicit = re.search(r'(?:ngày đăng|đăng ngày|cập nhật|thời gian)[\s:]*(\d{1,2}[/-]\d{1,2}[/-]\d{4})', text, re.IGNORECASE)
    if match_explicit:
        return match_explicit.group(1).replace('-', '/')
        
    # 2. Tìm trong thẻ thời gian
    for tag in soup.find_all(['span', 'div', 'p', 'em', 'i']):
        class_name = tag.get('class', [])
        if any(c.lower() in ['date', 'time', 'post-meta', 'published'] for c in class_name):
            m = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{4}', tag.get_text())
            if m: return m.group().replace('-', '/')

    # 3. Lấy ngày đầu tiên xuất hiện (nới lỏng điều kiện, lấy cả 2024)
    matches = re.findall(r'\d{1,2}[/-]\d{1,2}[/-](?:2024|2025|2026|2027)', text)
    if matches:
        return matches[0].replace('-', '/')
        
    return None

def parse_date(date_str):
    try: return datetime.strptime(date_str, "%d/%m/%Y")
    except: return datetime(2000, 1, 1)

def auto_categorize(title, default_cat):
    t = title.lower()
    if any(kw in t for kw in ['tiếng trung', 'tiếng hàn', 'ngoại ngữ', 'lớp học', 'học phần', 'lịch thi', 'điểm', 'thời khóa biểu', 'đăng ký', 'đào tạo', 'chứng chỉ', 'thực hành', 'kế hoạch giảng dạy']):
        return 'Học tập'
    if any(kw in t for kw in ['học phí', 'miễn giảm', 'nộp tiền', 'bảo hiểm', 'tài chính', 'thu tiền', 'học bổng']):
        return 'Tài chính'
    if any(kw in t for kw in ['việc làm', 'thực tập', 'tuyển dụng', 'doanh nghiệp', 'hướng nghiệp', 'tuyển kỹ sư']):
        return 'Hướng nghiệp'
    if any(kw in t for kw in ['sách', 'thư viện', 'giáo trình', 'tài liệu', 'phòng đọc', 'mượn', 'đọc']):
        return 'Thư viện'
    return default_cat

def crawl_general(url, base_cat, source_name="Website"):
    html = get_html(url)
    if not html: return []
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    
    main_content = soup.find('div', class_=re.compile(r'content|main|post-list|news|body', re.I))
    if not main_content: main_content = soup
    
    for a in main_content.find_all('a', href=True):
        title = a.get_text(strip=True).replace('\n', ' ')
        href = a['href']
        
        if len(title) > 15 and len(title.split()) >= 4 and not href.startswith(('javascript', '#', 'mailto')):
            full_url = urljoin(url, href)
            if any(ext in full_url.lower() for ext in ['.jpg', '.png', '.pdf', '.doc', 'login', 'search', 'page=']): continue

            if not any(item['originalUrl'] == full_url for item in items):
                print(f" -> Kiểm chứng tin: {title[:40]}...")
                real_date = get_real_date(full_url)
                
                # Sửa bộ lọc: Lấy tin có ngày (kể cả 2024)
                if real_date:
                    final_cat = auto_categorize(title, base_cat)
                    items.append({
                        "id": f"id_{len(items)}_{hash(full_url)}",
                        "title": title,
                        "category": final_cat,
                        "source": source_name,
                        "date": real_date,
                        "summary": f"[{final_cat}] Xem chi tiết tại liên kết đính kèm.",
                        "originalUrl": full_url
                    })
    return items

def main():
    print("Bắt đầu cào dữ liệu...")
    start = time.time()
    all_news = []
    
    sources = [
        ("https://tnut.edu.vn/tin-tuc-su-kien", "Thông báo chung", "Website"),
        ("https://tnut.edu.vn/thong-bao-dao-tao", "Học tập", "Website"),
        ("https://tnut.edu.vn/thong-bao-sv", "Công tác SV", "Website"),
        ("https://tnut.edu.vn/khao-thi-dbcl", "Học tập", "Website"),
        ("https://thuvien.tnut.edu.vn/tin-tuc", "Thư viện", "Website"),
        ("http://htdn.tnut.edu.vn/", "Hướng nghiệp", "Website"),
        ("http://portal.tnut.edu.vn/Notices.aspx", "Học tập", "Portal")
    ]
    
    for url, cat, source in sources:
        print(f"\n--- Quét nguồn: {url} ---")
        crawled = crawl_general(url, cat, source)
        all_news.extend(crawled)
        print(f"Hoàn thành nhánh này. Lọc được {len(crawled)} tin.")

    unique_news = []
    seen_urls = set()
    for item in all_news:
        if item['originalUrl'] not in seen_urls:
            seen_urls.add(item['originalUrl'])
            unique_news.append(item)

    unique_news.sort(key=lambda x: parse_date(x['date']), reverse=True)

    with open('news.json', 'w', encoding='utf-8') as f:
        json.dump(unique_news, f, ensure_ascii=False, indent=4)
        
    print(f"\n[THÀNH CÔNG] Đã lưu tổng cộng {len(unique_news)} tin tức. Chạy mất {round(time.time()-start, 2)}s")

if __name__ == '__main__':
    main()
