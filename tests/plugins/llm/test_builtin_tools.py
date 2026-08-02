"""测试内置业务工具"""

from datetime import date, timedelta

from nonebug import App
from pytest_mock import MockerFixture


def test_builtin_tool_schemas(app: App):
    """天气与节假日工具向模型暴露清晰且最小的参数 schema"""
    from src.plugins.llm.tools import registry

    params = {param.name: param for param in registry.to_params()}

    weather = params["query_weather"].parameters
    assert weather["required"] == ["location"]
    assert weather["properties"] == {
        "location": {
            "type": "string",
            "description": "城市、地区或艾欧泽亚地点名称",
        },
        "adm": {
            "type": "string",
            "description": "同名城市所属的上级行政区，不确定或无需区分时省略",
        },
    }

    holiday = params["query_holiday_status"].parameters
    assert holiday == {"type": "object", "properties": {}, "required": []}


async def test_query_weather_tool(app: App, mocker: MockerFixture):
    """天气工具复用现有艾欧泽亚天气查询"""
    from src.plugins.llm.schemas import ToolCall
    from src.plugins.llm.tools import registry

    mocked_time = mocker.patch("src.plugins.weather.eorzean_api.time")
    mocked_time.time.return_value = 1641619586

    result = await registry.execute(
        ToolCall(
            id="weather-1",
            name="query_weather",
            arguments={"location": "利姆萨·罗敏萨"},
        )
    )

    assert result.startswith("利姆萨·罗敏萨上层甲板\n当前天气：碧空")
    mocked_time.time.assert_called_once()


async def test_query_holiday_status_tool(app: App, mocker: MockerFixture):
    """节假日工具返回现有节假日查询结果"""
    from src.plugins.llm.schemas import ToolCall
    from src.plugins.llm.tools import registry

    today = date.today()
    get_recent_holiday = mocker.patch(
        "src.plugins.morning.plugins.morning_greeting.data_source.get_recent_holiday",
        return_value={
            "name": "测试节",
            "date": today + timedelta(days=1),
            "holiday": True,
            "after": False,
        },
    )
    get_recent_workday = mocker.patch(
        "src.plugins.morning.plugins.morning_greeting.data_source.get_recent_workday",
        return_value=None,
    )

    result = await registry.execute(
        ToolCall(
            id="holiday-1",
            name="query_holiday_status",
            arguments={},
        )
    )

    assert result == "明天就是测试节了，开不开心？"
    get_recent_holiday.assert_awaited_once_with()
    get_recent_workday.assert_awaited_once_with()
