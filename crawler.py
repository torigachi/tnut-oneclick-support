import json
import requests
from bs4 import BeautifulSoup
import urllib3
import re
from datetime import datetime
import time
from urllib.parse import urljoin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def fetch_date_from_detail_page(url):
    """Mở trực tiếp link bài viết gốc để truy xuất ngày đăng"""
    try:
        res = requests.get(url, headers=HEADERS, timeout=5, verify=False)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            text_content = soup.get_text()
            match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{4}', text_content)
            if match:
                return match.group().replace('-', '/')
    except:
        pass
    return "Không rõ ngày"

def auto_categorize(title, default_category):
    """Tự động phân loại tin tức dựa trên từ khóa trong Tiêu đề"""
    title_lower = title.lower()
    if any(kw in title_lower for kw in ['học phí', 'miễn giảm', 'thu tiền', 'bảo hiểm', 'tài chính', 'nộp tiền']):
        return 'Tài chính'
    if any(kw in title_lower for kw in ['việc làm', 'thực tập', 'tuyển dụng', 'hướng nghiệp', 'doanh nghiệp', 'học bổng']):
        return 'Hướng nghiệp'
    if any(kw in title_lower for kw in ['học phần', 'lịch thi', 'điểm thi', 'thời khóa biểu', 'đăng ký môn']):
        return 'Học tập'
    return default_category

def crawl_website_tnut():
    """Quét dữ liệu không giới hạn từ tất cả các đầu báo của trường"""
    news_items = []
    # Khai báo tất cả các nguồn của trường
    sources = [
        ("https://tnut.edu.vn/tin-tuc-su-kien", "Thông báo chung"),
        ("https://tnut.edu.vn/thong-bao-dao-tao", "Học tập"),
        ("https://tnut.edu.vn/thong-bao-sv", "Thông báo chung"),
        ("https://thuvien.tnut.edu.vn/", "Thư viện"),
        ("http://htdn.tnut.edu.vn/", "Hướng nghiệp") # Thêm nguồn Hướng nghiệp / Việc làm
    ]
    
    for url, base_category in sources:
        print(f"\n--- Đang quét không giới hạn: {url} ---")
        try:
            res = requests.get(url, headers=HEADERS, timeout=10, verify=False)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                for a in soup.find_all('a', href=True):
                    title = a.get_text(strip=True).replace('\n', ' ').strip()
                    href = a['href']
                    
                    # Nới lỏng bộ lọc: Chỉ cần là một câu có ý nghĩa (độ dài > 15 ký tự và nhiều hơn 3 từ)
                    if len(title) > 15 and len(title.split()) >= 4:
                        # Bỏ qua các link thao tác hoặc link ảo
                        if 'javascript' in href or href.startswith('#') or 'login' in href:
                            continue
                            
                        # Dùng urljoin tự động ghép đúng tên miền gốc (sửa lỗi link Thư viện bị sai)
                        full_url = urljoin(url, href)
                        
                        # Kiểm tra trùng lặp
                        if not any(item['originalUrl'] == full_url for item in news_items):
                            final_cat = auto_categorize(title, base_category)
                            print(f" -> [Lấy tin]: {title[:50]}...")
                            real_date = fetch_date_from_detail_page(full_url)
                            
                            news_items.append({
                                "id": f"web_{len(news_items)+1}",
                                "title": title,
                                "category": final_cat,
                                "source": "Website",
                                "date": real_date,
                                "summary": f"[{final_cat}] - Truy cập liên kết để xem chi tiết nội dung.",
                                "originalUrl": full_url
                            })
                            # KHÔNG CÒN GIỚI HẠN SỐ LƯỢNG NỮA
        except Exception as e:
            print(f"Lỗi khi quét {url}: {e}")
            
    return news_items

def crawl_portal_tnut():
    """Lấy thông báo từ Portal (Học tập & Tài chính)"""
    portal_items = []
    url = "http://portal.tnut.edu.vn/Notices.aspx"
    print("\n--- Đang quét Portal TNUT ---")
    try:
        res = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for a_tag in soup.find_all('a', href=True):
                title = a_tag.get_text(strip=True).replace('\n', ' ').strip()
                href = a_tag['href']
                
                if len(title) > 15 and 'NoticeDetail.aspx?id=' in href:
                    full_url = urljoin(url, href)
                    
                    if not any(item['originalUrl'] == full_url for item in portal_items):
                        final_cat = auto_categorize(title, "Học tập")
                        real_date = fetch_date_from_detail_page(full_url)
                        
                        portal_items.append({
                            "id": f"portal_{len(portal_items)+1}",
                            "title": title,
                            "category": final_cat,
                            "source": "Portal",
                            "date": real_date,
                            "summary": f"Thông báo Portal: {title}",
                            "originalUrl": full_url
                        })
    except Exception as e:
        print(f"Firewall chặn kết nối Portal: {e}")
    
    return portal_items

def get_facebook_news():
    return [
        {
            "id": "fb_tnut_1",
            "title": "Hoạt động của Đoàn Thanh niên - Hội Sinh viên TNUT",
            "category": "Thông báo chung",
            "source": "Facebook",
            "date": datetime.now().strftime("%d/%m/%Y"),
            "summary": "Theo dõi các cuộc thi, hoạt động ngoại khóa mới nhất...",
            "originalUrl": "https://www.facebook.com/Truongdhktcn"
        }
    ]

def main():
    print("=====================================================")
    print(" BẮT ĐẦU CÀO DỮ LIỆU (ĐÃ TẮT GIỚI HẠN & MỞ RỘNG)")
    print("=====================================================")
    
    start_time = time.time()
    
    web_news = crawl_website_tnut()
    portal_news = crawl_portal_tnut()
    fb_news = get_facebook_news()

    all_news = web_news + portal_news + fb_news

    with open('news.json', 'w', encoding='utf-8') as f:
        json.dump(all_news, f, ensure_ascii=False, indent=4)
        
    end_time = time.time()
    
    print("=====================================================")
    print(f"HOÀN TẤT! Đã cào tổng cộng: {len(all_news)} tin tức.")
    print(f"Thời gian chạy: {round(end_time - start_time, 2)} giây.")
    print("=====================================================")

if __name__ == '__main__':
    main()
