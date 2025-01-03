import argparse
import os
import sys
import json
from datetime import datetime, timedelta
from time import sleep
import re

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
            "--scrapper_url",
            type=str,
            help="Your Twitter username.",
        )

        parser.add_argument(
            "--file_path",
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
            type=str,
            help="Cache Path.",
        )

        parser.add_argument(
            "--exe",
            type=str,
            help="exe Path.",
        )
    except Exception as e:
        print(f"Error retrieving environment variables: {e}")
        print(json.dumps(Result.fail_with_msg(f"Error retrieving environment variables:").to_dict()))
        sys.exit(1)

    args = parser.parse_args()
    user_name = args.username
    password = args.password
    is_login = args.login
    chrome_cache = args.cache
    chrome_exe = args.exe
    file_path = args.file_path
    scrapper_url = args.scrapper_url
    # scrapper_url = "https://www.facebook.com/groups/939764370920262/?sorting_setting=CHRONOLOGICAL"
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
            headless=True,
            bypass_csp=True,
            slow_mo=10,
            locale='en-SG',
            # 跳过检测
            args=['--disable-blink-features=AutomationControlled'])

        browser.grant_permissions(["notifications"], origin="https://www.facebook.com/")
        page = browser.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})
        # 设置页面的缩放比例，例如将页面内容缩放至90%
        page.evaluate("() => document.body.style.zoom='90%'")
        print("GO TO https://www.facebook.com/")
        page.goto("https://www.facebook.com/")

        login_button_xpath = '//button[@id="loginbutton"]'
        login_button_locator = page.locator(login_button_xpath)
        # 登录模式  且 登录按钮存在
        if is_login and login_button_locator.is_visible():
            page.wait_for_function("window.location.href.startsWith('https://www.facebook.com/login/')",
                                   timeout=6000 * 10 * 4)
            print("Login Page Load normal")
            try:
                print("wait dialog cookie policy")
                cookie_popup_div = page.locator('//div[contains(@aria-label, "拒绝使用非必要 Cookie")]')
                if cookie_popup_div.count() > 0:
                    print("click first cookie policy choose")
                    cookie_popup_div.first.wait_for(state="visible", timeout=3000)  # 等待最多3秒
                    cookie_popup_div.first.click()  # 点击第一个可见的按钮
            except Exception as e:
                print("No Cookie policy", e)

            user_name_input_xpath = '//input[@autocomplete="username"]'
            page.fill(user_name_input_xpath, user_name)
            sleep(1)

            password_input_xpath = '//input[@autocomplete="current-password"]'
            page.fill(password_input_xpath, password)
            sleep(1)
            login_button_locator.click()
            page.wait_for_load_state('load', timeout=30000)  # 30秒等待加载完成
            if page.wait_for_function("window.location.href === 'https://www.facebook.com/'", timeout=6000 * 10 * 4):
                page.goto("https://www.facebook.com/")
                page.wait_for_function(f"window.location.href === 'https://www.facebook.com/'", timeout=6000 * 10 * 4)
                print("IN https://www.facebook.com/")

        page.goto(scrapper_url)
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
        posts = posts[1:-1]
        jsons = []
        for post in posts:
            json = extract_post_info(post)
            if json:
                jsons.append(json)

        if len(jsons) > 0:
            print(f"load fb posts count:{len(jsons)}")
            save_json_to_file(jsons, file_path)


def save_json_to_file(jsons, file_path):
    try:
        today_date = datetime.now().strftime("%Y-%m-%d")
        directory = os.path.join(file_path, today_date)
        if not os.path.exists(directory):
            os.makedirs(directory)
        file_name = f"{today_date}_fb.json"
        file_full_path = os.path.join(directory, file_name)
        with open(file_full_path, 'w', encoding='utf-8') as file:
            json.dump(jsons, file, ensure_ascii=False, indent=4)
        print(json.dumps(Result.ok(file_full_path).to_dict()))
    except Exception as e:
        print(json.dumps(Result.fail_with_msg(f"save JSON failed: {e}").to_dict()))

    # for tag in tags:
    #     query_url = get_query_tag(tag)
    #     page.goto(query_url)
    #     # page.wait_for_load_state('load', timeout=30000)  # 30秒等待加载完成
    #     page.wait_for_selector('xpath=//div[@role="feed"]')
    #     last_post_count = 0
    #     while True:
    #         # 获取当前页面中所有的帖子，假设每个帖子是 'div' 元素且是role="feed"下的子元素
    #         posts = page.query_selector_all('xpath=//div[@role="feed"]/div')
    #
    #         # 如果当前的帖子数量与上次相同，说明没有更多的帖子加载
    #         if len(posts) == last_post_count:
    #             print("No more content loaded.")
    #             break
    #
    #         # 更新帖子计数
    #         last_post_count = len(posts)
    #         # 向下滚动页面
    #         page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
    #         # 等待页面加载，调整等待时间以确保内容完全加载
    #         sleep(2)
    #         print(f"Loaded {len(posts)} posts, continuing to scroll...")
    #     for post in posts:
    #         json = extract_post_info(post)
    #         print(json)
    # https://www.facebook.com/search/posts?q=oshitlitter&filters=eyJyZWNlbnRfcG9zdHM6MCI6IntcIm5hbWVcIjpcInJlY2VudF9wb3N0c1wiLFwiYXJnc1wiOlwiXCJ9In0%3D
    # https://www.facebook.com/search/posts?q=test&filters=eyJyZWNlbnRfcG9zdHM6MCI6IntcIm5hbWVcIjpcInJlY2VudF9wb3N0c1wiLFwiYXJnc1wiOlwiXCJ9In0%3D


