#! /usr/bin/python
#
# The aglorithms in this file a word (such as a given name or surname) as
# input and return a 'phonetic skeleton' as output. A phonetic skeleton is a
# crude representation of the word which preserves only those elements which
# are likely to have a definite effect on the pronunciation of the word.
# Examples:
#
# Word       | Phonetic Skeleton
# David      | d#v#d
# still      | st#l
#
# In this example, all of the vowels have been replaced by hash signs and
# double letters have been changed to single letters.
#
# This is done using rule lists. A rule list is a series of substitutions
# which should be performed in order to turn a word into its phonetic skeleton.
# Each item in the list consists of a two-item array. The first member is an
# regular expression. The second member is a string which is the substitute for
# strings which match the regular expression.
#

#
# It might be useful to implement known phonetic systems. Here are some references:
# Soundexing and Geneology: http://www.avotaynu.com/soundex.htm
# Knuth's version: http://code.activestate.com/recipes/52213/
# Soundex Indexing System: http://www.archives.gov/research/census/soundex.html
# Python Implementation: http://rosettacode.org/wiki/Soundex#Python
#

import re

# These are the rules which have long been used in Fullname
# at Trinity College since the early 1990's. They were
# developed by David Chappell after he read Chaucer.
# It does fairly well on names of Western European origin.
fn_rules = [

	# These rules are not actually in the Perl implementation
	# because it was assumed that these steps would be performed
	# before it was called.
	[r'^(.+)$', lambda matchobj: matchobj.group(1).lower()],
	[r'[^a-z]', r''],

	# Change initial "Mc" (an abbreviation) to "Mac" (son of)
	[r'^mc', r'mac'],

	# Change initial "ps" (as in "Psalm") to "s"
	[r'ps', r's'],

	# caution to caushun
	[r'(.)tion', r'\1shun'],

    # Handle French "er" as in "centre", "theatre", etc.  While we
    # are at it, get "le" as in "little".
    [r'([^aeiouy])re$', r'\1er'],
    [r'([^aeiouyl])le$', r'\1el'],

    # The sequence "ph" has an "f" sound.
    [r'ph', r'f'],

    # A "x" at the begining of a word has a "z" sound.
    [r'^x', r'z'],

    # An "es" at the end of a word which has another vowel
    # is probably the same as "s".  In effect this rule makes 
    # "pates" and "pats", "cautions" and "cautiones" the same 
    # but not "les" and "ls".  (Yes, I know these are all silly
    # examples.)
    [r'(.[aeiouy][^aeiouy])es$', r'\1s'],

    # A "dj" or "dg" as in "knowledge" in the middle of a word sounds very much like "j".
    [r'(.)d[jg]', r'\1j'],
    [r'd[jg](.)', r'j\1'],

    # Words like "gnarled" are pronounced as "narled".
    # Also, "pneumatic" is pronounced "newmatic".
    [r'^[gp](n[aeiouy])', r'\1'],

    # A "g" and a "j" sound very much alike.  Change them all to "j".
    [r'g', r'j'],

    # Change "cz" to "tz" as in "czar" and "tzar".
    [r'cz', r'tz'],

    # A "z" after the first letter of a word most often has an "s" sound.
    # This should come after the "es" "s" ending rule because we
    # don't want "ez" changed to "s".  It should come after the "cz", "tz" rule.
	# Fixed 16 December 2011 to handle "Pizzoferrato" properly.
    #[r'(.)z', r'\1s'],
    [r'(.)z+', r'\1s'],

    # A "kw" followed by a vowel at the begining of a word, as in "kwick"
    # is more properly "qu" in English.  This one is for children.  Note that
    # this rule must come before the one which removes w's which are not
    # the first letter of the word.  It must also come before the rule which
    # changes "k" to "c".
    [r'^kw([aeiouy])', r'qu\1'],

    # A "w" not at the begining of a word frequently is
    # silent, so we will remove it.  This will mangle some
    # words but that doesn't really matter much.
    [r'(.)w', r'\1'],

    # If a word starts with "kn" followed by a vowel, the "k" is (almost) silent.
    # This helps "knight" and "night", "know" and "no" to come out the same.
    # This rule must come before the rule which changes "k" to "c".
    [r'^kn([aeiouy])', r'n\1'],

    # "k" most often sounds like "c", so convert it to "c".
    # Also change "ck" as in "truck" to "c".
    # We convert "k" to c" rather than the other way around 
    # because that would cause problems with "ch".
    [r'ck', r'c'],
    [r'k', r'c'],

    # The words "hole", "whole", "whore", "hoary", "when", "which" show that
    # it is hard to distinguish the sounds of leading "w", "h", and "wh".  We
    # will change them all to "wh".
    [r'^w([^h])', r'wh\1'],
    [r'^h(.)', r'wh\1'],

    # The sequence "tch" is almost indistinguishable from "ch".
    [r'tch', r'ch'],

    # Remove a trailing "e" if it follows a vowel and a consonant
    # or consonants since it probably only there to make the vowel long.
    # (Remember, we are not differentiating vowel sounds.)
    [r'([aeiouy][^aeiouy]+)e$', r'\1'],

	# Convert remaining vowels to pound signs. Note that "y" is a vowel
	# too except at the start of a word.
	[r'[aeiou]', r'#'],
	[r'(.)y', r'\1#'],

	# reduce repeated consonants or vowel marks to single instance
	[r'(.)\1+', r'\1'],
	]

