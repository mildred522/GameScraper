import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
from PIL import Image
import traceback  # 导入 traceback 模块
import time
import sys  # 导入 sys 模块
import requests
from io import BytesIO
import re
import json
import translators as ts  # --- ★★★ 翻译库 ★★★ ---
import webbrowser       # --- ★★★ 浏览器模块 ★★★ ---
import urllib.parse     # --- ★★★ 新增：用于Bilibili URL编码 ★★★ ---

# --- 爬虫相关导入 ---
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.common.exceptions import NoSuchElementException, TimeoutException
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium_stealth import stealth
except ImportError as e:
    print(f"--- 启动失败：缺少核心库 ---")
    print(f"错误: {e}")
    print("请确保已安装: C:/Python313/python.exe -m pip install selenium webdriver-manager pillow customtkinter selenium-stealth requests translators")
    input("... 按 Enter 键退出 ...")
    sys.exit(1)


# --- 全局变量 ---
DRIVER = None
IS_SCRAPING = False
APP_BG_COLOR = ["#FFFFFF", "#1B1B1B"]
CARD_BG_COLOR = ["#F7F7F7", "#242424"]
TRANSLATION_CACHE = {}  # --- ★★★ 翻译缓存 ★★★ ---

# --- 跳转点击函数 ---
def on_redirect_click(url):
    """
    在用户的默认浏览器中打开指定的 URL。
    """
    print(f"[Redirect] Click event received for URL: {url}")
    
    if url:
        print(f"[Redirect] 正在打开: {url}")
        try:
            webbrowser.open_new_tab(url)
        except Exception as e:
            print(f"[Redirect] 打开 URL 失败: {e}")
            messagebox.showerror("打开失败", f"无法打开链接：\n{e}")
    else:
        print("[Redirect] 警告：此条目没有 URL (url is None or empty)。")
        messagebox.showwarning("无链接", "抱歉，未能找到此游戏的有效链接。")

# --- 爬虫驱动程序管理 (使用 Stealth) ---
def get_driver(headless=False):
    global DRIVER
    if DRIVER:
        try: DRIVER.quit()
        except: pass

    print("[DEBUG] 正在配置 (Stealth) Chrome WebDriver...")
    options = webdriver.ChromeOptions()

    if headless: options.add_argument("--headless")
    options.add_argument("--window-size=1600,900")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    options.add_argument("--lang=en-US")
    options.add_experimental_option('prefs', {'intl.accept_languages': 'en,en_US'})
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option('useAutomationExtension', False)

    try:
        DRIVER = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        stealth(DRIVER,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
                )

        print("[DEBUG] (Stealth) 补丁已应用，等待 3 秒...")
        time.sleep(3) 

        print("[DEBUG] (Stealth) WebDriver 启动成功。")
        return DRIVER
    except Exception as e:
        print(f"--- WebDriver 初始化失败 ---")
        traceback.print_exc()
        if root:
            root.after(0, lambda: status_label.configure(text=f"爬虫初始化失败: 无法启动 Chrome", text_color="red"))
        return None

def close_driver():
    global DRIVER
    if DRIVER:
        try:
            DRIVER.quit()
            DRIVER = None
            print("[DEBUG] WebDriver 已关闭。")
        except Exception as e:
            print(f"[DEBUG] 关闭 WebDriver 时出错: {e}")

