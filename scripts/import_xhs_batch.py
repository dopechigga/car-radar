#!/usr/bin/env python3
"""Import the verified Xiaohongshu Top Case batch into the dashboard dataset."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "dist" / "data" / "hotspots.json"


RECORDS = [
    ("6aafbb6a00000000270176c9", "小米澎程拆车第一期。", "老章说车", "1天前 湖北", 1079, 202, 202, "https://sns-webpic-qc.xhscdn.com/202609221541/5d24066599fd74cd4b8d8994ce3f73fd/1040g008325b9r4mql0005o9g4be0jbti1stpqq8!nc_n_webp_mw_1", "https://www.xiaohongshu.com/explore/6aafbb6a00000000270176c9?xsec_token=ABaU_EGmDL4GnrjVh2egVkRHbCK6tWYSlhdHi0jwi_Gwk=&xsec_source=pc_feed", "视频"),
    ("6aadf9f70000000011032211", "小米澎程被拆成这样？找不到一颗自攻螺丝？", "塞车手kimi", "3天前 浙江", 652, 124, 284, "https://sns-webpic-qc.xhscdn.com/202609221541/bb04b13b4da4d8a31321b6b10f07d4ad/spectrum/1040g0k03259j04o7ka004bglirb8f0i15dlufeo!nc_n_webp_mw_1", "https://www.xiaohongshu.com/explore/6aadf9f70000000011032211?xsec_token=AB9ht4PNRMvCwHpAvOScrkaSvL4eQBRXarW6fZHS--7jc=&xsec_source=pc_feed", "视频"),
    ("6aadfeeb0000000029013d87", "小米员工车展", "Adolph", "3天前 北京", 598, 52, 81, "https://sns-webpic-qc.xhscdn.com/202609221527/2740c8d4f2c54bc64bfa34cd2e693c6b/notes_uhdr/1040g3qg3259jitdgk4005pbhs9d731fifki1b58!nc_n_webp_mw_1", "https://www.xiaohongshu.com/explore/6aadfeeb0000000029013d87?xsec_token=AB9ht4PNRMvCwHpAvOScrkaeBRdtz6UeYuZXAoWqv3Lvw=&xsec_source=pc_feed", "视频"),
    ("6aad064a000000002b013f30", "神车换代｜再见了，燃油718", "电动猩球KONG", "3天前 重庆", 242, 47, 146, "https://sns-webpic-qc.xhscdn.com/202609221527/05f2f10da8472b63112208dee635c703/notes_pre_post/1040g3k03258k39nvl0205npan940914hbf7ppm8!nc_n_webp_mw_1", "https://www.xiaohongshu.com/explore/6aad064a000000002b013f30?xsec_token=AB9ht4PNRMvCwHpAvOScrkaUyb44JYCOub-WvYHCLkqDE=&xsec_source=pc_feed", "图文"),
    ("6aab9ee8000000002a024b24", "贵4万的蔚来ES8，比理想i9强在哪？", "驭见未来", "4天前 广东", 196, 61, 488, "https://sns-webpic-qc.xhscdn.com/202609221530/92079ba9fad099cb559a9315d878154f/1040g2sg32579bbmu4qkg5pdeer04t3pkpjo2kho!nc_n_webp_mw_1", "https://www.xiaohongshu.com/explore/6aab9ee8000000002a024b24?xsec_token=ABLVYFFf8uoxzW5N3OapnOuM_waj93B3FALMgRxnS5M8w=&xsec_source=pc_feed", "图文"),
    ("6aa78571000000002502ed03", "i9 这个车一坐进去就感觉被夺舍了", "汽车一级调研员", "6天前 河南", 202, 33, 191, "https://sns-webpic-qc.xhscdn.com/202609221530/d012461e98381292ea90d9956ac6fed5/1040g0083253306c6ji605o94d6ig90s4ism9up8!nc_n_webp_mw_1", "https://www.xiaohongshu.com/explore/6aa78571000000002502ed03?xsec_token=ABQyFy_HO_Aif0ZLKzaZPispHyyWmVtgm2HMddZ2OobdM=&xsec_source=pc_feed", "图文"),
    ("6a9ab8580000000029018a73", "蔚小理车型这么多，你分得清吗？", "电动星球News", "4天前 广东", 291, 83, 47, "https://sns-webpic-qc.xhscdn.com/202609221530/711e05bd39003c47f080ded5aeff82b2/spectrum/1040g34o324qbrfrin2105oga0rgk0tct25vf15g!nc_n_webp_mw_1", "https://www.xiaohongshu.com/explore/6a9ab8580000000029018a73?xsec_token=ABU8ncdoinepF8Rp9NY3UHJBTRsJr226mRBs9ifYrx_s4=&xsec_source=pc_feed", "图文"),
    ("6aaa3c3b0000000026022196", "理想i9 大到什么程度？来，展示！", "陈震同学", "5天前 北京", 512, 58, 83, "https://sns-webpic-qc.xhscdn.com/202609221532/465735fff733c89d54303e75e9bbf10d/spectrum/1040g34o3255trh4m48105nkdjkm08u2nva1ej50!nc_n_webp_mw_1", "https://www.xiaohongshu.com/explore/6aaa3c3b0000000026022196?xsec_token=ABYnf8eE9HNnR0lMjS7PPFFdltmI1hg7uGDNfJZch7bgs=&xsec_source=pc_feed", "视频"),
    ("6aa8e711000000000b034bba", "感受下理想 i9 有多大", "吕亮", "7天前 上海", 304, 53, 152, "https://sns-webpic-qc.xhscdn.com/202609221532/279e609a7996cda1f1752a6b26dc789a/1040g0083254kd5ih3o005nklempg8dqaag11ulg!nc_n_webp_mw_1", "https://www.xiaohongshu.com/explore/6aa8e711000000000b034bba?xsec_token=ABTgaSAbPV3Msgy00RQqhsSjTXwF2Lzip6J6UF04OCQyg=&xsec_source=pc_feed", "视频"),
    ("6aab7d8e000000002b003092", "致理想汽车：i9低价上市辜负信任", "菜丶小四", "4天前 江苏", 189, 27, 646, "https://sns-webpic-qc.xhscdn.com/202609221532/0f438a97054ec3ed5d703f7a396057d8/note_pre_post_uhdr/1040g3r0325755fgt50005o7mearg80jkcug23uo!nc_n_webp_mw_1", "https://www.xiaohongshu.com/explore/6aab7d8e000000002b003092?xsec_token=ABLVYFFf8uoxzW5N3OapnOuHjhT7sz1kuKDEFhD6LDS2A=&xsec_source=pc_feed", "视频"),
    ("6aaa8535000000001203625c", "理想i9二排空间有多夸张？", "杨鹏鹏来也", "5天前 北京", 146, 39, 1382, "https://sns-webpic-qc.xhscdn.com/202609221532/1ca75bfe7c58723041606574b78ef0fb/1040g2sg32566c1sg44fg5p01veoah35n3c4gcu8!nc_n_webp_mw_1", "https://www.xiaohongshu.com/explore/6aaa8535000000001203625c?xsec_token=ABYnf8eE9HNnR0lMjS7PPFFXzQ0AhC_m8Lcc32iYzV9hs=&xsec_source=pc_feed", "视频"),
    ("6aabe41f0000000011034a59", "小鹏G9L 23.18万元起", "QA不是熊", "4天前 广东", 268, 38, 540, "https://sns-webpic-qc.xhscdn.com/202609221533/d4598f260a693394aa7fdad876d5804a/1040g2sg3257h26i64l0g5o38fr708hc48tvhsa0!nc_n_webp_mw_1", "https://www.xiaohongshu.com/explore/6aabe41f0000000011034a59?xsec_token=ABLVYFFf8uoxzW5N3OapnOuOoJQQPeY2W_-NkTqqx2YdI=&xsec_source=pc_feed", "图文"),
    ("6aac133e000000001103b06a", "小鹏G9L，同价位全球确实没有对手", "何小鹏", "4天前 广东", 362, 57, 220, "https://sns-webpic-qc.xhscdn.com/202609221533/8bb8602529142e66bd8f1a91c3f5bdc9/spectrum/1040g0k03257niv8t48005oljqqkmt6j78s21v7o!nc_n_webp_mw_1", "https://www.xiaohongshu.com/explore/6aac133e000000001103b06a?xsec_token=ABdjmILVh0X9My4RdH0_QZf5dKv9qcxSYTaYrcToN0Za4=&xsec_source=pc_feed", "视频"),
    ("6aaf7bfb00000000120034ba", "31.8万元！雷克萨斯新车正式上市", "小宇说车", "昨天 08:36 江西", 472, 99, 433, "https://sns-webpic-qc.xhscdn.com/202609221535/5a727851f19c130d70515e13db6ab/1040g008325c1cda644005pqvjmf62onok637o0o!nc_n_webp_mw_1", "https://www.xiaohongshu.com/explore/6aaf7bfb00000000120034ba?xsec_token=ABaU_EGmDL4GnrjVh2egVkRG3juU3Qoyw3nW2f1XV4RHU=&xsec_source=pc_feed", "图文"),
    ("6a9674b9000000002802df13", "更新｜2026年9月下旬新车发布日历", "爱看车的小胡呀", "3天前 广东", 200, 95, 57, "https://sns-webpic-qc.xhscdn.com/202609221535/d5cb664d2a0edc5f47dd4810f7ed15dd/1040g0083259kkina56605ng8736g8fap87tcbj0!nc_n_webp_mw_1", "https://www.xiaohongshu.com/explore/6a9674b9000000002802df13?xsec_token=ABi-RtrS5Wa55sQ-roWeTCvew6EpXgRbbZOUrvlBf_9TA=&xsec_source=pc_feed", "图文"),
    ("6aade3b7000000000d024e71", "新理想i6更新内容", "独钓寒江雪", "3天前 云南", 194, 75, 308, "https://sns-webpic-qc.xhscdn.com/202609221535/37834e73067d490e0234c14e6d0b327f/1040g0083259g7vpmkk605ntme12gbnbv3bjcdio!nc_n_webp_mw_1", "https://www.xiaohongshu.com/explore/6aade3b7000000000d024e71?xsec_token=AB9ht4PNRMvCwHpAvOScrkaeG7GtQLHWxMn0XtmN5HYqE=&xsec_source=pc_feed", "图文"),
    ("6aab7d70000000002802a69f", "我车库的 SUV 测评：揽胜是最好的商务 SUV", "KJ", "3天前 辽宁", 411, 118, 76, "https://sns-webpic-qc.xhscdn.com/202609221537/2993cbd55837ea35ebc010a5b92b371c/1040g00832574jl03kq005qfk32kgga04a6tjeg8!nc_n_webp_mw_1", "https://www.xiaohongshu.com/explore/6aab7d70000000002802a69f?xsec_token=ABLVYFFf8uoxzW5N3OapnOuPgYUEKnf3ISfCWJ2fwrJBM=&xsec_source=pc_feed", "图文"),
    ("6aafa3dd000000002601fba4", "国产智驾 VS 特斯拉 FSD V14，差距到底有多大？", "车轮沅动力", "1天前 湖南", 2096, 464, 713, "https://sns-webpic-qc.xhscdn.com/202609221537/dd34acc6c96e1705ceb37a6c5b804ea4/spectrum/1040g34o325b6vtcq44105nu71f1gbhr6objkbd0!nc_n_webp_mw_1", "https://www.xiaohongshu.com/explore/6aafa3dd000000002601fba4?xsec_token=ABaU_EGmDL4GnrjVh2egVkRMDb3fhy5920DmTdnKA4j8M=&xsec_source=pc_feed", "视频"),
    ("6aaba5330000000011037b63", "36.98万！理想i9哪些配置值得选？", "爱探店的芋圆", "4天前 重庆", 298, 93, 48, "https://sns-webpic-qc.xhscdn.com/202609221538/dc413b6e1390febaba7193a34ee6e6bf/1040g0083257a3r03kk704atdsomtjru9imcelt8!nc_n_webp_mw_1", "https://www.xiaohongshu.com/explore/6aaba5330000000011037b63?xsec_token=ABLVYFFf8uoxzW5N3OapnOuOuaOLncrzau-XVxn8rzFDo=&xsec_source=pc_feed", "视频"),
    ("6aae7c310000000028036468", "四年车主告诉你，蔚来电池的坑", "秋美丽的美好生活🌸", "2天前 北京", 422, 105, 588, "https://sns-webpic-qc.xhscdn.com/202609221539/d3b395502c41eb60dad5c7ce7126223d/notes_pre_post/1040g3k0325a2j2jn4c305n55erak14mkfek05go!nc_n_webp_mw_1", "https://www.xiaohongshu.com/explore/6aae7c310000000028036468?xsec_token=ABWAslZYP7KhHg8dMFYe3FXE4pnKy_RtjzFX9nTwDS59g=&xsec_source=pc_feed", "图文"),
    ("6ab08a12000000002603acd8", "造车梦醒：新能源车企倒下，买单的是车主", "超哥超车", "昨天 18:00 湖南", 519, 59, 64, "https://sns-webpic-qc.xhscdn.com/202609221539/a0a6b1b5eb1a33eb28d7c8164abcac9d/spectrum/1040g34o325c2vndm460g5p9nt7738p6aqmkepsg!nc_n_webp_mw_1", "https://www.xiaohongshu.com/explore/6ab08a12000000002603acd8?xsec_token=ABCSKFT7FGLZFWcgVCEQK5ekAMKxJgr9XrQE5NNVmED5I=&xsec_source=pc_feed", "视频"),
    ("6aa82ca90000000011039e16", "电车8年斩杀线，真实车主用车体验", "三刀侃车", "7天前 广东", 178, 78, 190, "https://sns-webpic-qc.xhscdn.com/202609221539/d466fe7f880240ac5fbbfc5421b623b5/1040g2sg3253tet1m40jg5pkk4f2gualfj9837bo!nc_n_webp_mw_1", "https://www.xiaohongshu.com/explore/6aa82ca90000000011039e16?xsec_token=ABTgaSAbPV3Msgy00RQqhsSgt8WnO44HRMT_p3HQUKSKU=&xsec_source=pc_feed", "视频"),
    ("6aafa30d00000000110375ee", "ID. AURA T6正式上市！", "一汽大众", "昨天 21:41 吉林", 271, 66, 49, "https://sns-webpic-qc.xhscdn.com/202609221540/737cb2fd48b3ff29a26d9f15a5d1d573/spectrum/1040g0k0325b881m0ka005nqr4cpgbhjdsm6mer0!nc_n_webp_mw_1", "https://www.xiaohongshu.com/explore/6aafa30d00000000110375ee?xsec_token=ABaU_EGmDL4GnrjVh2egVkROUopIHWmeSdAIM8yNefmUU=&xsec_source=pc_feed", "图文"),
    ("6aae41dc000000000b00c5bc", "老章拆车乐得嘴就没合上过", "双马尾萌妹", "2天前 广东", 215, 27, 146, "https://sns-webpic-qc.xhscdn.com/202609221541/b9b0292e4ca3dd65c99fe6d611f9c44f/notes_pre_post/1040g3k83259rot6t4k005ngj1ru0873956l6fmo!nc_n_webp_mw_1", "https://www.xiaohongshu.com/explore/6aae41dc000000000b00c5bc?xsec_token=ABWAslZYP7KhHg8dMFYe3FXIb5IIBt7DLvMEqHr8-q0PI=&xsec_source=pc_feed", "图文"),
]


EXISTING_COVERS = {
    "xhs-li-auto-owner-backlash": "https://sns-webpic-qc.xhscdn.com/202609221542/548550de4707f62d32176808dc32d171/notes_pre_post/1040g3k03256alkkpke0g4asih3ta8gib9fokee0!nc_n_webp_mw_1",
    "xhs-li-i8-three-questions": "https://sns-webpic-qc.xhscdn.com/202609221543/7b76e2e39028425272ca563a7153fc54/1040g0083255m0rqe4q0048hpcgt3ko4hctuhi48!nc_n_webp_mw_1",
    "xhs-li-i9-highway-range": "https://sns-webpic-qc.xhscdn.com/202609221538/3dba192057d64dcfa86f846261edd1b0/1040g0083257egamd46e05qkeddlku9017ukpbto!nc_n_webp_mw_1",
    "xhs-xpeng-g9l-adas-test": "https://sns-webpic-qc.xhscdn.com/202609221537/ce93ece848f9214a9156907e09fbe0db/1040g008325a15dq7k4005o83mibg86itaf15uk8!nc_n_webp_mw_1",
    "xhs-xpeng-g9l-config-guide": "https://sns-webpic-qc.xhscdn.com/202609221533/c75d052e0329e494af3654cf197ec636/1040g2sg3258q5m8cke2g5oq8p2lmbi2fbge9mlo!nc_n_webp_mw_1",
    "xhs-mi-n90-consumption": "https://sns-webpic-qc.xhscdn.com/202609221538/32703f4b1b34e1f0a202f2d22a14e4c1/notes_pre_post/1040g3k83253a3mcpjo405ob1aaegkp8dpol2pfo!nc_n_webp_mw_1",
}


BRAND_TERMS = ["理想", "小鹏", "蔚来", "小米", "雷克萨斯", "保时捷", "大众", "特斯拉", "奔驰", "劳斯莱斯", "问界", "哪吒", "高合"]
MODEL_TERMS = ["i9", "i8", "i6", "G9L", "ES8", "ES6", "ET5T", "N90", "718", "ID. AURA T6", "L9", "G63", "LX700h", "库里南", "揽胜"]


def age_minutes(raw: str) -> int:
    if "小时" in raw:
        match = re.search(r"(\d+)小时", raw)
        return (int(match.group(1)) if match else 1) * 60
    if "昨天" in raw or "1天前" in raw:
        return 1440
    match = re.search(r"(\d+)天前", raw)
    return int(match.group(1)) * 1440 if match else 10080


def make_item(record: tuple) -> dict:
    note_id, title, author, date, likes, saves, comments, cover, url, content_format = record
    total = likes + saves + comments
    haystack = f"{title} {author}"
    brands = [term + ("汽车" if term in {"理想", "小鹏", "蔚来", "小米", "大众"} else "") for term in BRAND_TERMS if term in haystack]
    models = [term for term in MODEL_TERMS if term.lower() in haystack.lower()]
    hot = min(99, round(72 + math.log10(max(total, 300) / 300 + 1) * 18))
    engagement = f"{likes:,}赞 · {saves:,}藏 · {comments:,}评"
    return {
        "id": f"xhs-{note_id}",
        "type": "case",
        "platform": "小红书",
        "category": ["爆款 Case", "近7日高互动"],
        "hot": hot,
        "create": max(76, hot - 1),
        "time": age_minutes(date),
        "timeText": "24小时优先 · 不足回溯近7日",
        "eventDate": date,
        "status": "公开详情已核验",
        "author": author,
        "engagement": engagement,
        "brands": brands or ["汽车行业"],
        "models": models,
        "title": f"小红书爆款｜{title}",
        "summary": f"{author}发布的{content_format}案例，详情页可见互动合计 {total:,}，核心主题为“{title}”。",
        "keyFact": engagement,
        "why": f"公开详情页可见互动达到 {total:,}，超过当前小红书高热门槛 300。",
        "points": [f"发布时间：{date}", f"互动量：{engagement}", f"内容形态：{content_format}"],
        "angles": [f"围绕“{title}”提炼事实型选题", "结合高赞评论继续拆解用户争议点"],
        "sources": [{"name": f"小红书｜{author} 原笔记", "publishedAt": date, "url": url}],
        "contentFormat": content_format,
        "cover": cover,
        "coverAlt": title,
        "coverStatus": "已采集",
        "collectedDate": "2026-09-22",
    }


def main() -> None:
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    items = data["items"]

    for item in items:
        cover = EXISTING_COVERS.get(item.get("id"))
        if cover:
            item["cover"] = cover
            item["coverStatus"] = "已采集"
            item["collectedDate"] = "2026-09-22"

    existing_ids = {item.get("id") for item in items}
    for record in RECORDS:
        item = make_item(record)
        if item["id"] not in existing_ids:
            items.append(item)
            existing_ids.add(item["id"])

    data["generatedAt"] = "2026-09-22T15:45:00+08:00"
    data["nextUpdate"] = "2026-09-23T09:00:00+08:00"
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    xhs = [item for item in items if item.get("type") == "case" and item.get("platform") == "小红书"]
    print(f"Imported {len(RECORDS)} new records; Xiaohongshu total: {len(xhs)}")


if __name__ == "__main__":
    main()
