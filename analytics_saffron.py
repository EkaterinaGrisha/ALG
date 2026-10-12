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
# (+ «сафриан» из транслита s-a-f-r-i-a-n). Ищется в строке, склеенной целиком,
# поэтому ловит и буквы через пробел/дефис/цифры, и любые окончания.
TARGET = re.compile(r'[шщс]афри[йи]?[ая]н')
# Обычное написание «шафран» — только внутри одного слова: при склейке через
# пробел оно возникает случайно («ваша франшиза» → «вашафраншиза»).
TARGET_WORD = re.compile(r'[шщс]афран')

HOMOGLYPH_TABLE = str.maketrans(HOMOGLYPH)
LEET_TABLE = str.maketrans(LEET)
TRANSLIT_RE = re.compile('|'.join(sorted(TRANSLIT, key=len, reverse=True)))
HAS_LATIN = re.compile(r'[a-z]')
HAS_LEET = re.compile('[' + re.escape(''.join(LEET)) + ']')
NOT_LETTER = re.compile(r'[^a-zа-яёії]')
NOT_CYR = re.compile(r'[^а-яё]')
REPEATS = re.compile(r'(.)\1+')


def translit(s):
    return TRANSLIT_RE.sub(lambda m: TRANSLIT[m.group()], s)


def normalize(s):
    # s — уже только буквы (латиница и кириллица). Два прочтения латиницы:
    # «по виду» (p → р) и «по звучанию» (sh → ш). Потом оставляем только
    # кириллицу и схлопываем повторы («шаааафриан» → «шафриан»).
    out = [s.translate(HOMOGLYPH_TABLE)]
    if HAS_LATIN.search(s):
        out.append(translit(s))
    return [REPEATS.sub(r'\1', NOT_CYR.sub('', v)) for v in out]


def bases(text):
    # текст как есть и текст с цифрами/знаками, прочитанными как буквы
    low = text.lower().replace('ё', 'е')
    res = [low]
    if HAS_LEET.search(low):
        res.append(low.translate(LEET_TABLE))
    return res


def suspicious(line):
    for b in bases(line):
        # 1) вся строка, склеенная в одно слово (разделители между буквами убраны)
        joined = normalize(NOT_LETTER.sub('', b))
        for v in joined:
            if TARGET.search(v) or TARGET.search(v[::-1]):
                return True
        # 2) «шафран» нашёлся в склейке — проверяем, что он внутри одного слова
        if any(TARGET_WORD.search(v) for v in joined):
            for word in b.split():
                for v in normalize(NOT_LETTER.sub('', word)):
                    if TARGET_WORD.search(v):
                        return True
    # 3) акростих из заглавных букв: «ШАрообразный ФРИтюр АНалитика»
    caps = ''.join(ch for ch in line if ch.isupper())
    if len(caps) >= 3:
        for v in normalize(NOT_LETTER.sub('', caps.lower())):
            if TARGET.search(v):
                return True
    return False


def read_lines_until_eof_with_input():
    lines = []
    while True:
        try:
            line = input()
            lines.append(line)
        except EOFError:
            break
    return lines


def main():
    lines = read_lines_until_eof_with_input()
    res = [str(i + 1) for i, line in enumerate(lines) if suspicious(line)]
    sys.stdout.write("\n".join(res) + ("\n" if res else ""))


if __name__ == "__main__":
    main()