# --- ★★★ 修正：爬虫 1: TapTap (恢复并修复URL) ★★★ ---
def scrape_taptap_data(driver):
    if not driver: return []
    data = []
    url = "https://www.taptap.cn/top/reserve"
    MY_KEYWORDS = {"二次元", "养成", "开放世界", "美少女"}
    
    try:
        print(f"[DEBUG] (TapTap) 正在打开 {url} ...")
        driver.get(url)
        wait = WebDriverWait(driver, 20)
        
        try:
            # ★★★ 恢复：使用您原来的选择器 ★★★
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.game-list-cell")))
            print("[DEBUG] (TapTap) 页面加载成功，模拟滚动 2 次...")
            for _ in range(2):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)
        except TimeoutException:
            print("--- (TapTap) 爬取失败：等待超时！(div.game-list-cell 未找到) ---")
            if root:
                root.after(0, lambda: status_label.configure(text="爬取 TapTap 超时！", text_color="red"))
            return []
        
        print("[DEBUG] (TapTap) 正在解析...")
        # ★★★ 恢复：使用您原来的选择器 ★★★
        game_cards = driver.find_elements(By.CSS_SELECTOR, "div.game-list-cell")

        for card in game_cards:
            try:
                game_name = card.find_element(By.CSS_SELECTOR, "div.app-title span.text").text
                icon_url = card.find_element(By.CSS_SELECTOR, "img.app-icon__img").get_attribute("src")
                
                # --- ★★★ 核心修正：基于您的HTML，链接在卡片内部的 <a> 标签 ★★★ ---
                game_url = None
                try:
                    # 找到包裹图标的 <a> (class="tap-router inline-flex game-cell__icon")
                    link_element = card.find_element(By.CSS_SELECTOR, "a.game-cell__icon")
                    game_url = link_element.get_attribute("href")
                    # (TapTap 的 href 是相对路径, e.g., /app/386208)
                    if game_url and game_url.startswith("/"):
                        game_url = "https://www.taptap.cn" + game_url
                except Exception as e_url:
                    print(f"[DEBUG] (TapTap) 抓取 URL 失败 (可能是广告卡片): {e_url}")
                # --- ★★★ 修正结束 ★★★ ---
                
                tag_texts = set() 
                release_info = "未知"
                try:
                    release_date_element = card.find_element(By.CSS_SELECTOR, "div.app-row-card__hint")
                    release_info = release_date_element.text
                except NoSuchElementException:
                    try:
                        tags = card.find_elements(By.CSS_SELECTOR, "div.game-cell__tags a")
                        tag_texts = {tag.text for tag in tags} 
                    except NoSuchElementException:
                        pass # 没标签也没关系

                if not MY_KEYWORDS.isdisjoint(tag_texts):
                    data.append({
                        "name": game_name,
                        "icon_url": icon_url,
                        "release": release_info,
                        "tags": list(tag_texts), 
                        "source": "TapTap",
                        "game_url": game_url 
                    })
            except Exception as e:
                print(f"[DEBUG] (TapTap) 解析一张卡片时出错: {e}")

    except Exception as e:
        print(f"--- (TapTap) 爬取时发生未知错误 ---")
        traceback.print_exc()
    return data

# --- ★★★ 修正：爬虫 2: Bilibili (构建搜索URL) ★★★ ---
def scrape_bilibili_data(driver):
    if not driver: return []
    data = []
    url = "https://game.bilibili.com/platform/ranks/expectation"
    MY_KEYWORDS = {"二次元", "养成", "开放世界", "美少女"}
    
    try:
        print(f"[DEBUG] (Bilibili) 正在打开 {url} ...")
        driver.get(url)
        wait = WebDriverWait(driver, 20)
        card_selector = (By.CSS_SELECTOR, "div[class*='list_item']")
        
        try:
            wait.until(EC.presence_of_element_located(card_selector))
            print("[DEBUG] (Bilibili) 页面加载成功，模拟滚动 3 次...")
            for _ in range(3):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2) 
        except TimeoutException:
            print("--- (Bilibili) 爬取失败：等待超时！(div[class*='list_item'] 未找到) ---")
            if root:
                root.after(0, lambda: status_label.configure(text="爬取B站超时！", text_color="red"))
            return []

        print("[DEBUG] (Bilibili) 正在解析...")
        game_cards = driver.find_elements(By.CSS_SELECTOR, "div[class*='list_item']")

        for card in game_cards:
            try:
                game_name = card.find_element(By.CSS_SELECTOR, "h1[class*='content_title']").text.strip()
                icon_url = card.find_element(By.CSS_SELECTOR, "img[class*='logo_icon']").get_attribute("src")
                
                # --- ★★★ 核心修正：无法抓取，改为构建搜索 URL (使用您提供的正确 URL) ★★★ ---
                game_url = None
                try:
                    # 使用您提供的正确搜索 URL
                    game_url = f"https://game.bilibili.com/platform/search/?keyword={urllib.parse.quote(game_name)}"
                except Exception as e_url:
                     print(f"[DEBUG] (Bili) 构建 URL 失败: {e_url}")
                # --- ★★★ 修正结束 ★★★ ---
                
                tags_elements = card.find_elements(By.CSS_SELECTOR, "div[class*='tagGroup'] > span[class*='tag']")
                tag_texts = {tag.text for tag in tags_elements if tag.text} 
                release_info = "预约中"

                if not MY_KEYWORDS.isdisjoint(tag_texts):
                    data.append({
                        "name": game_name,
                        "icon_url": icon_url,
                        "release": release_info,
                        "tags": list(tag_texts), 
                        "source": "Bilibili",
                        "game_url": game_url 
                    })
            except Exception as e:
                print(f"[DEBUG] (Bilibili) 解析一张卡片时出错: {e}")

    except Exception as e:
        print(f"--- (Bilibili) 爬取时发生未知错误 (可能是被反爬虫冻结) ---")
        traceback.print_exc()
        if root:
            root.after(0, lambda: status_label.configure(text="爬取B站失败！(详见命令行)", text_color="red"))
    return data

