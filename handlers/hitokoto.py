import aiohttp

from aiogram import Router, types
from aiogram.filters import Command

router = Router()

# 一言API分类映射
CATEGORY_MAP = {
    "动画": "a",
    "动漫": "a",
    "漫画": "a",
    "文学": "d",
    "影视": "h",
    "诗词": "i",
    "网易": "j",
    "哲学": "k",
    "抖机灵": "l",
}


@router.message(Command("hitokoto"))
async def cmd_hitokoto(message: types.Message):
    """一言"""
    parts = (message.text or "").split()

    url = "https://v1.hitokoto.cn/?c=a&c=b&c=d&c=h&c=i&c=j&c=k&c=l"

    if len(parts) > 1:
        category = parts[1]
        cat_code = CATEGORY_MAP.get(category)
        if cat_code:
            url = f"https://v1.hitokoto.cn/?c={cat_code}"
        else:
            cats = "、".join(CATEGORY_MAP.keys())
            await message.reply(f"未知分类「{category}」\n可用分类：{cats}")
            return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    await message.reply("❌ 获取一言失败，请稍后再试")
                    return
                data = await resp.json()

        text = data.get("hitokoto", "没有获取到内容")
        source = data.get("from", "")
        creator = data.get("from_who", "")

        result = f"📝 {text}"
        if source:
            result += f"\n\n—— 「{source}」"
        if creator:
            result += f" {creator}"

        type_map = {
            "a": "动画", "b": "漫画", "d": "文学",
            "h": "影视", "i": "诗词", "j": "网易",
            "k": "哲学", "l": "抖机灵",
        }
        cat_name = type_map.get(data.get("type", ""), "其他")
        result += f"\n📂 分类：{cat_name}"

        await message.reply(result)

    except Exception as e:
        await message.reply(f"❌ 获取一言失败：{e}")