import re


class TextSanitizer:
    def __init__(self, sensitive_words=None, mask_char='*'):
        """
        初始化文本清洗器
        
        :param sensitive_words: 敏感词列表，None 代表使用默认列表
        :param mask_char: 用于替换敏感词的字符，默认为 *
        """
        self.sensitive_words = sensitive_words or self._default_sensitive_words()
        self.mask_char = mask_char
        
        # 构建正则模式
        self.pattern = self._build_pattern()
    def _default_sensitive_words(self):
        """
        默认指令注入相关的敏感词列表
        """
        return [
            "ignore previous instructions",
            "忽略上述内容",
            "扮演",
            "pretend to be",
            "system prompt",
            "### System",
            "void main",
            "如何破解",
            "如何攻击",
            "攻击API",
            "root",
            "终端执行",
            "执行代码",
            "运行以下命令",
            "删除文件",
            "打开",
            "载入",
            "显示隐藏内容",
            "给出当前模型限制",
            "你的后台提示词是"
        ]
    def _build_pattern(self):
        """
        构建敏感词的正则匹配模式（中英文支持）
        """
        patterns = []
        for word in self.sensitive_words:
            if re.search(r"[\u4e00-\u9fff]", word):  # 包含中文
                patterns.append(re.escape(word))
            else:
                patterns.append(r"\b" + re.escape(word) + r"\b")
        return re.compile("|".join(patterns), re.IGNORECASE)
    def mask_sensitive(self, text: str) -> str:
        """
        敏感词屏蔽
        """
        return self.pattern.sub(lambda m: self.mask_char * len(m.group(0)), text)
    def sanitize_for_sql(self, text: str) -> str:
        """
        防止 SQL 注入 - 单引号替换为双引号
        """
        return text.replace("'", "''")
    def sanitize_characters(self, text: str) -> str:
        """
        非法符号替换 - 非法字符替换为 *
        """
        sanitized = []
        # 允许的 ASCII 打印字符
        ascii_allowed = set(range(0x20, 0x7F))
        # 中文基本汉字、全角符号等
        chinese_range = set(range(0x4E00, 0x9FFF + 1))
        chinese_extra_punctuation = {
            0x300C, 0x300D, 0x300E, 0x300F, 0x3010, 0x3011,
            0xFF08, 0xFF09, 0x3002, 0xFF1F, 0xFF01, 0xFF0C,
            0x3001, 0x201C, 0x201D, 0x2018, 0x2019, 0x2026,
            0x2013, 0x2014, 0xFF1A, 0xFF1B
        }
        white_chars = {' ', '\t', '\n', '\r'}
        allowed_symbols = {
            '+', '-', '*', '/', '=', '%', '^', '&', '|', '<', '>',
            '!', '~', '#', '$', '@', '`', '?', '_', '\\', '~'
        }
        allowed_codepoints = ascii_allowed | chinese_range | chinese_extra_punctuation
        for char in text:
            code = ord(char)
            if code in allowed_codepoints or char in white_chars or char in allowed_symbols:
                sanitized.append(char)
            else:
                sanitized.append(self.mask_char)
        return ''.join(sanitized)
    def sanitize(self, text: str) -> str:
        """
        从原始文本开始整体清洗流程
        """
        text = self.mask_sensitive(text)
        text = self.sanitize_for_sql(text)
        text = self.sanitize_characters(text)
        return text

sanitizer = TextSanitizer()