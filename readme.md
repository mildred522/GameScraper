# 最新二游 Pro (全球版) 🚀

一个聚合型的桌面 GUI 应用，用于抓取 Taptap、Bilibili、QooApp 和 Google Play 商店的即将上线/预约的二次元（Gacha）游戏。

![[在此处插入您的应用截图]](https://github.com/user/repo/assets/image.png)
*(提示: 运行程序后截一张图, 上传到 GitHub issue 中获取链接, 然后替换上面这行)*

---

## ✨ 功能特性

* **多平台聚合**: 一次点击，从四个主流游戏平台抓取数据：
    * TapTap (中国)
    * Bilibili (中国)
    * QooApp (国际)
    * Google Play (国际)
* **智能筛选**: 自动根据关键词（如 "二次元", "养成", "Anime", "RPG"）过滤游戏。
* **内置翻译**: 自动将 QooApp 和 Google Play 上的外文游戏名翻译为中文。
* **原文切换**: 只需点击翻译后的游戏名，即可在中文和原文之间来回切换。
* **异步加载**: 使用多线程异步加载游戏图标，界面流畅不卡顿。
* **现代 UI**: 使用 `CustomTkinter` 构建，支持亮色/暗色模式。

## 🛠️ 安装与运行

本项目使用 Python 3.10+ 和 `selenium-stealth` 来绕过反爬虫。

### 1. 先决条件

* **Python 3.10** 或更高版本。
* **Google Chrome** 浏览器（`webdriver-manager` 会自动下载对应的驱动）。
* **Git** (用于克隆本项目)。

### 2. 安装步骤

1.  克隆本仓库到本地：
    ```bash
    git clone [https://github.com/](https://github.com/)[您的GitHub用户名]/GameScraperGUI.git
    cd GameScraperGUI
    ```

2.  (推荐) 创建一个虚拟环境：
    ```bash
    python -m venv venv
    venv\Scripts\activate  # Windows
    # source venv/bin/activate  # macOS/Linux
    ```

3.  安装所有必需的 Python 库：
    ```bash
    pip install -r requirements.txt
    ```

### 3. 运行程序

一切准备就绪后，直接运行 `main.py`：

```bash
python main.py
```

程序启动后，点击 "刷新数据" 按钮开始爬取。

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE) 开源。