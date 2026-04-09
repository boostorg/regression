
import sys
import string

def chr_or_question_mark( c ):
    if chr(c) in string.printable and c < 128 and c not in ( 0x09, 0x0b, 0x0c ):
        return chr(c)
    else:
        return '?'

if sys.version_info[0] >= 3:
    char_translation_table = bytes.maketrans(
          bytes(range(0, 256))
        , bytes( bytearray( chr_or_question_mark(c).encode('latin-1')[0] for c in range(0, 256) ) )
        )
else:
    char_translation_table = string.maketrans( 
          ''.join( map( chr, range(0, 256) ) )
        , ''.join( map( chr_or_question_mark, range(0, 256) ) )
        )
