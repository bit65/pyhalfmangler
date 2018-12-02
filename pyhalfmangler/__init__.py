#!/usr/bin/python

highest_level = 0
BLOCKS_DONE = []
BLOCK_STACK = []
DEBUG = False

def print_indent(s):
	if DEBUG:
		print "\t" * len(BLOCK_STACK) + s

def is_digit(x):
	return ord('0') <= ord(x) <= ord('9')

def find_atomic(x, atomics):
	if len(atomics) == 0:
		return x[0]

	for s in atomics:
		if s == x[:len(s)]:
			return s

	return None

def append_child(x):
	global BLOCK_STACK
	global BLOCKS_DONE

	if len(BLOCK_STACK) == 0:
		BLOCKS_DONE.append(x)
	else:
		BLOCK_STACK[-1]["CHILDREN"].append(x)

def handle_block_start(x, sym):
	block = {
			"TYPE": "BLOCK",
			"VALUE": sym,
			"LEVEL": len(BLOCK_STACK),
			"CHILDREN": []
		}

	# Append to highest block child
	if len(BLOCK_STACK) != 0:
		BLOCK_STACK[-1]["CHILDREN"].append(block)

	print_indent(sym)

	BLOCK_STACK.append(block)

def handle_string(x, sym):
	global BLOCKS_DONE

	# Read string length
	length = 0
	digits = 0

	for c in x:
		if is_digit(c):
			digits += 1
		else:
			break

	length = int(x[:digits])

	string = {
			"TYPE": "SYMBOL",
			"VALUE": x[digits : digits + length]
		}

	print_indent(string["VALUE"])

	append_child(string)

	return digits + length

def handle_abbr(x, sym):
	stds = {
		"SB_": "SB_",
		"St": "std",
		"Sa": "std::allocator",
		"Sb": "std::basic_string",
		"Ss": "std::basic_string<char, std::char_traits<char>, std::allocator<char> >",
		"Si": "std::basic_istream<char, std::char_traits<char> >",
		"So": "std::basic_ostream<char, std::char_traits<char> >",
		"Sd": "std::basic_iostream<char, std::char_traits<char> >",
		"T_": "T"
		}

	if sym in stds:
		abbr = {
			"TYPE": "STATIC_ABBR",
			"VALUE": stds[sym]
			}
	else:
		stds["S_"] = "S_"

		# Add substitutions
		for j in xrange(10):
			stds["S%d_" % j] = "S%d_" % j

		abbr = {
			"TYPE": "ABBR",
			"VALUE": stds[sym]
		}

	print_indent(stds[sym])

	append_child(abbr)

def handle_podt(x, sym):
	qualifiers = {
			"P" : "*",
			"K" : "const"
		}

	types = {
			"c" : "char",
			"a" : "signed char"
		}

	length = 0
	for c in x:
		length += 1
		if c in types:
			append_child({"TYPE": "PODT_END", "VALUE": types[c]})

			break

		if c not in qualifiers and c not in types:
			length -= 1
			break

		append_child({"TYPE": "PODT", "VALUE": qualifiers[c]})

	return length

def handle_other(x, sym):
	other = {
			"TYPE": "OTHER",
			"VALUE": sym
		}

	print_indent(sym)

	append_child(other)

def handle_block_end(x, sym):
	global BLOCKS_DONE

	block = BLOCK_STACK.pop()

	print_indent("E")

	if block["LEVEL"] == 0:
		BLOCKS_DONE.append(block)

parser = [
		{
			"SYMBOLS":
				['N', 'I', 'X', "sr"],
			"HANDLE": handle_block_start
		},
		{
			"SYMBOLS":
				[str(x) for x in range(10)],
			"HANDLE": handle_string
		},
		{
			"SYMBOLS":
				["St", "Sa", "Sb", "Ss", "Si", "So", "Sd", "T_", "SB_", "S_"] + ["S%d_" % i for i in range(10) ],
			"HANDLE": handle_abbr
		},
		{
			"SYMBOLS":
				["P", "K", "c", "a"],
			"HANDLE": handle_podt
		},
		{
			"SYMBOLS":
				['E'],
			"HANDLE": handle_block_end
		},
		{
			"SYMBOLS":
				[],
			"HANDLE": handle_other
		}
	]

SLEVELS = []
SLEVEL_ANNOTS = {
			"S_" : 0,
			"S0_": 1,
			"S1_": 2,
			"S2_": 3,
			"S3_": 4,
			"S4_": 5,
			"S5_": 6,
			"S6_": 7,
			"S7_": 8,
			"S8_": 9,
			"S9_":10
		}

def insert_slevel(val):
	global SLEVELS

	SLEVELS.append(
			{
				"VALUE": val,
				"SLEVEL": len(SLEVELS) - 1
			})

def _print_demangled(block, slevel = None):
	global SUBSTITUTIONS
	global SLEVEL_BEGIN

	s = []

	if block["TYPE"] != "BLOCK":
		return block["VALUE"]

	if block["VALUE"] == "N":
		delim = "::"
		l = ""
		r = ""
	else:
		delim = ","
		l = "<"
		r = ">"

	reverse_print = ""
	end_print = ""
	for c in block["CHILDREN"]:
		if c["TYPE"] == "PODT":
			if c["VALUE"] == "*":
				end_print = " " + c["VALUE"]
			else:
				reverse_print = _print_demangled(c) + " " + reverse_print

			continue

		if (c["TYPE"] == "BLOCK"):
			# fill_slevels(s, delim)

			if c["VALUE"] == "I":
				s[-1] += _print_demangled(c, slevel)
				insert_slevel(delim.join(s))
			else:
				s.append(_print_demangled(c, slevel))

		elif c["TYPE"] == "ABBR":
			# print SLEVELS
			# print c["VALUE"]
			s.append(SLEVELS[SLEVEL_ANNOTS[c["VALUE"]]]["VALUE"])

			# print s
		elif c["TYPE"] == "STATIC_ABBR":
			s.append(reverse_print + c["VALUE"] +  end_print)
		else:
			s.append(reverse_print + c["VALUE"] +  end_print)

			insert_slevel(delim.join(s))

			if c["TYPE"] == "PODT_END":
				insert_slevel(delim.join(s) + "*")

			reverse_print = ""

			end_print = ""

	return l + delim.join(s) + r

def demangle(x):
	print x

	# Skip "_Z"
	x = x[2:]

	while len(x) > 0:
		for p in parser:
			sym = find_atomic(x, p["SYMBOLS"])

			# Try different atomic
			if sym is None:
				continue

			skip_len = p["HANDLE"](x, sym)

			if skip_len is not None:
				x = x[skip_len:]
			else:
				x = x[len(sym):]

			# Start searching from the beginning
			break

	s = []
	for block in BLOCKS_DONE:
		s.append(_print_demangled(block))

	return "%s\t%s(%s)" % (s[0], s[1], ", ".join(s[2:])) # .replace(",<", "<").replace("::<", "<")

if __name__ == "__main__":
	# print demangle("_ZN4Math13subtractExactImEENSt6__ndk19enable_ifIXsr11is_unsignedIT_EE5valueES3_E4typeES3_S3_")
	s = demangle("_ZNSt6__ndk16vectorINS_9sub_matchIPKcEENS_9allocatorIS4_EEE6assignIPS4_EENS_9enable_ifIXaasr21__is_forward_iteratorIT_EE5valuesr16is_constructibleIS4_NS_15iterator_traitsISB_E9referenceEEE5valueEvE4typeESB_SB_")
	print s
	# print SLEVELS