# This is a new version of the rules which David Chappell developed
# in 2011 after he learned Russian. It is intended to do better than
# fn_rules[] on Slavic names.
experimental_rules = [

	# Convert to lower case
	[r'^(.+)$', lambda matchobj: matchobj.group(1).lower()],

	# Remove nonletters
	[r'[^a-z]', r''],

	# Change initial "Mc" (an abbreviation) to "Mac" (son of)
	[r'^mc', r'mac'],

	# Change initial "ps" (as in "Psalm") to "s"
	[r'ps', r's'],

    # Words like "gnarled" are pronounced as "narled".
    # Also, "pneumatic" is pronounced "newmatic".
    [r'^[gp](n[aeiouy])', r'\1'],

	# caution to caushun
	[r'(.)tion', r'\1shun'],

    # A "g" and a "j" sound very much alike.  Change them all to "j".
    [r'g', r'j'],

    # The sequence "ph" has an "f" sound.
	# "Stephan" -> "Stefan"
    [r'ph', r'f'],

	# And now Stefan -> Stevan and Smirnoff -> Smirnov
	[r'f+', r'v'],

    # A "x" at the begining of a word has a "z" sound.
    [r'^x', r'z'],

    # A "dj" or "dg" as in "knowledge" in the middle of a word sounds very much like "j".
    [r'(.)d[jg]', r'\1j'],
    [r'd[jg](.)', r'j\1'],

    # Change "cz" and "ts" to "tz" as in "tsar", "czar", and "tzar".
    [r'[ct]z', r'tz'],

    # If a word starts with "kn" followed by a vowel, the "k" is (almost) silent.
    # This helps "knight" and "night", "know" and "no" to come out the same.
    # This rule must come before the rule which changes "k" to "c".
    [r'^kn([aeiouy])', r'n\1'],

    # Handle French "er" as in "centre", "theatre", etc.  While we
    # are at it, get "le" as in "chaple".
    [r'([^aeiouy])re$', r'\1er'],
    [r'([^aeiouyl])le$', r'\1el'],

    # An "es" at the end of a word which has another vowel
    # is probably the same as "s".  In effect this rule makes 
    # "pates" and "pats", "cautions" and "cautiones" the same 
    # but not "les" and "ls".  (Yes, I know these are all silly
    # examples.)
    [r'(.[aeiouy][^aeiouy])es$', r'\1s'],

    # A "z" after the first letter of a word most often has an "s" sound.
    # This should come after the "es" "s" ending rule because we
    # don't want "ez" changed to "s".  It should come after the "cz", "tz" rule.
    [r'(.)z+', r'\1s'],

    # A "kw" followed by a vowel at the begining of a word, as in "kwick"
    # is more properly "qu" in English.  This one is for children.  Note that
    # this rule must come before the one which removes w's which are not
    # the first letter of the word.  It must also come before the rule which
    # changes "k" to "c".
    [r'^kw([aeiouy])', r'qu\1'],

    # A "w" not at the begining of a word frequently is
    # silent, so we will remove it.  This will mangle some
    # words but that doesn't really matter much.
    #[r'(.)w', r'\1'],

	# Use of "v" where other languages have a vowel
	# Evan -> Ian
	# Ivan -> Ian
	[r'[ei]v[ea](.)', r'I\1'],
    
	# Transliteration of Cyrillic letters
	[r'kh', r'k'],					# Mikhail to Mikail
	[r'([oe])vy?a$', r'\1v'],		# Smirnova, Smirnovya, Smirneva to Smirnov

    # "c" most often sounds like "k", so convert it to "k".
    # Also change "ck" as in "truck" to "k".
	# Chapel -> Kapel
    [r'ck', r'k'],
    [r'ch', r'k'],
	[r'c', r'k'],

    # The words "hole", "whole", "whore", "hoary", "when", "which" show that
    # it is hard to distinguish the sounds of leading "w", "h", and "wh".  We
    # will change them all to "wh".
    [r'^w([^h])', r'wh\1'],
    [r'^h(.)', r'wh\1'],

	# "ohn" (as in John, Cohn, Krohn) is almost pronounced "n"
	[r'ohn', r'on'],

    # The sequence "tch" is almost indistinguishable from "ch".
    [r'tch', r'ch'],

    # Remove a trailing "e" if it follows a vowel and a consonant
    # or consonants since it probably only there to make the vowel long.
    # (Remember, we are not differentiating vowel sounds.)
    [r'([aeiouy][^aeiouy]+)e$', r'\1'],

	# Divide initial vowels into groups ("u' remains itself)
	[r'^[jy][aeiou]', r'I'],		# soft vowels
	[r'^[ao]', r'A'],
	[r'^[ei]', r'I'],
	[r'^u', r'U'],

	# Unsoften remaining vowels
	[r'[yj]([aeiouy])', r'\1'],	

	# convert remaining vowels to pound signs
	#[r'[aeiouy]', r'#'],
	# Remove remaining vowels
	[r'[aeiouy]', r''],

	# reduce repeated consonants
	[r'(.)\1+', r'\1'],

	# reduce repeated vowel marks to single instance
	#[r'([AEIOU])#', r'\1'],
	]

