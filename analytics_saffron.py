import codecs
import re
import sys

# Латинские буквы и символы, похожие на кириллические (подмена «по виду»)
HOMOGLYPH = {
    'a': 'а', 'b': 'в', 'c': 'с', 'e': 'е', 'h': 'н', 'k': 'к', 'm': 'м',
    'o': 'о', 'p': 'р', 't': 'т', 'x': 'х', 'y': 'у', 'w': 'ш', 'u': 'и',
    'n': 'п', 'r': 'г', 'i': 'и', 'f': 'ф',
    'і': 'и', 'ї': 'и',  # украинские i
}

# Цифры и знаки вместо букв (leet): 1 → и, 4 и @ → а, 0 → о, ...
LEET = {
    '1': 'и', '!': 'и', '|': 'и', '4': 'а', '@': 'а', '0': 'о', '3': 'з',
    '6': 'б', '7': 'т', '8': 'в', '$': 'с',
}

# Транслитерация (подмена «по звучанию»): shafriyan → шафриян
TRANSLIT = {
    'shch': 'щ', 'sch': 'щ', 'sh': 'ш', 'ch': 'ч', 'zh': 'ж', 'kh': 'х',
    'ts': 'ц', 'ya': 'я', 'ia': 'иа', 'yu': 'ю', 'yo': 'ё', 'ye': 'е',
    'a': 'а', 'b': 'б', 'c': 'к', 'd': 'д', 'e': 'е', 'f': 'ф', 'g': 'г',
    'h': 'х', 'i': 'и', 'j': 'й', 'k': 'к', 'l': 'л', 'm': 'м', 'n': 'н',
    'o': 'о', 'p': 'п', 'q': 'к', 'r': 'р', 's': 'с', 't': 'т', 'u': 'у',
    'v': 'в', 'w': 'ш', 'x': 'кс', 'y': 'й', 'z': 'з',
}

# Запрещённое слово после нормализации: шафриан / шафриян / шафрийан
# (+ «сафриан» из транслита s-a-f-r-i-a-n). Ищем только способы обхода из
# открытого реестра: обычный «шафран» (разрешённая специя) и слово задом
# наперёд к ним не относятся — каждое лишнее срабатывание стоит балл.
TARGET = re.compile(r'[шщс]афри[йи]?[ая]н')

HOMOGLYPH_TABLE = str.maketrans(HOMOGLYPH)
LEET_TABLE = str.maketrans(LEET)
TRANSLIT_RE = re.compile('|'.join(sorted(TRANSLIT, key=len, reverse=True)))

# Все преобразования применяются сразу к большому куску текста (это работает
# на уровне C), а перевод строки '\n' везде сохраняется — по числу '\n' перед
# найденным совпадением восстанавливается номер строки.
NOT_LETTER = re.compile(r'[^a-zа-яёії\n]')       # буквы + границы строк
NOT_CYR = re.compile(r'[^а-яё\n]')
NOT_CAPS = re.compile(r'[^A-ZА-ЯЁІЇ\n]')
REPEATS = re.compile(r'([а-яё])\1+')             # «шаааафриан» → «шафриан»
CHUNK = 1 << 20      # текст обрабатывается кусками ~1 млн символов по границе строк


def translit(s):
    return TRANSLIT_RE.sub(lambda m: TRANSLIT[m.group()], s)


def readings(s, not_cyr):
    # два прочтения латиницы: «по виду» (p → р) и «по звучанию» (sh → ш);
    # затем оставляем только кириллицу и схлопываем повторы букв
    for v in (s.translate(HOMOGLYPH_TABLE), translit(s)):
        yield REPEATS.sub(r'\1', not_cyr.sub('', v))


def scan(chunk, offset, found):
    def mark(view, patterns):
        for pat in patterns:
            for m in pat.finditer(view):
                found.add(offset + view.count('\n', 0, m.start()))

    low = chunk.lower().replace('ё', 'е')
    for base in (low, low.translate(LEET_TABLE)):   # как есть и цифры → буквы
        # 1) каждая строка склеена в одно слово: разделители между буквами убраны
        for v in readings(NOT_LETTER.sub('', base), NOT_CYR):
            mark(v, (TARGET,))
    # 2) акростих из заглавных букв: «ШАрообразный ФРИтюр АНалитика»
    caps = NOT_CAPS.sub('', chunk).lower()
    for v in readings(caps, NOT_CYR):
        mark(v, (TARGET,))


# Быстрый предфильтр (необходимое условие). В найденном слове после
# нормализации «ф» и «р» стоят рядом («…фри…»). Нормализация только удаляет
# не-кириллицу и схлопывает повторы, поэтому в исходной строке между ф/f и
# р/p/r могут стоять лишь не-кириллические символы и повторы «ф».
# Для акростиха нужны заглавные Ф/F и Р/P/R.
# (регистр задан явно: без re.I регулярное выражение работает быстрее)
PRE = re.compile(r'[фФfF](?:[^а-яёА-ЯЁ\n]|[фФ])*[рРpPrR]')
PRE_CAPS = re.compile(r'[ФF][^\n]*?[РPR]')


def scan_all(text, found, index=None):
    offset = 0               # сколько строк было в предыдущих кусках
    pos = 0
    n = len(text)
    while pos < n:
        end = n
        if n - pos > CHUNK:
            nl = text.find('\n', pos + CHUNK)
            if nl >= 0:
                end = nl + 1
        chunk = text[pos:end]
        local = set()
        scan(chunk, offset, local)
        found.update(local if index is None else (index[k] for k in local))
        offset += chunk.count('\n')
        pos = end


def read_blocks(size=1 << 22):
    # Ввод читается блоками и декодируется по частям, чтобы память не зависела
    # от размера датасета. Каждый блок состоит из целых строк. Строки делятся
    # только по '\n' — ровно как у input() ('\r' остаётся внутри строки).
    dec = codecs.getincrementaldecoder('utf-8')(errors='replace')
    rest = ''
    while True:
        b = sys.stdin.buffer.read(size)
        if not b:
            yield rest + dec.decode(b'', True)
            return
        s = rest + dec.decode(b)
        cut = s.rfind('\n')
        if cut < 0:
            rest = s
            continue
        yield s[:cut + 1]
        rest = s[cut + 1:]


def main():
    # строки-кандидаты, прошедшие предфильтр, и их номера (с нуля)
    index, cand = [], []
    base = 0                                 # строк в предыдущих блоках
    for text in read_blocks():
        starts = set()
        for pat in (PRE, PRE_CAPS):
            for m in pat.finditer(text):
                starts.add(text.rfind('\n', 0, m.start()) + 1)
        line_no, prev = base, 0
        for s in sorted(starts):
            line_no += text.count('\n', prev, s)
            prev = s
            e = text.find('\n', s)
            index.append(line_no)
            cand.append(text[s:] if e < 0 else text[s:e])
        base += text.count('\n')

    found = set()
    scan_all('\n'.join(cand), found, index)
    res = sorted(i + 1 for i in found)
    sys.stdout.write("\n".join(map(str, res)) + ("\n" if res else ""))


if __name__ == "__main__":
    main()
