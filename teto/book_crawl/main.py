from playwright.sync_api import sync_playwright
import time
import pandas as pd
import math
import os
from tqdm import tqdm

def str_prc(l):
    temp = [l[0].split(":")[1], l[1].split(":")[1], int(l[2].split(":")[1])]
    return temp

def click_locator(page, target_locator, nth=None, first=False):
    cnt = 0
    while cnt < 50:
        try:
            if first:
                locator = page.locator(target_locator).first
            elif nth is not None:
                locator = page.locator(target_locator).nth(nth)
            else:
                locator = page.locator(target_locator)
            locator.wait_for(state="visible", timeout=3000)
            locator.click(force=True)
            break
        except Exception as e:
            pass
        cnt += 1
    if not (cnt < 50) :
        raise TimeoutError

deci_cls = ["종교"]
deci_cls_eng = ["REG"]
url = "https://read365.edunet.net/PureScreen/SchoolSearch?schoolName=%EC%9D%B8%EC%B2%9C%EC%A0%84%EC%9E%90%EB%A7%88%EC%9D%B4%EC%8A%A4%ED%84%B0%EA%B3%A0%EB%93%B1%ED%95%99%EA%B5%90%20%EB%8F%84%EC%84%9C%EA%B4%80&provCode=E10&neisCode=E100000276"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url)
    missing_books = []

    df = pd.DataFrame(columns=[
        "book_type", "book_name", "book_desc", "book_img_link",
        "author", "publisher", "published_y"
    ])
    df = df.astype({"published_y": "Int64"})

    list_p_10 = []
    for i, book_type in enumerate(deci_cls):
        time.sleep(1)
        page.goto(url)
        click_locator(page, 'button:has-text("한국십진분류")')

        book_type_selector = f'ul.category_list li span:text-is("{book_type}")'
        tqdm.write(book_type_selector)
        click_locator(page, book_type_selector, first=True)

        time.sleep(1.5)
        total_num = int(page.locator('div.swiper-slide.is-active a:text-is("전체") > span').inner_text().replace(",", ""))
        cur_n = 0        
        
        pbar = tqdm(total=total_num, disable=False)

        page_n = 1
        while True:
            df = pd.DataFrame(columns=[
                    "book_type", "book_name", "book_desc", "book_img_link",
                    "author", "publisher", "published_y"
                ])
            df = df.astype({"published_y": "Int64"})
            
            book_list = page.locator("ul.book-list.list-type.list > li strong").count()

            for book_i in range(book_list):
                if cur_n < 0 :
                    cur_n += 1
                    pbar.update(1)
                else :
                    try :
                        click_locator(page, "ul.book-list.list-type.list li div.info-wrap strong.prod-name.d-block.fs5.fw-bd", nth=book_i)
                    except :
                        break

                    try:
                        page.wait_for_selector("div.writer.mb-sm span")
                        book_info = str_prc(page.locator("div.writer.mb-sm span").all_inner_texts())
                        book_name = page.locator("h3.prod-name.mb-xs").inner_text()
                    except:
                        tqdm.write(f"fail: page={page_n}, book={book_i}")

                    try:
                        book_description = page.locator("div.summary-wrap.fl-right.mb-sm").inner_text(timeout=500)
                    except:
                        book_description = ""

                    book_img = page.locator("div.img-wrap.shadow-sm.mb-ls img").first.get_attribute("src")

                    row = {
                        "book_type": book_type,
                        "book_name": book_name,
                        "book_desc": book_description,
                        "book_img_link": book_img,
                        "author": book_info[0],
                        "publisher": book_info[1],
                        "published_y": int(book_info[2]) if book_info[2] else None
                    }

                    list_p_10.append(row)
                    page.go_back()
                    pbar.update(1)
                    cur_n += 1

                if list_p_10:
                    df = pd.concat([
                        df,
                        pd.DataFrame(list_p_10).astype({"published_y": "Int64"})
                    ], ignore_index=True)
                list_p_10 = []
                df.to_csv(f"book_data/{deci_cls_eng[i]}.csv", index=False, mode='a', header=not os.path.exists(f"book_data/{deci_cls_eng[i]}.csv"))
                
                df = pd.DataFrame(columns=[
                        "book_type", "book_name", "book_desc", "book_img_link",
                        "author", "publisher", "published_y"
                    ])
                df = df.astype({"published_y": "Int64"})

            if page_n % 5 == 0:
                try :
                    click_locator(page, "i.icon-pading-next")
                except :
                    break
                page_n += 1
            else:
                try:
                    click_locator(page, f"div.list-paging.mt-xl a:text-is('{page_n+1}')")
                    page_n += 1
                except Exception as e:
                    break
            if cur_n == total_num :
                break

        pbar.close()
        
        page.close()
        page = browser.new_page()
        page.goto(url)