def extract_post_info(post):
    # 提取头像地址
    try:

        is_reels = post.evaluate("""
        (element) => {
            return element.querySelector('[data-pagelet="Reels"]') !== null;
        }
        """)

        if is_reels:
            avatar_url = post.evaluate("""
            (element) => {
             const avatarImage = element.querySelector('svg[aria-label="头像"][data-visualcompletion="ignore-dynamic"] image');
                 if (avatarImage) {
                    return avatarImage.getAttribute('xlink:href');
                 }
                return null;
            }
            """)
            username = post.evaluate("""
            (element)=>{
                const divElement = Array.from(element.querySelectorAll('span')).find(span =>   span.textContent.includes('短视频') || span.textContent.includes('Reels'));
                    if (divElement) {
                      const objectElement = divElement.querySelector('object[type="nested/pressable"]');
                      if (objectElement) {
                        const aElement = objectElement.querySelector('a');
                        if (aElement) {
                          return aElement.textContent.trim();
                        }
                      }
                    }
                return ''; 
             }
            """)

            post_id = post.evaluate("""
             (element) => {
                 const videoElement = element.querySelector('div[data-video-id]');
                 if (videoElement) {
                   return videoElement.getAttribute('data-video-id');
                 }
                 return null; 
             }
            """)
            post_link = ""
            if post_id:
                post_link = f"https://www.facebook.com/reel/{post_id}"

            profile_id = post.evaluate("""
              (element) => {
                const linkElement = element.querySelector('a[aria-label="查看所有者个人主页"]');
                if (linkElement) {
                  return linkElement.getAttribute('href');
                }
                return null;  // 如果没有找到相关元素，返回 null
              }
            """)
            if profile_id:
                profile_id = f"https://www.facebook.com{profile_id.split('/?')[0]}"
            post_content = post.evaluate("""
                (element) => {
                    const reelsDiv = element.querySelector('div[data-pagelet="Reels"]');
                    if (!reelsDiv) {
                        return '';
                    }
            
                    const nextSiblingDiv = reelsDiv.nextElementSibling;
                    if (!nextSiblingDiv) {
                        return ''; 
                    }
                    return nextSiblingDiv.textContent.trim();
                }
            """)
            timestamp = post.query_selector(
                'xpath=//span[contains(text(), "分钟") or contains(text(), "小时") or contains(text(), "天") or contains(text(), "月") or contains(text(), "年")]')
            if timestamp:
                timestamp = timestamp.text_content().strip()
                timestamp = parse_relative_time(timestamp)
            hashtags = post.evaluate("""
              (element) => {
                const results = [];
                const aTags = element.querySelectorAll('a[href*="hashtag"]');
                aTags.forEach(aTag => {
                    if (aTag.textContent.startsWith('#')) {
                        results.push(aTag.textContent.trim());
                    }
                });
                return [...new Set(results)]; 
            }
            """)
        else:
            profile_id = post.evaluate(
                """     (element) => {       
                        const profileLinkElement = element.querySelector('[data-ad-rendering-role="profile_name"] a');    
                        return profileLinkElement ? profileLinkElement.href : null;  
                } """)

            if profile_id:
                profile_id = profile_id.split('/?')[0]
                # profile_id = f"https://www.facebook.com/profile.php?id={profile_id}"
            username = post.evaluate("""
                (element) => {
                    const profileNameElement = element.querySelector('[data-ad-rendering-role="profile_name"] span a span');
                    return profileNameElement ? profileNameElement.innerText : null;
                }
            """)
            avatar_url = post.evaluate("""
                (element) => {
                    const svgImage = element.querySelector('svg[data-visualcompletion="ignore-dynamic"] image');
                    return svgImage ? svgImage.getAttribute('xlink:href') : null;
                }
            """)
            post_link = post.evaluate("""
                (element) => {
                const aTag = element.querySelector('a[role="link"][href*="/posts/"]');
                return aTag ? aTag.href : null;
                }
             """)
            post_id = ""
            if post_link:
                post_link = post_link.split('/?')[0]
            if post_link:
                post_id = post_link.split('/posts/')[1]

            timestamp = post.query_selector_all(
                'xpath=//a[contains(@aria-label, "小时") or contains(@aria-label, "分钟") or contains(@aria-label, "天") or contains(@aria-label, "月") or contains(@aria-label, "年")]')[
                0].get_attribute('aria-label')
            post_content = post.evaluate("""
            (element) => {
                const contentDiv = element.querySelector('div[data-ad-rendering-role="story_message"]');
                return contentDiv ? contentDiv.innerText : null;
            }
            """)

            hashtags = post.evaluate("""
            (element) => {
                const contentDiv = element.querySelector('div[data-ad-rendering-role="story_message"]');
                if (!contentDiv) return [];
    
                const tags = contentDiv.querySelectorAll('a');
                let tagArray = [];
                tags.forEach(tag => {
                    if (tag && tag.href && tag.href.includes('hashtag')) {
                        tagArray.push(tag.innerText);
                    }
                });
                return tagArray;
            }
            """)

        like_count = post.evaluate("""
        (element) => {
            const posts = Array.from(element.querySelectorAll('div[role="button"]'));
            for (let post of posts) {
                if (post.textContent.includes('所有心情：')) {
                    const siblingSpan = post.querySelector('span span span');
                    if (siblingSpan && siblingSpan.textContent.trim() !== '') {
                    return siblingSpan.textContent.trim();
                    }
                }
            }
            return 0;
        }
        """)

        comments = post.evaluate("""
        (element) => {
                const spans = Array.from(element.querySelectorAll('span'));
                for (let span of spans) {
                if (span.textContent.includes('条评论')) {
                    const match = span.textContent.match(/(\\d+)\\s*条评论/);
                    if (match) {
                        return match[1];
                    }
                }
            }
            return 0;  // 没有找到时返回 null
        }
        """)

        share = post.evaluate("""
        (element) => {
                const spans = Array.from(element.querySelectorAll('span'));
                for (let span of spans) {
                if (span.textContent.includes('次分享')) {
                    const match = span.textContent.match(/(\\d+)\\s*次分享/);
                    if (match) {
                        return match[1];
                    }
                }
            }
            return 0;  // 没有找到时返回 null
        }
        """)

        return {
            'avatarUrl': avatar_url,
            'username': username,
            'profileId': profile_id,
            'pushTime': timestamp,
            'postContent': post_content,
            'postLink': post_link,
            'postId': post_id,
            'hashtags': hashtags,
            'like': like_count,
            'comments': comments,
            'share': share,
        }

    except Exception as e:
        print(f"post parse exception:{e}")
        return None