# --- ★★★ 修正：爬虫 3: QooApp (通过ID构建URL) ★★★ ---
def scrape_qooapp_data(driver):
    if not driver: return []
    data = []
    url = "https://m-apps.qoo-app.com/upcoming" 
    ACG_TAGS = {"rpg", "adv", "action", "card", "stg", "otome", "simulation", "mmorpg", "strategy", "music"}

    try:
        print(f"[DEBUG] (QooApp) 正在打开 {url} ...")
        driver.get(url)
        time.sleep(5) 
        print("[DEBUG] (QooApp) 页面加载完毕，正在提取源码...")
        html = driver.page_source

        json_match = re.search(r"window\.__INITIAL_DATA__\s*=\s*({.*?});", html)
        if not json_match:
            print("--- (QooApp) 爬取失败：在 HTML 源码中未找到 window.__INITIAL_DATA__！ ---")
            return []

        print("[DEBUG] (QooApp) 成功提取 JSON，正在解析...")
        json_data = json.loads(json_match.group(1))
        items = json_data.get("app-ranking-view", {}).get("fetch", {}).get("games", {}).get("items", [])

        if not items:
            print("--- (QooApp) 爬取失败：JSON 结构中未找到 'items' 列表！ ---")
            return []

        print(f"[DEBUG] (QooApp) 找到 {len(items)} 个游戏，正在过滤...")
        for game in items:
            try:
                game_name = game.get("displayName")
                icon_url = game.get("icon")
                game_tags = set(g.lower() for g in game.get("gameType", []))

                if game_tags.isdisjoint(ACG_TAGS):
                    continue
                    
                # --- ★★★ 核心修正：从 JSON 获取 ID 并构建 URL ★★★ ---
                game_url = None
                try:
                    game_id = game.get("id")
                    if game_id:
                        # 基于您HTML中的 <a href="/en-US/app/146773"...> 结构
                        game_url = f"https://m-apps.qoo-app.com/en-US/app/{game_id}"
                except Exception:
                    pass
                # --- ★★★ 修正结束 ★★★ ---

                data.append({
                    "name": game_name,
                    "icon_url": icon_url,
                    "release": "Pre-register",
                    "tags": game.get("gameType", []),
                    "source": "QooApp",
                    "game_url": game_url 
                })
            except Exception as e:
                print(f"[DEBUG] (QooApp) 解析一个 JSON 条目时出错: {e}")

        print(f"[DEBUG] (QooApp) 过滤后剩下 {len(data)} 个二次元游戏。")
    except Exception as e:
        print(f"--- (QooApp) 爬取时发生未知错误 ---")
        traceback.print_exc()
        if root:
            root.after(0, lambda: status_label.configure(text="爬取QooApp失败！(详见命令行)", text_color="red"))
    return data

