# sakufumo.py  —— token级混合文本引擎 + 数字朗读 + 完整罗马音表 + 分块修复
import ctypes
import os
import sys
import re
import io
import wave as wv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# 1. 映射表
def load_mapping(tsv_path):
    m = {}
    with open(tsv_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or '\t' not in line:
                continue
            py, kana = line.split('\t', 1)
            m[py] = kana
    return m


# 2. 罗马音→片假名
_ROMAJI_TABLE = [
    # 三字符拗音
    ("tsu", "ツ"),
    # 二字符拗音・合拗音
    ("kya", "キャ"), ("kyu", "キュ"), ("kyo", "キョ"),
    ("gya", "ギャ"), ("gyu", "ギュ"), ("gyo", "ギョ"),
    ("sha", "シャ"), ("shu", "シュ"), ("sho", "ショ"),
    ("cha", "チャ"), ("chu", "チュ"), ("cho", "チョ"),
    ("nya", "ニャ"), ("nyu", "ニュ"), ("nyo", "ニョ"),
    ("hya", "ヒャ"), ("hyu", "ヒュ"), ("hyo", "ヒョ"),
    ("bya", "ビャ"), ("byu", "ビュ"), ("byo", "ビョ"),
    ("pya", "ピャ"), ("pyu", "ピュ"), ("pyo", "ピョ"),
    ("mya", "ミャ"), ("myu", "ミュ"), ("myo", "ミョ"),
    ("rya", "リャ"), ("ryu", "リュ"), ("ryo", "リョ"),
    ("ja", "ジャ"), ("ju", "ジュ"), ("jo", "ジョ"),
    # 二字符直音（先长后短避免误匹配）
    ("shi", "シ"), ("chi", "チ"),
    ("dzu", "ヅ"), ("dzi", "ヂ"),
    # 单字符直音
    ("ka", "カ"), ("ki", "キ"), ("ku", "ク"), ("ke", "ケ"), ("ko", "コ"),
    ("sa", "サ"), ("si", "シ"), ("su", "ス"), ("se", "セ"), ("so", "ソ"),
    ("ta", "タ"), ("ti", "チ"), ("tu", "ツ"), ("te", "テ"), ("to", "ト"),
    ("na", "ナ"), ("ni", "ニ"), ("nu", "ヌ"), ("ne", "ネ"), ("no", "ノ"),
    ("ha", "ハ"), ("hi", "ヒ"), ("hu", "フ"), ("he", "ヘ"), ("ho", "ホ"),
    ("fa", "ファ"), ("fi", "フィ"), ("fu", "フ"), ("fe", "フェ"), ("fo", "フォ"),
    ("ma", "マ"), ("mi", "ミ"), ("mu", "ム"), ("me", "メ"), ("no", "ノ"),
    ("ya", "ヤ"), ("yu", "ユ"), ("yo", "ヨ"),
    ("ra", "ラ"), ("ri", "リ"), ("ru", "ル"), ("re", "レ"), ("ro", "ロ"),
    ("la", "ラ"), ("li", "リ"), ("lu", "ル"), ("le", "レ"), ("lo", "ロ"),
    ("wa", "ワ"), ("wi", "ウィ"), ("we", "ウェ"), ("wo", "ヲ"),
    ("ga", "ガ"), ("gi", "ギ"), ("gu", "グ"), ("ge", "ゲ"), ("go", "ゴ"),
    ("za", "ザ"), ("zi", "ジ"), ("zu", "ズ"), ("ze", "ゼ"), ("zo", "ゾ"),
    ("da", "ダ"), ("di", "ディ"), ("du", "ドゥ"), ("de", "デ"), ("do", "ド"),
    ("ba", "バ"), ("bi", "ビ"), ("bu", "ブ"), ("be", "ベ"), ("bo", "ボ"),
    ("pa", "パ"), ("pi", "ピ"), ("pu", "プ"), ("pe", "ペ"), ("po", "ポ"),
    ("va", "バ"), ("vi", "ビ"), ("vu", "ブ"), ("ve", "ベ"), ("vo", "ボ"),
    ("je", "ジェ"), ("she", "シェ"), ("che", "チェ"),
    # 单字符元音+拨音
    ("a", "ア"), ("i", "イ"), ("u", "ウ"), ("e", "エ"), ("o", "オ"),
    ("n", "ン"),
]


def romaji_to_katakana(text):
    """贪心最长匹配罗马音→片假名"""
    text = text.lower().strip()
    result = []
    i = 0
    while i < len(text):
        matched = False
        for roma, kana in _ROMAJI_TABLE:
            if text[i:].startswith(roma):
                result.append(kana)
                i += len(roma)
                matched = True
                break
        if not matched:
            # 无法匹配的字符（如单独辅音）用最接近的假名替代
            fallback = {
                'c': 'ク', 'x': 'クス', 'q': 'ク', 'v': 'ブ',
                'l': 'ル', 'r': 'ル', 'b': 'ブ', 'd': 'ド',
                'f': 'フ', 'g': 'グ', 'h': 'フ', 'j': 'ジ',
                'k': 'ク', 'm': 'ム', 'p': 'プ', 's': 'ス',
                't': 'ト', 'w': 'ウ', 'z': 'ズ',
            }
            ch = text[i]
            result.append(fallback.get(ch, ''))
            i += 1
    return ''.join(result)


# 3. 数字→朗读 
_DIGIT_MAP = {
    '0': 'リン', '1': 'イー', '2': 'エー', '3': 'サン', '4': 'スー',
    '5': 'ウー', '6': 'リュウ', '7': 'チー', '8': 'バー', '9': 'ジュウ',
}


def digits_to_kana(num_str):
    """逐数字朗读（不拆位数）"""
    return ''.join(_DIGIT_MAP.get(ch, ch) for ch in num_str)


# 4. Token 化引擎
def tokenize(text):
    """
    将混合文本拆成 token 流，每个 token 带类型：
      ('cjk', char)    中文字符
      ('ascii', word)  连续拉丁字母
      ('digit', digits) 连续数字
      ('kana', char)   日文假名
      ('punct', char)  标点
      ('space', char)  空白
    """
    tokens = []
    buf_ascii = []
    buf_digit = []

    def flush_ascii():
        nonlocal buf_ascii
        if buf_ascii:
            tokens.append(('ascii', ''.join(buf_ascii)))
            buf_ascii = []

    def flush_digit():
        nonlocal buf_digit
        if buf_digit:
            tokens.append(('digit', ''.join(buf_digit)))
            buf_digit = []

    for ch in text:
        if '\u4e00' <= ch <= '\u9fff' or '\u3400' <= ch <= '\u4dbf':
            flush_ascii();
            flush_digit()
            tokens.append(('cjk', ch))
        elif ch.isascii() and ch.isalpha():
            flush_digit()
            buf_ascii.append(ch)
        elif ch.isdigit():
            flush_ascii()
            buf_digit.append(ch)
        elif '\u3040' <= ch <= '\u30ff':
            flush_ascii();
            flush_digit()
            tokens.append(('kana', ch))
        elif ch.isspace():
            flush_ascii();
            flush_digit()
            tokens.append(('space', ch))
        else:
            flush_ascii();
            flush_digit()
            tokens.append(('punct', ch))

    flush_ascii();
    flush_digit()
    return tokens


# 标点映射：中文/英文 → 日文
_PUNCT_MAP = {
    '，': '、', ',': '、', '.': '。', '。': '。', '、': '、',
    '！': '！', '!': '！', '？': '？', '?': '？',
    '：': '、', ':': '、', '；': '、', ';': '、',
    '…': '、', '～': 'ー', '~': 'ー', '（': '', '）': '',
    '(': '', ')': '', '【': '', '】': '', '「': '', '」': '',
    '"': '', "'": '', '“': '', '”': '', '‘': '', '’': '',
}


def mixed_text_to_kana(text, mapping):
    """核心转换：token 流 → 片假名"""
    from pypinyin import lazy_pinyin, Style

    def mixed_text_to_kana(text, mapping):
        from pypinyin import lazy_pinyin, Style

    def norm(py):
            """归一化 ü：预合成ü(U+00FC) 或 v → u+组合分音符(U+0308)，匹配tsv"""
            py = py.replace('\u00fc', 'u\u0308')  # ü → ü
            py = re.sub(r'(?<=[ln])v$', 'u\u0308', py)  # lv/nv → lü/nü
            return py

    tokens = tokenize(text)
    result = []
    for typ, val in tokens:
        if typ == 'cjk':
            py_list = lazy_pinyin(val, style=Style.NORMAL, errors='ignore')
            for py in py_list:
                result.append(mapping.get(norm(py), norm(py)))  # ← 加 norm()
        elif typ == 'ascii':
            result.append(romaji_to_katakana(val))
        elif typ == 'digit':
            result.append(digits_to_kana(val))
        elif typ == 'kana':
            result.append(val)
        elif typ == 'punct':
            result.append(_PUNCT_MAP.get(val, ''))
        elif typ == 'space':
            pass  # 剔除空格

    kana = ''.join(result)
    # 安全过滤：只保留假名、长音符、読点、句点、！、？
    kana = re.sub(r'[^\u30a0-\u30ff\u3040-\u309f\u3001\u3002\uff01\uff1f\u30fcー]', '', kana)
    return kana


def zh_to_kana(text, mapping):
    return mixed_text_to_kana(text, mapping)


# 5. AquesTalk 封装
class AQTK_VOICE(ctypes.Structure):
    _fields_ = [
        ("bas", ctypes.c_int), ("spd", ctypes.c_int), ("vol", ctypes.c_int),
        ("pit", ctypes.c_int), ("acc", ctypes.c_int), ("lmd", ctypes.c_int),
        ("fsc", ctypes.c_int),
    ]


VOICE_PRESETS = {
    "f1": AQTK_VOICE(0, 100, 100, 100, 100, 100, 100),
    "f2": AQTK_VOICE(1, 100, 100, 77, 150, 100, 100),
    "f3": AQTK_VOICE(0, 80, 100, 100, 100, 61, 148),
    "m1": AQTK_VOICE(2, 100, 100, 30, 100, 100, 100),
    "m2": AQTK_VOICE(2, 105, 100, 45, 130, 120, 100),
    "r1": AQTK_VOICE(2, 100, 100, 30, 20, 190, 100),
    "r2": AQTK_VOICE(1, 70, 100, 50, 50, 50, 180),
}

MAX_KANA_LEN = 180  # AquesTalk10 疑似安全上限


class AquesTalk:
    def __init__(self, dll_path):
        self.dll = ctypes.CDLL(dll_path)
        self.dll.AquesTalk_Synthe_Utf8.argtypes = [
            ctypes.POINTER(AQTK_VOICE), ctypes.c_char_p, ctypes.POINTER(ctypes.c_int)
        ]
        self.dll.AquesTalk_Synthe_Utf8.restype = ctypes.c_void_p
        self.dll.AquesTalk_FreeWave.argtypes = [ctypes.c_void_p]
        self.dll.AquesTalk_FreeWave.restype = None

    def synthe_raw(self, kana, voice='f1'):
        param = VOICE_PRESETS.get(voice, VOICE_PRESETS['f1'])
        size = ctypes.c_int(0)
        wav_ptr = self.dll.AquesTalk_Synthe_Utf8(
            ctypes.byref(param), kana.encode('utf-8'), ctypes.byref(size)
        )
        if not wav_ptr or size.value <= 0:
            raise Exception(f"错误码: {size.value}")
        data = ctypes.string_at(wav_ptr, size.value)
        self.dll.AquesTalk_FreeWave(wav_ptr)
        return data

    def synthe(self, kana, voice='f1'):
        """智能合成：超长按読点「、」切分"""
        if len(kana) <= MAX_KANA_LEN:
            return self.synthe_raw(kana, voice)

        # 按読点切分
        chunks = [c for c in kana.split('、') if c]
        # 合并短 chunk
        merged = []
        buf = ''
        for chk in chunks:
            if len(buf) + len(chk) + 1 > MAX_KANA_LEN and buf:
                merged.append(buf)
                buf = chk
            else:
                buf = buf + '、' + chk if buf else chk
        if buf:
            merged.append(buf)

        print(f"[少女分块中] 文本太长力…切分为 {len(merged)} 段...")
        all_data = []
        for i, chk in enumerate(merged):
            if not chk.strip():
                continue
            print(f"  合成第 {i + 1}/{len(merged)} 段 ({len(chk)} 字)...")
            all_data.append(self.synthe_raw(chk, voice))

        return all_data[0] if len(all_data) == 1 else self._concat_wav(all_data)

    def _concat_wav(self, wav_list):
        with wv.open(io.BytesIO(wav_list[0]), 'rb') as wf:
            params = wf.getparams()
            pcm_list = [wf.readframes(wf.getnframes())]
        for data in wav_list[1:]:
            with wv.open(io.BytesIO(data), 'rb') as wf:
                pcm_list.append(wf.readframes(wf.getnframes()))
        buf = io.BytesIO()
        with wv.open(buf, 'wb') as wf:
            wf.setparams(params)
            for pcm in pcm_list:
                wf.writeframes(pcm)
        return buf.getvalue()

    def synthe_to_file(self, kana, out_path, voice='f1'):
        data = self.synthe(kana, voice)
        with open(out_path, 'wb') as f:
            f.write(data)
        return out_path


# 6. 播放
def play_wav(filepath):
    import platform
    if platform.system() == 'Windows':
        import winsound
        winsound.PlaySound(filepath, winsound.SND_FILENAME)
    else:
        os.system(f'afplay "{filepath}"' if platform.system() == 'Darwin' else f'aplay "{filepath}"')


# 7. 主流程
def main():
    tsv_path = os.path.join(BASE_DIR, 'mapping.tsv')
    dll_path = os.path.join(BASE_DIR, 'lib64', 'AquesTalk.dll')

    if not os.path.exists(tsv_path):
        print(f"[错误] 找不到 mapping.tsv: {tsv_path}");
        sys.exit(1)
    if not os.path.exists(dll_path):
        print(f"[错误] 找不到 DLL: {dll_path}");
        sys.exit(1)

    mapping = load_mapping(tsv_path)
    aques = AquesTalk(dll_path)

    print("可用声種: f1(灵梦) f2(魔理沙) f3(ゆっくり) m1 m2 r1 r2")
    print("支持：中文 / 英文(罗马音) / 日文假名 / 数字 混合输入")
    text = input("要我念什么: ").strip()
    if not text:
        text = "你好，我是一个fumo，我很可爱，请给我钱"

    voice = input("声種 (默认f1): ").strip() or 'f1'

    kana = mixed_text_to_kana(text, mapping)
    print(f"\n[空耳] {kana}")
    print(f"[长度] {len(kana)} 字")

    wav_path = os.path.join(BASE_DIR, 'output.wav')
    try:
        aques.synthe_to_file(kana, wav_path, voice)
        print(f"[合成完成力！] → output.wav ({os.path.getsize(wav_path)} bytes)")
    except Exception as e:
        print(f"[合成失败喵] {e}")
        sys.exit(1)

    print("[少女播放中...]")
    play_wav(wav_path)
    print("[完成]")


if __name__ == '__main__':
    main()