# def get_query_tag(tag):
#     return f"https://www.facebook.com/search/posts?q={tag}&filters=eyJyZWNlbnRfcG9zdHM6MCI6IntcIm5hbWVcIjpcInJlY2VudF9wb3N0c1wiLFwiYXJnc1wiOlwiXCJ9In0%3D"

def parse_relative_time(relative_str):
    now = datetime.now()

    time_units = {
        '分钟': 'minutes',
        '小时': 'hours',
        '天': 'days',
    }

    # 使用正则表达式提取数字和单位
    match = re.match(r'(\d+)(分钟|小时|天)', relative_str)
    if match:
        value, unit = match.groups()
        value = int(value)
        if unit in time_units:
            delta = timedelta(**{time_units[unit]: value})
            return (now - delta).strftime('%Y-%m-%d %H:%M')

    match = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日(\d{1,2}):(\d{2})', relative_str)
    if match:
        year, month, day, hour, minute = map(int, match.groups())
        try:
            return datetime(year, month, day, hour, minute).strftime('%Y-%m-%d %H:%M')
        except ValueError:
            pass

    match = re.match(r'(\d{1,2})月(\d{1,2})日', relative_str)
    if match:
        month, day = map(int, match.groups())
        year = now.year
        # 如果当前月份小于给定月份，则认为是上一年
        if now.month < month or (now.month == month and now.day < day):
            year -= 1
        try:
            return datetime(year, month, day, 0, 0).strftime('%Y-%m-%d %H:%M')
        except ValueError:
            pass

    return now.strftime('%Y-%m-%d %H:%M')


if __name__ == '__main__':
    main()