# --- 爬虫 4: Google Play (最终版 - 已验证) ---
def scrape_google_play_data(driver):
    if not driver: return []
    data = []
    url = "https://play.google.com/store/search?q=anime%20role%20playing%20pre-registration&c=apps&gl=us&hl=en"
    
    try:
        print(f"[DEBUG] (Google Play) 正在打开 {url} ...")
        driver.get(url)
        wait = WebDriverWait(driver, 25) 
        
        try:
            loading_spinner_selector = (By.CSS_SELECTOR, "div[role='progressbar']")
            print("[DEBUG] (Google Play) 正在等待全屏加载动画消失(如果存在)...")
            wait.until(EC.invisibility_of_element_located(loading_spinner_selector))
            print("[DEBUG] (Google Play) 加载动画已消失(或从未出现)。")
        except TimeoutException:
            print("[DEBUG] (Google Play) 等待加载动画超时！页面可能卡住了。")
            pass

        time.sleep(1) 

        scroll_pause_time = 2.5
        scroll_count = 4 
        print(f"[DEBUG] (Google Play) 页面加载成功，开始模拟滚动 {scroll_count} 次...")
        
        for i in range(scroll_count):
            print(f"[DEBUG] (Google Play) 正在执行第 {i+1}/{scroll_count} 次滚动...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause_time)
            try:
                show_more_button = driver.find_element(By.XPATH, "//span[text()='Show more']/ancestor::button")
                if show_more_button and show_more_button.is_displayed():
                    print("[DEBUG] (Google Play) 发现了 'Show more' 按钮，点击它...")
                    show_more_button.click()
                    time.sleep(scroll_pause_time) 
            except NoSuchElementException:
                pass 
        
        print("[DEBUG] (Google Play) 滚动完成，正在解析...")
        
        xpath_selector = "//a[contains(@href, '/store/apps/details?id=')]/.."
        game_cards = driver.find_elements(By.XPATH, xpath_selector)
        
        if not game_cards:
            print("--- (Google Play) 爬取失败：未找到任何有效的应用卡片 (使用 XPath /..)！ ---")
            root.after(0, lambda: status_label.configure(text="爬取GP失败(未找到卡片)", text_color="red"))
            return []

        print(f"[DEBUG] (Google Play) 找到 {len(game_cards)} 个可能的应用卡片，正在解析...")
        
        parsed_games = set() 
        limit = 20 # 您的 20 个上限

        for card in game_cards:
            if len(data) >= limit:
                print(f"[DEBUG] (Google Play) 已达到 {limit} 条数据上限，停止解析。")
                break
                
            try:
                full_text = card.text
                if not full_text:
                    continue
                    
                game_name = full_text.split('\n')[0].strip()
                
                icon_img = card.find_element(By.TAG_NAME, "img")
                icon_url = icon_img.get_attribute("src")

                if not game_name or not icon_url or game_name in parsed_games:
                    continue
                
                if "googleusercontent.com/profile/picture" in icon_url:
                    continue
                    
                game_url = None
                try:
                    # 获取 URL
                    link_tag = card.find_element(By.TAG_NAME, "a")
                    game_url = link_tag.get_attribute("href")
                    if game_url.startswith("/"):
                        game_url = "https://play.google.com" + game_url
                except Exception:
                    pass

                parsed_games.add(game_name) 
                
                data.append({
                    "name": game_name,
                    "icon_url": icon_url,
                    "release": "Pre-registration (GP)", 
                    "tags": ["Google Play", "Anime", "RPG", "Pre-registration"], 
                    "source": "Google Play",
                    "game_url": game_url 
                })
            except Exception as e:
                pass 
                
    except TimeoutException:
        print("--- (Google Play) 爬取失败：等待超时！ ---")
        if root:
            root.after(0, lambda: status_label.configure(text="爬取 Google Play 超时！", text_color="red"))
    except Exception as e:
        print(f"--- (Google Play) 爬取时发生未知错误 ---")
        traceback.print_exc()
        if root:
            root.after(0, lambda: status_label.configure(text="爬取 Google Play 失败！(详见命令行)", text_color="red"))
            
    print(f"[DEBUG] (Google Play) 过滤后剩下 {len(data)} 个游戏。")
    return data


# --- 异步翻译 ---
def translate_async(text, name_label):
    global TRANSLATION_CACHE
    if text in TRANSLATION_CACHE:
        translated_text = TRANSLATION_CACHE[text]
        if root:
            root.after(0, lambda: update_label_with_translation(name_label, translated_text, is_from_cache=True))
        return
    try:
        print(f"[Translate] 正在翻译: {text}")
        translated_text = ts.translate_text(text, to_language='zh-CN', translator='google')
        print(f"[Translate] 成功: {text} -> {translated_text}")
        TRANSLATION_CACHE[text] = translated_text
        if root:
            root.after(0, lambda: update_label_with_translation(name_label, translated_text))
    except Exception as e:
        print(f"[Translate] 翻译失败 {text}: {e}")
        TRANSLATION_CACHE[text] = text
        if root:
             root.after(0, lambda: update_label_with_translation(name_label, text, is_failure=True))

# --- 用于更新UI和状态的辅助函数 ---
def update_label_with_translation(name_label, translated_text, is_from_cache=False, is_failure=False):
    try:
        if is_failure:
            name_label.translated_name = name_label.original_name
            name_label.is_translated = False
        else:
            name_label.configure(text=f"✨ {translated_text}")
            name_label.translated_name = translated_text
            name_label.is_translated = True
        if is_from_cache and not is_failure:
             print(f"[Translate] 使用缓存: {name_label.original_name} -> {translated_text}")
    except Exception as e:
        print(f"[UpdateLabelError] 更新标签失败: {e}")

# --- 标签点击事件处理程序 ---
def on_name_label_click(event, label):
    if not hasattr(label, "is_translated") or not hasattr(label, "original_name"):
        return
    try:
        if label.is_translated:
            label.configure(text=f"✨ {label.original_name}")
            label.is_translated = False
        else:
            if label.translated_name:
                label.configure(text=f"✨ {label.translated_name}")
                label.is_translated = True
            else:
                print("[DEBUG] 切换失败，翻译尚未完成。")
                pass
    except Exception as e:
        print(f"[ToggleError] 切换翻译时出错: {e}")


def load_image_async(url, image_label):
    try:
        if url.startswith("//"):
            url = "https:" + url
        if "o.qoo-img.com" in url and "?" in url:
            url = url.split("?")[0]
            
        if url.startswith("data:image"):
            header, encoded = url.split(",", 1)
            image_data = base64.b64decode(encoded)
        elif "=s" in url:
            url = re.sub(r"=s\d+", "=s120", url)
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            image_data = response.content
        else:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            image_data = response.content

        img = Image.open(BytesIO(image_data))
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(60, 60))

        def update_label():
            image_label.configure(image=ctk_img, text="", fg_color="transparent")
            image_label.image = ctk_img

        if root:
            root.after(0, update_label)
    except Exception as e:
        print(f"[ImageLoad] 加载图片失败 {url}: {e}")
        if root:
            root.after(0, lambda: image_label.configure(text="X", text_color="red"))


