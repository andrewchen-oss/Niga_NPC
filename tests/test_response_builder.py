"""
[INPUT]: 依赖 app.bot.response_builder
[OUTPUT]: ResponseBuilder 的单元测试
[POS]: tests 模块的回复构建器测试
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from app.bot.response_builder import ResponseBuilder


def test_no_image():
    response = ResponseBuilder.no_image()
    assert response in ResponseBuilder.NO_IMAGE


def test_face_search_success():
    links = ["http://a.com", "http://b.com", "http://c.com"]
    response = ResponseBuilder.face_search_success(links)
    assert "http://a.com" in response
    assert "http://b.com" in response
    assert "http://c.com" in response


def test_roast_success():
    roast = "这是一段吐槽内容"
    response = ResponseBuilder.roast_success(roast)
    assert response == roast


def test_no_target():
    response = ResponseBuilder.no_target()
    assert response in ResponseBuilder.NO_TARGET


def test_error():
    response = ResponseBuilder.error()
    assert response in ResponseBuilder.ERROR
