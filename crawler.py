import json
import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def crawl_website_tnut():
    """Bóc tách quy mô lớn từ nhiều danh mục Website TNUT"""
    news_items = []
    # Quét 3 danh mục lớn của trường để lấy nhiều thông tin nhất có thể
    sources = [
        ("https://tnut.edu.vn/tin-tuc-su-kien", "Thông báo chung"),
        ("https://tnut.edu.vn/thong-bao-dao-tao", "Học tập"),
        ("https://tnut.edu.vn/thong-bao-sv", "Công tác SV")
    ]
    
    for url, category in sources:
        try:
            res = requests.get(url, headers=HEADERS, timeout=10, verify=False)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                for a in soup.find_all('a', href=True):
                    title = a.get_text(strip=True)
                    href = a['href']
                    
                    if len(title) > 25 and ('/tin-tuc' in href or '.html' in href or 'id=' in href):
                        full_url = href if href.startswith('http') else f"https://tnut.edu.vn{href}"
                        
                        # Chống trùng lặp bài viết
                        if not any(item['originalUrl'] == full_url for item in news_items):
                            news_items.append({
                                "id": f"web_{len(news_items)+1}",
                                "title": title,
                                "category": category,
                                "source": "Website",
                                "date": "Mới nhất",
                                "summary": f"Thông báo từ Website TNUT: {title}",
                                "originalUrl": full_url
                            })
                            # Tăng giới hạn lên lấy 15 bài mỗi mục (Tổng có thể lên tới 45 bài)
                            if len(news_items) >= 45:
                                break
        except Exception as e:
            print(f"Lỗi cào {url}: {e}")
            
    return news_items

def crawl_portal_tnut():
    """Cố gắng cào Portal, nếu bị Tường lửa (Firewall) chặn thì dùng dữ liệu ghim"""
    portal_items = []
    url = "http://portal.tnut.edu.vn/Notices.aspx"
    try:
        res = requests.get(url, headers=HEADERS, timeout=8, verify=False)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                title = a.get_text(strip=True)
                href = a['href']
                if len(title) > 15 and 'NoticeDetail.aspx?id=' in href:
                    full_url = f"http://portal.tnut.edu.vn/{href.lstrip('/')}"
                    if not any(item['originalUrl'] == full_url for item in portal_items):
                        portal_items.append({
                            "id": f"portal_{len(portal_items)+1}",
                            "title": title,
                            "category": "Học tập",
                            "source": "Portal",
                            "date": "Mới nhất",
                            "summary": f"Thông báo học vụ từ Portal TNUT: {title}",
                            "originalUrl": full_url
                        })
                    if len(portal_items) >= 10: # Tăng lấy 10 tin Portal
                        break
    except Exception as e:
        print(f"Máy chủ GitHub bị chặn khi vào Portal TNUT: {e}")
    
    # NẾU GITHUB BỊ CHẶN, SỬ DỤNG DANH SÁCH GHIM TĨNH
    if not portal_items:
        portal_items = [
            {
                "id": "portal_def_1",
                "title": "[Ghim] Hướng dẫn đăng ký học phần bổ sung và nộp học phí",
                "category": "Tài chính",
                "source": "Portal",
                "date": "Thông báo ghim",
                "summary": "Truy cập Portal để xem quy trình mở cổng đăng ký học phần bổ sung và nộp học phí...",
                "originalUrl": "http://portal.tnut.edu.vn/NoticeDetail.aspx?id=1025"
            },
            {
                "id": "portal_def_2",
                "title": "[Ghim] Quy định về chuẩn đầu ra Tiếng Anh và Tin học",
                "category": "Học tập",
                "source": "Portal",
                "date": "Thông báo ghim",
                "summary": "Sinh viên tra cứu yêu cầu chuẩn đầu ra và thời hạn nộp chứng chỉ xét tốt nghiệp...",
                "originalUrl": "http://portal.tnut.edu.vn/NoticeDetail.aspx?id=1020"
            }
        ]
    return portal_items

def get_facebook_news():
    """Vì Facebook chống cào tự động, bạn có thể tự thay đổi Link bài viết mới vào đây"""
    return [
        {
            "id": "fb_tnut_1",
            "title": "[Ghim] Hoạt động của Đoàn Thanh niên - Hội Sinh viên TNUT",
            "category": "Phong trào",
            "source": "Facebook",
            "date": "Tin nổi bật",
            "summary": "Theo dõi các cuộc thi, hoạt động ngoại khóa và phong trào tình nguyện mới nhất của Đoàn trường...",
            "originalUrl": "https://www.facebook.com/Truongdhktcn"
        },
        {
            "id": "fb_tnut_2",
            "title": "[Ghim] Cơ hội việc làm, Thực tập cho Sinh viên năm cuối",
            "category": "Hướng nghiệp",
            "source": "Facebook",
            "date": "Tin nổi bật",
            "summary": "Cập nhật các tin tức tuyển dụng từ doanh nghiệp liên kết với nhà trường thông qua Fanpage...",
            "originalUrl": "https://www.facebook.com/Truongdhktcn"
        }
    ]

def main():
    print("Bắt đầu lấy dữ liệu quy mô lớn...")
    web_news = crawl_website_tnut()
    portal_news = crawl_portal_tnut()
    fb_news = get_facebook_news()

    all_news = web_news + portal_news + fb_news

    with open('news.json', 'w', encoding='utf-8') as f:
        json.dump(all_news, f, ensure_ascii=False, indent=4)
        
    print(f"Hoàn tất! Tổng cộng {len(all_news)} tin (Web: {len(web_news)}, Portal: {len(portal_news)}, FB: {len(fb_news)})")

if __name__ == '__main__':
    main()