# --- UI 函数 ---
def create_main_window():
    print("[DEBUG] 2. 正在创建主窗口 (ctk.CTk)...")
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk(fg_color=APP_BG_COLOR)
    root.title("最新二游 Pro (全球版)")
    root.geometry("650x850")
    root.grid_rowconfigure(1, weight=1)
    root.grid_columnconfigure(0, weight=1)
    print("[DEBUG] 3. 主窗口创建完毕。")
    return root

# --- UI 列表 (添加跳转按钮) ---
def populate_game_list(container, game_data):
    print(f"[DEBUG] 5. 正在填充数据 (共 {len(game_data)} 条)...")
    for widget in container.winfo_children():
        widget.destroy()
    if not game_data:
        no_data_label = ctk.CTkLabel(master=container, text="暂无数据。点击“刷新”获取。",
                                     font=("PingFang SC", 14), text_color="#999999",
                                     bg_color=APP_BG_COLOR)
        no_data_label.pack(pady=50)
        return

    for game in game_data:
        card_frame = ctk.CTkFrame(master=container, fg_color=CARD_BG_COLOR, corner_radius=8)
        card_frame.pack(fill="x", pady=(0, 8), padx=10)

        card_frame.grid_columnconfigure(0, weight=0) 
        card_frame.grid_columnconfigure(1, weight=1) 

        icon_label = ctk.CTkLabel(master=card_frame,
                                  text="...",
                                  width=60,
                                  height=60,
                                  font=ctk.CTkFont(size=20),
                                  fg_color=["#E0E0E0", "#333333"],
                                  text_color=["#AAAAAA", "#555555"],
                                  corner_radius=8)
        icon_label.grid(row=0, column=0, rowspan=3, sticky="nw", padx=15, pady=15)

        info_frame = ctk.CTkFrame(master=card_frame, fg_color="transparent")
        info_frame.grid(row=0, column=1, rowspan=3, sticky="nsew", padx=(0, 15), pady=10)
        
        info_frame.grid_columnconfigure(0, weight=1) # 游戏名 (占满)
        info_frame.grid_columnconfigure(1, weight=0) # 来源 (自动)
        info_frame.grid_columnconfigure(2, weight=0) # 新按钮 (自动)
        
        info_frame.grid_rowconfigure(2, weight=1)

        icon_url = game.get("icon_url")
        if icon_url:
            threading.Thread(target=load_image_async, args=(icon_url, icon_label), daemon=True).start()

        game_name = game['name'].strip()
        
        my_tags = {"二次元", "养成", "开放世界", "美少女"}
        game_tags = set(game.get("tags", []))
        is_acg = (not my_tags.isdisjoint(game_tags)) or (game['source'] in ('QooApp', 'Google Play'))
        
        name_color = ["#9C27B0", "#E040FB"] if is_acg else ["#333333", "#E0E0E0"]
        display_name = f"✨ {game_name}" if is_acg else game_name

        name_label = ctk.CTkLabel(master=info_frame, text=display_name,
                                  font=ctk.CTkFont(family="PingFang SC", size=16, weight="bold"),
                                  text_color=name_color, anchor="w",
                                  cursor="hand2")
        name_label.grid(row=0, column=0, sticky="w", pady=(0, 2))

        # --- 为切换功能附加状态 ---
        name_label.original_name = game_name
        name_label.translated_name = None 
        name_label.is_translated = False 
        
        if game['source'] in ('QooApp', 'Google Play'):
            name_label.bind("<Button-1>", lambda event, lbl=name_label: on_name_label_click(event, lbl))
            
            if game_name in TRANSLATION_CACHE:
                translated = TRANSLATION_CACHE[game_name]
                update_label_with_translation(name_label, translated, is_from_cache=True)
            else:
                threading.Thread(target=translate_async, args=(game_name, name_label), daemon=True).start()
        
        source = game.get("source", "")
        source_color = "#00A1D6"  # Bilibili
        if source == "TapTap":
            source_color = ["#AAAAAA", "#555555"]
        elif source == "QooApp":
            source_color = "#007bff"
        elif source == "Google Play":
            source_color = ["#34A853", "#4CAF50"] # Google Green
            
        source_label = ctk.CTkLabel(master=info_frame, text=source, font=ctk.CTkFont(family="PingFang SC", size=10, weight="bold"), text_color=source_color, anchor="e")
        source_label.grid(row=0, column=1, sticky="ne", padx=(5, 0), pady=(2, 0))

        # --- ★★★ 添加跳转按钮 (并修复禁用状态的显示) ★★★ ---
        game_url = game.get("game_url") 

        link_button = ctk.CTkButton(
            master=info_frame,
            text="🔗", 
            width=20,
            height=20,
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            hover_color=["#E0E0E0", "#333333"],
            text_color=["#555555", "#AAAAAA"],
            command=lambda url=game_url: on_redirect_click(url) 
        )
        link_button.grid(row=0, column=2, sticky="ne", padx=(2, 0), pady=(0, 0))
        
        # ★★★ 核心修正：添加“禁用”状态的视觉提示 ★★★
        if not game_url:
            link_button.configure(state="disabled")
            link_button.configure(text="❌", text_color="gray")
        # --- ★★★ 修正结束 ★★★ ---
            
        release_info = game["release"].strip()
        release_color = ["#666666", "#AAAAAA"]

        if "日" in release_info or "首发" in release_info or "公测" in release_info or "测试" in release_info or "Pre-register" in release_info or "Pre-registration (GP)" in release_info:
            release_color = ["#28a745", "#50C878"] # 绿色 (即将发布)
        elif release_info != "未知":
            release_color = ["#007bff", "#58a6ff"]
        if release_info == "预约中":
            release_color = ["#28a745", "#50C878"]

        release_label = ctk.CTkLabel(master=info_frame, text=release_info, font=ctk.CTkFont(family="PingFang SC", size=12), text_color=release_color, anchor="w")
        release_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 5)) # columnspan=3

        if game.get("tags", []):
            tags_str = ", ".join(game["tags"])
            tags_label = ctk.CTkLabel(master=info_frame, text=tags_str, font=ctk.CTkFont(family="PingFang SC", size=10, slant="italic"), text_color=["#999999", "#777777"], anchor="w", wraplength=450)
            tags_label.grid(row=2, column=0, columnspan=3, sticky="sw") # columnspan=3

    print("[DEBUG] 6. 数据填充完毕。")


