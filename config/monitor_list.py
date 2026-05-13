from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config.loader import ConfigLoader


_INDEX_SYMBOLS = {
    "sh000001": ("000001.SH", "上证指数"),
    "sh000688": ("000688.SH", "科创50"),
    "sh000905": ("000905.SH", "中证500"),
    "hkhsi": ("HSI", "恒生指数"),
}

_NAME_OVERRIDES = {
    "159934": "黄金ETF",
    "512400": "有色金属ETF",
    "560390": "A500红利",
    "688981": "中芯国际",
    "002050": "三花智控",
    "01810.HK": "小米集团-W",
    "09988.HK": "阿里巴巴-W",
    "02020.HK": "安踏体育",
    "00285.HK": "比亚迪电子",
    "09880.HK": "优必选",
    "83690.HK": "美团-WR",
}

_UNSUPPORTED_PREFIX_REASONS = {
    "usr_": "当前实现未接入美股/美股指数历史数据与实时行情抓取",
    "nf_": "当前实现未接入中金所期货连续合约历史数据与实时行情抓取",
    "hf_": "当前实现未接入海外商品/CFD历史数据与实时行情抓取",
}


_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"


def _get_raw_monitor_list(config: Dict[str, Any]) -> List[str]:
    return list(config.get("notification", {}).get("feishu", {}).get("monitor_list", []))


def _parse_supported_symbol(symbol: str) -> Optional[Dict[str, str]]:
    normalized_symbol = symbol.strip().lower()
    if not normalized_symbol:
        return None

    if normalized_symbol in _INDEX_SYMBOLS:
        code, name = _INDEX_SYMBOLS[normalized_symbol]
        return {"code": code, "name": name, "type": "index"}

    if normalized_symbol.startswith(("sh", "sz")) and len(normalized_symbol) == 8:
        market = normalized_symbol[:2]
        code = normalized_symbol[2:]
        if not code.isdigit():
            return None

        if market == "sh" and code.startswith("5"):
            return {"code": code, "name": _NAME_OVERRIDES.get(code, symbol), "type": "etf"}

        if market == "sz" and code.startswith("159"):
            return {"code": code, "name": _NAME_OVERRIDES.get(code, symbol), "type": "etf"}

        if market == "sh" and code.startswith(("6", "688")):
            return {"code": code, "name": _NAME_OVERRIDES.get(code, symbol), "type": "stock"}

        if market == "sz" and code.startswith(("0", "3")):
            return {"code": code, "name": _NAME_OVERRIDES.get(code, symbol), "type": "stock"}

    if normalized_symbol.startswith("hk") and len(normalized_symbol) == 7:
        code = normalized_symbol[2:]
        if code.isdigit():
            hk_code = f"{code}.HK"
            return {"code": hk_code, "name": _NAME_OVERRIDES.get(hk_code, symbol), "type": "hk"}

    return None


def _unsupported_reason(symbol: str) -> str:
    normalized_symbol = symbol.strip().lower()
    for prefix, reason in _UNSUPPORTED_PREFIX_REASONS.items():
        if normalized_symbol.startswith(prefix):
            return reason
    return "当前实现无法识别该代码格式，未接入对应历史数据与实时行情抓取"


def load_monitor_list_from_config(config: Dict[str, Any]) -> List[Dict[str, str]]:
    monitor_list = []
    for symbol in _get_raw_monitor_list(config):
        parsed = _parse_supported_symbol(symbol)
        if parsed is not None:
            monitor_list.append(parsed)
    return monitor_list


def get_unsupported_monitor_symbols(config: Dict[str, Any]) -> List[Tuple[str, str]]:
    unsupported = []
    for symbol in _get_raw_monitor_list(config):
        if _parse_supported_symbol(symbol) is None:
            unsupported.append((symbol, _unsupported_reason(symbol)))
    return unsupported


def load_monitor_list(config_path: str = str(_DEFAULT_CONFIG_PATH)) -> List[Dict[str, str]]:
    config = ConfigLoader.load(config_path)
    return load_monitor_list_from_config(config)
