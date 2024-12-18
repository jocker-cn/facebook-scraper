import argparse
import json
import os
import sys
from time import sleep
from typing import re

from playwright.sync_api import sync_playwright
from result import Result


def main():
    global scraper
    parser = argparse.ArgumentParser(
        add_help=True,
        usage="python scraper [option] ... [arg] ...",
        description="Twitter Scraper is a tool that allows you to scrape tweets from twitter without using Twitter's API.",
    )

    try:
        parser.add_argument(
            "--username",
            type=str,
            help="Your Twitter mail.",
        )

        parser.add_argument(
            "--password",
            type=str,
            help="Your Twitter username.",
        )

        parser.add_argument(
            "--filePath",
            type=str,
            default=None,
            help="Your Save File Path.",
        )

        parser.add_argument(
            "--hashtag",
            type=str,
            default=None,
            help="Your Save File Path.",
        )

        parser.add_argument(
            "--login",
            action='store_true',
            default=False,
            help="Your Save File Path.",
        )

        parser.add_argument(
            "--cache",
            action='store_true',
            help="Cache Path.",
        )

        parser.add_argument(
            "--exe",
            action='store_true',
            help="exe Path.",
        )
    except Exception as e:
        print(f"Error retrieving environment variables: {e}")
        print(json.dumps(Result.fail_with_msg(f"Error retrieving environment variables:").to_dict()))
        sys.exit(1)

    args = parser.parse_args()
    # user_name = args.user
    # cookie_file = args.cookiesPath
    # password = args.password
    # is_login = args.login
    # tags = [] if not args.hashtag else [x.strip() for x in args.hashtag.split(',')]

    user_name = "hollyshitprojct1@gmail.com"
    password = "kh22LZHn$!tY#yq"
    is_login = True
    is_login = True
    cookie_file = "True"
    tags = ['oshitlitter']
    # chrome_cache = args.cache

    # chrome_exe = args.exe
    chrome_cache = "D:\\facebook"
    chrome_exe = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    # 登录
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch_persistent_context(  # 指定本机用户缓存地址
            channel="chrome",
            user_data_dir=chrome_cache,
            # 指定本机google客户端exe的路径
            executable_path=chrome_exe,
            # 要想通过这个下载文件这个必然要开  默认是False
            accept_downloads=True,
            # 设置不是无头模式
            headless=False,
            bypass_csp=True,
            slow_mo=10,
            # 跳过检测
            args=['--disable-blink-features=AutomationControlled'])

        browser.grant_permissions(["notifications"], origin="https://www.facebook.com/")
        page = browser.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})
        # 设置页面的缩放比例，例如将页面内容缩放至90%
        page.evaluate("() => document.body.style.zoom='90%'")
        print("GO TO https://www.facebook.com/")
        page.goto("https://www.facebook.com/")

        login_button_xpath = '//button[@data-testid="royal_login_button"]'
        login_button_locator = page.locator(login_button_xpath)
        # 登录模式  且 登录按钮存在
        if is_login and login_button_locator.is_visible():
            page.wait_for_function(f"window.location.href === 'https://www.facebook.com/'", timeout=6000 * 10 * 4)
            print("Page Load normal")
            try:
                print("wait dialog cookie policy")
                cookie_popup_div = page.locator('//div[contains(@aria-label, "拒绝使用非必要 Cookie")]')
                if cookie_popup_div.count() > 0:
                    print("click first cookie policy choose")
                    cookie_popup_div.first.wait_for(state="visible", timeout=3000)  # 等待最多3秒
                    cookie_popup_div.first.click()  # 点击第一个可见的按钮
            except Exception as e:
                print("No Cookie policy", e)

            user_name_input_xpath = '//input[@data-testid="royal_email"]'
            page.fill(user_name_input_xpath, user_name)
            sleep(1)

            password_input_xpath = '//input[@data-testid="royal_pass"]'
            page.fill(password_input_xpath, password)
            sleep(1)
            login_button_xpath = '//button[@data-testid="royal_login_button"]'  # 使用 XPath 查找 input 元素
            page.click(login_button_xpath)
            page.wait_for_load_state('load', timeout=30000)  # 30秒等待加载完成
            if page.wait_for_function(f"window.location.href === 'https://www.facebook.com/?sk=welcome'",
                                      timeout=6000 * 10 * 4):
                page.goto("https://www.facebook.com/")
                page.wait_for_function(f"window.location.href === 'https://www.facebook.com/'", timeout=6000 * 10 * 4)
                print("IN https://www.facebook.com/")

        for tag in tags:
            query_url = get_query_tag(tag)
            page.goto(query_url)
            # page.wait_for_load_state('load', timeout=30000)  # 30秒等待加载完成
            page.wait_for_selector('xpath=//div[@role="feed"]')
            last_post_count = 0
            while True:
                # 获取当前页面中所有的帖子，假设每个帖子是 'div' 元素且是role="feed"下的子元素
                posts = page.query_selector_all('xpath=//div[@role="feed"]/div')

                # 如果当前的帖子数量与上次相同，说明没有更多的帖子加载
                if len(posts) == last_post_count:
                    print("No more content loaded.")
                    break

                # 更新帖子计数
                last_post_count = len(posts)
                # 向下滚动页面
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                # 等待页面加载，调整等待时间以确保内容完全加载
                sleep(2)
                print(f"Loaded {len(posts)} posts, continuing to scroll...")
            for post in posts:
                json = extract_post_info(post)
                print(json)
        # https://www.facebook.com/search/posts?q=oshitlitter&filters=eyJyZWNlbnRfcG9zdHM6MCI6IntcIm5hbWVcIjpcInJlY2VudF9wb3N0c1wiLFwiYXJnc1wiOlwiXCJ9In0%3D
        # https://www.facebook.com/search/posts?q=test&filters=eyJyZWNlbnRfcG9zdHM6MCI6IntcIm5hbWVcIjpcInJlY2VudF9wb3N0c1wiLFwiYXJnc1wiOlwiXCJ9In0%3D


