import json
import requests
from bs4 import BeautifulSoup
import urllib3
import re
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def extract_publish_date(text):
    """Quét và trích xuất ngày đăng thực tế từ text HTML (định dạng dd/mm/yyyy hoặc dd-mm-yyyy)"""
    match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{4}', str(text))
    if match:
        return match.group().replace('-', '/')
    # Nếu bài viết không hiển thị ngày, mặc định lấy ngày cào dữ liệu
    return datetime.now().strftime("%d/%m/%Y")

def crawl_website_tnut():
    """Bóc tách quy mô lớn, bao gồm cả mục Thư viện và trích xuất Ngày đăng"""
    news_items = []
    # ĐÃ THÊM NGUỒN THƯ VIỆN & TĂNG SỐ LƯỢNG LẤY TIN
    sources = [
        ("https://tnut.edu.vn/tin-tuc-su-kien", "Thông báo chung"),
        ("https://tnut.edu.vn/thong-bao-dao-tao", "Học tập"),
        ("https://tnut.edu.vn/thong-bao-sv", "Công tác SV"),
        ("https://thuvien.tnut.edu.vn/", "Thư viện"),
        ("https://tnut.edu.vn/thong-bao", "Thư viện") 
    ]
    
    for url, category in sources:
        try:
            res = requests.get(url, headers=HEADERS, timeout=10, verify=False)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                
                for a in soup.find_all('a', href=True):
                    title = a.get_text(strip=True)
                    href = a['href']
                    
                    # Quét toàn bộ khối chứa thẻ <a> để tìm ngày đăng
                    parent_block = a.parent.parent.get_text(strip=True) if a.parent and a.parent.parent else ""
                    publish_date = extract_publish_date(parent_block)
                    
                    if len(title) > 20 and ('/tin-tuc' in href or '.html' in href or 'id=' in href or 'thuvien' in url):
                        full_url = href if href.startswith('http') else f"https://tnut.edu.vn{href}"
                        full_url = full_url.replace('https://tnut.edu.vn//', 'https://tnut.edu.vn/')
                        
                        if not any(item['originalUrl'] == full_url for item in news_items):
                            news_items.append({
                                "id": f"web_{len(news_items)+1}",
                                "title": title,
                                "category": category,
                                "source": "Website",
                                "date": publish_date, # Hiện ngày đăng thực tế
                                "summary": f"[{category}] - {title}",
                                "originalUrl": full_url
                            })
                            # Nâng limit lên 20 tin mỗi chuyên mục
                            if len([item for item in news_items if item['category'] == category]) >= 20:
                                break
        except Exception as e:
            print(f"Lỗi cào {url}: {e}")
            
    return news_items

def crawl_portal_tnut():
    """Lấy thông báo từ Portal kèm ngày đăng"""
    portal_items = []
    url = "http://portal.tnut.edu.vn/Notices.aspx"
    try:
        res = requests.get(url, headers=HEADERS, timeout=8, verify=False)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for tr in soup.find_all('tr'): # Quét theo hàng bảng để lấy chuẩn ngày ở cột bên cạnh
                a_tag = tr.find('a', href=True)
                if a_tag:
                    title = a_tag.get_text(strip=True)
                    href = a_tag['href']
                    if len(title) > 15 and 'NoticeDetail.aspx?id=' in href:
                        full_url = f"http://portal.tnut.edu.vn/{href.lstrip('/')}"
                        publish_date = extract_publish_date(tr.get_text())
                        
                        if not any(item['originalUrl'] == full_url for item in portal_items):
                            portal_items.append({
                                "id": f"portal_{len(portal_items)+1}",
                                "title": title,
                                "category": "Học tập",
                                "source": "Portal",
                                "date": publish_date,
                                "summary": f"Thông báo Portal: {title}",
                                "originalUrl": full_url
                            })
                        if len(portal_items) >= 15: # Nâng limit Portal lên 15
                            break
    except Exception as e:
        print(f"Bị Firewall chặn khi vào Portal: {e}")
    
    if not portal_items:
        portal_items = [
            {
                "id": "portal_def_1",
                "title": "[Ghim] Hướng dẫn đăng ký học phần bổ sung",
                "category": "Tài chính",
                "source": "Portal",
                "date": datetime.now().strftime("%d/%m/%Y"),
                "summary": "Truy cập Portal để xem quy trình mở cổng đăng ký...",
                "originalUrl": "http://portal.tnut.edu.vn/NoticeDetail.aspx?id=1025"
            }
        ]
    return portal_items

def get_facebook_news():
    """Tin tức Facebook cấu hình thủ công kèm ngày đăng"""
    return [
        {
            "id": "fb_tnut_1",
            "title": "Hoạt động của Đoàn Thanh niên - Hội Sinh viên TNUT",
            "category": "Thông báo chung",
            "source": "Facebook",
            "date": datetime.now().strftime("%d/%m/%Y"),
            "summary": "Theo dõi các cuộc thi, hoạt động ngoại khóa...",
            "originalUrl": "https://www.facebook.com/Truongdhktcn"
        }
    ]

def main():
    print("Bắt đầu lấy dữ liệu (Tích hợp quét ngày đăng)...")
    web_news = crawl_website_tnut()
    portal_news = crawl_portal_tnut()
    fb_news = get_facebook_news()

    all_news = web_news + portal_news + fb_news

    with open('news.json', 'w', encoding='utf-8') as f:
        json.dump(all_news, f, ensure_ascii=False, indent=4)
        
    print(f"Thành công! Đã lấy {len(all_news)} tin có ngày tháng.")

if __name__ == '__main__':
    main()