# Compile all of the regular expressions.
for experimental_rule in experimental_rules:
	experimental_rule[0] = re.compile(experimental_rule[0])
for fn_rule in fn_rules:
	fn_rule[0] = re.compile(fn_rule[0])

# Convert a word to lower case and run it through
# the substitutions listed above.
def apply_rules(word, rules):
	for rule in rules:
		word = rule[0].sub(rule[1], word)
	return word

# Convert a word into a phonetic skeleton as Fullname did.
def fn_phonetic(word):
	return apply_rules(word, fn_rules)

# Convert a word into a phonetic skeleton using the new rules.
def experimental_phonetic(word):
	return apply_rules(word, experimental_rules)

if __name__ == "__main__":
	import sys

	if len(sys.argv) > 1:
		for word in sys.argv[1:]:
			print experimental_phonetic(word)
	else:
		def test_function(function, name1, name2, should_match):
			skel1 = function(name1)
			skel2 = function(name2)
			if should_match:
				if skel1 != skel2:
					print "Failure to match: %s (%s) and %s (%s)" % (name1, skel1, name2, skel2)
			else:
				if skel1 == skel2:
					print "Spurious match: %s (%s) and %s (%s)" % (name1, skel1, name2, skel2)
		
		def test_fn_phonetic(name1, name2, should_match):
			return test_function(fn_phonetic, name1, name2, should_match)	
	
		def test_experimental_phonetic(name1, name2, should_match):
			return test_function(experimental_phonetic, name1, name2, should_match)	
	
		test_fn_phonetic("Chappell", "Chaple", True)
		test_fn_phonetic("Maria", "Mary", True)
		test_fn_phonetic("Mariya", "Mary", True)
		test_fn_phonetic("John", "Ian", False)

		test_experimental_phonetic("John", "Ian", True)

