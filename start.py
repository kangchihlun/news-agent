import openai
import requests
import json
import schedule
import platform
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Get API Keys from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

if not OPENAI_API_KEY or not NEWS_API_KEY:
    raise ValueError("Please set OPENAI_API_KEY and NEWS_API_KEY in your .env file")

# 計算昨天的日期
def get_yesterday():
    return (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

# 爬取昨天的熱門新聞
def fetch_hot_news(language="en", page_size=20):
    yesterday = get_yesterday()
    url = f"https://newsapi.org/v2/everything?q=trending&from={yesterday}&to={yesterday}&language={language}&pageSize={page_size}&sortBy=popularity&apiKey={NEWS_API_KEY}"
    
    response = requests.get(url)
    data = response.json()

    if data.get("status") != "ok":
        return {"error": "Failed to fetch news", "details": data}
    
    return {"articles": data.get("articles", [])}

# 使用 GPT 生成新聞摘要與推理
def summarize_news(title, content):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
    這是一條新聞標題：「{title}」
    內容摘要：「{content}」
    
    請生成一個 **簡短摘要**（1-2 句），並給出 **簡短推理**（1 句），推測這則新聞可能對世界或某個領域的影響。
    """
    
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": "你是一位專業新聞分析師，擅長提供簡潔有力的新聞摘要與推理。"},
                  {"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content.strip()

# 找出昨天最熱門的前5則新聞，並用 AI 生成摘要
def get_top_5_articles():
    news_data = fetch_hot_news()
    articles = news_data.get("articles", [])

    if not articles:
        return "No articles found for yesterday."

    # 依據新聞的熱門程度（popularity, relevancy）排序
    sorted_articles = sorted(articles, key=lambda x: x.get("popularity", 0), reverse=True)
    
    top_5 = sorted_articles[:5]
    result = []

    for i, article in enumerate(top_5, 1):
        title = article['title']
        content = article.get('description', '') or article.get('content', '新聞內容過短，無法摘要')
        url = article['url']

        # 使用 GPT 生成新聞簡報
        ai_summary = summarize_news(title, content)

        result.append(f"""
        🔥 **第 {i} 則新聞：{title}**  
        📌 **來源**: {article['source']['name']}  
        🌍 **新聞連結**: [點擊查看]({url})  
        📝 **AI 簡報**: {ai_summary}  
        """)

    return "\n".join(result)

# 設置定時任務，每天上午9點執行
def schedule_news_fetch():
    print("Fetching yesterday's top trending news...")
    top_news = get_top_5_articles()
    
    print("🔥 昨天最熱門的 5 則新聞 🔥")
    print(top_news)


os_name = platform.system()
if os_name == "Darwin":
    schedule.every().minute.do(schedule_news_fetch)
else:# 設定每天早上 9 點執行
    schedule.every().day.at("09:00").do(schedule_news_fetch)

# 持續運行
if __name__ == "__main__":
    print("News scheduler is running...")

    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分鐘檢查一次