# --- 主线程 (激活所有爬虫) ---
def run_scraper_in_thread():
    global IS_SCRAPING
    if IS_SCRAPING:
        tk.messagebox.showinfo("提示", "爬虫正在运行中，请勿重复点击。")
        return

    populate_game_list(scrollable_frame, [])
    IS_SCRAPING = True
    status_label.configure(text="正在努力爬取数据，请稍候...", text_color="#999999")
    refresh_button.configure(state="disabled")
    progress_bar.start()
    thread = threading.Thread(target=target_function)
    thread.daemon = True
    thread.start()

# --- 目标函数 (已修复 NameError) ---
def target_function():
    """
    线程的目标函数：
    1. 启动 WebDriver
    2. 爬取 TapTap
    3. 爬取 Bilibili
    4. 爬取 QooApp
    5. 爬取 Google Play (新)
    6. 关闭 WebDriver
    7. 更新 UI
    """
    all_data = []
    driver = get_driver(headless=False) 

    if driver:
        # 1. 爬取 TapTap
        root.after(0, lambda: status_label.configure(text="(1/4) 正在爬取 TapTap..."))
        taptap_data = scrape_taptap_data(driver)
        all_data.extend(taptap_data)

        # 2. 爬取 Bilibili (保持激活)
        root.after(0, lambda: status_label.configure(text="(2/4) 正在爬取 Bilibili..."))
        bilibili_data = scrape_bilibili_data(driver)
        all_data.extend(bilibili_data)

        # 3. 爬取 QooApp
        root.after(0, lambda: status_label.configure(text="(3/4) 正在爬取 QooApp..."))
        qooapp_data = scrape_qooapp_data(driver)
        all_data.extend(qooapp_data)
        
        # 4. 爬取 Google Play (新)
        root.after(0, lambda: status_label.configure(text="(4/4) 正在爬取 Google Play... (可能较慢)"))
        google_play_data = scrape_google_play_data(driver)
        all_data.extend(google_play_data)

        # 5. 关闭驱动
        close_driver()
    
    # 6. 去重 
    print(f"[DEBUG] 爬取完毕，总共 {len(all_data)} 条数据，开始去重...")
    unique_games = {}
    for game in all_data:
        game_name_key = re.sub(r"[\s\W_]+", "", game['name']).lower()[:8]
        if game_name_key not in unique_games:
            unique_games[game_name_key] = game
        else:
            # ★★★ 修正：修复 NameError (game_key_name -> game_name_key) ★★★
            if unique_games[game_name_key]['source'] in ('Google Play', 'QooApp'):
                 unique_games[game_name_key] = game

    final_data = list(unique_games.values())
    print(f"[DEBUG] 去重后剩余 {len(final_data)} 条数据。")

    # 7. 更新 UI
    root.after(0, lambda: update_ui_with_scraped_data(final_data))
    IS_SCRAPING = False

