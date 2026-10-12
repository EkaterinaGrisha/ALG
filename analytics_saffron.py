import codecs
import re
import sys
import unicodedata

# Латинские буквы и символы, похожие на кириллические (подмена «по виду»)
HOMOGLYPH = {
    'a': 'а', 'b': 'в', 'c': 'с', 'e': 'е', 'h': 'н', 'k': 'к', 'm': 'м',
    'o': 'о', 'p': 'р', 't': 'т', 'x': 'х', 'y': 'у', 'w': 'ш', 'u': 'и',
    'n': 'п', 'r': 'г', 'i': 'и', 'f': 'ф',
    'і': 'и', 'ї': 'и',  # украинские i
}

# Греческие и прочие буквы-двойники кириллицы (применяются до всего остального)
CONFUSABLE = {
    'α': 'а', 'ɑ': 'а', 'ρ': 'р', 'ϱ': 'р', 'φ': 'ф', 'ϕ': 'ф', 'ɸ': 'ф',
    'ι': 'и', 'η': 'н', 'ο': 'о', 'ε': 'е', 'κ': 'к', 'τ': 'т', 'χ': 'х',
    'μ': 'м', 'β': 'в', 'ν': 'и', 'ω': 'ш', 'ɯ': 'ш', 'ʜ': 'н', 'ᴎ': 'и',
    # заглавные — в заглавные, чтобы не терялся акростих
    'Α': 'А', 'Ρ': 'Р', 'Φ': 'Ф', 'Ι': 'И', 'Η': 'Н', 'Ο': 'О', 'Ε': 'Е',
    'Κ': 'К', 'Τ': 'Т', 'Χ': 'Х', 'Μ': 'М', 'Β': 'В', 'Ω': 'Ш',
}

# Цифры и знаки вместо кириллических букв: 1 → и, 4 и @ → а, 0 → о, ...
LEET = {
    '1': 'и', '!': 'и', '|': 'и', '4': 'а', '@': 'а', '0': 'о', '3': 'з',
    '6': 'б', '7': 'т', '8': 'в', '$': 'с',
}
# ... и вместо латинских букв (sh4fr1an, $hafrian, 5hafrian)
LEET_LAT = {
    '1': 'i', '!': 'i', '|': 'i', '4': 'a', '@': 'a', '0': 'o', '3': 'e',
    '5': 's', '$': 's', '7': 't', '8': 'b',
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
# Другие схемы транслита: ch/sz/sh → ш (франц., польск.), ph → ф, y → и
TRANSLIT2 = dict(TRANSLIT)
TRANSLIT2.update({'ch': 'ш', 'sz': 'ш', 'ph': 'ф', 'y': 'и', 'ya': 'иа', 'ee': 'и'})

# Запрещённое слово после нормализации: шафриан / шафриян / шафрийан /
# шафрьян / шафрияан (+ «сафриан» из транслита s-a-f-r-i-a-n), любые окончания.
# Обычный «шафран» (разрешённая специя) сюда не попадает: после «р» обязательна
# гласная или знак из [иыйьъ].
TARGET = re.compile(r'[шщс]афр[иыйьъ]+[ая]+н')

HOMOGLYPH_TABLE = str.maketrans(HOMOGLYPH)
CONFUSABLE_TABLE = str.maketrans(CONFUSABLE)
LEET_TABLE = str.maketrans(LEET)
LEET_LAT_TABLE = str.maketrans(LEET_LAT)


def make_translit(table):
    rx = re.compile('|'.join(sorted(table, key=len, reverse=True)))
    return lambda s: rx.sub(lambda m: table[m.group()], s)


TRANSLITS = (make_translit(TRANSLIT), make_translit(TRANSLIT2))

# Все преобразования применяются сразу к большому куску текста (это работает
# на уровне C), а перевод строки '\n' везде сохраняется — по числу '\n' перед
# найденным совпадением восстанавливается номер строки.
NOT_LETTER = re.compile(r'[^a-zа-яёії\n]')       # буквы + границы строк
NOT_CYR = re.compile(r'[^а-яё\n]')
NOT_CAPS = re.compile(r'[^A-ZА-ЯЁІЇ\n]')
REPEATS = re.compile(r'([а-яё])\1+')             # «шаааафриан» → «шафриан»
TRIPLE_I = re.compile(r'[il1|]{3}')              # III → ш
MARKS = re.compile(r'[̀-ͯ]')           # диакритика: š → s, á → a
CHUNK = 1 << 20      # текст обрабатывается кусками ~1 млн символов по границе строк


def readings(s):
    # прочтения латиницы: «по виду» (p → р) и «по звучанию» (sh → ш) в двух
    # схемах транслита; затем оставляем только кириллицу и схлопываем повторы
    for v in (s.translate(HOMOGLYPH_TABLE),) + tuple(tr(s) for tr in TRANSLITS):
        yield REPEATS.sub(r'\1', NOT_CYR.sub('', v))


def scan(chunk, offset, found):
    def mark(view):
        for m in TARGET.finditer(view):
            found.add(offset + view.count('\n', 0, m.start()))

    # диакритику снимаем, двойники из других алфавитов переводим в кириллицу
    text = MARKS.sub('', unicodedata.normalize('NFKD', chunk)).translate(CONFUSABLE_TABLE)
    low = text.lower().replace('ё', 'е')
    low = TRIPLE_I.sub('ш', low)
    for base in (low, low.translate(LEET_TABLE), low.translate(LEET_LAT_TABLE)):
        # каждая строка склеена в одно слово: разделители между буквами убраны
        for v in readings(NOT_LETTER.sub('', base)):
            mark(v)
    # акростих из заглавных букв: «ШАрообразный ФРИтюр АНалитика»
    caps = NOT_CAPS.sub('', text.replace('III', 'Ш')).lower()
    for v in readings(caps):
        mark(v)


# Быстрый предфильтр (необходимое условие). В найденном слове после
# нормализации «ф» и «р» стоят рядом («…фр…»). Нормализация только удаляет
# не-кириллицу и схлопывает повторы, поэтому в исходной строке между ф-подобным
# символом (ф, f, ph, φ) и р-подобным (р, p, r, ρ) могут стоять лишь
# не-кириллические символы и повторы «ф». Для акростиха нужны заглавные Ф и Р.
PRE = re.compile(r'(?:[фФfFφΦϕɸ]|[pP][hH])(?:[^а-яёА-ЯЁ\n]|[фФ])*[рРpPrRρΡϱ]')
PRE_CAPS = re.compile(r'[ФFΦ][^\n]*?[РPRΡ]')


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
