#!/usr/bin/env python3
import json
import re
import time
from urllib.parse import unquote

import urllib3
from lxml import etree

from models.base.web import get_html
from models.crawlers.guochan import get_number_list

urllib3.disable_warnings()  # yapf: disable


# import traceback


def get_actor_photo(actor):
    actor = actor.split(",")
    data = {}
    for i in actor:
        actor_photo = {i: ""}
        data.update(actor_photo)
    return data


def get_detail_info(html, real_url):
    number = unquote(real_url.split("/")[-1])
    item_list = html.xpath('//ol[@class="breadcrumb"]//text()')
    new_item_list = []
    [new_item_list.append(i) for i in item_list if i.strip()]
    if new_item_list:
        title = new_item_list[-1].strip()
        studio = "麻豆" if "麻豆" in new_item_list[1] else new_item_list[-2].strip()
        title, number, actor, series = get_actor_title(title, number, studio)
        if "系列" in new_item_list[-2]:
            series = new_item_list[-2].strip()
        cover = html.xpath('//div[@class="post-image-inner"]/img/@src')
        cover = cover[0] if cover else ""
        return True, number, title, actor, real_url, cover, studio, series
    return False, "", "", "", "", "", "", ""


def get_search_info(html, number_list):
    item_list = html.xpath('//div[@class="post-item"]')
    for each in item_list:
        title = each.xpath("h3/a/text()")
        if title:
            for n in number_list:
                if n.upper() in title[0].upper():
                    number = n
                    real_url = each.xpath("h3/a/@href")
                    real_url = real_url[0] if real_url else ""
                    cover = each.xpath('div[@class="post-item-image"]/a/div/img/@src')
                    cover = cover[0] if cover else ""
                    studio_url = each.xpath("a/@href")
                    studio_url = studio_url[0] if studio_url else ""
                    studio = each.xpath("a/span/text()")
                    studio = studio[0] if studio else ""
                    if "麻豆" in studio_url:
                        studio = "麻豆"
                    title, number, actor, series = get_actor_title(title[0], number, studio)
                    return True, number, title, actor, real_url, cover, studio, series
    return False, "", "", "", "", "", "", ""


def get_actor_title(title, number, studio):
    temp_list = re.split(r"[\., ]", title.replace("/", "."))
    actor_list = []
    new_title = ""
    series = ""
    for i in range(len(temp_list)):
        if number.upper() in temp_list[i].upper():
            number = temp_list[i]
            continue
        if "系列" in temp_list[i]:
            series = temp_list[i]
            continue
        if i < 2 and ("传媒" in temp_list[i] or studio in temp_list[i]):
            continue
        if i > 2 and (
            studio == temp_list[i] or "麻豆" in temp_list[i] or "出品" in temp_list[i] or "传媒" in temp_list[i]
        ):
            break
        if i < 3 and len(temp_list[i]) <= 4 and len(actor_list) < 1:
            actor_list.append(temp_list[i])
            continue
        if len(temp_list[i]) <= 3 and len(temp_list[i]) > 1:
            actor_list.append(temp_list[i])
            continue
        new_title += "." + temp_list[i]
    title = new_title if new_title else title
    return title.strip("."), number, ",".join(actor_list), series


def main(number, appoint_url="", log_info="", req_web="", language="zh_cn", file_path="", appoint_number=""):
    start_time = time.time()
    website_name = "cnmdb"
    req_web += "-> %s" % website_name
    title = ""
    cover_url = ""
    web_info = "\n       "
    log_info += " \n    🌐 cnmdb"
    debug_info = ""
    real_url = appoint_url
    series = ""

    try:
        if real_url:
            debug_info = f"番号地址: {real_url} "
            log_info += web_info + debug_info
            result, response = get_html(real_url)
            if result:
                detail_page = etree.fromstring(response, etree.HTMLParser())
                result, number, title, actor, real_url, cover_url, studio, series = get_detail_info(
                    detail_page, real_url
                )
            else:
                debug_info = "没有找到数据 %s " % response
                log_info += web_info + debug_info
                raise Exception(debug_info)

        else:
            # 处理番号
            number_list, filename_list = get_number_list(number, appoint_number, file_path)
            for each in number_list:
                real_url = "https://cnmdb.net/" + each
                debug_info = f"请求地址: {real_url} "
                log_info += web_info + debug_info
                result, response = get_html(real_url, keep=False)
                if result:
                    detail_page = etree.fromstring(response, etree.HTMLParser())
                    result, number, title, actor, real_url, cover_url, studio, series = get_detail_info(
                        detail_page, real_url
                    )
                    break
            else:
                filename_list = re.split(r"[\.,，]", file_path)
                for each in filename_list:
                    if len(each) < 5 or "传媒" in each or "麻豆" in each:
                        continue
                        
                    search_url = f"https://cnmdb.net/search/keyword-{each}.html"
                    debug_info = f"请求地址: {search_url} "
                    log_info += web_info + debug_info
                    result, response = get_html(search_url, keep=False)
                    if not result:
                        debug_info = "网络请求错误: %s" % response
                        log_info += web_info + debug_info
                        raise Exception(debug_info)
                    search_page = etree.fromstring(response, etree.HTMLParser())
                    result, number, title, actor, real_url, cover_url, studio, series = get_search_info(
                        search_page, number_list
                    )
                    if result:
                        break
                else:
                    debug_info = "没有匹配的搜索结果"
                    log_info += web_info + debug_info
                    raise Exception(debug_info)

        actor_photo = get_actor_photo(actor)

        try:
            dic = {
                "number": number,
                "title": title,
                "originaltitle": title,
                "actor": actor,
                "outline": "",
                "originalplot": "",
                "tag": "",
                "release": "",
                "year": "",
                "runtime": "",
                "score": "",
                "series": series,
                "country": "CN",
                "director": "",
                "studio": studio,
                "publisher": studio,
                "source": "cnmdb",
                "website": real_url,
                "actor_photo": actor_photo,
                "cover": cover_url,
                "poster": "",
                "extrafanart": "",
                "trailer": "",
                "image_download": False,
                "image_cut": "no",
                "log_info": log_info,
                "error_info": "",
                "req_web": req_web
                + "(%ss) "
                % (
                    round(
                        (time.time() - start_time),
                    )
                ),
                "mosaic": "国产",
                "wanted": "",
            }
            debug_info = "数据获取成功！"
            log_info += web_info + debug_info
            dic["log_info"] = log_info
        except Exception as e:
            debug_info = "数据生成出错: %s" % str(e)
            log_info += web_info + debug_info
            raise Exception(debug_info)

    except Exception as e:
        # print(traceback.format_exc())
        debug_info = str(e)
        dic = {
            "title": "",
            "cover": "",
            "website": "",
            "log_info": log_info,
            "error_info": debug_info,
            "req_web": req_web
            + "(%ss) "
            % (
                round(
                    (time.time() - start_time),
                )
            ),
        }
    dic = {website_name: {"zh_cn": dic, "zh_tw": dic, "jp": dic}}
    js = json.dumps(
        dic,
        ensure_ascii=False,
        sort_keys=False,
        indent=4,
        separators=(",", ": "),
    )
    return js


if __name__ == "__main__":
    print(main('XSJ138.2.2.',file_path='XSJ138.2.3.4'))  
