"""测试节假日数据生成脚本：通知解析、写出排版、把新数据并进已有文件"""

import json
from pathlib import Path

import httpx
import respx

NOTICE_URL = "https://example.com/notice.html"
REPO_ROOT = Path(__file__).resolve().parents[3]

# 2027 年通知：短假写「放假，共N天」，日期后带（周X），春节带农历说明
NOTICE_2027 = """
<h1>受权发布丨国务院办公厅关于2027年部分节假日安排的通知</h1>
<p>一、元旦：1月1日（周五）至3日（周日）放假，共3天。</p>
<p>二、春节：2月5日（农历除夕、周五）至13日（农历正月初八、周六）放假调休，共9天。1月31日（周日）、2月14日（周日）上班。</p>
<p>三、清明节：4月3日（周六）至5日（周一）放假，共3天。</p>
<p>四、劳动节：5月1日（周六）至5日（周三）放假调休，共5天。5月8日（周六）上班。</p>
<p>五、端午节：6月9日（周三）放假，共1天。</p>
<p>六、中秋节：9月15日（周三）放假，共1天。</p>
<p>七、国庆节：10月1日（周五）至7日（周四）放假调休，共7天。9月26日（周日）、10月9日（周六）上班。</p>
"""

# 2024 年通知：短假写「放假，与周末连休」，调休写「（星期日）」
NOTICE_2024 = """
<h1>国务院办公厅关于2024年部分节假日安排的通知</h1>
<p>一、元旦：1月1日放假，与周末连休。</p>
<p>二、春节：2月10日至17日放假调休，共8天。2月4日（星期日）、2月18日（星期日）上班。</p>
<p>三、清明节：4月4日至6日放假调休，共3天。4月7日（星期日）上班。</p>
<p>四、劳动节：5月1日至5日放假调休，共5天。4月28日（星期日）、5月11日（星期六）上班。</p>
<p>五、端午节：6月10日放假，与周末连休。</p>
<p>六、中秋节：9月15日至17日放假调休，共3天。9月14日（星期六）上班。</p>
<p>七、国庆节：10月1日至7日放假调休，共7天。9月29日（星期日）、10月12日（星期六）上班。</p>
"""


def test_parse_holidays_2027():
    """解析 2027 年通知：一日假期按天数算，不能默认成 3 天"""
    from src.plugins.morning.plugins.morning_greeting.generate_holidays import (
        parse_holidays,
    )

    with respx.mock:
        respx.get(NOTICE_URL).mock(return_value=httpx.Response(200, text=NOTICE_2027))
        assert parse_holidays(NOTICE_URL) == {
            "2027": {
                "2027-01-01": {"name": "元旦", "duration": 3, "workdays": []},
                "2027-02-05": {
                    "name": "春节",
                    "duration": 9,
                    "workdays": ["2027-01-31", "2027-02-14"],
                },
                "2027-04-03": {"name": "清明节", "duration": 3, "workdays": []},
                "2027-05-01": {"name": "劳动节", "duration": 5, "workdays": ["2027-05-08"]},
                "2027-06-09": {"name": "端午节", "duration": 1, "workdays": []},
                "2027-09-15": {"name": "中秋节", "duration": 1, "workdays": []},
                "2027-10-01": {
                    "name": "国庆节",
                    "duration": 7,
                    "workdays": ["2027-09-26", "2027-10-09"],
                },
            }
        }


def test_parse_holidays_2024():
    """解析「与周末连休」「（星期日）」这种老写法，结果应与已发布的 2024 年数据一致"""
    from src.plugins.morning.plugins.morning_greeting.generate_holidays import (
        parse_holidays,
    )

    with respx.mock:
        respx.get(NOTICE_URL).mock(return_value=httpx.Response(200, text=NOTICE_2024))
        assert parse_holidays(NOTICE_URL) == {
            "2024": {
                # 元旦当天是周一，假期从上一个周六开始
                "2023-12-30": {"name": "元旦", "duration": 3, "workdays": []},
                "2024-02-10": {
                    "name": "春节",
                    "duration": 8,
                    "workdays": ["2024-02-04", "2024-02-18"],
                },
                "2024-04-04": {"name": "清明节", "duration": 3, "workdays": ["2024-04-07"]},
                "2024-05-01": {
                    "name": "劳动节",
                    "duration": 5,
                    "workdays": ["2024-04-28", "2024-05-11"],
                },
                "2024-06-08": {"name": "端午节", "duration": 3, "workdays": []},
                "2024-09-15": {"name": "中秋节", "duration": 3, "workdays": ["2024-09-14"]},
                "2024-10-01": {
                    "name": "国庆节",
                    "duration": 7,
                    "workdays": ["2024-09-29", "2024-10-12"],
                },
            }
        }


def test_dump_holidays_keeps_repo_style(tmp_path: Path):
    """写出的排版要和仓库里的 public/holidays.json 一字不差，更新一年数据才不会整篇重排"""
    from src.plugins.morning.plugins.morning_greeting.generate_holidays import dump_holidays

    source = REPO_ROOT / "public" / "holidays.json"
    data = json.loads(source.read_text(encoding="utf-8"))

    target = tmp_path / "holidays.json"
    dump_holidays(data, target)

    assert target.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
    assert json.loads(target.read_text(encoding="utf-8")) == data


def test_main_adds_new_year(tmp_path: Path):
    """把解析出的新一年并进已有文件，旧年份保持原样"""
    from src.plugins.morning.plugins.morning_greeting.generate_holidays import main

    data_file = tmp_path / "holidays.json"
    data_file.write_text(
        """{
  "2026": {
    "2026-01-01": {
      "name": "元旦",
      "duration": 3,
      "workdays": ["2026-01-04"]
    }
  }
}
""",
        encoding="utf-8",
    )

    with respx.mock:
        respx.get(NOTICE_URL).mock(return_value=httpx.Response(200, text=NOTICE_2027))
        main(NOTICE_URL, data_file)

    text = data_file.read_text(encoding="utf-8")
    assert text.startswith(
        """{
  "2026": {
    "2026-01-01": {
      "name": "元旦",
      "duration": 3,
      "workdays": ["2026-01-04"]
    }
  },
  "2027": {
"""
    )
    data = json.loads(text)
    assert list(data) == ["2026", "2027"]
    assert data["2027"]["2027-06-09"] == {"name": "端午节", "duration": 1, "workdays": []}
