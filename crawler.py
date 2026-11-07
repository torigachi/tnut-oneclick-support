import json
import urllib.request
import ssl
import re
import time
from datetime import datetime
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from facebook_scraper import get_posts

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def parse_date(date_str):
    try: return datetime.strptime(date_str, "%d/%m/%Y")
    except: return datetime(2000, 1, 1)

def extract_date_from_soup(soup_element):
    """Quét tìm ngày tháng năm chính xác từ cấu trúc thẻ hoặc nội dung văn bản xung quanh bài viết"""
    text = soup_element.get_text(separator=' ', strip=True)
    
    # 1. Tìm các định dạng ngày tháng rõ ràng (dd/mm/yyyy hoặc dd-mm-yyyy)
    match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', text)
    if match:
        d, m, y = match.groups()
        return f"{d.zfill(2)}/{m.zfill(2)}/{y}"
        
    # 2. Tìm trong các thẻ có class liên quan đến thời gian/ngày tháng
    for tag in soup_element.find_all(['span', 'div', 'p', 'em', 'small', 'time']):
        cls = str(tag.get('class', '')).lower()
        if any(k in cls for k in ['date', 'time', 'post-meta', 'published', 'sự kiện']):
            m_tag = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', tag.get_text())
            if m_tag:
                d, m, y = m_tag.groups()
                return f"{d.zfill(2)}/{m.zfill(2)}/{y}"
                
    return None

def auto_categorize(title, default_cat):
    t = title.lower()
    if any(kw in t for kw in ['tiếng trung', 'tiếng hàn', 'ngoại ngữ', 'lớp học', 'học phần', 'lịch thi', 'điểm', 'thời khóa biểu', 'đăng ký', 'đào tạo', 'chứng chỉ', 'thực hành', 'kế hoạch giảng dạy', 'tự học']):
        return 'Học tập'
    if any(kw in t for kw in ['học phí', 'miễn giảm', 'nộp tiền', 'bảo hiểm', 'tài chính', 'thu tiền', 'học bổng']):
        return 'Tài chính'
    if any(kw in t for kw in ['việc làm', 'thực tập', 'tuyển dụng', 'doanh nghiệp', 'hướng nghiệp', 'tuyển kỹ sư']):
        return 'Hướng nghiệp'
    if any(kw in t for kw in ['sách', 'thư viện', 'giáo trình', 'tài liệu', 'phòng đọc', 'mượn']):
        return 'Thư viện'
    return default_cat

def process_html_content(html, url, base_cat, source_name):
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    main_content = soup.find('div', class_=re.compile(r'content|main|post-list|news|body|container', re.I))
    if not main_content: main_content = soup
    
    # Duyệt qua các khối bài viết hoặc thẻ a
    for a in main_content.find_all('a', href=True):
        title = a.get_text(strip=True).replace('\n', ' ')
        href = a['href']
        
        if len(title) > 20 and not href.startswith(('javascript', '#', 'mailto')):
            full_url = urljoin(url, href)
            if any(ext in full_url.lower() for ext in ['.jpg', '.png', '.pdf', '.doc', 'login', 'search', 'page=']): continue
            
            # Lấy vùng chứa bài viết (thẻ cha cấp cao hơn một chút để quét ngày)
            container = a.find_parent(['article', 'div', 'li', 'section']) or a.find_parent()
            real_date = extract_date_from_soup(container) if container else None
            
            # Nếu vẫn không tìm thấy, quét tiếp toàn bộ trang hoặc dùng mặc định
            if not real_date:
                real_date = datetime.now().strftime("%d/%m/%Y")
                
            final_cat = auto_categorize(title, base_cat)
            
            items.append({
                "id": f"id_{hash(full_url)}",
                "title": title,
                "category": final_cat,
                "source": source_name,
                "date": real_date,
                "summary": f"[{final_cat}] Khám phá thông tin chi tiết trên trang gốc.",
                "originalUrl": full_url
            })
    return items

# CÀO WEBSITE TĨNH
def crawl_static(url, base_cat, source_name):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            html = response.read().decode('utf-8', errors='ignore')
            return process_html_content(html, url, base_cat, source_name)
    except Exception as e:
        print(f"Lỗi khi cào web tĩnh {url}: {e}")
        return []

# CÀO PORTAL BẰNG TRÌNH DUYỆT ẢO (PLAYWRIGHT)
def crawl_portal_dynamic(url, base_cat):
    print(f"--- Đang mở trình duyệt ảo quét Portal: {url} ---")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(5000)
            html = page.content()
            browser.close()
            return process_html_content(html, url, base_cat, "Portal")
    except Exception as e:
        print(f"Lỗi khi cào Portal: {e}")
        return []

# CÀO FANPAGE FACEBOOK
def crawl_facebook(page_name, limit=10):
    print(f"--- Đang quét Fanpage Facebook: {page_name} ---")
    items = []
    try:
        for post in get_posts(page_name, pages=2):
            if not post['text']: continue
            
            text_content = post['text'].replace('\n', ' ')
            title = text_content[:80] + '...' if len(text_content) > 80 else text_content
            date_str = post['time'].strftime("%d/%m/%Y") if post['time'] else datetime.now().strftime("%d/%m/%Y")
            final_cat = auto_categorize(text_content, "Thông báo chung")
            
            items.append({
                "id": f"fb_{post['post_id']}",
                "title": title,
                "category": final_cat,
                "source": "Facebook",
                "date": date_str,
                "summary": text_content[:150] + '... [Xem thêm trên Facebook]',
                "originalUrl": post['post_url']
            })
            if len(items) >= limit: break
    except Exception as e:
        print(f"Lỗi quét Facebook: {e}")
    return items

def main():
    print("BẮT ĐẦU QUY TRÌNH THU THẬP DỮ LIỆU ĐA NGUỒN...")
    start = time.time()
    all_news = []
    
    static_sources = [
        ("https://tnut.edu.vn/tin-tuc-su-kien", "Thông báo chung", "Website"),
        ("https://tnut.edu.vn/thong-bao-dao-tao", "Học tập", "Website"),
        ("https://tnut.edu.vn/thong-bao-sv", "Công tác SV", "Website"),
        ("https://thuvien.tnut.edu.vn/tin-tuc", "Thư viện", "Website"),
        ("http://htdn.tnut.edu.vn/", "Hướng nghiệp", "Website")
    ]
    for url, cat, source in static_sources:
        all_news.extend(crawl_static(url, cat, source))
        
    all_news.extend(crawl_portal_dynamic("http://portal.tnut.edu.vn/#/home", "Học tập"))
    all_news.extend(crawl_facebook("tnut.edu.vn", limit=10))

    unique_news = []
    seen_urls = set()
    for item in all_news:
        if item['originalUrl'] not in seen_urls:
            seen_urls.add(item['originalUrl'])
            unique_news.append(item)

    unique_news.sort(key=lambda x: parse_date(x['date']), reverse=True)

    with open('news.json', 'w', encoding='utf-8') as f:
        json.dump(unique_news, f, ensure_ascii=False, indent=4)
        
    print(f"\n[HOÀN TẤT] Tổng số: {len(unique_news)} tin tức. Chạy mất {round(time.time()-start, 2)}s")

if __name__ == '__main__':
    main()
