import re
from dataclasses import dataclass, field


@dataclass
class DesensitizeContext:
    """Holds mapping of real values to placeholders for reversible desensitization."""
    customer_map: dict[str, str] = field(default_factory=dict)
    person_map: dict[str, str] = field(default_factory=dict)
    _customer_counter: int = 0
    _person_counter: int = 0

    def _customer_placeholder(self, name: str) -> str:
        if name not in self.customer_map:
            self._customer_counter += 1
            self.customer_map[name] = f"[客户{chr(64 + self._customer_counter)}]"
        return self.customer_map[name]

    def _person_placeholder(self, name: str) -> str:
        if name not in self.person_map:
            self._person_counter += 1
            self.person_map[name] = f"[联系人{self._person_counter}]"
        return self.person_map[name]

    def desensitize(self, text: str, customer_names: list[str], person_names: list[str]) -> str:
        result = text
        for name in sorted(customer_names, key=len, reverse=True):
            if name:
                result = result.replace(name, self._customer_placeholder(name))
        for name in sorted(person_names, key=len, reverse=True):
            if name:
                result = result.replace(name, self._person_placeholder(name))
        result = _mask_phones(result)
        result = _fuzz_amounts(result)
        result = _strip_detailed_address(result)
        return result

    def restore(self, text: str) -> str:
        result = text
        for real, placeholder in self.customer_map.items():
            result = result.replace(placeholder, real)
        for real, placeholder in self.person_map.items():
            result = result.replace(placeholder, real)
        return result


_PHONE_RE = re.compile(r"(\d{3})\d{4}(\d{4})")
_AMOUNT_RE = re.compile(r"[¥￥]\s?(\d[\d,]*\.?\d*)\s*万?元?")
_AMOUNT_RAW_RE = re.compile(r"(\d{4,})")  # standalone large numbers


def _mask_phones(text: str) -> str:
    return _PHONE_RE.sub(r"\1****\2", text)


def _fuzz_amounts(text: str) -> str:
    def _replace(m: re.Match) -> str:
        raw = m.group(1).replace(",", "")
        try:
            val = float(raw)
        except ValueError:
            return m.group(0)
        if val >= 10000:
            return f"约{round(val / 10000)}万元"
        if val >= 1000:
            return f"约{round(val / 1000)}千元"
        return m.group(0)
    return _AMOUNT_RE.sub(_replace, text)


def _strip_detailed_address(text: str) -> str:
    # Keep province/city, strip street-level detail
    addr_re = re.compile(r"([一-龥]{2,4}[省市区县][一-龥]{2,6}[市区县]?)[一-龥\d\-A-Za-z号栋楼室]{4,}")
    return addr_re.sub(r"\1", text)
