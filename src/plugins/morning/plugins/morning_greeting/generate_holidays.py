"""生成节假日信息

https://sousuo.www.gov.cn/sousuo/search.shtml?code=17da70961a7&searchWord=部分节假日安排的通知&dataTypeId=15&sign=&pageNo=1
"""

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

DATA_FILE = Path.cwd() / "public" / "holidays.json"


def parse_holidays(url: str):
    """解析中国法定节假日信息

    网址：
        https://www.gov.cn/zhengce/content/202310/content_6911527.htm

    原始数据：
        一、元旦：1月1日放假，与周末连休。

        二、春节：2月10日至17日放假调休，共8天。2月4日（星期日）、2月18日（星期日）上班。鼓励各单位结合带薪年休假等制度落实，安排职工在除夕（2月9日）休息。

        三、清明节：4月4日至6日放假调休，共3天。4月7日（星期日）上班。

        四、劳动节：5月1日至5日放假调休，共5天。4月28日（星期日）、5月11日（星期六）上班。

        五、端午节：6月10日放假，与周末连休。

        六、中秋节：9月15日至17日放假调休，共3天。9月14日（星期六）上班。

        七、国庆节：10月1日至7日放假调休，共7天。9月29日（星期日）、10月12日（星期六）上班。

    解析结果：
        "2024": {
            "2023-12-30": {
                "name": "元旦",
                "duration": 3,
                "workdays": []
            },
            "2024-02-10": {
                "name": "春节",
                "duration": 8,
                "workdays": [
                    "2024-02-04",
                    "2024-02-18"
                ]
            },
            "2024-04-04": {
                "name": "清明节",
                "duration": 3,
                "workdays": [
                    "2024-04-07"
                ]
            },
            "2024-05-01": {
                "name": "劳动节",
                "duration": 5,
                "workdays": [
                    "2024-04-28",
                    "2024-05-11"
                ]
            },
            "2024-06-08": {
                "name": "端午节",
                "duration": 3,
                "workdays": []
            },
            "2024-09-15": {
                "name": "中秋节",
                "duration": 3,
                "workdays": [
                    "2024-09-14"
                ]
            },
            "2024-10-01": {
                "name": "国庆节",
                "duration": 7,
                "workdays": [
                    "2024-09-29",
                    "2024-10-12"
                ]
            }
    """
    r = httpx.get(url)
    r.raise_for_status()

    # 获取纯文本
    soup = BeautifulSoup(r.text, "html.parser")
    rtext = soup.get_text()

    # 定义正则表达式模式
    year_pattern = re.compile(r"国务院办公厅关于(\d{4})年")
    pattern = re.compile(
        r"[一二三四五六七]、(\S+?)：(?:(\d+月\d+日)(?:（\S+?）)?(?:至\d+日(?:（\S+?）)?)?)放假(?:调休，共(\d+)天)?(?:，与周末连休)?(?:。(\d+月\d+日（周[一二三四五六日]）(?:、\d+月\d+日（周[一二三四五六日]）)?上班)?)?"
    )

    # 匹配所有节假日信息
    year_match = year_pattern.search(rtext)
    assert year_match, "未找到年份"
    matches = pattern.findall(rtext)
    assert matches, "未找到节假日信息"

    # 构建字典
    holidays = {}
    current_year = year_match.group(1)
    for match in matches:
        name, date_range, days_off, work_days = match
        start_date_str = date_range.split("至")[0]
        start_date = datetime.strptime(f"{current_year}-{start_date_str}", "%Y-%m月%d日")
        start_date_iso = start_date.isoformat()[:10]

        # 处理 与周末连休 的情况
        if "与周末连休" in rtext:
            # 如果节假日是周一，则 start_date_iso 为周六
            if start_date.weekday() == 0:
                start_date_iso = (start_date - timedelta(days=2)).isoformat()[:10]
            # 不同节假日的连休天数不同
            match name:
                case "春节":
                    duration = 8
                case "劳动节":
                    duration = 5
                case "国庆节":
                    duration = 7
                case _:
                    duration = 3
        else:
            duration = int(days_off) if days_off else 3

        holidays[start_date_iso] = {
            "name": name,
            "duration": duration,
            "workdays": [
                datetime.strptime(f"{current_year}-{day.split('（')[0]}", "%Y-%m月%d日").isoformat()[:10]
                for day in work_days.split("、")
            ]
            if work_days
            else [],
        }

    return {str(current_year): holidays}


if __name__ == "__main__":
    url = sys.argv[1]
    holidays = parse_holidays(url)
    with DATA_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    data.update(holidays)
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