def update_ui_with_scraped_data(scraped_data):
    """爬取完成后，更新 UI 界面。"""
    global app_data
    app_data = scraped_data

    # 排序
    def sort_key(game):
        release_str = game['release']
        if "今日" in release_str: return "0"
        if "月" in release_str and "日" in release_str: return "1" + release_str
        if "公测" in release_str: return "2" + release_str
        if "测试" in release_str: return "3" + release_str 
        if "预约" in release_str or "Pre-register" in release_str or "Pre-registration (GP)" in release_str: return "4" + release_str
        if "On Google Play" in release_str: return "5" 
        return "6" + release_str 

    try:
        sorted_data = sorted(scraped_data, key=sort_key)
    except Exception as e:
        print(f"[DEBUG] 排序失败: {e}")
        sorted_data = scraped_data

    populate_game_list(scrollable_frame, sorted_data)

    progress_bar.stop()
    refresh_button.configure(state="normal")
    status_label.configure(text="数据已更新", text_color="gray")

    if scraped_data:
        tk.messagebox.showinfo("完成", f"已成功聚合 {len(app_data)} 条游戏数据。")
    else:
        tk.messagebox.showerror("失败", "未能爬取到数据，请检查网络或爬虫逻辑。")

def on_closing():
    """窗口关闭时调用"""
    close_driver()
    root.destroy()

