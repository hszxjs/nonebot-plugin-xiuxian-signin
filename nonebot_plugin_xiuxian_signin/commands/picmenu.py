"""PicMenu 菜单数据与底部提示（R-18）。

PICMENU_NEXT_FUNCS 同时用于插件元数据的 funcs/menu_data，command_hint 负责
把分组名翻成「可发送：…」的 footer 文案。纯数据 + 纯函数。"""
from __future__ import annotations

from ..mystic_menu import MYSTIC_PICMENU_ENTRY


PICMENU_NEXT_FUNCS = [
    {
        'func': '入门与状态',
        'trigger_method': '签到 / 面板 / 新手教程 / 帮助',
        'trigger_condition': '首次签到会抽取灵根；每天签到获得修为和 1 次垂钓',
        'brief_des': '开始修炼，查看个人境界、灵根、资源和新手说明',
        'detail_des': '`签到` 获得每日修为和灵河垂钓次数；`面板` 查看境界、灵根、修为、灵石和当前装备；私聊 `新手教程` 打开入门引导；`帮助` 查看完整说明。',
    },
    {
        'func': '历练面板',
        'trigger_method': '历练 / 历练面板 / 战力 / 灵器 / 功法 / 阵盘 / 神通',
        'trigger_condition': '签到入门后可查看；灵器、功法、阵盘、符箓和神通会影响战力',
        'brief_des': '汇总战力、装备槽位、功法阵盘、符箓、神通和常用历练入口',
        'detail_des': '`历练` 或 `历练面板` 会输出专用图片面板，集中展示主手、副手、护甲、本命灵器、功法、阵盘、傀儡、符箓、仙源、境界品相、神通与常用装备指令；`战力` 查看文字版战力计算。',
    },
    {
        'func': '背包与图鉴',
        'trigger_method': '背包 / 图鉴 / 神通 / 神通图鉴 / 灵器图鉴 / 功法图鉴 / 唯一装备图鉴',
        'trigger_condition': '图鉴无需拥有物品；背包编号以当前面板为准',
        'brief_des': '查看物品、用途、获取途径和已领悟神通',
        'detail_des': '`背包` 管理丹药、符箓、灵石、妖丹、灵食、奇物和材料；`图鉴 名称` 查询用途和故事；`神通` 查看传承材料；`神通图鉴` 查看可领悟路线。',
    },
    {
        'func': '修为与突破',
        'trigger_method': '突破 / 炼化灵液 / 炼化妖丹 1 / 后天灵根 / 散功',
        'trigger_condition': '境界圆满后进入瓶颈，需要对应突破道具',
        'brief_des': '处理瓶颈、灵液、妖丹和五行补全',
        'detail_des': '瓶颈后多余修为会凝成精纯灵液；`炼化灵液` 转回修为；`炼化妖丹 编号` 获得修为；化神破炼虚需要五行补全，可用 `后天灵根` 查看丹灵根和器灵根。',
    },
    {
        'func': '灵器与战力',
        'trigger_method': '灵器 / 装备灵器 1 主手 / 卸下灵器 / 祭炼本命灵器 1 / 战力',
        'trigger_condition': '灵器按境界绑定；同境界内凡品到天阶均可存在',
        'brief_des': '管理主手、副手、护甲、本命灵器和战力榜',
        'detail_des': '低境界只能装备本境界能驾驭的灵器；假仙后可获得仙器；仙帝兵和其他唯一装备归入唯一装备体系。发送 `战力` 查看当前计算。',
    },
    {
        'func': '功法与阵盘',
        'trigger_method': '功法 / 学习功法 1 / 参悟功法 1 / 阵盘 / 布置阵盘 1 / 阵法推演 1',
        'trigger_condition': '重复获得同名功法或阵盘会转为推演成长',
        'brief_des': '提升签到收益、技能倍率、阵法倍率和熟练度上限',
        'detail_des': '功法唯一存在，重复获得会推演升层；阵盘可升品升阶，熟练度继承。仙阶极品后可以继续无限推演。',
    },
    {
        'func': '炼丹炼器与符箓',
        'trigger_method': '炼丹 / 炼丹 筑基丹 / 炼器 / 炼器图鉴 / 绘制符箓 1',
        'trigger_condition': '炼丹师、炼器师等路线会开放对应制作能力',
        'brief_des': '制作丹药、灵器、阵盘、傀儡和符箓',
        'detail_des': '材料品阶和品质会影响成品；`炼器图鉴` 查看配方；`绘制符箓` 可制作普通符箓和突破符令。',
    },
    dict(MYSTIC_PICMENU_ENTRY),
    {
        'func': '御兽秘境',
        'trigger_method': '御兽秘境开局 PVE / 御兽秘境开局 PVP / 加入御兽秘境 / 御兽秘境图鉴',
        'trigger_condition': '群聊开局，私聊在任务堂招募随从；PVP/PVE均需4人，单人1V2在私聊开启',
        'brief_des': '类酒馆战棋的4人排位斗兽、4V4秘境演武与单人1V2试炼',
        'detail_des': '新版秘境固定地图按骰子前进，普通战斗在私聊中进行，Boss 以队伍人数分段并支持续战投票；战斗失败后可发布秘境救援。',
    },
    {
        'func': '路线与身份',
        'trigger_method': '修炼路线 / 选择路线 剑修 / 选择身份 天机阁弟子 / 双修 @群友',
        'trigger_condition': '主路线同一时间只能选择一种；身份有境界和签到天数门槛',
        'brief_des': '选择剑修、术修、炼丹师、炼器师、阵法师和身份令牌',
        'detail_des': '新版秘境固定地图按骰子前进，普通战斗在私聊中进行，Boss 以队伍人数分段并支持续战投票；战斗失败后可发布秘境救援。',
    },
    {
        'func': '交易与商店',
        'trigger_method': '商店 / 购买 1 / 出售 丹药 1 / 批量出售 杂物 20 / 批量出售低阶灵器 / 万宝楼 / 交易 @对方 灵器 1 100',
        'trigger_condition': '交易、万宝楼和排行榜主要在群聊使用',
        'brief_des': '购买、出售、公开寄售和玩家间交易',
        'detail_des': '`商店` 每日刷新；`批量出售低阶灵器` 会出售背包中低于自身境界的非唯一灵器，不影响已装备灵器；`万宝楼挂售 类别 编号` 公开寄售；`交易 @对方 类别 编号 价格` 指定交易；唯一装备不会被批量出售。',
    },
    {
        'func': '休闲与排行',
        'trigger_method': '斗地主 / 斗地主帮助 / 排行 / 战力榜',
        'trigger_condition': '休闲玩法不影响主线修炼；斗地主需群聊',
        'brief_des': '斗地主、修为榜、战力榜和每日话痨榜',
        'detail_des': '`斗地主帮助` 查看牌局规则；`排行`、`战力榜` 查看群内排名。',
    },
    {
        'func': '后台管理',
        'trigger_method': '浏览器访问 /xiuxian-admin',
        'trigger_condition': '服主需要在 NoneBot 后端启用管理页，可配置管理 Token',
        'brief_des': '查看和修改玩家档案、物品属性、灵器规则、秘境掉落配置',
        'detail_des': '新版秘境固定地图按骰子前进，普通战斗在私聊中进行，Boss 以队伍人数分段并支持续战投票；战斗失败后可发布秘境救援。',
    },
]


def command_hint(func: str) -> str:
    """根据功能分类名，返回底部命令提示文案。

    从 PICMENU_NEXT_FUNCS 中查找对应分组的 trigger_method，统一加上“可发送：”
    前缀，供查看类面板的 footer 使用，让玩家知道下一步可以发什么命令。
    """
    for entry in PICMENU_NEXT_FUNCS:
        if entry.get("func") == func:
            method = str(entry.get("trigger_method") or "").strip()
            if method:
                return f"可发送：{method}"
            break
    return ""