def extract_post_info(post):
    # 提取头像地址
    try:
        avatar_url = post.evaluate("""
        (element) => {
            const svgImage = element.querySelector('svg[data-visualcompletion="ignore-dynamic"] image');
            return svgImage ? svgImage.getAttribute('xlink:href') : null;
        }
    """)

        # 提取用户名
        username = post.evaluate("""
        (element) => {
            const profileNameElement = element.querySelector('[data-ad-rendering-role="profile_name"] span a span');
            return profileNameElement ? profileNameElement.innerText : null;
        }
    """)

        profile_id = post.evaluate(
            """     (element) => {       
                    const profileLinkElement = element.querySelector('[data-ad-rendering-role="profile_name"] a');    
                    return profileLinkElement ? profileLinkElement.href : null;  
            } """)
        if "id=" in profile_id:
            profile_id = profile_id.split("id=")[1].split("&")[0]
            profile_id = f"https://www.facebook.com/profile.php?id={profile_id}"

        # 提取发布时间
        timestamp = post.query_selector_all(
            'xpath=//a[contains(@aria-label, "小时") or contains(@aria-label, "天") or contains(@aria-label, "月") or contains(@aria-label, "年")]')[
            0].get_attribute('aria-label')

        return {
            'avatarUrl': avatar_url,
            'username': username,
            'profileId': profile_id,
            'pushTime': timestamp
        }
    except Exception as e:
        print(f"post parse exception:{e}")
        return None


def get_query_tag(tag):
    return f"https://www.facebook.com/search/posts?q={tag}&filters=eyJyZWNlbnRfcG9zdHM6MCI6IntcIm5hbWVcIjpcInJlY2VudF9wb3N0c1wiLFwiYXJnc1wiOlwiXCJ9In0%3D"


if __name__ == '__main__':
    main()