# --- 主程序入口 ---
if __name__ == "__main__":

    root = None
    scrollable_frame = None
    refresh_button = None
    status_label = None
    progress_bar = None

    try:
        print("[DEBUG] 1. 脚本开始执行 `if __name__ == '__main__':` ...")
        
        import base64 

        root = create_main_window()

        print("[DEBUG] 4. 正在设置UI组件...")

        header_frame = ctk.CTkFrame(master=root, corner_radius=0, fg_color=APP_BG_COLOR)
        header_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=10)

        title_label = ctk.CTkLabel(master=header_frame, text="最新二游",
                                     font=ctk.CTkFont(family="PingFang SC", size=24, weight="bold"),
                                     bg_color="transparent")
        title_label.pack(side="left")

        refresh_button = ctk.CTkButton(master=header_frame, text="刷新数据", font=ctk.CTkFont(family="PingFang SC", size=12, weight="bold"), command=run_scraper_in_thread)
        refresh_button.pack(side="right")

        status_frame = ctk.CTkFrame(master=root, corner_radius=0, fg_color=APP_BG_COLOR)
        status_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 10))
        status_frame.grid_columnconfigure(0, weight=1)

        status_label = ctk.CTkLabel(master=status_frame, text="等待刷新...",
                                     font=ctk.CTkFont(family="PingFang SC", size=10),
                                     text_color="gray",
                                     bg_color="transparent")
        status_label.grid(row=0, column=0, sticky="w")

        progress_bar = ctk.CTkProgressBar(master=status_frame, orientation="horizontal", mode="indeterminate")
        progress_bar.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        progress_bar.set(0)
        progress_bar.stop()

        scrollable_frame_container = ctk.CTkScrollableFrame(master=root, fg_color=APP_BG_COLOR)
        scrollable_frame_container.grid(row=1, column=0, sticky="nsew", padx=5)
        scrollable_frame = scrollable_frame_container

        populate_game_list(scrollable_frame, [])

        root.protocol("WM_DELETE_WINDOW", on_closing)

        print("[DEBUG] 7. UI组件设置完毕, 启动 mainloop...")
        root.mainloop()

        print("[DEBUG] 8. Mainloop 已退出 (正常关闭窗口)。")

    except Exception as e:
        print("\n\n--- SCRIPT FAILED WITH AN ERROR ---")
        traceback.print_exc()
        print("-------------------------------------\n")
        input("... 按 Enter 键退出 ...")

    finally:
        print("脚本执行完毕。")
        pass