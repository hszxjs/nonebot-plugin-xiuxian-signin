"""命令文本常量表（R-18）。

所有触发词、前缀、面板文案常量集中在此，供 parsing / rules / panels 复用。
本模块只含不可变数据，不引用任何运行时对象。"""
from __future__ import annotations


SIGNIN_TEXTS = {"签到", "修仙签到", "每日签到"}
STATUS_TEXTS = {"\u6211\u7684\u4fee\u4e3a", "\u4fee\u4e3a", "\u5883\u754c", "\u7075\u6839", "\u9762\u677f", "\u4e2a\u4eba\u9762\u677f"}
# 签到日历：独立查询/翻月词组 + 补签词组（签到功能的延伸，不算新系统）
SIGNIN_CALENDAR_TEXTS = {"签到日历", "签到日历表", "日历", "我的日历"}
MAKEUP_SIGN_PREFIXES = ("补签",)
HELP_TEXTS = {"\u5e2e\u52a9", "\u4fee\u4ed9\u5e2e\u52a9", "\u6307\u4ee4", "\u8bf4\u660e", "\u73a9\u6cd5", "\u83dc\u5355"}
CATALOG_TEXTS = {
    "\u56fe\u9274",
    "\u56fe\u5f55",
    "\u5883\u754c\u56fe\u9274",
    "\u7a81\u7834\u56fe\u9274",
    "\u54c1\u76f8\u56fe\u9274",
    "\u7a81\u7834\u54c1\u76f8\u56fe\u9274",
    "\u9053\u5177\u54c1\u76f8\u56fe\u9274",
    "\u4e39\u836f\u56fe\u9274",
    "\u7b26\u7b93\u56fe\u9274",
    "\u7075\u5668\u56fe\u9274",
    "\u529f\u6cd5\u56fe\u9274",
    "\u9635\u76d8\u56fe\u9274",
    "\u6750\u6599\u56fe\u9274",
    "\u795e\u901a\u56fe\u9274",
    "\u7075\u6750\u56fe\u9274",
}
CATALOG_QUERY_PREFIXES = ("图鉴", "图录", "查看图鉴")
BREAKTHROUGH_TEXTS = {"\u7a81\u7834", "\u5883\u754c\u7a81\u7834", "\u7834\u5883", "\u67e5\u770b\u7a81\u7834", "\u7a81\u7834\u72b6\u6001", "\u6563\u529f", "\u91cd\u4fee", "\u81ea\u5e9f\u4fee\u4e3a"}
CULTIVATION_RANK_TEXTS = {"\u4fee\u4e3a\u699c", "\u7fa4\u4fee\u4e3a\u699c", "\u5883\u754c\u699c", "\u6392\u884c", "\u6392\u884c\u699c"}
POWER_RANK_TEXTS = {"战力榜", "群战力榜"}
POWER_TEXTS = {"战力", "我的战力"}
ADVENTURE_TEXTS = {"历练", "历练面板", "历练帮助"}
NEWBIE_TUTORIAL_TEXTS = {"新手教程"}
ARTIFACT_LIST_TEXTS = {"\u7075\u5668", "\u6211\u7684\u7075\u5668", "\u7075\u5668\u5217\u8868", "\u88c5\u5907\u5217\u8868"}
METHOD_LIST_TEXTS = {"功法", "我的功法", "功法列表"}
ARRAY_LIST_TEXTS = {"阵盘", "我的阵盘", "阵盘列表", "阵法", "我的阵法"}
PUPPET_LIST_TEXTS = {"傀儡", "我的傀儡", "傀儡列表"}
PLANT_LIST_TEXTS = {"灵植", "我的灵植", "灵植列表"}
ITEM_LIST_TEXTS = {"\u9053\u5177", "\u6211\u7684\u9053\u5177", "\u80cc\u5305", "\u7269\u54c1", "\u6211\u7684\u7269\u54c1", "\u5305\u88f9"}
ACQUIRED_ROOT_TEXTS = {"\u540e\u5929\u7075\u6839", "\u4e39\u7075\u6839", "\u5668\u7075\u6839", "\u70bc\u5316\u7075\u6839", "\u4e94\u884c\u8865\u5168"}
SPECIAL_ABILITY_TEXTS = {"神通", "我的神通"}
SPECIAL_ABILITY_CATALOG_TEXTS = {"神通图鉴"}
ROUTE_TEXTS = {"\u4fee\u70bc\u8def\u7ebf", "\u8def\u7ebf", "\u8eab\u4efd", "\u8eab\u4efd\u4ee4\u724c", "\u5b97\u95e8\u8eab\u4efd"}
TASK_TEXTS = {"每日任务", "任务", "我的任务", "今日任务", "接取任务", "领取任务"}
SHOP_TEXTS = {"商店", "坊市", "每日商店"}
ALCHEMY_TEXTS = {"炼丹", "丹方"}
REFINING_TEXTS = {'炼器', '炼器图鉴', '炼器帮助'}
ARRAY_DEDUCTION_TEXTS = {'阵法推演', '推演阵法'}
IMMORTAL_SEED_TEXTS = {'仙源', '我的仙源', '仙源图鉴', '仙种', '我的仙种', '仙种图鉴'}
EMPEROR_CATALOG_TEXTS = {'唯一装备图鉴'}
TALISMAN_DRAW_TEXTS = {"\u7ed8\u5236\u7b26\u7b93", "\u753b\u7b26", "\u5236\u7b26", "\u7b26\u7b93\u7ed8\u5236", "\u7ed8\u7b26"}
TIANJI_MYSTIC_TEXTS = {"天机秘境", "天机探索", "天机示警"}
UNEQUIP_TEXTS = {"卸下灵器", "卸下装备"}
EQUIP_PREFIXES = ("装备灵器", "装备")
ARTIFACT_SLOT_NAMES = ("主手", "副手", "护甲", "护盾")
TALISMAN_EQUIP_PREFIXES = ("装备符箓", "佩戴符箓", "符箓栏")
TALISMAN_UNEQUIP_TEXTS = {"卸下符箓", "卸下符箓栏"}
METHOD_EQUIP_PREFIXES = ("参悟功法", "修炼功法", "装备功法")
METHOD_DETAIL_PREFIXES = ("学习功法", "查看功法", "功法详情", "功法页面")
ARRAY_EQUIP_PREFIXES = ("布置阵盘", "装备阵盘", "布阵", "布置阵法")
PUPPET_EQUIP_PREFIXES = ("装备傀儡", "唤醒傀儡", "启用傀儡")
PLANT_EQUIP_PREFIXES = ("栽种灵植", "种植灵植", "种灵植")
PILL_USE_PREFIXES = ("使用丹药", "服用丹药", "服丹", "吃丹药")
PILL_BATCH_USE_PREFIXES = ("批量使用丹药", "批量服用丹药", "批量服丹", "一键服丹", "一键使用丹药")
TALISMAN_USE_PREFIXES = ("使用符箓", "激发符箓", "用符")
STONE_USE_PREFIXES = ("炼化灵石", "使用灵石", "吸收灵石")
STONE_BATCH_USE_PREFIXES = ("批量炼化灵石", "批量使用灵石", "批量吸收灵石", "一键炼化灵石", "一键使用灵石")
DEMON_CORE_USE_PREFIXES = ("炼化妖丹", "吸收妖丹", "使用妖丹")
DEMON_CORE_BATCH_USE_PREFIXES = ("批量炼化妖丹", "批量吸收妖丹", "一键炼化妖丹", "一键吸收妖丹")
SPIRIT_LIQUID_USE_PREFIXES = ("炼化灵液", "炼化精纯灵液", "吸收灵液", "吸收精纯灵液", "使用灵液", "使用精纯灵液")
FOOD_USE_PREFIXES = ("使用灵食", "食用灵食", "吃灵食")
FOOD_BATCH_USE_PREFIXES = ("批量使用灵食", "批量食用灵食", "批量吃灵食", "一键吃灵食", "一键使用灵食")
BATCH_USE_ALL_WORDS = {"全部", "全", "all", "ALL", "All"}
CURIO_USE_PREFIXES = ("使用奇物", "催动奇物", "参悟奇物")
MISC_USE_PREFIXES = ("鉴定杂物", "鉴定")
DAN_ROOT_PREFIXES = ("\u70bc\u5316\u4e39\u7075\u6839", "\u51dd\u7ec3\u4e39\u7075\u6839", "\u8865\u5168\u4e39\u7075\u6839")
ARTIFACT_ROOT_PREFIXES = ("\u70bc\u5316\u5668\u7075\u6839", "\u51dd\u7ec3\u5668\u7075\u6839", "\u8865\u5168\u5668\u7075\u6839", "\u70bc\u5668\u4e3a\u6839")
ROUTE_SELECT_PREFIXES = ("选择路线", "切换路线")
IDENTITY_SELECT_PREFIXES = ("选择身份", "加入身份", "晋升身份")
EVIL_SELECT_TEXTS = {"选择邪修", "加入邪修", "同修邪修"}
EVIL_QUIT_TEXTS = {"退出邪修", "脱离邪修"}
TASK_COMPLETE_PREFIXES = ("完成任务", "提交任务")
BUY_PREFIXES = ("购买", "买入")
SELL_PREFIXES = ("出售", "卖出")
ALCHEMY_PREFIXES = ("炼丹",)
REFINING_PREFIXES = ('炼器',)
ARRAY_DEDUCTION_PREFIXES = ('阵法推演', '推演阵法')
LIFE_ARTIFACT_PREFIXES = ('祭炼本命灵器', '本命灵器', '祭炼本命')
IMMORTAL_SEED_EQUIP_PREFIXES = ('装备仙源', '纳入仙源', '装备仙种', '纳入仙种')
BATCH_SELL_PREFIXES = ('批量出售', '批量卖出', '一键出售')
LOW_REALM_ARTIFACT_BATCH_SELL_PREFIXES = ('批量出售低阶灵器', '批量卖出低阶灵器', '一键出售低阶灵器', '清理低阶灵器')
TRADE_OFFER_PREFIXES = ('交易', '出售给')
TRADE_ACCEPT_PREFIXES = ('接受交易', '购买交易')
TRADE_CANCEL_PREFIXES = ('取消交易', '撤销交易')
MARKET_TEXTS = {'万宝楼', '万宝楼列表', '万宝阁', '寄售列表'}
MARKET_OFFER_PREFIXES = ('万宝楼挂售', '万宝楼寄售', '挂售', '寄售')
MARKET_BUY_PREFIXES = ('万宝楼购买', '万宝楼买入', '购买万宝楼')
MARKET_CANCEL_PREFIXES = ('万宝楼下架', '下架寄售', '下架')
RESCUE_REQUEST_PREFIXES = ('秘境救援', '发起救援')
RESCUE_TAKE_PREFIXES = ('救援', '接受救援')
TALISMAN_DRAW_PREFIXES = ("\u7ed8\u5236\u7b26\u7b93", "\u753b\u7b26", "\u5236\u7b26", "\u7ed8\u7b26")
SPECIAL_ABILITY_LEARN_PREFIXES = ("\u9886\u609f\u795e\u901a", "\u53c2\u609f\u795e\u901a")
DUEL_PREFIXES = ("pk", "PK", "切磋", "挑战")
NORMAL_DUEL_TEXTS = {"申请普通斗法", "普通斗法", "普通斗法申请", "申请斗法", "斗法匹配"}
FISHING_TEXTS = ("\u5782\u9493", "\u9493\u9c7c", "\u8bf8\u5929\u4e07\u754c\u5782\u9493")
COMMAND_PREFIX_CHARS = "/!！.。"
PENDING_FISHING_TTL = 120
NORMAL_DUEL_PREPARE_SECONDS = 60
NORMAL_DUEL_DURATION_SECONDS = 60
NORMAL_DUEL_ACTION_SEGMENT_LABELS = {
    "face": "\u8868\u60c5\u672f\u5f0f",
    "mface": "\u6536\u85cf\u8868\u60c5\u672f\u5f0f",
    "image": "\u5f71\u50cf\u672f\u5f0f",
    "record": "\u97f3\u6d6a\u672f\u5f0f",
    "video": "\u955c\u5f71\u672f\u5f0f",
    "dice": "\u9ab0\u7075\u672f\u5f0f",
    "rps": "\u62f3\u4ee4\u672f\u5f0f",
    "poke": "\u6307\u52b2\u672f\u5f0f",
    "share": "\u501f\u52bf\u672f\u5f0f",
    "json": "\u5f02\u6587\u672f\u5f0f",
    "xml": "\u5f02\u6587\u672f\u5f0f",
}
NORMAL_DUEL_IGNORED_SEGMENT_TYPES = {"at", "reply", "node"}
RANK_SETTLE_HOUR = 22
RANK_SETTLE_MINUTE = 0
