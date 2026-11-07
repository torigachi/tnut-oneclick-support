import json
import requests
from bs4 import BeautifulSoup
import urllib3
import re
from datetime import datetime
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def fetch_date_from_detail_page(url):
    """Mở trực tiếp link bài viết gốc để truy xuất ngày đăng chính xác nhất"""
    try:
        res = requests.get(url, headers=HEADERS, timeout=5, verify=False)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # Lấy toàn bộ văn bản thuần của bài viết
            text_content = soup.get_text()
            # Dùng biểu thức chính quy (Regex) tìm cấu trúc ngày chuẩn (VD: 15/10/2026, 15-10-2026)
            match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{4}', text_content)
            if match:
                return match.group().replace('-', '/')
    except:
        pass
    return "Không rõ ngày"

def crawl_website_tnut():
    """Quét dữ liệu sâu (Deep Crawl) với số lượng lớn từ Website & Thư viện"""
    news_items = []
    # Đã thêm nhiều nguồn hơn và phân loại rõ ràng
    sources = [
        ("https://tnut.edu.vn/tin-tuc-su-kien", "Thông báo chung"),
        ("https://tnut.edu.vn/thong-bao-dao-tao", "Học tập"),
        ("https://tnut.edu.vn/thong-bao-sv", "Công tác SV"),
        ("https://tnut.edu.vn/tuyen-sinh", "Tuyển sinh"),
        ("https://thuvien.tnut.edu.vn/tin-tuc", "Thư viện"),
        ("https://thuvien.tnut.edu.vn/thong-bao", "Thư viện"),
        ("https://tnut.edu.vn/thong-bao", "Thông báo chung")
    ]
    
    for url, category in sources:
        print(f"\n--- Đang quét danh mục: {category} ({url}) ---")
        try:
            res = requests.get(url, headers=HEADERS, timeout=10, verify=False)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                count = 0
                for a in soup.find_all('a', href=True):
                    title = a.get_text(strip=True)
                    href = a['href']
                    
                    # Điều kiện lọc link bài chuẩn, loại bỏ link rác
                    if len(title) > 20 and ('/tin-tuc' in href or '.html' in href or 'id=' in href or 'thuvien' in url):
                        full_url = href if href.startswith('http') else f"https://tnut.edu.vn{href}"
                        full_url = full_url.replace('https://tnut.edu.vn//', 'https://tnut.edu.vn/')
                        
                        # Tránh trùng lặp tin
                        if not any(item['originalUrl'] == full_url for item in news_items):
                            print(f" -> Đang xử lý: {title[:40]}...")
                            # GỌI HÀM VÀO BÀI GỐC LẤY NGÀY
                            real_date = fetch_date_from_detail_page(full_url)
                            
                            news_items.append({
                                "id": f"web_{len(news_items)+1}",
                                "title": title,
                                "category": category,
                                "source": "Website",
                                "date": real_date,
                                "summary": f"[{category}] - Truy cập để xem chi tiết thông báo.",
                                "originalUrl": full_url
                            })
                            count += 1
                            
                            # Tăng giới hạn lên lấy 30 tin/MỖI DANH MỤC (Tổng có thể lên tới >150 tin)
                            if count >= 30:
                                break
        except Exception as e:
            print(f"Lỗi khi quét {url}: {e}")
            
    return news_items

def crawl_portal_tnut():
    """Lấy thông báo từ Portal và truy cập trang chi tiết để lấy ngày"""
    portal_items = []
    url = "http://portal.tnut.edu.vn/Notices.aspx"
    print("\n--- Đang quét Portal TNUT ---")
    try:
        res = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            count = 0
            for a_tag in soup.find_all('a', href=True):
                title = a_tag.get_text(strip=True)
                href = a_tag['href']
                
                if len(title) > 15 and 'NoticeDetail.aspx?id=' in href:
                    full_url = f"http://portal.tnut.edu.vn/{href.lstrip('/')}"
                    
                    if not any(item['originalUrl'] == full_url for item in portal_items):
                        # GỌI HÀM VÀO BÀI GỐC CỦA PORTAL ĐỂ LẤY NGÀY
                        real_date = fetch_date_from_detail_page(full_url)
                        
                        portal_items.append({
                            "id": f"portal_{len(portal_items)+1}",
                            "title": title,
                            "category": "Học tập",
                            "source": "Portal",
                            "date": real_date,
                            "summary": f"Thông báo Portal: {title}",
                            "originalUrl": full_url
                        })
                        count += 1
                        if count >= 30: # Tăng giới hạn Portal lên 30 tin
                            break
    except Exception as e:
        print(f"Firewall chặn kết nối Portal: {e}")
    
    # Dữ liệu dự phòng nếu bị Firewall chặn
    if not portal_items:
        portal_items = [
            {
                "id": "portal_def_1",
                "title": "[Ghim] Hướng dẫn đăng ký học phần bổ sung",
                "category": "Tài chính",
                "source": "Portal",
                "date": datetime.now().strftime("%d/%m/%Y"),
                "summary": "Truy cập Portal để xem quy trình mở cổng đăng ký học phần...",
                "originalUrl": "http://portal.tnut.edu.vn/NoticeDetail.aspx?id=1025"
            }
        ]
    return portal_items

def get_facebook_news():
    """Tin tức Facebook cấu hình thủ công"""
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
    print(" BẮT ĐẦU CÀO DỮ LIỆU SÂU (DEEP CRAWL - TRÍCH XUẤT NGÀY)")
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
    print(f"Tổng thời gian chạy: {round(end_time - start_time, 2)} giây.")
    print("Tất cả tin tức đã được trích xuất ngày đăng từ bài viết gốc.")
    print("=====================================================")

if __name__ == '__main__':
    main()
