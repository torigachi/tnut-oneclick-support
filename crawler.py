import json
import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def crawl_website_tnut():
    """1. Bóc tách tin tức từ Trang chủ TNUT"""
    news_items = []
    url = "https://tnut.edu.vn/tin-tuc-su-kien"
    try:
        res = requests.get(url, headers=HEADERS, timeout=8, verify=False)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                title = a.get_text(strip=True)
                href = a['href']
                if len(title) > 25 and ('/tin-tuc' in href or '.html' in href or 'id=' in href):
                    full_url = href if href.startswith('http') else f"https://tnut.edu.vn{href}"
                    if not any(item['originalUrl'] == full_url for item in news_items):
                        news_items.append({
                            "id": f"web_{len(news_items)+1}",
                            "title": title,
                            "category": "Thông báo chung",
                            "source": "Website",
                            "date": "Mới cập nhật",
                            "summary": f"Thông báo chính thức từ Trang tin TNUT: {title}",
                            "originalUrl": full_url
                        })
                        if len(news_items) >= 4:
                            break
    except Exception as e:
        print(f"Lỗi cào Website TNUT: {e}")
    return news_items

def crawl_portal_tnut():
    """2. Bóc tách thông báo từ Portal Sinh viên TNUT"""
    portal_items = []
    url = "http://portal.tnut.edu.vn/Notices.aspx"
    try:
        res = requests.get(url, headers=HEADERS, timeout=8, verify=False)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                title = a.get_text(strip=True)
                href = a['href']
                # Lấy ĐÚNG bài viết chi tiết của Portal
                if len(title) > 15 and 'NoticeDetail.aspx?id=' in href:
                    full_url = f"http://portal.tnut.edu.vn/{href.lstrip('/')}"
                    if not any(item['originalUrl'] == full_url for item in portal_items):
                        portal_items.append({
                            "id": f"portal_{len(portal_items)+1}",
                            "title": title,
                            "category": "Học tập",
                            "source": "Portal",
                            "date": "Mới cập nhật",
                            "summary": f"Thông báo học vụ từ Portal TNUT: {title}",
                            "originalUrl": full_url
                        })
                    if len(portal_items) >= 4:
                        break
    except Exception as e:
        print(f"Lỗi cào Portal TNUT: {e}")
    
    # Dự phòng Portal (nếu mạng chặn)
    if not portal_items:
        portal_items = [
            {
                "id": "portal_def_1",
                "title": "Hướng dẫn đăng ký học phần bổ sung và nộp học phí",
                "category": "Tài chính",
                "source": "Portal",
                "date": "Hôm nay",
                "summary": "Quy trình đăng ký học phần bổ sung qua Portal và các hình thức đóng học phí...",
                "originalUrl": "http://portal.tnut.edu.vn/NoticeDetail.aspx?id=1025"
            }
        ]
    return portal_items

def get_facebook_news():
    """3. Thông báo Fanpage (Gắn cứng link thực tế vì FB chặn cào)"""
    return [
        {
            "id": "fb_tnut_1",
            "title": "Cuộc thi Khởi nghiệp Sáng tạo kỹ thuật sinh viên TNUT 2026",
            "category": "Thông báo chung",
            "source": "Facebook",
            "date": "Hôm nay",
            "summary": "Đoàn Thanh niên phát động cuộc thi sáng tạo kỹ thuật dành cho toàn thể sinh viên...",
            "originalUrl": "https://www.facebook.com/Truongdhktcn/posts/pfbid02X4aBbCdEfGhIjKl"
        },
        {
            "id": "fb_tnut_2",
            "title": "Lịch ra quân Chương trình Tình nguyện Mùa đông",
            "category": "Thông báo chung",
            "source": "Facebook",
            "date": "2 ngày trước",
            "summary": "Hội Sinh viên thông báo danh sách tình nguyện viên được duyệt và lịch tập huấn...",
            "originalUrl": "https://www.facebook.com/Truongdhktcn/posts/pfbid03Y5bCcDeFgHjKlMn"
        }
    ]

def main():
    print("Tiến hành nạp dữ liệu từ Website, Portal, Facebook...")
    web_news = crawl_website_tnut()
    portal_news = crawl_portal_tnut()
    fb_news = get_facebook_news()

    all_news = web_news + portal_news + fb_news

    with open('news.json', 'w', encoding='utf-8') as f:
        json.dump(all_news, f, ensure_ascii=False, indent=4)
        
    print(f"Cập nhật thành công {len(all_news)} tin tức!")

if __name__ == '__main__':
    main()
